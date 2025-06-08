"""!
@file mainPage.py
@brief Main entry point for JuriScan web application
@details Provides search engine selection interface and launches corresponding Streamlit apps
@author Magni && Testoni
@date 2025
"""

import streamlit as st
import subprocess
import json # Import for reading JSON
from pathlib import Path # Import for path manipulation
import pandas as pd # Import for displaying dataframes

#Titolo
st.title("THESISSIMO")
# Options for the search engine selection
motori_di_ricerca = ["Postgres", "Whoosh", "PyLucene"]

scelta = st.selectbox("Scegli un motore di ricerca:", motori_di_ricerca)
def esegui_streamlit(motore):
    """!
    @brief Launch specific search engine UI application
    @param motore String identifier for the chosen search engine
    @details Starts subprocess with appropriate Streamlit application based on user selection.
             Supports PostgreSQL, Whoosh, and PyLucene search engines.
    @return None
    """
    # Get the directory of the current script (mainPage.py), which is q:\Juriscan\JuriScan\WebApp
    webapp_dir = Path(__file__).parent

    if motore == "Postgres":
        # Run PostgresUI.py from the webapp_dir
        subprocess.Popen(["streamlit", "run", "PostgresUI.py"], cwd=webapp_dir)
    elif motore == "Whoosh":
        # Run WhooshUI.py from the webapp_dir
        subprocess.Popen(["streamlit", "run", "WhooshUI.py"], cwd=webapp_dir)
    elif motore == "PyLucene":
        print("PyLucene") # Keep for debugging if needed
        # Run PyLuceneUI.py from the webapp_dir
        subprocess.Popen(["streamlit", "run", "PyLuceneUI.py"], cwd=webapp_dir)
# Esegui il file corrispondente
if st.button("Avvia Motore di Ricerca Selezionato"):
    esegui_streamlit(scelta)
    st.success(f"Applicazione per {scelta} avviata con successo!")

# Path to the benchmark results and plots
BENCHMARK_RESULTS_FILE = Path(__file__).parent.parent / "Benchmark" / "Results" / "benchmark_results.json"
# Corrected path as per user's manual edit
COMPARATIVE_PLOTS_DIR = Path(__file__).parent.parent / "Benchmark" / "Plots" / "Comparative" 

def mostra_benchmark():
    """!
    @brief Displays benchmark results and comparative plots
    @details Reads data from benchmark_results.json and displays metrics.
             Also, lists and shows images from the Plots/Comparative/ directory.
    @return None
    """
    st.header("Risultati Benchmark")

    if not BENCHMARK_RESULTS_FILE.exists():
        st.error(f"File dei risultati benchmark non trovato: {BENCHMARK_RESULTS_FILE}")
        return

    try:
        with open(BENCHMARK_RESULTS_FILE, 'r') as f:
            results = json.load(f)
    except Exception as e:
        st.error(f"Errore nel caricamento del file JSON dei benchmark: {e}")
        return

    st.subheader("Metriche di Performance")
    
    # Prepare data for a summary table
    summary_data = []
    for engine, metrics in results.items():
        summary_data.append({
            "Motore": engine,
            "MAP": f"{metrics.get('MAP', 'N/A'):.4f}",
            "Avg Response Time (s)": f"{metrics.get('AvgResponseTime', 'N/A'):.4f}",
            "Mean P@5": f"{metrics.get('MeanP@5', 'N/A'):.2f}",
            "Mean R@5": f"{metrics.get('MeanR@5', 'N/A'):.4f}",
            "Mean P@10": f"{metrics.get('MeanP@10', 'N/A'):.2f}",
            "Mean R@10": f"{metrics.get('MeanR@10', 'N/A'):.4f}",
            "Mean P@20": f"{metrics.get('MeanP@20', 'N/A'):.2f}",
            "Mean R@20": f"{metrics.get('MeanR@20', 'N/A'):.4f}",
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df.set_index("Motore"))

    st.subheader("Grafici Comparativi")
    if not COMPARATIVE_PLOTS_DIR.exists() or not COMPARATIVE_PLOTS_DIR.is_dir():
        # Use the corrected path in the warning message
        st.warning(f"Directory dei grafici comparativi non trovata: {COMPARATIVE_PLOTS_DIR}") 
        return

    plot_files = list(COMPARATIVE_PLOTS_DIR.glob("*.png")) + \
                 list(COMPARATIVE_PLOTS_DIR.glob("*.jpg")) + \
                 list(COMPARATIVE_PLOTS_DIR.glob("*.jpeg"))

    if not plot_files:
        st.info("Nessun grafico comparativo trovato.")
    else:
        for plot_file in plot_files:
            try:
                st.image(str(plot_file), caption=plot_file.name)
            except Exception as e:
                st.error(f"Errore nel caricamento del grafico {plot_file.name}: {e}")



# Expander for benchmark visualization
with st.expander("Visualizza Risultati Benchmark"): 
    mostra_benchmark()
