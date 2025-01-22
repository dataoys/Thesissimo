import streamlit as st
import psycopg2 as ps
import sys
from pathlib import Path

# Ottieniamo il percorso assoluto della directory root del progetto
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Per debug, verifica il path
print("Project root:", project_root)
print("Python path:", sys.path)

from Queries import dbConn


def search(title_true, abstract_true, corpus_true):
    conn = dbConn()
    cur = conn.cursor()
    search_query = st.text_input("🔍 Inserisci il testo da cercare", "")
    if search_query:
        #ricerca su tutti i campi dei documenti
        if title_true & abstract_true & corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords 
            FROM docs 
            WHERE to_tsvector(corpus) @@ to_tsquery(%s)
            OR to_tsvector(title) @@ to_tsquery(%s)
            OR to_tsvector(abstract) @@ to_tsquery(%s)
            '''
            cur.execute(q, (search_query, search_query, search_query))
        #ricerca solamente sul titolo dei nostri documenti
        if title_true and not abstract_true and not corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords 
            FROM docs 
            WHERE to_tsvector(title) @@ to_tsquery(%s)
            '''
            cur.execute(q, (search_query,))
        #ricerca sull'abstract dei documenti
        if abstract_true and not title_true and not corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords 
            FROM docs 
            WHERE to_tsvector(abstract) @@ to_tsquery(%s)
            '''
            cur.execute(q, (search_query,))
        #ricerca solo sul corpo del testo dei nostri documenti
        if corpus_true and not title_true and not abstract_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords 
            FROM docs 
            WHERE to_tsvector(corpus) @@ to_tsquery(%s)
            '''
            cur.execute(q, (search_query,))
                
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results

def main():
    st.title("📚 Ricerca Documenti", )
    #st.write('🔧Filtra la tua ricerca!')
    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo")
        with col2:
            abstract_true = st.checkbox("Abstract")
        with col3:
            corpus_true = st.checkbox("Corpus")
        results = search(title_true, abstract_true, corpus_true)
        
    if results:
        st.success(f"Trovati {len(results)} documenti")
        
        for doc in results:
            with st.expander(f"📄 {doc[1]}"):  # doc[1] è il titolo
                st.write("**ID:** ", doc[0])
                st.write("**Abstract:**", doc[2])
                st.write("**Corpus**", doc[3])
                if doc[4] != "No keywords available":
                    st.write("**Keywords:**", doc[4])
                st.markdown("---")
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")


if __name__ == "__main__":
    main()