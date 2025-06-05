import json
import time
import numpy as np
from pathlib import Path
import sys

# Add the project root to Python path so we can import SearchEngine
PROJECT_ROOT = Path(__file__).parent.parent  # Benchmark/benchmark.py -> root project
sys.path.insert(0, str(PROJECT_ROOT))

import lucene # Import lucene here for the getVMEnv check

# Attempt to import your search engine modules
try:
    # Using aliased imports from __init__.py for clarity
    from SearchEngine import (
        pylucene_search_documents,
        pylucene_create_index,
        pylucene_initialize_jvm,
        whoosh_search_documents,
        whoosh_create_or_get_index, # Assuming Whoosh index needs to be explicitly created/opened
        postgres_search
    )
    ENGINES_AVAILABLE = True
except ImportError as e:
    print(f"Error importing search engine modules: {e}")
    print("Please ensure paths are correct and SearchEngine package is importable.")
    ENGINES_AVAILABLE = False
    # Define placeholders if import fails, so the script doesn't crash immediately
    pylucene_search_documents = pylucene_create_index = pylucene_initialize_jvm = None
    whoosh_search_documents = whoosh_create_or_get_index = None
    postgres_search = None


# Define root path for JuriScan project
PROJECT_ROOT = Path(__file__).parent.parent  # Benchmark/benchmark.py -> root project

# Define index paths relative to the project root
PYLUCENE_INDEX_PATH = PROJECT_ROOT / "SearchEngine" / "index"
WHOOSH_INDEX_PATH = PROJECT_ROOT / "WhooshIndex"  # Secondo .gitignore è nella root
JSON_DOCS_FILE = PROJECT_ROOT / "WebScraping" / "results" / "Docs_cleaned.json"


def load_queries_from_uin(uin_file_path):
    """Loads queries from the uin.txt file."""
    queries = []
    try:
        with open(uin_file_path, 'r', encoding='utf-8') as f: # Added encoding
            lines = f.readlines()  # Leggi tutte le righe
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("Query:"):
                    # La query effettiva è sulla riga successiva
                    if i + 1 < len(lines):
                        query_text = lines[i+1].strip()
                        if query_text: # Assicurati che la riga della query non sia vuota
                            queries.append(query_text)
                        i += 1 # Salta la riga della query che abbiamo appena letto
                i += 1
    except FileNotFoundError:
        print(f"ERROR: uin.txt not found at {uin_file_path}")
    return queries

def load_ground_truth(ground_truth_file_path):
    """Loads ground truth from a JSON file."""
    try:
        with open(ground_truth_file_path, 'r') as f:
            ground_truth = json.load(f)
        return ground_truth
    except FileNotFoundError:
        print(f"Ground truth file not found: {ground_truth_file_path}")
        print("Please create it by manually judging pooled results.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {ground_truth_file_path}")
        return {}

def get_pylucene_results(query_string, searcher, ranking_type="BM25"):
    """Wrapper for PyLucene search."""
    if not pylucene_search_documents or not searcher:
        return []
    # Pass all field booleans as True for a broad search during benchmark
    results, _, _ = pylucene_search_documents(searcher, True, True, True, query_string, ranking_type)
    formatted_results = []
    if results:
        for hit in results.scoreDocs:
            # Correzione: usa searcher.storedFields().document(doc_id)
            doc = searcher.storedFields().document(hit.doc)
            formatted_results.append({"id": doc.get("id"), "score": hit.score})
    return formatted_results

def get_whoosh_results(query_string, ix, ranking_type="BM25F"):
    """Wrapper for Whoosh search."""
    if not whoosh_search_documents or not ix:
        return []
    # Pass all field booleans as True for a broad search
    results = whoosh_search_documents(str(WHOOSH_INDEX_PATH), query_string, True, True, True, ranking_type)
    return [{"id": r[0], "score": r[5]} for r in results]

def get_postgres_results(query_string, ranking_type="ts_rank_cd"):
    """Wrapper for PostgreSQL search."""
    if not postgres_search:
        return []
    # Pass all field booleans as True for a broad search
    results = postgres_search(query_string, True, True, True, ranking_type)
    return [{"id": str(r[0]), "score": r[6]} for r in results] # Ensure ID is string, score/rank at index 6


def calculate_precision_at_k(retrieved_ids, relevant_ids_set, k):
    """Calculates Precision@k."""
    if k == 0: return 0.0
    top_k_retrieved = retrieved_ids[:k]
    relevant_in_top_k = len([doc_id for doc_id in top_k_retrieved if doc_id in relevant_ids_set])
    return relevant_in_top_k / k

def calculate_recall_at_k(retrieved_ids, relevant_ids_set, k, total_relevant_in_pool):
    """Calculates Recall@k relative to the judged pool."""
    if total_relevant_in_pool == 0:
        return 1.0 if not relevant_ids_set else 0.0 # Perfect recall if no relevant docs exist
    top_k_retrieved = retrieved_ids[:k]
    relevant_in_top_k = len([doc_id for doc_id in top_k_retrieved if doc_id in relevant_ids_set])
    return relevant_in_top_k / total_relevant_in_pool

def calculate_average_precision(retrieved_ids, relevant_ids_set):
    """Calculates Average Precision (AP)."""
    if not relevant_ids_set:
        return 0.0
    
    hits = 0
    sum_precisions = 0.0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids_set:
            hits += 1
            sum_precisions += hits / (i + 1)
            
    return sum_precisions / len(relevant_ids_set) if relevant_ids_set else 0.0


def run_benchmark():
    """Main benchmarking function."""
    if not ENGINES_AVAILABLE:
        print("Search engine modules not available. Exiting benchmark.")
        return

    uin_file = PROJECT_ROOT / "uin.txt"  # Il file uin.txt è nella root
    ground_truth_file = PROJECT_ROOT / "GroundTruth" / "Pool.json"  # Assumi che sia in Benchmark/GroundTruth

    queries = load_queries_from_uin(uin_file)
    ground_truth = load_ground_truth(ground_truth_file)

    if not queries:
        print("No queries found. Exiting.")
        return
    if not ground_truth:
        print("No ground truth loaded. Exiting. Please create ground_truth.json.")
        return

    # Initialize PyLucene Searcher
    pylucene_searcher = None
    if pylucene_create_index and pylucene_initialize_jvm:
        try:
            # Ensure JVM is initialized before creating index.
            # create_index in Pylucene.py should also call initialize_jvm,
            # but calling it here ensures it's done if create_index doesn't.
            pylucene_initialize_jvm()
            _, pylucene_searcher = pylucene_create_index() # This uses the path defined in Pylucene.py
            if pylucene_searcher:
                print("PyLucene Searcher initialized successfully.")
            else:
                print("Failed to initialize PyLucene searcher from create_index.")
        except Exception as e:
            print(f"Error initializing PyLucene: {e}")
            import traceback
            traceback.print_exc()
            pylucene_searcher = None
    
    # Initialize Whoosh Index
    whoosh_ix = None
    if whoosh_create_or_get_index:
        try:
            # Ensure the Whoosh index directory exists or can be created
            WHOOSH_INDEX_PATH.mkdir(parents=True, exist_ok=True)
            whoosh_ix = whoosh_create_or_get_index(str(WHOOSH_INDEX_PATH), str(JSON_DOCS_FILE))
            if whoosh_ix:
                print(f"Whoosh Index opened/created successfully at {WHOOSH_INDEX_PATH}")
            else:
                print(f"Failed to initialize Whoosh Index at {WHOOSH_INDEX_PATH}")
        except Exception as e:
            print(f"Error initializing Whoosh Index: {e}")
            import traceback
            traceback.print_exc()
            whoosh_ix = None


    engines = {}
    if pylucene_searcher:
        engines["PyLucene"] = lambda q: get_pylucene_results(q, pylucene_searcher)
    else:
        print("PyLucene engine not available for benchmarking.")
        
    if whoosh_ix:
        engines["Whoosh"] = lambda q: get_whoosh_results(q, whoosh_ix)
    else:
        print("Whoosh engine not available for benchmarking.")

    if postgres_search: # Postgres doesn't need explicit index opening here
        engines["PostgreSQL"] = lambda q: get_postgres_results(q)
    else:
        print("PostgreSQL engine not available for benchmarking.")

    if not engines:
        print("No search engines available for benchmarking. Exiting.")
        return
        
    k_values = [5, 10, 20] # For P@k and R@k

    all_results = {}

    for engine_name, search_func in engines.items():
        # Removed redundant availability checks here as they are handled during engine setup
        print(f"\nBenchmarking Engine: {engine_name}")
        engine_metrics = {
            "P@k": {k: [] for k in k_values},
            "R@k": {k: [] for k in k_values},
            "AP": [],
            "ResponseTimes": []
        }

        for query_idx, query_string in enumerate(queries):
            print(f"  Query {query_idx + 1}/{len(queries)}: {query_string[:50]}...")
            
            # query_ground_truth è una lista di ID di documenti dal Pool.json
            # o None se la query non è in Pool.json
            pooled_doc_ids_for_query = ground_truth.get(query_string) 
            
            if pooled_doc_ids_for_query is None:
                print(f"    Warning: No ground truth (pooled documents) for query: {query_string}")
                relevant_ids_set = set()
                total_relevant_in_pool = 0
            elif not isinstance(pooled_doc_ids_for_query, list):
                print(f"    Warning: Ground truth for query '{query_string}' is not a list, skipping. Found: {type(pooled_doc_ids_for_query)}")
                relevant_ids_set = set()
                total_relevant_in_pool = 0
            else:
                # Opzione 1: Tutti i documenti nel pool per questa query sono considerati rilevanti.
                relevant_ids_set = set(str(doc_id) for doc_id in pooled_doc_ids_for_query) # Assicura che gli ID siano stringhe
                total_relevant_in_pool = len(relevant_ids_set)
                if total_relevant_in_pool == 0:
                    print(f"    Note: Query '{query_string}' is in Pool.json but has an empty list of documents.")


            start_time = time.time()
            retrieved_results = search_func(query_string) # List of {"id": str, "score": float}
            end_time = time.time()
            engine_metrics["ResponseTimes"].append(end_time - start_time)

            retrieved_ids = [res["id"] for res in retrieved_results]

            for k in k_values:
                p_at_k = calculate_precision_at_k(retrieved_ids, relevant_ids_set, k)
                engine_metrics["P@k"][k].append(p_at_k)
                
                r_at_k = calculate_recall_at_k(retrieved_ids, relevant_ids_set, k, total_relevant_in_pool)
                engine_metrics["R@k"][k].append(r_at_k)

            ap = calculate_average_precision(retrieved_ids, relevant_ids_set)
            engine_metrics["AP"].append(ap)

        # Calculate averages
        avg_metrics = {"MAP": np.mean(engine_metrics["AP"]) if engine_metrics["AP"] else 0.0,
                       "AvgResponseTime": np.mean(engine_metrics["ResponseTimes"]) if engine_metrics["ResponseTimes"] else 0.0}
        for k in k_values:
            avg_metrics[f"MeanP@{k}"] = np.mean(engine_metrics["P@k"][k]) if engine_metrics["P@k"][k] else 0.0
            avg_metrics[f"MeanR@{k}"] = np.mean(engine_metrics["R@k"][k]) if engine_metrics["R@k"][k] else 0.0
        
        all_results[engine_name] = avg_metrics
        print(f"  Average Metrics for {engine_name}: {avg_metrics}")

    print("\n--- Overall Benchmark Summary ---")
    for engine_name, metrics in all_results.items():
        print(f"Engine: {engine_name}")
        for metric_name, value in metrics.items():
            print(f"  {metric_name}: {value:.4f}")
    
    # You can save `all_results` to a file or further process it.
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nBenchmark results saved to {output_file}")


if __name__ == "__main__":
    # The JVM initialization is now primarily handled within the PyLucene setup block
    # in run_benchmark(). A general check here can be kept if desired, but might be redundant.
    if ENGINES_AVAILABLE and pylucene_initialize_jvm:
        try:
            # This call is more of a safeguard.
            # If PyLucene is used, initialize_jvm() inside Pylucene.py's create_index
            # or the explicit call in run_benchmark() should handle it.
            if not lucene.getVMEnv():
                 pylucene_initialize_jvm()
                 print("JVM initialized by __main__ block.")
        except Exception as e:
            print(f"Could not initialize JVM for PyLucene in __main__ (may already be initialized or error): {e}")

    run_benchmark()
