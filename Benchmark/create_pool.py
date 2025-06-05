import json
from pathlib import Path
import lucene # Import lucene here for the getVMEnv check
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.search import IndexSearcher
from java.nio.file import Paths
import sys
import traceback

# Determine project_root: assumes create_pool.py is in JuriScan/Benchmark/
_current_file_path = Path(__file__).resolve()
# Assuming structure /root/JuriScan/Benchmark/create_pool.py
# then project_root should be /root/JuriScan
project_root = _current_file_path.parent.parent
sys.path.append(str(project_root))

# Import whoosh.index functions directly
try:
    from whoosh.index import open_dir as whoosh_open_dir_lib, EmptyIndexError as WhooshEmptyIndexError_lib # Renamed for clarity
    WHOOSH_LIB_AVAILABLE = True
    print("Whoosh library (open_dir, EmptyIndexError) imported successfully from whoosh.index.")
except ImportError:
    print("Whoosh library (whoosh.index) not found. Whoosh functionality will be disabled.")
    WHOOSH_LIB_AVAILABLE = False
    whoosh_open_dir_lib = None
    WhooshEmptyIndexError_lib = None


# Attempt to import your search engine modules from SearchEngine package
try:
    from SearchEngine import (
        pylucene_search_documents,
        pylucene_initialize_jvm,
        whoosh_search_documents, 
        postgres_search
    )
    ENGINES_MODULES_AVAILABLE = True
    print("Successfully imported modules from SearchEngine package.")
    if whoosh_search_documents:
        print("SearchEngine.whoosh_search_documents (your custom function) imported successfully.")
    else:
        print("SearchEngine.whoosh_search_documents (your custom function) is None after import attempt from SearchEngine package.")

except ImportError as e:
    print(f"Error importing SearchEngine modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print("Please ensure JuriScan directory is in PYTHONPATH or script is run correctly.")
    ENGINES_MODULES_AVAILABLE = False
    pylucene_search_documents = pylucene_initialize_jvm = None
    whoosh_search_documents = None 
    postgres_search = None

# Define root path for JuriScan project
PROJECT_ROOT = project_root 

# Define index paths and output file path
PYLUCENE_INDEX_DIR = PROJECT_ROOT / "SearchEngine" / "index"
WHOOSH_INDEX_DIR = PROJECT_ROOT / "SearchEngine" / "WhooshIndex"
UIN_FILE_PATH = PROJECT_ROOT / "uin.txt"
POOL_OUTPUT_DIR = PROJECT_ROOT / "GroundTruth"
POOL_JSON_OUTPUT_FILE = POOL_OUTPUT_DIR / "Pool.json"

# Number of top results to fetch from each engine for pooling
TOP_N_FOR_POOLING = 20

# Define ranking types for each engine
PYLUCENE_RANKING_TYPES = ["BM25", "TFIDF"] # "TFIDF" will map to ClassicSimilarity in Pylucene.py
WHOOSH_RANKING_TYPES = ["BM25F", "TF_IDF"]
POSTGRES_RANKING_TYPES = ["ts_rank", "ts_rank_cd"]


def load_queries_from_uin(uin_file_path):
    """Loads queries from the uin.txt file."""
    queries = []
    try:
        with open(uin_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("Query:"):
                    if i + 1 < len(lines):
                        query_text = lines[i+1].strip()
                        if query_text:
                            queries.append(query_text)
                        i += 1 
                i += 1
    except FileNotFoundError:
        print(f"ERROR: uin.txt not found at {uin_file_path}")
    return queries

def get_pylucene_top_n_ids(query_string, searcher, n=TOP_N_FOR_POOLING, ranking_type="BM25"):
    """Wrapper for PyLucene search to get top N document IDs."""
    if not pylucene_search_documents or not searcher:
        return []
    try:
        results, _, _ = pylucene_search_documents(searcher, True, True, True, query_string, ranking_type)
        doc_ids = []
        if results:
            for i, hit in enumerate(results.scoreDocs):
                if i >= n:
                    break
                doc = searcher.storedFields().document(hit.doc)
                doc_ids.append(str(doc.get("id")))
        return doc_ids
    except Exception as e:
        print(f"Error during PyLucene search for query '{query_string}': {e}")
        traceback.print_exc()
        return []


def get_whoosh_top_n_ids(query_string, ix_path_str, n=TOP_N_FOR_POOLING, ranking_type="BM25F"):
    """Wrapper for Whoosh search to get top N document IDs using an existing index."""
    if not whoosh_search_documents: 
        print("SearchEngine.whoosh_search_documents (custom function) not available in get_whoosh_top_n_ids.")
        return []
    try:
        results = whoosh_search_documents(ix_path_str, query_string, True, True, True, ranking_type)
        return [str(r[0]) for r in results[:n]]
    except WhooshEmptyIndexError_lib: # Use the aliased import
        print(f"Whoosh index at {ix_path_str} is empty or invalid (caught by get_whoosh_top_n_ids).")
        return []
    except Exception as e:
        print(f"Error searching Whoosh index at {ix_path_str} for query '{query_string}': {e}")
        traceback.print_exc()
        return []

def get_postgres_top_n_ids(query_string, n=TOP_N_FOR_POOLING, ranking_type="ts_rank_cd"):
    """Wrapper for PostgreSQL search to get top N document IDs."""
    if not postgres_search:
        return []
    try:
        results = postgres_search(query_string, True, True, True, ranking_type)
        return [str(r[0]) for r in results[:n]]
    except Exception as e:
        print(f"Error during PostgreSQL search for query '{query_string}': {e}")
        traceback.print_exc()
        return []

def create_relevance_pool():
    """
    Reads queries, runs them on all search engines using EXISTING indices with multiple ranking types,
    pools top N results, and saves them to Pool.json for manual relevance judgment.
    """
    if not ENGINES_MODULES_AVAILABLE:
        print("SearchEngine modules not available. Cannot create pool.")
        return

    queries = load_queries_from_uin(UIN_FILE_PATH)
    if not queries:
        print(f"No queries found in {UIN_FILE_PATH}. Exiting.")
        return

    # Initialize PyLucene Searcher from EXISTING index
    pylucene_searcher = None
    if pylucene_initialize_jvm and pylucene_search_documents:
        try:
            pylucene_initialize_jvm()
            print(f"Attempting to open existing PyLucene index at: {PYLUCENE_INDEX_DIR}")
            if not PYLUCENE_INDEX_DIR.exists() or not PYLUCENE_INDEX_DIR.is_dir():
                print(f"PyLucene index directory does not exist: {PYLUCENE_INDEX_DIR}")
            else:
                directory = FSDirectory.open(Paths.get(str(PYLUCENE_INDEX_DIR)))
                if DirectoryReader.indexExists(directory):
                    reader = DirectoryReader.open(directory)
                    pylucene_searcher = IndexSearcher(reader)
                    print("PyLucene Searcher opened successfully from existing index.")
                else:
                    print(f"No valid PyLucene index found at {PYLUCENE_INDEX_DIR}. Please create it first.")
        except Exception as e:
            print(f"Error opening existing PyLucene index: {e}")
            traceback.print_exc()

    # Verify Whoosh Index
    whoosh_index_verified = False
    print("\n--- Whoosh Index Verification (in create_pool.py) ---")
    if WHOOSH_LIB_AVAILABLE:
        print("Whoosh library (whoosh_open_dir_lib) is available.")
        # Check if your custom search function from SearchEngine.Whoosh is available
        if 'whoosh_search_documents' in globals() and whoosh_search_documents is not None:
            print("Your custom SearchEngine.whoosh_search_documents function is available.")
            print(f"Verifying Whoosh index at path: {WHOOSH_INDEX_DIR}")
            if WHOOSH_INDEX_DIR.exists():
                print(f"Directory {WHOOSH_INDEX_DIR} exists.")
                if WHOOSH_INDEX_DIR.is_dir():
                    print(f"{WHOOSH_INDEX_DIR} is a directory.")
                    try:
                        # Attempt to open the index to see if it's valid
                        print(f"Attempting to open Whoosh index with whoosh_open_dir_lib: {str(WHOOSH_INDEX_DIR)}")
                        temp_ix = whoosh_open_dir_lib(str(WHOOSH_INDEX_DIR)) # Use aliased import
                        print(f"Successfully opened Whoosh index: {temp_ix}")
                        doc_count = temp_ix.doc_count()
                        if doc_count > 0:
                            print(f"Whoosh index at {WHOOSH_INDEX_DIR} is valid and contains {doc_count} documents.")
                            whoosh_index_verified = True
                        else:
                            print(f"Whoosh index at {WHOOSH_INDEX_DIR} is EMPTY (0 documents). Please ensure it's populated by running SearchEngine/Whoosh.py.")
                        temp_ix.close()
                    except WhooshEmptyIndexError_lib: # Use the aliased import
                         print(f"Whoosh index at {WHOOSH_INDEX_DIR} is reported as EMPTY by Whoosh during open_dir. Please ensure it's populated by running SearchEngine/Whoosh.py.")
                    except Exception as e:
                        print(f"Error during Whoosh index verification (e.g., not a valid index, permissions): {e}")
                        traceback.print_exc()
                else:
                    print(f"Path {WHOOSH_INDEX_DIR} is not a directory.")
            else:
                print(f"Whoosh index directory does not exist: {WHOOSH_INDEX_DIR}. Please create it first by running SearchEngine/Whoosh.py.")
        else:
            print("Your custom SearchEngine.whoosh_search_documents function is NOT available (was None or not in globals).")
    else:
        print("Whoosh library (whoosh.index open_dir) itself is not available (import failed).")
    print(f"Whoosh index verified status (in create_pool.py): {whoosh_index_verified}")
    print("--- End Whoosh Index Verification ---\n")


    pooled_results = {}

    for query_idx, query_string in enumerate(queries):
        print(f"\nProcessing Query {query_idx + 1}/{len(queries)}: {query_string[:60]}...")
        
        unique_doc_ids_for_query = set()

        # PyLucene
        if pylucene_searcher:
            for rank_type in PYLUCENE_RANKING_TYPES:
                print(f"  Querying PyLucene with {rank_type} ranking...")
                pyl_ids = get_pylucene_top_n_ids(query_string, pylucene_searcher, ranking_type=rank_type)
                unique_doc_ids_for_query.update(pyl_ids)
                print(f"    PyLucene ({rank_type}) returned {len(pyl_ids)} IDs.")
        else:
            print("  PyLucene searcher not available for this query (ensure index exists and is valid).")

        # Whoosh
        if whoosh_index_verified: 
            for rank_type in WHOOSH_RANKING_TYPES:
                print(f"  Querying Whoosh with {rank_type} ranking...")
                wh_ids = get_whoosh_top_n_ids(query_string, str(WHOOSH_INDEX_DIR), ranking_type=rank_type)
                unique_doc_ids_for_query.update(wh_ids)
                print(f"    Whoosh ({rank_type}) returned {len(wh_ids)} IDs.")
        else:
            print("  Whoosh index not verified or search function not available for this query.")
            
        # PostgreSQL
        if postgres_search:
            for rank_type in POSTGRES_RANKING_TYPES:
                print(f"  Querying PostgreSQL with {rank_type} ranking...")
                pg_ids = get_postgres_top_n_ids(query_string, ranking_type=rank_type)
                unique_doc_ids_for_query.update(pg_ids)
                print(f"    PostgreSQL ({rank_type}) returned {len(pg_ids)} IDs.")
        else:
            print("  PostgreSQL search function not available for this query.")
            
        pooled_results[query_string] = sorted(list(unique_doc_ids_for_query))
        print(f"  Total unique IDs pooled for this query: {len(pooled_results[query_string])}")

    # Ensure the output directory exists
    POOL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save the pooled results
    try:
        with open(POOL_JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(pooled_results, f, indent=2, ensure_ascii=False)
        print(f"\nPooled document IDs saved to: {POOL_JSON_OUTPUT_FILE}")
        print("You can now manually review this file and create a new JSON file with relevance judgments.")
        print("The format for the judged file should be (e.g., GroundTruth/JudgedPool.json): ")
        print("""
        {
            "query text from uin.txt": {
                "doc_id_1": 1,  // 1 for relevant, 0 for not relevant
                "doc_id_2": 0,
                ...
            },
            "... another query ...": { ... }
        }
        """)
    except IOError as e:
        print(f"Error writing pooled results to {POOL_JSON_OUTPUT_FILE}: {e}")


if __name__ == "__main__":
    print(f"Running create_pool.py from: {_current_file_path}")
    print(f"Project root set to: {project_root}")
    print(f"Python sys.path includes: {project_root}")

    if ENGINES_MODULES_AVAILABLE and pylucene_initialize_jvm:
        try:
            if not lucene.getVMEnv():
                 pylucene_initialize_jvm()
                 print("JVM initialized by create_pool.py __main__ block.")
            else:
                # Ensure thread is attached even if VM is already initialized
                env = lucene.getVMEnv()
                env.attachCurrentThread()
                print("JVM was already initialized. Attached current thread.")

        except Exception as e:
            print(f"Could not initialize/attach JVM for PyLucene in __main__: {e}")
            traceback.print_exc()
    
    create_relevance_pool()

