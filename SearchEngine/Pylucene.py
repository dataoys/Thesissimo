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
    
    Supports both field-specific and checkbox-based searches.
    """
    if not query_string.strip():
        return None, None, None
    
    try:
        # Set similarity based on ranking type
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else:
            searcher.setSimilarity(ClassicSimilarity())
            
        analyzer = StandardAnalyzer()
        
        # Build query based on search type
        if ':' in query_string:
            # Field-specific search
            query = parse_advanced_query(query_string, analyzer)
        else:
            # Checkbox-based search
            query_builder = BooleanQuery.Builder()
            
            if title_true:
                parser = QueryParser("title", analyzer)
                title_query = parser.parse(query_string)
                query_builder.add(title_query, BooleanClause.Occur.SHOULD)
                
            if abstract_true:
                parser = QueryParser("abstract", analyzer)
                abstract_query = parser.parse(query_string)
                query_builder.add(abstract_query, BooleanClause.Occur.SHOULD)
                
            if corpus_true:
                parser = QueryParser("corpus", analyzer)
                corpus_query = parser.parse(query_string)
                query_builder.add(corpus_query, BooleanClause.Occur.SHOULD)
                
            if not any([title_true, abstract_true, corpus_true]):
                return None, None, None
                
            query = query_builder.build()
        
        # Execute search
        results = searcher.search(query, 100)
        
        # Calculate precision-recall metrics
        precision_values, recall_values, scores = calculate_precision_recall(
            searcher, query_string, ranking_type
        )
        
        # Generate precision-recall plot
        plot_path = None
        if precision_values and recall_values:
            plot_path = plot_precision_recall_curve(
                precision_values,
                recall_values,
                query_string
            )
            
        return results, plot_path, scores
        
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
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))
        
        # Tokenization and initial cleaning
        tokens = word_tokenize(query_string.lower())
        tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
        
        # POS tagging and lemmatization
        pos_tags = pos_tag(tokens)
        lemmatized = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) 
                     for word, tag in pos_tags]

        # 3. Semantic Expansion
        expanded_terms = set()
        expanded_terms.update(lemmatized)
        expanded_terms.update(keywords)
        
        # WordNet expansions
        for term in lemmatized:
            synsets = wordnet.synsets(term)
            for synset in synsets[:2]:  # Limit to top 2 synsets per term
                # Add synonyms
                expanded_terms.update(
                    lemma.name().lower()
                    for lemma in synset.lemmas()
                    if lemma.name().lower() not in stop_words
                )
                
                # Add hypernyms (more general terms)
                for hypernym in synset.hypernyms():
                    expanded_terms.update(
                        lemma.name().lower()
                        for lemma in hypernym.lemmas()
                        if lemma.name().lower() not in stop_words
                    )
                
                # Add hyponyms (more specific terms)
                for hyponym in synset.hyponyms()[:2]:  # Limit hyponyms
                    expanded_terms.update(
                        lemma.name().lower()
                        for lemma in hyponym.lemmas()
                        if lemma.name().lower() not in stop_words
                    )

        # 4. Clean expanded terms
        cleaned_terms = {
            term.replace('_', ' ') 
            for term in expanded_terms 
            if len(term) > 2
        }

        # 5. Build Lucene query
        query_parts = []
        
        # Boost original keywords
        for keyword in keywords:
            query_parts.append(f'({keyword})^2')
            
        # Add other terms
        other_terms = cleaned_terms - set(keywords)
        query_parts.extend(other_terms)
        
        # Build final query with OR operator
        final_query = ' OR '.join(query_parts)
        return final_query

    except Exception as e:
        print(f"Error expanding query: {e}")
        return query_string  # Fallback to original query

def parse_advanced_query(query_string, analyzer):
    """
    Parse a query string that may contain field-specific searches.
    Example: "title:space AND corpus:python" or "abstract:law OR title:justice"
    """
    query_builder = BooleanQuery.Builder()
    
    # Split by AND first
    and_parts = query_string.split(' AND ')
    for and_part in and_parts:
        # Handle OR parts within each AND clause
        or_parts = and_part.split(' OR ')
        or_query_builder = BooleanQuery.Builder()
        
        for or_part in or_parts:
            if ':' in or_part:
                field, term = or_part.split(':', 1)
                field = field.lower().strip()
                term = term.strip().strip('"').strip("'").strip()
                
                if field in ['title', 'abstract', 'corpus']:
                    parser = QueryParser(field, analyzer)
                    field_query = parser.parse(term)
                    or_query_builder.add(field_query, BooleanClause.Occur.SHOULD)
            else:
                # If no field is specified, search in all fields
                term = or_part.strip()
                for field in ['title', 'abstract', 'corpus']:
                    parser = QueryParser(field, analyzer)
                    field_query = parser.parse(term)
                    or_query_builder.add(field_query, BooleanClause.Occur.SHOULD)
        
        # Add the OR combination to main query with MUST (AND)
        query_builder.add(or_query_builder.build(), BooleanClause.Occur.MUST)
    
    return query_builder.build()

def build_checkbox_query(query_string, title_true, abstract_true, corpus_true, analyzer):
    """
    Build a query based on checkbox selections and search terms.
    
    Args:
        query_string (str): The search terms
        title_true (bool): Whether to search in title
        abstract_true (bool): Whether to search in abstract
        corpus_true (bool): Whether to search in corpus
        analyzer (StandardAnalyzer): The Lucene analyzer to use
        
    Returns:
        Query: A Lucene query object
    """
    query_builder = BooleanQuery.Builder()
    expanded_terms = expand_query(query_string)
    
    if not any([title_true, abstract_true, corpus_true]):
        return None
        
    if title_true:
        title_query = QueryParser("title", analyzer).parse(expanded_terms)
        query_builder.add(title_query, BooleanClause.Occur.SHOULD)
        
    if abstract_true:
        abstract_query = QueryParser("abstract", analyzer).parse(expanded_terms)
        query_builder.add(abstract_query, BooleanClause.Occur.SHOULD)
        
    if corpus_true:
        corpus_query = QueryParser("corpus", analyzer).parse(expanded_terms)
        query_builder.add(corpus_query, BooleanClause.Occur.SHOULD)
        
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