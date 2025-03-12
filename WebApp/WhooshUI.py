import streamlit as st
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import numpy as np

# Ottieniamo il percorso assoluto della directory root del progetto
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from SearchEngine import create_or_get_index, search_documents

def calculate_precision_recall(results, relevant_docs):
    retrieved_docs = len(results)
    true_positives = sum(1 for doc in results if doc[0] in relevant_docs)
    
    precision = true_positives / retrieved_docs if retrieved_docs > 0 else 0
    recall = true_positives / len(relevant_docs) if relevant_docs else 0
    
    return precision, recall

def plot_precision_recall(precision, recall):
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
def main():
    project_root = Path(__file__).parent.parent
    index_dir = str(project_root / "WhooshIndex")  
    json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 

    # Inizializza l'indice solo se necessario
    ix = create_or_get_index(index_dir, json_file)
    if not ix:
        st.error("Impossibile inizializzare l'indice. Riprova.")
        return

    st.title("📚 Ricerca Documenti")

    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo")
        with col2:
            abstract_true = st.checkbox("Abstract")
        with col3:
            corpus_true = st.checkbox("Corpus")

    st.info("""💡 Lil Tip: Do a query with natural language \n
    - es: "document about radioactivity" 
    - The output will include synonyms 
    - The more term you use, the better the search!""") 
    
    query_string = st.text_input("🔍 Inserisci il testo da cercare", "")
    results = search_documents(index_dir, query_string,title_true, abstract_true, corpus_true)

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

if __name__ == '__main__':
    main()


