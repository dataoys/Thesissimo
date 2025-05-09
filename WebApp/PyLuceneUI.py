import lucene
try:
    lucene.initVM()
except ValueError:
    pass  # JVM è già in esecuzione, ignoriamo l'errore

import streamlit as st
from pathlib import Path
import sys
import numpy as np
import os

project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
sys.path.append(str(project_root))

from SearchEngine.Pylucene import create_index, search_documents

directory, searcher = create_index()

def searchUI():
    st.sidebar.image('/root/JuriScan/forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png', width=150)
    st.sidebar.write("Thesissimo è un motore di ricerca innovativo progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di  migliaia di tesi universitarie relative a materie scientifiche. Che si tratti di scienze, astrofisica, o ingegneria noi abbiamo la risposta. Con una ricerca precisa, rapida e facile da usare, Thesissimo rende più facile l'accesso a risorse accademiche.")
    st.title("📚 Ricerca Documenti")
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

        # Mostra il grafico Precision-Recall se disponibile
        if plot_path and os.path.exists(plot_path):
            st.subheader("📊 Metriche di Performance")
            st.image(plot_path, caption="Curva Precision-Recall")
            
            if pr_metrics:
                precision_values, recall_values = pr_metrics
                st.write(f"Precision media: {np.mean(precision_values):.3f}")
                st.write(f"Recall media: {np.mean(recall_values):.3f}")

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

if __name__ == "__main__":
    searchUI()