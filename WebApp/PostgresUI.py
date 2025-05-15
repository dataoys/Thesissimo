import streamlit as st
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from SearchEngine.Postgres import search

def searchUI():
    """
    Main function of the Streamlit postgres application.

    This function creates the main interface of the Streamlit application for the Postgres search engine.
    """
    st.sidebar.image('/root/JuriScan/forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png', width=150)
    st.sidebar.write("Thesissimo è un motore di ricerca innovativo progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di  migliaia di tesi universitarie relative a materie scientifiche. Che si tratti di scienze, astrofisica, o ingegneria noi abbiamo la risposta. Con una ricerca precisa, rapida e facile da usare, Thesissimo rende più facile l'accesso a risorse accademiche.")
    st.title("📚 Ricerca Documenti")
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


if __name__ == "__main__":
    searchUI()