from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.analysis import StemmingAnalyzer
import os
import json
from pathlib import Path
import streamlit as st
import psycopg2 as ps
import sys

#Listo tutti i campi dei docuenti nell'indice
def create_schema():
    return Schema(
        id=ID(stored=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        abstract=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        corpus=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        keywords=TEXT(stored=True),
        url=TEXT(stored=True)
    )

#Creiamo l'indice
def create_index(index_dir):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    schema = create_schema()
    #Creo l'indice tramite la funzione proprietaria di whoosh
    return create_in(index_dir, schema)

# Indicizza i documenti
def index_documents(index_dir, json_file):
    index = create_index(index_dir)
    writer = index.writer()

    #Apro il file con i documenti
    with open(json_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    #Leggo dal file tutti i campi e li aggiungo all'indice
    for doc in documents:
        writer.add_document(
            id=str(doc['id']),
            title=doc['title'],
            abstract=doc['abstract'],
            corpus=doc['corpus'],
            keywords=doc.get('keywords', ''),
            url=doc['url']
        )

    #Salvo le modifiche nel file di indice
    writer.commit()

# Ricerca nei documenti
def search_documents(index_dir, query_string, title_true, abstract_true, corpus_true):
    from whoosh import index

    index = index.open_dir(index_dir)
    #Performo una ricerca
    with index.searcher() as searcher:

        if title_true & abstract_true & corpus_true:
            #Creo la query concatenando la ricerca su più campi dei documenti
            query = QueryParser("title", index.schema).parse(query_string) | QueryParser("abstract", index.schema).parse(query_string) | QueryParser("corpus", index.schema).parse(query_string)

            #imposto in una lista i valori dei campi del documento ritrovato e li ritorno
            results = searcher.search(query)

            return [(result['id'], result['title'], result['abstract'], result['corpus'], result['keywords'], result['url']) for result in results]
        #ricerca solamente sul titolo dei nostri documenti
        if title_true and not abstract_true and not corpus_true:
            #creazione della query di ricerca title-based
            query = QueryParser("title", index.schema).parse(query_string)
            #imposto in una lista i valori dei campi del documento ritrovato e li ritorno
            results = searcher.search(query)

            return [(result['id'], result['title'], result['abstract'], result['corpus'], result['keywords'], result['url']) for result in results]
        
        #ricerca sull'abstract dei documenti
        if abstract_true and not title_true and not corpus_true:
            #creazione della query di ricerca abstract-based
            query = QueryParser("abstract", index.schema).parse(query_string)
            #imposto in una lista i valori dei campi del documento ritrovato e li ritorno
            results = searcher.search(query)

            return [(result['id'], result['title'], result['abstract'], result['corpus'], result['keywords'], result['url']) for result in results]
        #ricerca solo sul corpo del testo dei nostri documenti
        if corpus_true and not title_true and not abstract_true:
            #creazione della query di ricerca corpus-based
            query = QueryParser("corpus", index.schema).parse(query_string)
            #imposto in una lista i valori dei campi del documento ritrovato e li ritorno
            results = searcher.search(query)

            return [(result['id'], result['title'], result['abstract'], result['corpus'], result['keywords'], result['url']) for result in results]
        
        
        

# Funzione principale per indicizzare e cercare
def main():
    #settiamo le directory per i percorsi dei documenti e del progetto per creare indice
    project_root = Path(__file__).parent.parent
    index_dir = str(project_root / "WhooshIndex")  
    json_file = str(project_root / "WebScraping/results/Docs.json") 

    # Indicizza i documenti
    index_documents(index_dir, json_file) 

    st.title("📚 Ricerca Documenti")

    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo")
        with col2:
            abstract_true = st.checkbox("Abstract")
        with col3:
            corpus_true = st.checkbox("Corpus")

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
                # Aggiungiamo anche un pulsante per il link diretto
                st.markdown(f"[🔗 Vai al documento originale]({doc[5]})")
                st.markdown("---")
    else:
        st.warning("Nessun documento trovato per la ricerca effettuata.")
    # Esempio di ricerca

    if results:
        print(f"Trovati {len(results)} documenti:")
        for doc in results:
            print(f"ID: {doc[0]} \n Titolo: {doc[1]} \n Abstract: {doc[2]} \n URL: {doc[5]} \n")
    else:
        print("Nessun documento trovato.")

if __name__ == '__main__':
    main()


