"""!
@file Pylucene.py
@brief PyLucene search engine implementation for JuriScan
@details This module provides PyLucene-based document indexing and searching capabilities
         with support for BM25 and Classic similarity algorithms.
@author Magni && Testoni
@date 2025
"""

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
    """!
    @brief Initialize the Java Virtual Machine for PyLucene
    @details Sets up the JVM with headless configuration for server environments.
             Attaches the current thread to the JVM if it's already initialized.
    @return None
    @throws Exception if JVM initialization fails
    """
    if not lucene.getVMEnv():
        print("Inizializzazione JVM...")
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    env = lucene.getVMEnv()
    env.attachCurrentThread()

# Rinominata da expand_query e leggermente affinata
def expand_natural_language_query(natural_language_string):
    """!
    @brief Expand a natural language phrase using NLP techniques.
    @param natural_language_string The natural language phrase to expand.
    @return Expanded query string formatted for Lucene, OR-ing terms.
    @details Uses YAKE for keyword extraction, NLTK for NLP processing, and WordNet
             for semantic expansion with synonyms. Hypernyms and hyponyms are generally excluded for precision.
    """
    try:
        # 1. Keyword extraction with YAKE
        kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,
            dedupLim=0.9,
            dedupFunc='seqm',
            windowsSize=1,
            top=5, # Extract top 5 keywords
            features=None
        )
        yake_keywords_with_scores = kw_extractor.extract_keywords(natural_language_string)
        yake_keywords = [kw[0].lower() for kw in yake_keywords_with_scores]

        # 2. NLP Processing for WordNet expansion
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))
        
        tokens = word_tokenize(natural_language_string.lower())
        # Filter out stopwords, non-alphanumeric, and common Lucene operators if they appear as simple tokens
        lucene_operators_as_tokens = {'and', 'or', 'not', 'to'} 
        processed_tokens = [
            token for token in tokens 
            if token.isalnum() and token not in stop_words and token not in lucene_operators_as_tokens
        ]
        
        pos_tags = pos_tag(processed_tokens)
        lemmatized_terms_for_wordnet = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) 
                                       for word, tag in pos_tags]

        # 3. Semantic Expansion using WordNet (focus on synonyms from the first synset)
        wordnet_expanded_terms = set()
        for term in lemmatized_terms_for_wordnet:
            synsets = wordnet.synsets(term)
            if synsets: # Check if synsets are found
                first_synset = synsets[0] # Use only the first, most relevant synset
                for lemma in first_synset.lemmas():
                    synonym = lemma.name().lower().replace('_', ' ') # Replace underscores with spaces for phrases
                    if synonym not in stop_words and len(synonym) > 2: # Basic cleaning for synonyms
                        wordnet_expanded_terms.add(synonym)
        
        # 4. Combine and Clean Terms
        final_terms_set = set(yake_keywords) # Start with YAKE keywords
        final_terms_set.update(lemmatized_terms_for_wordnet) # Add lemmatized original terms
        final_terms_set.update(wordnet_expanded_terms) # Add WordNet synonyms
        
        # Final cleaning of all collected terms
        final_cleaned_terms = {
            term for term in final_terms_set
            if term not in stop_words and len(term) > 2 and term.strip() # Ensure not empty after strip
        }

        # 5. Build Lucene Query string
        query_parts = []
        # Add YAKE keywords with higher boost, handle phrases by quoting
        for kw in yake_keywords:
            if kw in final_cleaned_terms: 
                query_parts.append(f'("{kw}")^2' if ' ' in kw else f'({kw})^2')
                final_cleaned_terms.discard(kw) # Avoid re-adding

        # Add remaining cleaned terms (original lemmatized, synonyms) with default boost
        for term in final_cleaned_terms:
            query_parts.append(f'"{term}"' if ' ' in term else term) # Quote phrases
        
        if not query_parts:
            print(f"Warning: Query expansion for '{natural_language_string}' resulted in no terms. Falling back to escaped original.")
            return QueryParser.escape(natural_language_string)

        expanded_lucene_query = ' OR '.join(query_parts)
        return expanded_lucene_query

    except Exception as e:
        print(f"Errore nell'espansione della query (NL) '{natural_language_string}': {e}")
        return QueryParser.escape(natural_language_string) # Fallback to escaped original query


def calculate_precision_recall(searcher, query_string_for_search, ranking_type="BM25", threshold=0.5):
    """!
    @brief Calculate precision and recall metrics for a given query (INTERNAL HEURISTIC)
    @note This function's output (precision/recall values based on score threshold)
          is NOT directly used by benchmark.py for its final P@k, R@k, MAP metrics,
          as benchmark.py uses JudgedPool.json. This is more for internal diagnostics if needed.
          Uses the provided query_string_for_search directly.
    """
    try:
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else:
            searcher.setSimilarity(ClassicSimilarity())
            
        query_builder = BooleanQuery.Builder()
        analyzer = StandardAnalyzer()
        
        # This internal P/R uses the query_string_for_search as is (already expanded if it was NL).
        # It builds a SHOULD query across standard fields for its heuristic P/R.
        # This part is not critical for benchmark.py's metrics.
        q_title = QueryParser("title", analyzer).parse(query_string_for_search)
        q_abstract = QueryParser("abstract", analyzer).parse(query_string_for_search)
        q_corpus = QueryParser("corpus", analyzer).parse(query_string_for_search)
        
        query_builder.add(q_title, BooleanClause.Occur.SHOULD)
        query_builder.add(q_abstract, BooleanClause.Occur.SHOULD)
        query_builder.add(q_corpus, BooleanClause.Occur.SHOULD)
        
        query = query_builder.build()
        results = searcher.search(query, 100)

        if not results or results.totalHits.value == 0:
            return [], [], []

        scores = np.array([scoreDoc.score for scoreDoc in results.scoreDocs])
        if len(scores) == 0: return [], [], []
            
        min_score = np.min(scores)
        max_score = np.max(scores)
        if max_score == min_score: # Avoid division by zero; handle all same scores
            normalized_scores = np.ones_like(scores) if max_score > 0 else np.zeros_like(scores)
        else:
            normalized_scores = (scores - min_score) / (max_score - min_score)

        current_threshold = threshold if threshold is not None else np.percentile(normalized_scores, 70)
        y_true = np.where(normalized_scores >= current_threshold, 1, 0)
        
        if not (np.any(y_true == 1) and np.any(y_true == 0)): # Need both classes for curve
            return [], [], [] 
        
        precision_values, recall_values, _ = precision_recall_curve(y_true, normalized_scores)
        
        if len(recall_values) > 0:
            unique_idx = np.unique(recall_values, return_index=True)[1]
            return precision_values[unique_idx].tolist(), recall_values[unique_idx].tolist(), normalized_scores.tolist()
        else:
            return [], [], []

    except Exception as e:
        # Be more specific about where this error is coming from
        print(f"Errore nel calcolo precision-recall (interno Pylucene.py, query='{query_string_for_search}'): {str(e)}")
        return [], [], []

def search_documents(searcher, title_true, abstract_true, corpus_true, query_string, ranking_type):
    """!
    @brief Main search function for PyLucene engine
    @param searcher The Lucene IndexSearcher object
    @param title_true Boolean flag to search in title field (used if query is natural language)
    @param abstract_true Boolean flag to search in abstract field (used if query is natural language)
    @param corpus_true Boolean flag to search in corpus field (used if query is natural language)
    @param query_string The search query string. Can be natural language or Lucene syntax.
    @param ranking_type Ranking algorithm to use ("BM25" or "TFIDF" which maps to ClassicSimilarity)
    @return Tuple containing (results_object, precision_recall_data_tuple_or_None, None_for_plot_path)
    """
    if not query_string.strip():
        return None, None, None
    
    try:
        if ranking_type == "BM25":
            searcher.setSimilarity(BM25Similarity())
        else: 
            searcher.setSimilarity(ClassicSimilarity())
            
        analyzer = StandardAnalyzer()
        
        # Heuristic to detect if query_string is likely Lucene syntax
        # This check can be refined, but covers common cases.
        is_lucene_syntax_query = any(op in query_string for op in [':', ' AND ', ' OR ', ' NOT ', '(', ')', '"', '*', '?']) or \
                                 any(op in query_string.upper() for op in [' AND ', ' OR ', ' NOT '])

        query_for_internal_pr = query_string # For the heuristic P/R calculation

        if not is_lucene_syntax_query and (title_true or abstract_true or corpus_true):
            # Query seems to be natural language, and specific fields are targeted for search
            expanded_nl_query = expand_natural_language_query(query_string)
            query_for_internal_pr = expanded_nl_query # Use expanded for internal P/R
            
            query_builder = BooleanQuery.Builder()
            # Build a SHOULD query across the selected fields for the expanded natural language query
            if title_true:
                q_title = QueryParser("title", analyzer).parse(expanded_nl_query)
                query_builder.add(q_title, BooleanClause.Occur.SHOULD)
            if abstract_true:
                q_abstract = QueryParser("abstract", analyzer).parse(expanded_nl_query)
                query_builder.add(q_abstract, BooleanClause.Occur.SHOULD)
            if corpus_true: # Default to corpus if no other field is true, or if it's selected
                q_corpus = QueryParser("corpus", analyzer).parse(expanded_nl_query)
                query_builder.add(q_corpus, BooleanClause.Occur.SHOULD)
            
            # Ensure at least one clause was added if fields were true
            if not (title_true or abstract_true or corpus_true):
                 print(f"Warning: Natural language query '{query_string}' but no fields selected for search.")
                 return None, None, None # Or search a default field

            final_query_obj = query_builder.build()
            if not final_query_obj.clauses(): # Check if any clauses were actually added
                print(f"Warning: No clauses built for natural language query '{query_string}'. Defaulting to corpus search.")
                # Fallback: search expanded query against corpus if builder is empty for some reason
                final_query_obj = QueryParser("corpus", analyzer).parse(expanded_nl_query)

        else:
            # Query is likely Lucene syntax, or it's a general query without specific field flags for NL expansion
            # Parse it directly. QueryParser uses "corpus" as default field for terms without explicit field.
            # Fields specified in query_string (e.g., title:term) will be respected.
            query_parser = QueryParser("corpus", analyzer) # Default field for terms without specifier
            # query_parser.setAllowLeadingWildcard(True) # Consider if needed
            # query_parser.setEnablePositionIncrements(True) # Good default
            final_query_obj = query_parser.parse(query_string)
            # query_for_internal_pr remains original query_string

        results = searcher.search(final_query_obj, 100) # Max 100 results

        # Internal P/R calculation (heuristic, not benchmark's final metrics)
        # Pass the query string that was effectively used or representative for internal P/R
        pr_values, rc_values, _ = calculate_precision_recall(
            searcher, query_for_internal_pr, ranking_type
        )
        
        return results, (pr_values, rc_values), None
        
    except Exception as e:
        print(f"Errore durante la ricerca (query: '{query_string}'): {e}")
        # import traceback # Uncomment for debugging
        # traceback.print_exc()
        return None, None, None

def get_wordnet_pos(tag):
    """!
    @brief Map NLTK POS tags to WordNet POS tags for lemmatization
    @param tag NLTK POS tag string
    @return WordNet POS tag constant
    @details Converts NLTK part-of-speech tags to WordNet format for accurate lemmatization
    """
    tag_dict = {
        'N': wordnet.NOUN,
        'V': wordnet.VERB,
        'R': wordnet.ADV,
        'J': wordnet.ADJ
    }
    return tag_dict.get(tag[0], wordnet.NOUN)

# Percorsi base
project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
index_file = str(project_root / "SearchEngine/index")

def index_exists(index_path):
    """!
    @brief Check if a valid Lucene index exists at the specified path
    @param index_path Path to the index directory
    @return True if valid index exists, False otherwise
    @details Verifies both directory existence and index validity using DirectoryReader
    """
    try:
        directory = FSDirectory.open(Paths.get(index_path))
        return DirectoryReader.indexExists(directory)
    except Exception:
        return False

def create_index():
    """!
    @brief Create or open PyLucene index for document searching
    @return Tuple containing (directory, searcher) objects
    @details Creates new index if none exists, otherwise opens existing index.
             Processes documents from JSON file using incremental parsing for memory efficiency.
    @throws Exception if indexing fails or JVM initialization problems occur
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
if __name__ == "__main__":
    print("Avvio indicizzazione...")
    directory, searcher = create_index()
    print("Indice creato e pronto per la ricerca")