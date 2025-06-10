"""!
@file benchmark.py
@brief Main benchmarking script for evaluating search engine performance
@details Implements comprehensive evaluation of PyLucene, Whoosh, and PostgreSQL engines
         using precision, recall, MAP metrics and generates visualization plots
@author Magni && Testoni
@date 2025
"""

import numpy as np
from pathlib import Path
import sys
import seaborn as sns
import matplotlib.pyplot as plt
import json 
import time #response time measurement
import traceback # Added for error handling

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
        whoosh_create_or_get_index, 
        postgres_search
    )
    # Imports needed for opening indexes directly if create_or_get_index is not sufficient
    from org.apache.lucene.store import FSDirectory
    from org.apache.lucene.index import DirectoryReader
    from org.apache.lucene.search import IndexSearcher
    from java.nio.file import Paths as JavaPaths # Renamed to avoid conflict with pathlib.Path
    
    # Import whoosh.index functions directly for opening index
    try:
        from whoosh.index import open_dir as whoosh_open_dir_lib, EmptyIndexError as WhooshEmptyIndexError_lib
        WHOOSH_LIB_AVAILABLE = True
    except ImportError:
        WHOOSH_LIB_AVAILABLE = False
        whoosh_open_dir_lib = None
        print("Whoosh library (whoosh.index) not found. Whoosh functionality may be limited.")

    ENGINES_AVAILABLE = True
except ImportError as e:
    print(f"Error importing search engine modules or Lucene/Whoosh components: {e}")
    print("Please ensure paths are correct and SearchEngine package is importable.")
    ENGINES_AVAILABLE = False
    # Define placeholders if import fails, so the script doesn't crash immediately
    pylucene_search_documents = pylucene_create_index = pylucene_initialize_jvm = None
    whoosh_search_documents = whoosh_create_or_get_index = None
    postgres_search = None
    FSDirectory = DirectoryReader = IndexSearcher = JavaPaths = None # Placeholders
    whoosh_open_dir_lib = None # Placeholder

# Define root path for JuriScan project
PROJECT_ROOT = Path(__file__).parent.parent  # Benchmark/benchmark.py -> root project

# Define index paths relative to the project root
PYLUCENE_INDEX_PATH = PROJECT_ROOT / "SearchEngine" / "index"
WHOOSH_INDEX_PATH = PROJECT_ROOT / "SearchEngine" / "WhooshIndex" # Adjusted to match create_pool.py
JSON_DOCS_FILE = PROJECT_ROOT / "WebScraping" / "results" / "Docs_cleaned.json"

# Define paths for UIN file, Judged Pool, and Results output
UIN_FILE_PATH = PROJECT_ROOT / "uin.txt"
JUDGED_POOL_FILE_PATH = PROJECT_ROOT / "GroundTruth" / "JudgedPool.json"
BENCHMARK_RESULTS_FILE = PROJECT_ROOT / "Benchmark" / "Results" / "benchmark_results.json"


# Define plot directories
PLOTS_DIR = PROJECT_ROOT / "Plots"
PYLUCENE_PLOTS_DIR = PLOTS_DIR / "Pylucene"
WHOOSH_PLOTS_DIR = PLOTS_DIR / "Whoosh"  
POSTGRES_PLOTS_DIR = PLOTS_DIR / "Postgres"

def create_plot_directories():
    """!
    @brief Create plot directories if they don't exist
    @details Creates directory structure for storing engine-specific and comparative plots
    @return None
    """
    PYLUCENE_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    WHOOSH_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    POSTGRES_PLOTS_DIR.mkdir(parents=True, exist_ok=True)

def plot_precision_recall_metrics(engine_metrics, engine_name, k_values):
    """!
    @brief Generate and save precision-recall plots for an engine using Seaborn
    @param engine_metrics Dictionary containing metrics data for the engine
    @param engine_name Name of the search engine (PyLucene, Whoosh, PostgreSQL)
    @param k_values List of k values used for P@k and R@k calculations
    @details Creates box plots, bar plots, histograms and scatter plots for:
             - Precision@k distribution and means
             - Recall@k distribution and means  
             - Average Precision distribution
             - Response time analysis
    @return None
    """
    # Determine plot directory based on engine name
    if engine_name.lower() == "pylucene":
        plot_dir = PYLUCENE_PLOTS_DIR
    elif engine_name.lower() == "whoosh":
        plot_dir = WHOOSH_PLOTS_DIR
    elif engine_name.lower() == "postgresql":
        plot_dir = POSTGRES_PLOTS_DIR
    else:
        plot_dir = PLOTS_DIR / engine_name.lower()
        plot_dir.mkdir(parents=True, exist_ok=True)
    
    sns.set_style("whitegrid")
    sns.set_palette("husl")
    
    # 1. Plot Precision@k for all k values
    plt.figure(figsize=(12, 8))
    
    # Prepare data for precision plot
    precision_data = []
    for k in k_values:
        for query_idx, precision in enumerate(engine_metrics["P@k"][k]):
            precision_data.append({
                'Query': f'Q{query_idx+1}',
                'K': f'P@{k}',
                'Precision': precision
            })
    
    if precision_data:
        import pandas as pd
        df_precision = pd.DataFrame(precision_data)
        
        plt.subplot(2, 2, 1)
        sns.boxplot(data=df_precision, x='K', y='Precision')
        plt.title(f'{engine_name} - Precision@k Distribution')
        plt.ylabel('Precision')
        plt.ylim(0, 1)
        
        plt.subplot(2, 2, 2)
        sns.barplot(data=df_precision, x='K', y='Precision', estimator=np.mean, errorbar=('ci', 95)) # MODIFICATO: ci -> errorbar
        plt.title(f'{engine_name} - Mean Precision@k')
        plt.ylabel('Mean Precision')
        plt.ylim(0, 1)
    
    # 2. Plot Recall@k for all k values
    recall_data = []
    for k in k_values:
        for query_idx, recall in enumerate(engine_metrics["R@k"][k]):
            recall_data.append({
                'Query': f'Q{query_idx+1}',
                'K': f'R@{k}',
                'Recall': recall
            })
    
    if recall_data:
        df_recall = pd.DataFrame(recall_data)
        
        plt.subplot(2, 2, 3)
        sns.boxplot(data=df_recall, x='K', y='Recall')
        plt.title(f'{engine_name} - Recall@k Distribution')
        plt.ylabel('Recall')
        plt.ylim(0, 1)
        
        plt.subplot(2, 2, 4)
        sns.barplot(data=df_recall, x='K', y='Recall', estimator=np.mean, errorbar=('ci', 95)) # MODIFICATO: ci -> errorbar
        plt.title(f'{engine_name} - Mean Recall@k')
        plt.ylabel('Mean Recall')
        plt.ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(plot_dir / f'{engine_name}_precision_recall_at_k.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Plot Average Precision (AP) distribution
    plt.figure(figsize=(10, 6))
    
    if engine_metrics["AP"]:
        ap_data = pd.DataFrame({
            'Query': [f'Q{i+1}' for i in range(len(engine_metrics["AP"]))],
            'Average_Precision': engine_metrics["AP"]
        })
        
        plt.subplot(1, 2, 1)
        sns.histplot(data=ap_data, x='Average_Precision', bins=20, kde=True)
        plt.title(f'{engine_name} - Average Precision Distribution')
        plt.xlabel('Average Precision')
        plt.xlim(0, 1)
        
        plt.subplot(1, 2, 2)
        sns.boxplot(data=ap_data, y='Average_Precision')
        plt.title(f'{engine_name} - AP Box Plot')
        plt.ylabel('Average Precision')
        plt.ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(plot_dir / f'{engine_name}_average_precision.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Plot Response Times
    plt.figure(figsize=(10, 6))
    
    if engine_metrics["ResponseTimes"]:
        response_data = pd.DataFrame({
            'Query': [f'Q{i+1}' for i in range(len(engine_metrics["ResponseTimes"]))],
            'Response_Time': engine_metrics["ResponseTimes"]
        })
        
        plt.subplot(1, 2, 1)
        sns.histplot(data=response_data, x='Response_Time', bins=20, kde=True)
        plt.title(f'{engine_name} - Response Time Distribution')
        plt.xlabel('Response Time (seconds)')
        
        plt.subplot(1, 2, 2)
        sns.scatterplot(data=response_data, x='Query', y='Response_Time')
        plt.title(f'{engine_name} - Response Time per Query')
        plt.ylabel('Response Time (seconds)')
        plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(plot_dir / f'{engine_name}_response_times.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Plots saved for {engine_name} in {plot_dir}")

def plot_comparative_analysis(all_results, k_values):
    """!
    @brief Generate comparative plots across all search engines
    @param all_results Dictionary containing aggregated results for all engines
    @param k_values List of k values used for evaluation
    @details Creates comparative visualizations including:
             - Precision and recall comparison bar charts
             - MAP comparison across engines
             - Response time comparison
             - Performance heatmap
    @return None
    """
    import pandas as pd
    
    comparative_dir = PLOTS_DIR / "Comparative"
    comparative_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare data for comparative analysis
    engines = list(all_results.keys())
    metrics_data = []
    
    for engine in engines:
        metrics = all_results[engine]
        for k in k_values:
            metrics_data.append({
                'Engine': engine,
                'Metric': f'P@{k}',
                'Value': metrics.get(f'MeanP@{k}', 0)
            })
            metrics_data.append({
                'Engine': engine,
                'Metric': f'R@{k}',
                'Value': metrics.get(f'MeanR@{k}', 0)
            })
        
        metrics_data.append({
            'Engine': engine,
            'Metric': 'MAP',
            'Value': metrics.get('MAP', 0)
        })
        
        metrics_data.append({
            'Engine': engine,
            'Metric': 'Avg Response Time',
            'Value': metrics.get('AvgResponseTime', 0)
        })
    
    if metrics_data:
        df_metrics = pd.DataFrame(metrics_data)
        
        # 1. Precision and Recall Comparison
        plt.figure(figsize=(14, 8))
        
        plt.subplot(1, 2, 1)
        sns.barplot(data=df_metrics[df_metrics['Metric'].str.startswith('P@')], x='Metric', y='Value', hue='Engine', errorbar=None) # MODIFICATO: ci -> errorbar
        plt.title('Precision@k Comparison')
        plt.ylabel('Precision')
        plt.ylim(0, 1)
        plt.xticks(rotation=45)
        
        plt.subplot(1, 2, 2)
        sns.barplot(data=df_metrics[df_metrics['Metric'].str.startswith('R@')], x='Metric', y='Value', hue='Engine', errorbar=None) # MODIFICATO: ci -> errorbar
        plt.title('Recall@k Comparison')
        plt.ylabel('Recall')
        plt.ylim(0, 1)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(comparative_dir / 'precision_recall_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. MAP and Avg Response Time Comparison
        plt.figure(figsize=(10, 6))
        
        sns.barplot(data=df_metrics[df_metrics['Metric'].isin(['MAP', 'Avg Response Time'])], x='Metric', y='Value', hue='Engine', errorbar=None) # MODIFICATO: ci -> errorbar
        plt.title('MAP and Avg Response Time Comparison')
        plt.ylabel('Value')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(comparative_dir / 'map_avg_response_time_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Performance Heatmap
        heatmap_data = df_metrics.pivot_table(index='Engine', columns='Metric', values='Value')
        plt.figure(figsize=(12, 8))
        sns.heatmap(heatmap_data, annot=True, cmap='viridis', fmt=".2f")
        plt.title('Performance Heatmap')
        plt.xlabel('Metric')
        plt.ylabel('Engine')
        
        plt.tight_layout()
        plt.savefig(comparative_dir / 'performance_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Comparative plots saved in {comparative_dir}")
    else:
        print("No metrics data available for comparative analysis.")

# --- New Metric Calculation Functions ---

def calculate_precision_at_k(retrieved_ids, relevant_ids_set, k):
    """Calculates Precision@k."""
    if k == 0: return 0.0
    retrieved_k = retrieved_ids[:k]
    relevant_retrieved_k = [doc_id for doc_id in retrieved_k if doc_id in relevant_ids_set]
    return len(relevant_retrieved_k) / k

def calculate_recall_at_k(retrieved_ids, relevant_ids_set, k):
    """Calculates Recall@k."""
    if not relevant_ids_set: return 0.0 # Or 1.0 if no relevant docs means all tasks done? Usually 0.
    retrieved_k = retrieved_ids[:k]
    relevant_retrieved_k = [doc_id for doc_id in retrieved_k if doc_id in relevant_ids_set]
    return len(relevant_retrieved_k) / len(relevant_ids_set)

def calculate_average_precision(retrieved_ids, relevant_ids_set):
    """Calculates Average Precision (AP)."""
    if not relevant_ids_set: return 0.0

    ap_sum = 0.0
    relevant_hits = 0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids_set:
            relevant_hits += 1
            precision_at_i = relevant_hits / (i + 1)
            ap_sum += precision_at_i
            
    return ap_sum / len(relevant_ids_set) if relevant_ids_set else 0.0

# --- Helper functions for loading data ---

def load_queries_from_uin(uin_file_path):
    """Loads queries from the UIN file."""
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

def load_relevance_judgments(judged_pool_file_path):
    """Loads relevance judgments from JudgedPool.json."""
    try:
        with open(judged_pool_file_path, 'r', encoding='utf-8') as f:
            judgments = json.load(f)
        # Convert doc IDs in judgments to strings for consistency
        processed_judgments = {}
        for query, doc_relevance_map in judgments.items():
            processed_judgments[query] = {str(doc_id): relevance for doc_id, relevance in doc_relevance_map.items()}
        return processed_judgments
    except FileNotFoundError:
        print(f"ERROR: JudgedPool.json not found at {judged_pool_file_path}. Please run judge_pool.py first.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {judged_pool_file_path}")
        return None

# --- Main Benchmarking Logic ---

def run_benchmarks():
    """Runs the full benchmark suite."""
    if not ENGINES_AVAILABLE:
        print("Search engine modules not available. Aborting benchmark.")
        return

    if pylucene_initialize_jvm:
        try:
            if not lucene.getVMEnv():
                pylucene_initialize_jvm()
                print("JVM initialized by benchmark.py.")
            else:
                env = lucene.getVMEnv()
                env.attachCurrentThread() # Ensure thread is attached
                print("JVM was already initialized. Attached current thread for benchmark.py.")
        except Exception as e:
            print(f"Could not initialize/attach JVM for PyLucene: {e}")
            traceback.print_exc()
            # Decide if PyLucene should be skipped or abort
            # For now, we'll let it try and fail later if pylucene_searcher is None

    create_plot_directories()
    queries = load_queries_from_uin(UIN_FILE_PATH)
    judgments = load_relevance_judgments(JUDGED_POOL_FILE_PATH)

    if not queries or not judgments:
        print("Missing queries or judgments. Aborting benchmark.")
        return

    k_values = [5, 10, 20]
    all_engine_results_summary = {} # For benchmark_results.json
    
    # --- PyLucene Benchmark ---
    pylucene_searcher = None
    if IndexSearcher: # Check if Lucene components were imported
        try:
            print(f"Attempting to open PyLucene index at: {PYLUCENE_INDEX_PATH}")
            if PYLUCENE_INDEX_PATH.exists() and PYLUCENE_INDEX_PATH.is_dir():
                directory = FSDirectory.open(JavaPaths.get(str(PYLUCENE_INDEX_PATH)))
                if DirectoryReader.indexExists(directory):
                    reader = DirectoryReader.open(directory)
                    pylucene_searcher = IndexSearcher(reader)
                    print("PyLucene Searcher opened successfully.")
                else:
                    print(f"No valid PyLucene index found at {PYLUCENE_INDEX_PATH}.")
                    print("Please ensure the PyLucene index is correctly populated, possibly by running your project's PyLucene indexing script (e.g., one that writes to this path).")
            else:
                print(f"PyLucene index directory does not exist: {PYLUCENE_INDEX_PATH}")
                print("Please ensure the PyLucene index is created, possibly by running a script like `SearchEngine/Pylucene.py` or your project's PyLucene indexing script.")
        except Exception as e:
            print(f"Error opening PyLucene index: {e}")
            traceback.print_exc()

    if pylucene_search_documents and pylucene_searcher:
        print("\n--- Benchmarking PyLucene ---")
        engine_name = "PyLucene"
        ranking_type = "BM25" 
        
        per_query_metrics_list = [] # To store detailed metrics for each query

        # These lists are for the plot_precision_recall_metrics function
        all_query_aps = []
        all_query_response_times = []
        all_query_precisions_at_k = {k: [] for k in k_values}
        all_query_recalls_at_k = {k: [] for k in k_values}

        for query_idx, query_string in enumerate(queries):
            print(f"  Query {query_idx+1}/{len(queries)}: {query_string[:60]}...")
            true_relevant_docs_map = judgments.get(query_string, {})
            true_relevant_ids_set = {doc_id for doc_id, rel in true_relevant_docs_map.items() if rel == 1}

            if not true_relevant_ids_set:
                print(f"    Warning: No relevant documents found for query '{query_string}' in judgments. Metrics might be 0 or undefined.")

            start_time = time.time()
            search_results_obj, pr_data, _ = pylucene_search_documents(pylucene_searcher, True, True, True, query_string, ranking_type)
            response_time = time.time() - start_time
            
            current_query_metrics = {
                "query_string": query_string,
                "response_time": response_time
            }
            all_query_response_times.append(response_time)

            retrieved_doc_ids = []
            num_hits = 0
            if search_results_obj and hasattr(search_results_obj, 'scoreDocs'):
                num_hits = len(search_results_obj.scoreDocs)
                for hit in search_results_obj.scoreDocs:
                    doc = pylucene_searcher.storedFields().document(hit.doc)
                    retrieved_doc_ids.append(str(doc.get("id")))
            
            print(f"    PyLucene Search: Retrieved {num_hits} documents. Response time: {response_time:.4f}s")

            ap = calculate_average_precision(retrieved_doc_ids, true_relevant_ids_set)
            current_query_metrics["AP"] = ap
            all_query_aps.append(ap)

            for k in k_values:
                p_at_k = calculate_precision_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                r_at_k = calculate_recall_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                current_query_metrics[f"P@{k}"] = p_at_k
                current_query_metrics[f"R@{k}"] = r_at_k
                all_query_precisions_at_k[k].append(p_at_k)
                all_query_recalls_at_k[k].append(r_at_k)
            
            per_query_metrics_list.append(current_query_metrics)

        # Aggregate metrics for PyLucene for summary and comparative plots
        all_engine_results_summary[engine_name] = {
            "MAP": np.mean(all_query_aps) if all_query_aps else 0.0,
            "AvgResponseTime": np.mean(all_query_response_times) if all_query_response_times else 0.0,
            "PerQueryMetrics": per_query_metrics_list # Store detailed per-query metrics
        }
        for k in k_values:
            all_engine_results_summary[engine_name][f"MeanP@{k}"] = np.mean(all_query_precisions_at_k[k]) if all_query_precisions_at_k[k] else 0.0
            all_engine_results_summary[engine_name][f"MeanR@{k}"] = np.mean(all_query_recalls_at_k[k]) if all_query_recalls_at_k[k] else 0.0
        
        pylucene_plot_metrics_for_function = {"AP": all_query_aps, "ResponseTimes": all_query_response_times, "P@k": all_query_precisions_at_k, "R@k": all_query_recalls_at_k}
        plot_precision_recall_metrics(pylucene_plot_metrics_for_function, engine_name, k_values)
    else:
        print("\nSkipping PyLucene benchmark: searcher or search function not available.")

    # --- Whoosh Benchmark ---
    whoosh_ix = None
    if WHOOSH_LIB_AVAILABLE and whoosh_open_dir_lib:
        try:
            print(f"\nAttempting to open Whoosh index at: {WHOOSH_INDEX_PATH}")
            if WHOOSH_INDEX_PATH.exists() and WHOOSH_INDEX_PATH.is_dir():
                whoosh_ix = whoosh_open_dir_lib(str(WHOOSH_INDEX_PATH))
                doc_count = whoosh_ix.doc_count()
                print(f"Whoosh index opened successfully. Documents: {doc_count}")
                if doc_count == 0:
                    print(f"WARNING: Whoosh index at {WHOOSH_INDEX_PATH} is empty. Please ensure it's populated, possibly by running your project's Whoosh indexing script (e.g., SearchEngine/Whoosh.py).")
                    whoosh_ix = None # Treat empty index as unavailable for benchmarking
            else:
                print(f"Whoosh index directory does not exist: {WHOOSH_INDEX_PATH}")
                print("Please ensure the Whoosh index is created, possibly by running a script like `SearchEngine/Whoosh.py` or your project's Whoosh indexing script.")
        except WhooshEmptyIndexError_lib:
            print(f"Whoosh index at {WHOOSH_INDEX_PATH} is empty (reported by Whoosh). Please ensure it's populated.")
        except Exception as e:
            print(f"Error opening Whoosh index: {e}")
            traceback.print_exc()
    
    if whoosh_search_documents and whoosh_ix:
        print("\n--- Benchmarking Whoosh ---")
        engine_name = "Whoosh"
        ranking_type = "BM25F"

        per_query_metrics_list = []
        all_query_aps = []
        all_query_response_times = []
        all_query_precisions_at_k = {k: [] for k in k_values}
        all_query_recalls_at_k = {k: [] for k in k_values}

        with whoosh_ix.searcher() as whoosh_searcher_obj: 
            for query_idx, query_string in enumerate(queries):
                print(f"  Query {query_idx+1}/{len(queries)}: {query_string[:60]}...")
                true_relevant_docs_map = judgments.get(query_string, {})
                true_relevant_ids_set = {doc_id for doc_id, rel in true_relevant_docs_map.items() if rel == 1}

                if not true_relevant_ids_set:
                     print(f"    Warning: No relevant documents found for query '{query_string}' in judgments.")

                start_time = time.time()
                search_results_list = whoosh_search_documents(str(WHOOSH_INDEX_PATH), query_string, True, True, True, ranking_type)
                response_time = time.time() - start_time
                
                current_query_metrics = {
                    "query_string": query_string,
                    "response_time": response_time
                }
                all_query_response_times.append(response_time)
                
                retrieved_doc_ids = [str(r[0]) for r in search_results_list] if search_results_list else []
                print(f"    Whoosh Search: Retrieved {len(retrieved_doc_ids)} documents. Response time: {response_time:.4f}s")
                
                ap = calculate_average_precision(retrieved_doc_ids, true_relevant_ids_set)
                current_query_metrics["AP"] = ap
                all_query_aps.append(ap)

                for k in k_values:
                    p_at_k = calculate_precision_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                    r_at_k = calculate_recall_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                    current_query_metrics[f"P@{k}"] = p_at_k
                    current_query_metrics[f"R@{k}"] = r_at_k
                    all_query_precisions_at_k[k].append(p_at_k)
                    all_query_recalls_at_k[k].append(r_at_k)
                
                per_query_metrics_list.append(current_query_metrics)

        all_engine_results_summary[engine_name] = {
            "MAP": np.mean(all_query_aps) if all_query_aps else 0.0,
            "AvgResponseTime": np.mean(all_query_response_times) if all_query_response_times else 0.0,
            "PerQueryMetrics": per_query_metrics_list
        }
        for k in k_values:
            all_engine_results_summary[engine_name][f"MeanP@{k}"] = np.mean(all_query_precisions_at_k[k]) if all_query_precisions_at_k[k] else 0.0
            all_engine_results_summary[engine_name][f"MeanR@{k}"] = np.mean(all_query_recalls_at_k[k]) if all_query_recalls_at_k[k] else 0.0
        
        whoosh_plot_metrics_for_function = {"AP": all_query_aps, "ResponseTimes": all_query_response_times, "P@k": all_query_precisions_at_k, "R@k": all_query_recalls_at_k}
        plot_precision_recall_metrics(whoosh_plot_metrics_for_function, engine_name, k_values)
    else:
        print("\nSkipping Whoosh benchmark: index or search function not available.")

    # --- PostgreSQL Benchmark ---
    if postgres_search:
        print("\n--- Benchmarking PostgreSQL ---")
        engine_name = "PostgreSQL"
        ranking_type = "ts_rank_cd"

        per_query_metrics_list = []
        all_query_aps = []
        all_query_response_times = []
        all_query_precisions_at_k = {k: [] for k in k_values}
        all_query_recalls_at_k = {k: [] for k in k_values}

        for query_idx, query_string in enumerate(queries):
            print(f"  Query {query_idx+1}/{len(queries)}: {query_string[:60]}...")
            true_relevant_docs_map = judgments.get(query_string, {})
            true_relevant_ids_set = {doc_id for doc_id, rel in true_relevant_docs_map.items() if rel == 1}
            
            if not true_relevant_ids_set:
                 print(f"    Warning: No relevant documents found for query '{query_string}' in judgments.")

            start_time = time.time()
            search_results_list = postgres_search(query_string, True, True, True, ranking_type)
            response_time = time.time() - start_time

            current_query_metrics = {
                "query_string": query_string,
                "response_time": response_time
            }
            all_query_response_times.append(response_time)

            retrieved_doc_ids = [str(r[0]) for r in search_results_list] if search_results_list else []
            # PostgreSQL already prints debug info, so an additional print here might be redundant unless specifically desired
            # print(f"    PostgreSQL Search: Retrieved {len(retrieved_doc_ids)} documents. Response time: {response_time:.4f}s")


            ap = calculate_average_precision(retrieved_doc_ids, true_relevant_ids_set)
            current_query_metrics["AP"] = ap
            all_query_aps.append(ap)

            for k in k_values:
                p_at_k = calculate_precision_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                r_at_k = calculate_recall_at_k(retrieved_doc_ids, true_relevant_ids_set, k)
                current_query_metrics[f"P@{k}"] = p_at_k
                current_query_metrics[f"R@{k}"] = r_at_k
                all_query_precisions_at_k[k].append(p_at_k)
                all_query_recalls_at_k[k].append(r_at_k)
            
            per_query_metrics_list.append(current_query_metrics)
        
        all_engine_results_summary[engine_name] = {
            "MAP": np.mean(all_query_aps) if all_query_aps else 0.0,
            "AvgResponseTime": np.mean(all_query_response_times) if all_query_response_times else 0.0,
            "PerQueryMetrics": per_query_metrics_list
        }
        for k in k_values:
            all_engine_results_summary[engine_name][f"MeanP@{k}"] = np.mean(all_query_precisions_at_k[k]) if all_query_precisions_at_k[k] else 0.0
            all_engine_results_summary[engine_name][f"MeanR@{k}"] = np.mean(all_query_recalls_at_k[k]) if all_query_recalls_at_k[k] else 0.0

        postgres_plot_metrics_for_function = {"AP": all_query_aps, "ResponseTimes": all_query_response_times, "P@k": all_query_precisions_at_k, "R@k": all_query_recalls_at_k}
        plot_precision_recall_metrics(postgres_plot_metrics_for_function, engine_name, k_values)
    else:
        print("\nSkipping PostgreSQL benchmark: search function not available.")

    # Save aggregated results to JSON file
    try:
        BENCHMARK_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_engine_results_summary, f, indent=2, ensure_ascii=False)
        print(f"\nBenchmark results saved to: {BENCHMARK_RESULTS_FILE}")
    except IOError as e:
        print(f"Error writing benchmark results to {BENCHMARK_RESULTS_FILE}: {e}")

    # Generate comparative plots if there are results
    if all_engine_results_summary:
        plot_comparative_analysis(all_engine_results_summary, k_values)
    else:
        print("\nNo engine results to generate comparative plots.")
    
    print("\nBenchmark run complete.")


if __name__ == "__main__":
    print(f"Running benchmark.py from: {Path(__file__).resolve()}")
    print(f"Project root: {PROJECT_ROOT}")
    run_benchmarks()
