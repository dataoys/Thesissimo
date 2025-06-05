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
    
    # Set seaborn style
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
        sns.barplot(data=df_precision, x='K', y='Precision', estimator=np.mean, ci=95)
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
        sns.barplot(data=df_recall, x='K', y='Recall', estimator=np.mean, ci=95)
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
   