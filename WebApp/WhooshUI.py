"""!
@file WhooshUI.py
@brief Streamlit web interface for Whoosh search engine
@details Provides interactive web UI for document search using Whoosh with precision-recall visualization
@author Magni && Testoni
@date 2025
"""

import streamlit as st
from pathlib import Path
import sys
import matplotlib.pyplot as plt

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from SearchEngine.Whoosh import create_or_get_index, search_documents

# Path to the engine-specific plots
WHOOSH_PLOTS_DIR = project_root / "Benchmark" / "Plots" / "Whoosh"

def show_engine_specific_benchmark_plots():
    """!
    @brief Displays engine-specific benchmark plots for Whoosh.
    @details Lists and shows images from the Benchmark/Plots/Whoosh/ directory.
    @return None
    """
    st.subheader("Benchmark Specifici per Whoosh")
    if not WHOOSH_PLOTS_DIR.exists() or not WHOOSH_PLOTS_DIR.is_dir():
        st.warning(f"Directory dei grafici specifici per Whoosh non trovata: {WHOOSH_PLOTS_DIR}")
        return

    plot_files = list(WHOOSH_PLOTS_DIR.glob("*.png")) + \
                 list(WHOOSH_PLOTS_DIR.glob("*.jpg")) + \
                 list(WHOOSH_PLOTS_DIR.glob("*.jpeg"))

    if not plot_files:
        st.info("Nessun grafico specifico trovato per Whoosh.")
    else:
        for plot_file in plot_files:
            try:
                st.image(str(plot_file), caption=plot_file.name)
            except Exception as e:
                st.error(f"Errore nel caricamento del grafico {plot_file.name}: {e}")

def calculate_precision_recall(results, relevant_docs):
    """!
    @brief Calculate precision and recall metrics for search results
    @param results List of search results from Whoosh engine
    @param relevant_docs List of relevant document IDs for evaluation
    @return Tuple containing (precision, recall) values
    @details Computes precision as true positives / retrieved documents
             and recall as true positives / total relevant documents
    """
    retrieved_docs = len(results)
    true_positives = sum(1 for doc in results if doc[0] in relevant_docs)
    
    precision = true_positives / retrieved_docs if retrieved_docs > 0 else 0
    recall = true_positives / len(relevant_docs) if relevant_docs else 0
    
    return precision, recall

def plot_precision_recall(precision, recall):
    """!
    @brief Generate and display precision-recall curve plot
    @param precision List of precision values to plot
    @param recall List of recall values to plot
    @details Creates matplotlib figure with precision-recall curve,
             displays grid and proper axis limits, integrates with Streamlit
    """
    plt.figure()
    plt.plot(recall, precision, marker='o')
    plt.title('Precision-Recall Curve')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.0])
    plt.grid()
    st.pyplot(plt)

# Funzione principale per indicizzare e cercare
def searchUI():
    """!
    @brief Main Streamlit UI function for Whoosh search interface
    @details Creates complete web interface including:
             - Search field configuration and filters
             - Document ranking type selection
             - Results display with expandable document details
             - Precision-recall visualization in sidebar
    @return None
    """
    project_root = Path(__file__).parent.parent
    index_dir = str(project_root / "WhooshIndex")  
    json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 

    # Inizializza l'indice solo se necessario
    ix = create_or_get_index(index_dir, json_file)
    if not ix:
        st.error("Impossibile inizializzare l'indice. Riprova.")
        return

    st.sidebar.image('/root/JuriScan/forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png', width=150)
    st.sidebar.write("Thesissimo è un motore di ricerca innovativo progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di  migliaia di tesi universitarie relative a materie scientifiche. Che si tratti di scienze, astrofisica, o ingegneria noi abbiamo la risposta. Con una ricerca precisa, rapida e facile da usare, Thesissimo rende più facile l'accesso a risorse accademiche.")
    st.title("📚 Ricerca Documenti - Whoosh") # Added engine name to title
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
    results = search_documents(index_dir, query_string,title_true, abstract_true, corpus_true, ranking_type)

    if results:
        st.success(f"Trovati {len(results)} documenti")
        
        for doc in results:
            # Creiamo un link cliccabile con il titolo
            title_html = f'📄 {doc[1]}'
            with st.expander(title_html, expanded=False):
                st.write("**ID:** ", doc[0])
                st.write("**Abstract:**", doc[2])
                if doc[4] != "No keywords available":
                    st.write("**Keywords:**", doc[4])
                # Aggiungiamo il ranking score
                st.write("**Relevance Score:** {:.2f}".format(doc[5]))
                # Aggiungiamo il link diretto
                st.markdown(f"[🔗 Vai al documento originale]({doc[6]})")
                st.markdown("---")

        relevant_docs = [...]  # Definisci qui i documenti rilevanti per il tuo caso d'uso
        precision, recall = calculate_precision_recall(results, relevant_docs)
        
        # Mostra il grafico nella barra laterale
        st.sidebar.header("Precision e Recall")
        plot_precision_recall(precision, recall)
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")

    # Expander for engine-specific benchmark visualization
    with st.expander("Visualizza Benchmark Specifici per Whoosh"):
        show_engine_specific_benchmark_plots()

if __name__ == '__main__':
    searchUI()


