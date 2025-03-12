import streamlit as st
from pathlib import Path
import sys

# Ottieniamo il percorso assoluto della directory root del progetto
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from SearchEngine.Pylucene import create_index, search_documents

def pylucene():
    #per non importare pylucene anche qui recupero il valori di ritorno dell'index
    directory, searcher = create_index()
    st.title("📚 Ricerca Documenti")

    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo", value=True)
        with col2:
            abstract_true = st.checkbox("Abstract", value=True)
        with col3:
            corpus_true = st.checkbox("Corpus", value=True)


    query_string = st.text_input("🔍 Inserisci il testo da cercare", "")
    results = search_documents(searcher,title_true, abstract_true, corpus_true, query_string)
    print (results)
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
    pylucene()