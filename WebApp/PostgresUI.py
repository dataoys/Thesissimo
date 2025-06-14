"""!
@file PostgresUI.py
@brief Streamlit web interface for PostgreSQL search engine
@details Provides interactive web UI for document search using PostgreSQL full-text search
@author Magni && Testoni
@date 2025
"""

import streamlit as st
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from SearchEngine.Postgres import search

# Path to the engine-specific plots
POSTGRES_PLOTS_DIR = project_root / "Benchmark" / "Plots" / "Postgres"

def show_engine_specific_benchmark_plots():
    """!
    @brief Displays engine-specific benchmark plots for PostgreSQL.
    @details Lists and shows images from the Benchmark/Plots/Postgres/ directory.
    @return None
    """
    st.subheader("Benchmark Specifici per PostgreSQL")
    if not POSTGRES_PLOTS_DIR.exists() or not POSTGRES_PLOTS_DIR.is_dir():
        st.warning(f"Directory dei grafici specifici per PostgreSQL non trovata: {POSTGRES_PLOTS_DIR}")
        return

    plot_files = list(POSTGRES_PLOTS_DIR.glob("*.png")) + \
                 list(POSTGRES_PLOTS_DIR.glob("*.jpg")) + \
                 list(POSTGRES_PLOTS_DIR.glob("*.jpeg"))

    if not plot_files:
        st.info("Nessun grafico specifico trovato per PostgreSQL.")
    else:
        for plot_file in plot_files:
            try:
                st.image(str(plot_file), caption=plot_file.name)
            except Exception as e:
                st.error(f"Errore nel caricamento del grafico {plot_file.name}: {e}")

def searchUI():
    """!
    @brief Main Streamlit UI function for PostgreSQL search interface
    @details Creates complete web interface including:
             - Search field configuration and filters
             - PostgreSQL ranking type selection (ts_rank, ts_rank_cd)
             - Results display with document ranking scores
             - Support for field-specific and natural language queries
    @return None
    """
    st.sidebar.image('/root/JuriScan/forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png', width=150)
    st.sidebar.write("Thesissimo è un motore di ricerca innovativo progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di  migliaia di tesi universitarie relative a materie scientifiche. Che si tratti di scienze, astrofisica, o ingegneria noi abbiamo la risposta. Con una ricerca precisa, rapida e facile da usare, Thesissimo rende più facile l'accesso a risorse accademiche.")
    st.title("📚 Ricerca Documenti - PostgreSQL") # Added engine name to title
    ranking_type = st.radio("🔍 Seleziona il tipo di ranking", ["ts_rank", "ts_rank_cd"])

    
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
 
    search_query = st.text_input("🔍 Inserisci il testo da cercare", "")

    results = search(search_query, title_true, abstract_true, corpus_true, ranking_type)
        
    if results:
        st.success(f"Trovati {len(results)} documenti")
        
        for doc in results:
            # Creiamo un link cliccabile con il titolo
            title_html = f'📄 {doc[1]}'
            with st.expander(title_html, expanded=False):
                st.write("**ID:** ", doc[0])
                st.write("**Abstract:**", doc[2])
                st.write("**Ranking:**", doc[6])
                if doc[4] != "No keywords available":
                    st.write("**Keywords:**", doc[4])
                # Aggiungiamo anche un pulsante per il link diretto
                st.markdown(f"[🔗 Vai al documento originale]({doc[5]})")
                st.markdown("---")
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")

    # Expander for engine-specific benchmark visualization
    with st.expander("Visualizza Benchmark Specifici per PostgreSQL"):
        show_engine_specific_benchmark_plots()

if __name__ == "__main__":
    searchUI()