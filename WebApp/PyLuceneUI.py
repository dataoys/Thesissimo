"""!
@file PyLuceneUI.py
@brief Streamlit web interface for PyLucene search engine
@details Provides interactive web UI for document search using PyLucene with JVM management
@author Magni && Testoni
@date 2025
"""

import lucene
try:
    lucene.initVM()
except ValueError:
    pass  # JVM è già in esecuzione, ignoriamo l'errore

import streamlit as st
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
sys.path.append(str(project_root))

from SearchEngine.Pylucene import create_index, search_documents

# Path to the engine-specific plots
PYLUCENE_PLOTS_DIR = project_root / "Benchmark" / "Plots" / "Pylucene" # Corrected to Pylucene

directory, searcher = create_index()

def show_engine_specific_benchmark_plots():
    """!
    @brief Displays engine-specific benchmark plots for PyLucene.
    @details Lists and shows images from the Benchmark/Plots/Pylucene/ directory.
    @return None
    """
    st.subheader("Benchmark Specifici per PyLucene")
    if not PYLUCENE_PLOTS_DIR.exists() or not PYLUCENE_PLOTS_DIR.is_dir():
        st.warning(f"Directory dei grafici specifici per PyLucene non trovata: {PYLUCENE_PLOTS_DIR}")
        return

    plot_files = list(PYLUCENE_PLOTS_DIR.glob("*.png")) + \
                 list(PYLUCENE_PLOTS_DIR.glob("*.jpg")) + \
                 list(PYLUCENE_PLOTS_DIR.glob("*.jpeg"))

    if not plot_files:
        st.info("Nessun grafico specifico trovato per PyLucene.")
    else:
        for plot_file in plot_files:
            try:
                st.image(str(plot_file), caption=plot_file.name)
            except Exception as e:
                st.error(f"Errore nel caricamento del grafico {plot_file.name}: {e}")

def searchUI():
    """!
    @brief Main Streamlit UI function for PyLucene search interface
    @details Creates complete web interface including:
             - JVM initialization and index management
             - Search field configuration and filters
             - Document ranking type selection (TF_IDF, BM25)
             - Results display with document scores and links
             - Integration with PyLucene precision-recall metrics
    @return None
    """
    st.sidebar.image('/root/JuriScan/forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png', width=150)
    st.sidebar.write("Thesissimo è un motore di ricerca innovativo progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di  migliaia di tesi universitarie relative a materie scientifiche. Che si tratti di scienze, astrofisica, o ingegneria noi abbiamo la risposta. Con una ricerca precisa, rapida e facile da usare, Thesissimo rende più facile l'accesso a risorse accademiche.")
    st.title("📚 Ricerca Documenti - PyLucene") # Added engine name to title
    ranking_type = st.radio("🔍 Seleziona il tipo di ranking", ["TF_IDF", "BM25"])

    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo")
        with col2:
            abstract_true = st.checkbox("Abstract")
        with col3:
            corpus_true = st.checkbox("Corpus")
    
    st.info("""Lil Tip: Do a query with natural language. The output will include synonyms, so the more term you use, the better the search!\n\nFor example:\n\n
         Document about radioactivity\n\n
        """, icon="💡") 

    query_string = st.text_input("🔍 Inserisci il testo da cercare", "")
    results, pr_metrics, plot_path = search_documents(searcher, title_true, abstract_true, corpus_true, query_string, ranking_type)
    
    if results:
        st.success(f"Trovati {len(results.scoreDocs)} documenti")

        # Mostra i risultati
        for scoreDoc in results.scoreDocs:
            doc = searcher.storedFields().document(scoreDoc.doc)
            title_html = f'📄 {doc.get("title")}'
            with st.expander(title_html, expanded=False):
                st.write("**ID:** ", scoreDoc.doc)
                st.write("**Abstract:**", doc.get("abstract"))
                if doc.get("keywords") != "No keywords available":
                    st.write("**Keywords:**", doc.get("keywords"))
                url=doc.get("url")
                st.markdown(f"[🔗 Vai al documento originale]({url})")
                st.markdown("---")
                st.write("**Punteggio**", scoreDoc.score)
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")

    # Expander for engine-specific benchmark visualization
    with st.expander("Visualizza Benchmark Specifici per PyLucene"):
        show_engine_specific_benchmark_plots()

if __name__ == "__main__":
    searchUI()