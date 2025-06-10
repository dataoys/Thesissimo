"""!
@file judge_pool.py
@brief Creates a relevance judgment file from a pool of documents.
@details Reads Pool.json and fetches document content from PostgreSQL to generate 
         JudgedPool.json. It attempts to automatically assess relevance based on 
         keyword matching between the query and document content (title/abstract).
         This file is intended to be manually reviewed and updated.
@authors Magni && Testoni
@date 2024
"""

import json
from pathlib import Path
import sys
import re
import traceback

# Determine project_root: assumes judge_pool.py is in JuriScan/Benchmark/
_current_file_path = Path(__file__).resolve()
project_root = _current_file_path.parent.parent 
sys.path.append(str(project_root))

# Define paths
POOL_INPUT_FILE = project_root / "GroundTruth" / "Pool.json"
JUDGED_OUTPUT_FILE = project_root / "GroundTruth" / "JudgedPool.json"

# Attempt to import PostgreSQL connection utilities
try:
    # Adjusted import path and function name based on your PostgresQuery.py
    from Queries.PostgresQuery import dbConn as postgres_connect_db 
    POSTGRES_UTILS_AVAILABLE = True
    print("Successfully imported PostgreSQL utility 'dbConn' as 'postgres_connect_db' from Queries.PostgresQuery.")
except ImportError as e:
    print("--------------------------------------------------------------------------------")
    print(f"IMPORTANT WARNING: Could not import `dbConn` from `Queries.PostgresQuery` (Error: {e}).")
    print("This script will use a placeholder function, and database operations WILL FAIL.")
    print("Please ensure `Queries/PostgresQuery.py` exists and `dbConn` is defined correctly.")
    print("Also, ensure `Queries` directory has an `__init__.py` file if it's treated as a package.")
    print("--------------------------------------------------------------------------------")
    POSTGRES_UTILS_AVAILABLE = False
    
    def postgres_connect_db():
        print("********************************************************************************")
        print("Placeholder `postgres_connect_db` called because import failed.")
        print("ACTION REQUIRED: Fix the import `from Queries.PostgresQuery import dbConn`.")
        print("********************************************************************************")
        return None

# --- Helper function to extract keywords from query ---
def extract_keywords_from_query(query_string):
    """
    Extracts potential keywords from a query string.
    Removes common field specifiers and boolean operators.
    Handles quoted phrases as single keywords.
    """
    # Remove field specifiers like title:, abstract:, corpus:
    query_cleaned = re.sub(r'\b(title|abstract|corpus|content):', '', query_string, flags=re.IGNORECASE)
    
    # Extract quoted phrases
    phrases = re.findall(r'"([^"]+)"', query_cleaned)
    
    # Remove quoted phrases from query to process remaining words
    query_no_phrases = re.sub(r'"[^"]+"', '', query_cleaned)
    
    # Tokenize remaining words and filter out common operators and short words
    words = re.findall(r'\b\w+\b', query_no_phrases.lower())
    
    # Define common operators/stopwords to ignore (can be expanded)
    operators_stopwords = {'and', 'or', 'not', 'the', 'a', 'is', 'of', 'in', 'to', 'for'}
    
    keywords = [word for word in words if word not in operators_stopwords and len(word) > 1]
    
    # Add extracted phrases (as lowercase)
    keywords.extend([phrase.lower() for phrase in phrases])
    
    return list(set(keywords)) # Return unique keywords

# --- Relevance Assessment Function ---
def is_document_relevant(query_string, doc_data, keyword_match_threshold=0.5):
    """
    Determines if a document is relevant to a query based on keyword matching.
    Args:
        query_string (str): The search query.
        doc_data (dict): Dictionary containing document data (e.g., 'title', 'abstract', 'content').
        keyword_match_threshold (float): Minimum fraction of query keywords that must be found.
                                         If 0, any match makes it relevant. If 1, all must match.
    Returns:
        int: 1 if relevant, 0 otherwise.
    """
    if not doc_data:
        return 0

    query_keywords = extract_keywords_from_query(query_string)
    if not query_keywords: # No keywords to match
        return 0

    doc_text = ""
    if 'title' in doc_data and doc_data['title']:
        doc_text += str(doc_data['title']).lower() + " "
    if 'abstract' in doc_data and doc_data['abstract']:
        doc_text += str(doc_data['abstract']).lower() + " "
    # Fallback to 'content' if abstract is empty or not present
    if not (doc_data.get('abstract')) and 'content' in doc_data and doc_data['content']:
         doc_text += str(doc_data['content']).lower() + " "

    if not doc_text.strip(): # No document text to search in
        return 0

    matched_keywords_count = 0
    for keyword in query_keywords:
        # For phrases, check exact match. For words, check if word is present.
        if ' ' in keyword: # It's a phrase
            if keyword in doc_text:
                matched_keywords_count += 1
        elif re.search(r'\b' + re.escape(keyword) + r'\b', doc_text): # Whole word match
            matched_keywords_count += 1
    
    if not query_keywords: # Avoid division by zero if query had no usable keywords
        return 0

    # Relevance condition: e.g., at least keyword_match_threshold percent of query keywords found
    # Or simply if any keyword is found (matched_keywords_count > 0)
    # For a stricter approach: if all keywords are found
    # if matched_keywords_count == len(query_keywords):
    #    return 1
    
    # Using a threshold:
    if (matched_keywords_count / len(query_keywords)) >= keyword_match_threshold:
        return 1
        
    return 0

def get_document_content_from_postgres(doc_id, conn):
    """!
    @brief Fetches document content (title, abstract, corpus) from PostgreSQL.
    @param doc_id The ID of the document to fetch.
    @param conn Active PostgreSQL database connection object.
    @return Dictionary {'title': <title>, 'abstract': <abstract_or_content>} or None if error/not found.
    @details Assumes a table named 'DOCS' with columns 'id', 'title', 'abstract', 'corpus'.
             Adjust table and column names as per your schema if different.
    """
    if not conn:
        print(f"No database connection available to fetch doc ID {doc_id}.")
        return None
    
    content = {'title': None, 'abstract': None}
    try:
        with conn.cursor() as cur:
            # Adjusted SQL query for DOCS table and relevant text fields
            sql_query = """
                SELECT title, abstract, corpus 
                FROM DOCS 
                WHERE id = %s;
            """
            cur.execute(sql_query, (int(doc_id),)) # Assuming doc_id from pool is string, convert to int for DB
            record = cur.fetchone()
            if record:
                title, abstract_val, corpus_val = record
                content['title'] = title
                # Choose the best available text for 'abstract' field for relevance check
                # Prioritize abstract, then corpus
                if abstract_val:
                    content['abstract'] = abstract_val
                elif corpus_val:
                    content['abstract'] = corpus_val # Use corpus if abstract is empty
                else:
                    content['abstract'] = "" # Ensure it's a string
                return content
            else:
                print(f"    Document ID {doc_id} not found in PostgreSQL.")
                return None
    except Exception as e:
        print(f"Error fetching document ID {doc_id} from PostgreSQL: {e}")
        traceback.print_exc()
        return None

def load_pooled_documents(pool_file_path):
    """!
    @brief Load pooled document IDs from Pool.json.
    @param pool_file_path Path to the Pool.json file.
    @return Dictionary of {query_string: [doc_id1, doc_id2, ...]} or None if error.
    """
    try:
        with open(pool_file_path, 'r', encoding='utf-8') as f:
            pooled_data = json.load(f)
        return pooled_data
    except FileNotFoundError:
        print(f"ERROR: Pool file not found at {pool_file_path}")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {pool_file_path}")
        return None

def create_judgment_file(pooled_data, output_file_path):
    """!
    @brief Create and save the JudgedPool.json file with automatic relevance assessment
           using content fetched from PostgreSQL.
    @param pooled_data Dictionary of pooled documents {query: [doc_ids]}.
    @param output_file_path Path to save the JudgedPool.json file.
    @details For each query, relevance of pooled documents is assessed using keyword matching
             against content (title/abstract) fetched from PostgreSQL.
    """
    if not pooled_data:
        print("No pooled data to process.")
        return
    
    if not POSTGRES_UTILS_AVAILABLE: # Check if the import itself was successful
        print("PostgreSQL utilities (dbConn) could not be imported. Cannot fetch document content.")
        return

    db_conn = None
    try:
        db_conn = postgres_connect_db()
        if not db_conn:
            print("Failed to connect to PostgreSQL. Cannot create judgments.")
            return

        judgments = {}
        for query_string, doc_ids in pooled_data.items():
            print(f"Processing query: {query_string[:100]}...")
            judgments[query_string] = {}
            query_keywords_for_log = extract_keywords_from_query(query_string)
            print(f"  Extracted keywords for query: {query_keywords_for_log}")

            for doc_id_str in doc_ids: 
                doc_content_from_db = get_document_content_from_postgres(doc_id_str, db_conn)
                
                if doc_content_from_db:
                    relevance_score = is_document_relevant(query_string, doc_content_from_db, keyword_match_threshold=0.5)
                    judgments[query_string][doc_id_str] = relevance_score
                    if relevance_score == 1:
                        print(f"    Doc ID {doc_id_str} judged RELEVANT for query.")
                else:
                    # If content couldn't be fetched (e.g., doc not in DB or DB error)
                    judgments[query_string][doc_id_str] = 0 
                    print(f"    Warning: Content for Doc ID {doc_id_str} could not be fetched from PostgreSQL or not found. Marked as not relevant.")
        
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(judgments, f, indent=2, ensure_ascii=False)
        print(f"Successfully created judgment file: {output_file_path}")
        print("Please review and update this file with actual relevance judgments.")
        print("Format: {query: {doc_id: 1 (relevant) or 0 (not relevant)}}")

    except Exception as e:
        print(f"An error occurred during judgment file creation: {e}")
        traceback.print_exc()
    finally:
        if db_conn:
            # Directly close the connection object from dbConn()
            try:
                db_conn.close()
                print("PostgreSQL connection closed.")
            except Exception as e:
                print(f"Error closing PostgreSQL connection: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    print(f"Running judge_pool.py from: {_current_file_path}")
    print(f"Project root set to: {project_root}")
            
    pooled_docs = load_pooled_documents(POOL_INPUT_FILE)
    
    if pooled_docs:
        # No longer loads all_documents from a file
        create_judgment_file(pooled_docs, JUDGED_OUTPUT_FILE)
    else:
        if not pooled_docs:
            print("Could not proceed: Pooled documents (Pool.json) not loaded.")
