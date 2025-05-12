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
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve
import numpy as np
import yake
import tempfile
import nltk
from nltk.tokenize import word_tokenize
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

def calculate_precision_recall(searcher, query_string, ranking_type="BM25", threshold=0.5):
    """
    Calculate precision and recall for a determined query.
    """
    try:
        # Esegui la ricerca
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else:
            searcher.setSimilarity(ClassicSimilarity())
            
        analyzer = StandardAnalyzer()
        query = parse_advanced_query(query_string, analyzer)
        results = searcher.search(query, 100)

        if not results or results.totalHits.value == 0:
            return [], [], []

        # Normalizza gli scores in modo più robusto
        scores = np.array([scoreDoc.score for scoreDoc in results.scoreDocs])
        if len(scores) == 0:
            return [], [], []
            
        # Normalizzazione min-max invece che solo max
        min_score = np.min(scores)
        max_score = np.max(scores)
        if max_score == min_score:
            normalized_scores = np.ones_like(scores)
        else:
            normalized_scores = (scores - min_score) / (max_score - min_score)

        # Usa una soglia adattiva basata sulla distribuzione degli scores
        if threshold is None:
            threshold = np.percentile(normalized_scores, 70)  # top 30% come rilevanti
            
        # Calcola y_true
        y_true = np.where(normalized_scores >= threshold, 1, 0)
        
        if not (np.any(y_true == 1) and np.any(y_true == 0)):
            return [], [], []
        
        # Calcola precision-recall
        precision_values, recall_values, _ = precision_recall_curve(y_true, normalized_scores)
        
        # Filtro i valori per rimuovere duplicati e ordinare
        unique_idx = np.unique(recall_values, return_index=True)[1]
        precision_values = precision_values[unique_idx]
        recall_values = recall_values[unique_idx]
        
        return precision_values.tolist(), recall_values.tolist(), normalized_scores.tolist()

    except Exception as e:
        print(f"Errore nel calcolo precision-recall: {str(e)}")
        return [], [], []

def plot_precision_recall_curve(precision_values, recall_values, query_string):
    """
    Genera il grafico precision-recall.
    """
    try:
        plt.figure(figsize=(10, 6))
        
        # Ordina i valori per recall crescente per una curva più pulita
        sorting_idx = np.argsort(recall_values)
        recall_values = np.array(recall_values)[sorting_idx]
        precision_values = np.array(precision_values)[sorting_idx]
        
        # Plotting
        plt.plot(recall_values, precision_values, 'b-', label='P/R curve')
        
        # Aggiungi media precision e recall come linee tratteggiate
        avg_precision = np.mean(precision_values)
        avg_recall = np.mean(recall_values)
        
        plt.axhline(y=avg_precision, color='r', linestyle='--', 
                   label=f'Avg Precision: {avg_precision:.3f}')
        plt.axvline(x=avg_recall, color='g', linestyle='--', 
                   label=f'Avg Recall: {avg_recall:.3f}')
        
        # Configurazione del grafico
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title(f'Precision-Recall Curve\nQuery: "{query_string}"')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(loc='lower left')
        
        # Imposta i limiti degli assi da 0 a 1
        plt.xlim([-0.05, 1.05])
        plt.ylim([-0.05, 1.05])

        # Salva il grafico
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, bbox_inches='tight', dpi=300)
            plt.close()
            return tmp.name

    except Exception as e:
        print(f"Errore nella generazione del grafico: {str(e)}")
        return None

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
        return None, None, None
    
    try:
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else:
            searcher.setSimilarity(ClassicSimilarity())
            
        analyzer = StandardAnalyzer()
        
        # If the query contains field-specific searches, ignore the checkboxes
        if ':' in query_string:
            query = parse_advanced_query(query_string, analyzer)
        else:
            # Use the original checkbox-based logic
            query_builder = BooleanQuery.Builder()
            expanded_query = expand_query(query_string)
            
            if title_true:
                title_query = QueryParser("title", analyzer).parse(expanded_query)
                query_builder.add(title_query, BooleanClause.Occur.SHOULD)
            if abstract_true:
                abstract_query = QueryParser("abstract", analyzer).parse(expanded_query)
                query_builder.add(abstract_query, BooleanClause.Occur.SHOULD)
            if corpus_true:
                corpus_query = QueryParser("corpus", analyzer).parse(expanded_query)
                query_builder.add(corpus_query, BooleanClause.Occur.SHOULD)
            
            query = query_builder.build()
        
        results = searcher.search(query, 100)
        
        # Calcola precision-recall
        precision_values, recall_values, scores = calculate_precision_recall(
            searcher, query_string, ranking_type
        )
        
        # Genera il grafico
        plot_path = None
        if precision_values and recall_values:
            plot_path = plot_precision_recall_curve(
                precision_values, recall_values, query_string
            )

        return results, (precision_values, recall_values), plot_path
        
    except Exception as e:
        print(f"Errore durante la ricerca: {e}")
        return None, None, None

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
            windowsSize=1,
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
        
        return final_query

    except Exception as e:
        print(f"Errore nell'espansione della query: {e}")
        return query_string  # Fallback to original query

def parse_advanced_query(query_string, analyzer):
    """
    Parse a query string that may contain field-specific searches.
    Example: "title:space AND corpus:python" or "abstract:law OR title:justice"
    """
    query_builder = BooleanQuery.Builder()
    
    # Split the query by AND/OR operators
    parts = query_string.split(' AND ')
    for and_part in parts:
        or_parts = and_part.split(' OR ')
        or_builder = BooleanQuery.Builder()
        
        for part in or_parts:
            if ':' in part:
                # Field-specific search
                field, term = part.split(':', 1)
                field = field.lower().strip()
                term = term.strip()
                if field in ['title', 'abstract', 'corpus', 'keywords']:
                    expanded_term = expand_query(term)
                    field_query = QueryParser(field, analyzer).parse(expanded_term)
                    or_builder.add(field_query, BooleanClause.Occur.SHOULD)
            else:
                # Default search in all fields
                term = part.strip()
                if term:
                    expanded_term = expand_query(term)
                    title_query = QueryParser("title", analyzer).parse(expanded_term)
                    abstract_query = QueryParser("abstract", analyzer).parse(expanded_term)
                    corpus_query = QueryParser("corpus", analyzer).parse(expanded_term)
                    
                    or_builder.add(title_query, BooleanClause.Occur.SHOULD)
                    or_builder.add(abstract_query, BooleanClause.Occur.SHOULD)
                    or_builder.add(corpus_query, BooleanClause.Occur.SHOULD)
        
        or_query = or_builder.build()
        query_builder.add(or_query, BooleanClause.Occur.MUST)
    
    return query_builder.build()

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