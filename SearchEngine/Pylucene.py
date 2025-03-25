import lucene
try:
    lucene.initVM()
except ValueError:
    pass  # JVM è già in esecuzione, ignoriamo l'errore

from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader
from org.apache.lucene.document import Document, Field, StringField, TextField 
from org.apache.lucene.search import IndexSearcher, BooleanQuery, BooleanClause
from org.apache.lucene.queryparser.classic import QueryParser
from java.nio.file import Paths

from pathlib import Path
import json
project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
index_file= str(project_root / "SearchEngine/index")

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

from org.apache.lucene.search.similarities import BM25Similarity, ClassicSimilarity

def search_documents(searcher, title_true, abstract_true, corpus_true, query_string, ranking_type):
    """
    Search documents in the index with the specified ranking type.

    Arguments:
        searcher (IndexSearcher): The Lucene IndexSearcher object.
        title_true (bool): Whether to search in the title field.
        abstract_true (bool): Whether to search in the abstract field.
        corpus_true (bool): Whether to search in the corpus field.
        query_string (str): The user's query string.
        ranking_type (str): The ranking type to use ("BM25" or "TF_IDF").

    Returns:
        TopDocs: The search results.
    """
    analyzer = StandardAnalyzer()
    boolean_query = BooleanQuery.Builder()

    # Verifica che la query non sia vuota
    if not query_string or query_string.isspace():
        return None

    # Espansione della query
    expanded_query_string = expand_query(query_string)

    # Aggiungi i campi alla query booleana
    if title_true:
        title_query = QueryParser("title", analyzer).parse(expanded_query_string)
        boolean_query.add(title_query, BooleanClause.Occur.SHOULD)
    if abstract_true:
        abstract_query = QueryParser("abstract", analyzer).parse(expanded_query_string)
        boolean_query.add(abstract_query, BooleanClause.Occur.SHOULD)
    if corpus_true:
        corpus_query = QueryParser("corpus", analyzer).parse(expanded_query_string)
        boolean_query.add(corpus_query, BooleanClause.Occur.SHOULD)

    # Costruisci la query
    query = boolean_query.build()

    # Configura la funzione di ranking in base alla scelta dell'utente
    if ranking_type == "BM25":
        searcher.setSimilarity(BM25Similarity())  # BM25 con parametri predefiniti
    elif ranking_type == "TF_IDF":
        searcher.setSimilarity(ClassicSimilarity())  # TF-IDF

    # Esegui la ricerca
    results = searcher.search(query, 10)  # Limita i risultati a 10 documenti
    return results

def create_index():
    # Attacca il thread corrente alla JVM. Con Streamlit, che usa thread multipli, 
    # dobbiamo assicurarci che il thread corrente sia collegato alla JVM prima di usare 
    # le funzionalità di Lucene.
    env = lucene.getVMEnv()
    env.attachCurrentThread()

    # Creazione dell'indice in memoria
    directory = FSDirectory.open(Paths.get(index_file))
    config = IndexWriterConfig(StandardAnalyzer())
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
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
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    return directory, searcher

