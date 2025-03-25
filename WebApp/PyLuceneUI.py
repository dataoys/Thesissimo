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

directory, searcher = create_index()

def searchUI():
    
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

    query_string = st.text_input("🔍 Inserisci il testo da cercare", "")
    results = search_documents(searcher,title_true, abstract_true, corpus_true, query_string, ranking_type)
    #print (results)
    if results:

        st.success(f"Trovati {len(results.scoreDocs)} documenti")

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
                st.write("**Punteggio**",scoreDoc.score)
            #print(f"Document ID: {scoreDoc.doc}, Score: {scoreDoc.score}, Content: {doc.get("content")}")
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")

    directory.close()

if __name__ == "__main__":
    searchUI()