import lucene
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader
from org.apache.lucene.document import Document, Field, StringField, TextField 
from org.apache.lucene.search import IndexSearcher, BooleanQuery, BooleanClause
from org.apache.lucene.queryparser.classic import QueryParser
from java.nio.file import Paths
from org.apache.lucene.search.similarities import BM25Similarity, ClassicSimilarity

from pathlib import Path
import ijson
project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
index_file= str(project_root / "SearchEngine/index")

import yake
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer

# Scarico le risorse di NLTK necessarie
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    nltk.download('stopwords')

def initialize_jvm():
    if not lucene.getVMEnv():
        print("Inizializzazione JVM...")
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    env = lucene.getVMEnv()
    env.attachCurrentThread()

def search_documents(searcher, title_true, abstract_true, corpus_true, query_string, ranking_type):
    """
    Search Engine PyLucene Function.
    
    This function takes the user's input string from the search bar, and 3 boolean values that represent
    the user's choice of where to search (title, abstract, corpus).
    
    Arguments:
        searcher (IndexSearcher): The Lucene searcher object
        title_true (bool): Search in title
        abstract_true (bool): Search in abstract
        corpus_true (bool): Search in corpus
        query_string (str): The user's input
        ranking_type (str): The ranking method to use ("TF_IDF" or "BM25")
        
    Returns:
        TopDocs: Lucene search results
    """
    if not query_string.strip():
        return None
        
    if not any([title_true, abstract_true, corpus_true]):
        return None
    
    try:
        # Espandi la query
        expanded_query = expand_query(query_string)
        
        # Configura il ranking
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else:  # TF_IDF
            searcher.setSimilarity(ClassicSimilarity())
            
        # Crea la query booleana
        query_builder = BooleanQuery.Builder()
        analyzer = StandardAnalyzer()
        
        # Aggiungi campi alla ricerca in base ai filtri
        if title_true:
            title_query = QueryParser("title", analyzer).parse(expanded_query)
            query_builder.add(title_query, BooleanClause.Occur.SHOULD)
            
        if abstract_true:
            abstract_query = QueryParser("abstract", analyzer).parse(expanded_query)
            query_builder.add(abstract_query, BooleanClause.Occur.SHOULD)
            
        if corpus_true:
            corpus_query = QueryParser("corpus", analyzer).parse(expanded_query)
            query_builder.add(corpus_query, BooleanClause.Occur.SHOULD)
            
        # Esegui la ricerca
        query = query_builder.build()
        results = searcher.search(query, 100)  # Limitato a 100 risultati
        return results
        
    except Exception as e:
        print(f"Errore durante la ricerca: {e}")
        return None

def get_wordnet_pos(tag):
    """
    Maps NLTK POS tags to WordNet POS tags
    """
    tag_dict = {
        'N': wordnet.NOUN,
        'V': wordnet.VERB,
        'R': wordnet.ADV,
        'J': wordnet.ADJ
    }
    return tag_dict.get(tag[0], wordnet.NOUN)

def expand_query(query_string):
    """
    Expands a natural language query using YAKE for keyword extraction,
    NLTK for NLP processing, and WordNet for semantic expansion.
    
    Args:
        query_string (str): The natural language query
        
    Returns:
        str: Expanded query for Lucene
    """
    try:
        # 1. Keyword extraction with YAKE
        kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,
            dedupLim=0.9,
            dedupFunc='seqm',
            windowSize=1,
            top=5,
            features=None
        )
        keywords = [kw[0].lower() for kw in kw_extractor.extract_keywords(query_string)]

        # 2. NLP Processing
        # Initialize tools
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))
        
        # Tokenization and initial cleaning
        tokens = word_tokenize(query_string.lower())
        tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
        
        # POS tagging for better lemmatization
        pos_tags = pos_tag(tokens)
        
        # Lemmatization with POS tags
        lemmatized = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) 
                     for word, tag in pos_tags]

        # 3. Semantic Expansion
        expanded_terms = set()
        
        # Add original terms
        expanded_terms.update(lemmatized)
        expanded_terms.update(keywords)
        
        # Add WordNet expansions
        for term in lemmatized:
            # Get synsets
            synsets = wordnet.synsets(term)
            
            for synset in synsets[:2]:  # Limit to top 2 synsets per term
                # Add synonyms
                expanded_terms.update(lemma.name().lower() 
                                   for lemma in synset.lemmas())
                
                # Add hypernyms (more general terms)
                expanded_terms.update(
                    lemma.name().lower()
                    for hypernym in synset.hypernyms()
                    for lemma in hypernym.lemmas()
                )
                
                # Add hyponyms (more specific terms)
                expanded_terms.update(
                    lemma.name().lower()
                    for hyponym in synset.hyponyms()[:2]  # Limit hyponyms
                    for lemma in hyponym.lemmas()
                )

        # 4. Clean and format expanded terms
        # Remove underscores, stopwords, and short terms
        cleaned_terms = {
            term.replace('_', ' ') 
            for term in expanded_terms 
            if term not in stop_words and len(term) > 2
        }

        # 5. Build Lucene query
        # Combine terms with OR operator and boost important terms
        query_parts = []
        
        # Boost original keywords
        for keyword in keywords:
            query_parts.append(f'({keyword})^2')
            
        # Add other terms
        query_parts.extend(list(cleaned_terms - set(keywords)))
        
        final_query = ' OR '.join(query_parts)
        
        print(f"Query espansa: {final_query}")  # Debug
        return final_query

    except Exception as e:
        print(f"Errore nell'espansione della query: {e}")
        return query_string  # Fallback to original query

# Percorsi base
project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
index_file = str(project_root / "SearchEngine/index")

def index_exists(index_path):
    """
    Check if a valid index exists at the specified path.
    """
    try:
        directory = FSDirectory.open(Paths.get(index_path))
        return DirectoryReader.indexExists(directory)
    except Exception:
        return False

def create_index():
    """
    Creates a new index only if it doesn't exist, otherwise opens the existing one.
    """
    # Inizializziamo la JVM
    initialize_jvm()

    print("Verifico esistenza indice...")
    
    # Verifica se l'indice esiste
    if index_exists(index_file):
        print("Indice esistente trovato, apertura in corso...")
        directory = FSDirectory.open(Paths.get(index_file))
        reader = DirectoryReader.open(directory)
        searcher = IndexSearcher(reader)
        return directory, searcher
    
    print("Creazione nuovo indice...")
    
    # Setup base per nuovo indice
    directory = FSDirectory.open(Paths.get(index_file))
    config = IndexWriterConfig(StandardAnalyzer())
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    writer = IndexWriter(directory, config)
    
    total_docs = 0
    
    try:
        print("Inizio lettura documenti...")
        with open(json_file, 'rb') as f:
            parser = ijson.parse(f)
            current_doc = {}
            
            for prefix, event, value in parser:
                if prefix.endswith('.id'):
                    if current_doc:
                        try:
                            doc = Document()
                            doc.add(StringField("id", str(current_doc.get('id', '')), Field.Store.YES))
                            doc.add(TextField("title", str(current_doc.get('title', '')), Field.Store.YES))
                            doc.add(TextField("abstract", str(current_doc.get('abstract', '')), Field.Store.YES))
                            doc.add(TextField("corpus", str(current_doc.get('corpus', '')), Field.Store.YES))
                            doc.add(TextField("keywords", str(current_doc.get('keywords', '')), Field.Store.YES))
                            doc.add(TextField("url", str(current_doc.get('url', '')), Field.Store.YES))
                            
                            writer.addDocument(doc)
                            total_docs += 1
                            
                            if total_docs % 1000 == 0:
                                print(f"Indicizzati {total_docs} documenti")
                                writer.commit()
                        except:
                            print("Indicizzazione documento fallita")
                            
                    current_doc = {'id': value}
                elif prefix.endswith('.title'):
                    current_doc['title'] = value
                elif prefix.endswith('.abstract'):
                    current_doc['abstract'] = value
                elif prefix.endswith('.corpus'):
                    current_doc['corpus'] = value
                elif prefix.endswith('.keywords'):
                    current_doc['keywords'] = value
                elif prefix.endswith('.url'):
                    current_doc['url'] = value

        # Commit finale
        writer.commit()
        print(f"Indicizzazione completata! Documenti totali: {total_docs}")

    except Exception as e:
        print(f"Errore durante l'indicizzazione: {e}")
        raise
    finally:
        writer.close()
    
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    return directory, searcher

#RIMUOVERE COMMENTO ED ESEGUIRE PER GENERARE INDICE
#if __name__ == "__main__":
    print("Avvio indicizzazione...")
    directory, searcher = create_index()
    print("Indice creato e pronto per la ricerca")