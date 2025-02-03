import lucene
try:
    lucene.initVM()
except ValueError:
    pass  # JVM è già in esecuzione, ignoriamo l'errore

from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.store import ByteBuffersDirectory
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader
from org.apache.lucene.document import Document, Field, StringField, TextField
from org.apache.lucene.search import IndexSearcher, BooleanQuery, BooleanClause
from org.apache.lucene.queryparser.classic import QueryParser
import streamlit as st
import json
from pathlib import Path
import yake
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords

#  Scarico le risorse di NLTK necessarie
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    nltk.download('stopwords')


project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 

#Questa funzione permette l'esapnsione della query, ovveero la ricerca contestualizzata
def expand_query(query_string):

    # Estrazione parole chiave con YAKE
    kw_extractor = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=5)
    keywords = [kw[0] for kw in kw_extractor.extract_keywords(query_string)]

    # Tokenizzazione e stemming con NLTK
    stemmer = PorterStemmer()
    stop_words = set(stopwords.words('english'))
    
    tokens = word_tokenize(query_string.lower())  # Tokenizzazione
    stemmed_tokens = [stemmer.stem(word) for word in tokens if word.isalnum() and word not in stop_words]  # Rimozione stopword e stemming
    
    # Unione delle parole chiave YAKE e dei termini stemmatizzati
    expanded_terms = list(set(keywords + stemmed_tokens))
    
    return " OR ".join(expanded_terms)  # Formattazione per Lucene

def search_documents(searcher, title_true, abstract_true, corpus_true, query_string):
    analyzer = StandardAnalyzer()
    boolean_query = BooleanQuery.Builder()

    expanded_query_string = expand_query(query_string)

    if title_true:
        title_query = QueryParser("title", analyzer).parse(expanded_query_string)
        boolean_query.add(title_query, BooleanClause.Occur.SHOULD)
    if abstract_true:
        abstract_query = QueryParser("abstract", analyzer).parse(expanded_query_string)
        boolean_query.add(abstract_query, BooleanClause.Occur.SHOULD)
    if corpus_true:
        corpus_query = QueryParser("corpus", analyzer).parse(expanded_query_string)
        boolean_query.add(corpus_query, BooleanClause.Occur.SHOULD)

    query = boolean_query.build()
    results = searcher.search(query,10)
    return results


def test_pylucene():
     # Attacca il thread corrente alla JVM. Con Streamlit, che usa thread multipli, 
     # dobbiamo assicurarci che il thread corrente sia collegato alla JVM prima di usare 
     # le funzionalità di Lucene.
    env = lucene.getVMEnv()
    env.attachCurrentThread()

    # Creazione dell'indice in memoria
    directory = ByteBuffersDirectory()
    analyzer = StandardAnalyzer()
    config = IndexWriterConfig(analyzer)
    writer = IndexWriter(directory, config)
    
    
    
    with open(json_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    for d in documents:
        doc = Document()
        doc.add(TextField("title", d['title'], Field.Store.YES))
        doc.add(TextField("abstract", d['abstract'], Field.Store.YES))
        doc.add(TextField("corpus", d['corpus'], Field.Store.YES))
        doc.add(TextField("keywords", d['keywords'], Field.Store.YES))
        doc.add(StringField("url", d['url'], Field.Store.YES))
        
        #scriviamo il documenti nell'indice
        writer.addDocument(doc)    
    #chiudiamo l'indice    
    writer.close()

    
    st.title("📚 Ricerca Documenti")

    with st.expander('🔧Filtra la tua ricerca!'):
        col1, col2, col3 = st.columns(3)
        with col1:
            title_true = st.checkbox("Titolo")
        with col2:
            abstract_true = st.checkbox("Abstract")
        with col3:
            corpus_true = st.checkbox("Corpus")

    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
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
    test_pylucene()