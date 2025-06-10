"""!
@file judge_pool.py
@brief Creates a relevance judgment file from a pool of documents.
@details Reads Pool.json and Docs_cleaned.json to generate JudgedPool.json.
         It attempts to automatically assess relevance based on keyword matching
         between the query and document content (title/abstract).
         This file is intended to be manually reviewed and updated.
@authors Magni && Testoni
@date 2024
"""

import json
from pathlib import Path
import sys
import re

# Determine project_root: assumes judge_pool.py is in JuriScan/Benchmark/
_current_file_path = Path(__file__).resolve()
project_root = _current_file_path.parent.parent 
sys.path.append(str(project_root))

# Define paths
POOL_INPUT_FILE = project_root / "GroundTruth" / "Pool.json"
JUDGED_OUTPUT_FILE = project_root / "GroundTruth" / "JudgedPool.json"
# DOCS_CONTENT_FILE = project_root / "WebScraping" / "results" / "Docs_cleaned.json" # This will be determined dynamically

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


def load_all_documents_content(docs_file_path):
    """!
    @brief Load all document contents from the specified JSON file.
    @param docs_file_path Path to the documents JSON file (e.g., Docs_cleaned.json).
    @return Dictionary of {doc_id: {doc_content_fields}} or None if error.
    """
    try:
        with open(docs_file_path, 'r', encoding='utf-8') as f:
            all_docs_data = json.load(f)
        # Ensure keys are strings if they are not already (though JSON keys are usually strings)
        return {str(k): v for k, v in all_docs_data.items()}
    except FileNotFoundError:
        print(f"ERROR: Documents content file not found at {docs_file_path}")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {docs_file_path}")
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

def create_judgment_file(pooled_data, all_docs_content, output_file_path):
    """!
    @brief Create and save the JudgedPool.json file with automatic relevance assessment.
    @param pooled_data Dictionary of pooled documents {query: [doc_ids]}.
    @param all_docs_content Dictionary of all document contents {doc_id: {fields}}.
    @param output_file_path Path to save the JudgedPool.json file.
    @details For each query, relevance of pooled documents is assessed using keyword matching.
    """
    if not pooled_data:
        print("No pooled data to process.")
        return
    if not all_docs_content:
        print("No document content available for relevance assessment. Cannot create judgments.")
        return

    judgments = {}
    for query_string, doc_ids in pooled_data.items():
        print(f"Processing query: {query_string[:100]}...")
        judgments[query_string] = {}
        query_keywords_for_log = extract_keywords_from_query(query_string) # For logging
        print(f"  Extracted keywords for query: {query_keywords_for_log}")

        for doc_id_str in doc_ids: # doc_ids from Pool.json should be strings
            doc_content = all_docs_content.get(doc_id_str)
            if doc_content:
                # Using a threshold of 0.5, meaning at least half of the unique query keywords must match.
                # Adjust this threshold as needed.
                # If extract_keywords_from_query returns an empty list, is_document_relevant will return 0.
                relevance_score = is_document_relevant(query_string, doc_content, keyword_match_threshold=0.5)
                judgments[query_string][doc_id_str] = relevance_score
                if relevance_score == 1:
                    print(f"    Doc ID {doc_id_str} judged RELEVANT for query.")
            else:
                judgments[query_string][doc_id_str] = 0 # Document content not found, assume not relevant
                print(f"    Warning: Content for Doc ID {doc_id_str} not found in Docs_cleaned.json. Marked as not relevant.")
    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(judgments, f, indent=2, ensure_ascii=False)
        print(f"Successfully created judgment file: {output_file_path}")
        print("Please review and update this file with actual relevance judgments.")
        print("Format: {query: {doc_id: 1 (relevant) or 0 (not relevant)}}")
    except IOError as e:
        print(f"Error writing judgment file to {output_file_path}: {e}")

if __name__ == "__main__":
    print(f"Running judge_pool.py from: {_current_file_path}")
    print(f"Project root set to: {project_root}")

    # Determine the actual path for the documents content file
    base_docs_dir = project_root / "WebScraping" / "results"
    
    all_documents = None
    actual_docs_file_path = None

    if not base_docs_dir.exists():
        print(f"ERROR: The directory for documents content does not exist: {base_docs_dir}")
    elif not base_docs_dir.is_dir():
        print(f"ERROR: The path for documents content is not a directory: {base_docs_dir}")
    else:
        print(f"Searching for documents content file in directory: {base_docs_dir}")
        possible_docs_filenames = ["Docs_cleaned.json", "docs_cleaned.json"]
        for filename_to_check in possible_docs_filenames:
            path_to_check = base_docs_dir / filename_to_check
            if path_to_check.exists() and path_to_check.is_file():
                actual_docs_file_path = path_to_check
                print(f"Found documents content file at: {actual_docs_file_path}")
                break
        
        if actual_docs_file_path:
            all_documents = load_all_documents_content(actual_docs_file_path)
        else:
            # This message will be printed if the directory exists but the file doesn't.
            print(f"ERROR: Documents content file not found in directory {base_docs_dir} with expected names like {possible_docs_filenames}.")
            
    pooled_docs = load_pooled_documents(POOL_INPUT_FILE)
    
    if pooled_docs and all_documents:
        create_judgment_file(pooled_docs, all_documents, JUDGED_OUTPUT_FILE)
    else:
        if not pooled_docs:
            print("Could not proceed: Pooled documents (Pool.json) not loaded.")
        # This consolidated message will appear if all_documents is None for any reason (dir missing, file missing)
        if not all_documents:
            print("Could not proceed: All documents content (e.g., Docs_cleaned.json) not loaded. Please check previous error messages for details.")
