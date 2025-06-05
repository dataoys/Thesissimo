"""!
@file Whoosh.py
@brief Whoosh search engine implementation for JuriScan
@details Pure Python search engine with advanced NLP features and semantic query expansion
@author Magni && Testoni
@date 2025
"""

import os
import ijson
from whoosh.index import create_in
from whoosh import index as whoosh_module_index # Alias to avoid conflict
from whoosh.fields import Schema, TEXT, ID
from whoosh.scoring import TF_IDF, BM25F
from whoosh.qparser import OrGroup, MultifieldParser
from whoosh.analysis import StemmingAnalyzer
from whoosh import qparser
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer
import nltk
import yake  
from pathlib import Path # Import Path
import traceback # For detailed error printing

# Add this function after the imports
def setup_nltk():
    """!
    @brief Download and setup required NLTK resources
    @details Downloads WordNet, POS tagger, tokenizer, and stopwords if not available.
             Includes error handling and fallback mechanisms.
    @return None
    @throws Exception if NLTK resources cannot be downloaded
    """
    try:
        # Test if WordNet is available by trying to access a basic attribute or method
        # Using synsets as a more robust check than all_lemma_names for initialization
        nltk.corpus.wordnet.synsets('test')
        print("✅ NLTK resources (including WordNet) appear to be loaded.")
    except (LookupError, AttributeError) as e: # Catch AttributeError as well
        print(f"⏳ NLTK resources not found or WordNet not fully initialized ({e}). Downloading/Reloading...")
        try:
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('omw-1.4', quiet=True)  # Open Multilingual WordNet
            print("👍 NLTK resources downloaded.")
            # Attempt to force load WordNet after download
            from nltk.corpus import wordnet as wn
            wn.ensure_loaded()
            print("✅ NLTK WordNet explicitly loaded.")
        except Exception as e_download:
            print(f"❌ Error downloading or loading NLTK resources: {e_download}")
            # Consider raising an error or handling it if essential for app startup
            # For now, we'll let it proceed, but functionality might be impaired.

# Function to create index schema
def create_schema():
    """!
    @brief Generate Whoosh index schema for document structure
    @return Schema object configured for document fields
    @details Creates schema with ID, title, abstract, corpus, keywords, and URL fields.
             Uses stemming analyzer for text fields to improve search recall.
    """
    # Eseguiamo stemming di soli campi testuali significativi
    return Schema(
        id=ID(stored=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        abstract=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        corpus=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        keywords=TEXT(stored=True),
        url=TEXT(stored=True)
    )

# Creazione dell'indice
def create_whoosh_index_internal(index_dir):
    """!
    @brief Internal function to create new Whoosh index structure
    @param index_dir Path to the index directory
    @return Index object for the newly created index
    @details Creates directory if needed and initializes empty Whoosh index with schema
    """
    if not os.path.exists(index_dir):
        print(f"Creating directory for Whoosh index: {index_dir}")
        os.makedirs(index_dir) # Use makedirs to create parent dirs if needed
    schema = create_schema()
    print(f"Creating new Whoosh index in {index_dir} with schema.")
    ix = create_in(index_dir, schema)
    return ix

# Indicizzazione dei documenti in batch
def index_documents(index_dir, json_file, batch_size=1000):
    """!
    @brief Index documents from JSON file into Whoosh index
    @param index_dir Path to the index directory
    @param json_file Path to the JSON document file
    @param batch_size Number of documents to process in each batch (default: 1000)
    @return Index object for the populated index
    @details Forces rebuild of index, processes documents in batches for memory efficiency.
             Uses incremental JSON parsing to handle large files.
    """
    print(f"--- Starting Whoosh Indexing ---")
    print(f"Index directory: {index_dir}")
    print(f"JSON source file: {json_file}")
    # Crea un nuovo indice (forza la ricreazione)
    ix = create_whoosh_index_internal(index_dir)
    doc_count = 0
    
    try:
        # Leggere il file JSON in modo incrementale con ijson
        with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
            parser = ijson.parse(f)
            current_doc = {}
            batch = []
            
            for prefix, event, value in parser:
                if prefix.endswith('.id'):
                    if current_doc:  # Se abbiamo un documento completo, aggiungiamolo al batch
                        batch.append(current_doc)
                        current_doc = {}
                    current_doc['id'] = str(value)
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

                # Se il batch raggiunge la dimensione specificata, scrivilo nell'indice
                if len(batch) >= batch_size:
                    with ix.writer() as writer:
                        for doc in batch:
                            writer.add_document(
                                id=doc['id'],
                                title=doc.get('title', ''),
                                abstract=doc.get('abstract', ''),
                                corpus=doc.get('corpus', ''),
                                keywords=doc.get('keywords', ''),
                                url=doc.get('url', '')
                            )
                    doc_count += len(batch)
                    print(f"📦 Batch di {len(batch)} documenti indicizzati. Totale: {doc_count}")
                    batch = []

            # Gestisci l'ultimo documento e batch
            if current_doc:
                batch.append(current_doc)
            if batch:
                with ix.writer() as writer:
                    for doc in batch:
                        writer.add_document(
                            id=doc['id'],
                            title=doc.get('title', ''),
                            abstract=doc.get('abstract', ''),
                            corpus=doc.get('corpus', ''),
                            keywords=doc.get('keywords', ''),
                            url=doc.get('url', '')
                        )
                doc_count += len(batch)
                print(f"📦 Ultimo batch di {len(batch)} documenti indicizzati. Totale finale: {doc_count}")

    except Exception as e:
        print(f"❌ Errore durante l'indicizzazione: {e}")
        traceback.print_exc() # Print full traceback
        # raise # Re-raise if you want to stop execution
    
    print(f"✅ Indicizzazione completata! Totale documenti indicizzati: {doc_count}")
    return ix

# Funzione per cercare nei documenti indicizzati
def parse_advanced_query(query_string, schema):
    """!
    @brief Parse complex query strings with field specifications and operators
    @param query_string Query string to parse (may contain field:term AND/OR operators)
    @param schema Whoosh schema object for field validation
    @return Parsed Query object or None if parsing fails
    @details Handles field-specific searches, phrase queries, and logical operators.
             Expands non-field queries to search across multiple fields.
    """
    try:
        # Check if query has any field specifications
        has_field_specs = any(field + ":" in query_string for field in ['title', 'abstract', 'corpus', 'keywords'])
        
        # For queries without field specifications but with AND/OR operators
        if not has_field_specs and (" AND " in query_string or " OR " in query_string):
            print(f"Processing query without field specs: {query_string}")
            
            # Create a specific parser for non-field queries with AND/OR
            parser = qparser.QueryParser("content", schema)
            parser.add_plugin(qparser.GroupPlugin())
            parser.add_plugin(qparser.PhrasePlugin())
            
            # Split the query into terms respecting quotes
            terms = []
            current_term = ""
            in_quotes = False
            
            for char in query_string:
                if char == '"':
                    in_quotes = not in_quotes
                    current_term += char
                elif char == ' ' and not in_quotes:
                    if current_term:
                        terms.append(current_term)
                        current_term = ""
                else:
                    current_term += char
            
            if current_term:
                terms.append(current_term)
            
            # Build the query with appropriate operators
            final_query_parts = []
            i = 0
            while i < len(terms):
                if terms[i].upper() in ["AND", "OR"]:
                    # Skip operators
                    i += 1
                    continue
                    
                # Handle phrase (with quotes)
                term = terms[i].strip('"')
                
                # Build a sub-query that searches this term in all fields
                sub_query = []
                for field in ['title', 'abstract', 'corpus']:
                    if '"' in terms[i]:
                        # For phrases, keep them intact
                        sub_query.append(f'{field}:"{term}"')
                    else:
                        # For single terms
                        sub_query.append(f'{field}:{term}')
                
                final_query_parts.append("(" + " OR ".join(sub_query) + ")")
                
                # Check if we need to add an operator
                if i + 1 < len(terms) and terms[i+1].upper() in ["AND", "OR"]:
                    final_query_parts.append(terms[i+1])
                    i += 2
                else:
                    i += 1
            
            # Join all parts
            expanded_query = " ".join(final_query_parts)
            print(f"Expanded query: {expanded_query}")
            
            # Parse with a field-aware parser
            field_parser = qparser.QueryParser("content", schema)
            field_parser.add_plugin(qparser.FieldsPlugin())
            field_parser.add_plugin(qparser.PhrasePlugin())
            field_parser.add_plugin(qparser.OperatorsPlugin())
            
            return field_parser.parse(expanded_query)
            
        # For field-specific queries or simple queries
        elif has_field_specs:
            # Use a parser that respects field prefixes
            parser = qparser.QueryParser("content", schema)
            parser.add_plugin(qparser.FieldsPlugin())
        else:
            # For simple queries without operators, search across all fields
            parser = qparser.MultifieldParser(['title', 'abstract', 'corpus'], 
                                           schema,
                                           group=qparser.OrGroup)
        
        # Add plugins for advanced features
        parser.add_plugin(qparser.PhrasePlugin())
        parser.add_plugin(qparser.OperatorsPlugin())
        
        # Parse and return the query
        return parser.parse(query_string)
        
    except Exception as e:
        print(f"Error parsing advanced query: {e}")
        print(f"Query string was: {query_string}")
        import traceback
        traceback.print_exc()
        return None

def search_documents(index_dir, query_string, title_true, abstract_true, corpus_true, ranking_type):
    """!
    @brief Main search function for Whoosh engine
    @param index_dir Path to the Whoosh index directory
    @param query_string The search query string
    @param title_true Boolean flag to search in title field
    @param abstract_true Boolean flag to search in abstract field
    @param corpus_true Boolean flag to search in corpus field
    @param ranking_type Scoring algorithm ("TF_IDF" or "BM25F")
    @return List of tuples containing (id, title, abstract, corpus, keywords, score, url)
    @details Supports both simple and advanced query parsing with natural language processing
    """
    if not query_string.strip():
        return []
    
    print(f"\n--- Whoosh Search ---")
    print(f"Index dir: {index_dir}")
    print(f"Query: '{query_string}', Ranking: {ranking_type}")
    print(f"Fields - Title: {title_true}, Abstract: {abstract_true}, Corpus: {corpus_true}")

    # If no fields are selected, default to searching all fields
    if not any([title_true, abstract_true, corpus_true]):
        title_true = True
        abstract_true = True
        corpus_true = True

    # Choose scoring function
    if ranking_type == "TF_IDF":
        scorer = TF_IDF()
    else:
        scorer = BM25F() # Default to BM25F
    
    try:
        print(f"Attempting to open Whoosh index at: {index_dir}")
        ix = whoosh_module_index.open_dir(index_dir) # Use aliased import
        print(f"Whoosh index opened. Doc count: {ix.doc_count()}")
    except Exception as e:
        print(f"❌ Error opening Whoosh index at {index_dir}: {e}")
        traceback.print_exc()
        return []

    try:
        with ix.searcher(weighting=scorer) as searcher:
            # Use advanced parsing for complex queries with field specifications or AND/OR operators
            if ':' in query_string or ' AND ' in query_string or ' OR ' in query_string:
                print(f"Using advanced query parsing for: {query_string}")
                query_obj = parse_advanced_query(query_string, ix.schema)
                if query_obj is None:
                    print("Failed to parse advanced query")
                    return []
            else:
                # Simple query (no field specs, no AND/OR)
                print(f"Using simple query: {query_string}")
                
                # Determine fields to search based on checkboxes
                fields = []
                if title_true:
                    fields.append("title")
                if abstract_true:
                    fields.append("abstract")
                if corpus_true:
                    fields.append("corpus")
                
                # For phrase queries, preserve the exact phrase
                if '"' in query_string:
                    phrase_to_search = query_string  # Keep quotes intact
                else:
                    # Process the query for better results
                    phrase_to_search = process_natural_query(query_string)
                
                # Use MultifieldParser for simple queries
                parser = MultifieldParser(fields, ix.schema, group=OrGroup)
                parser.add_plugin(qparser.PhrasePlugin())
                query_obj = parser.parse(phrase_to_search)
            
            # Print the final query for debugging
            print(f"Final query object: {query_obj}")
            
            # Execute search
            results = searcher.search(query_obj, limit=100)
            print(f"Search returned {len(results)} results")
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append((
                    result['id'],
                    result['title'],
                    result['abstract'],
                    result['corpus'],
                    result['keywords'],
                    result.score,
                    result['url']
                ))
            
            return formatted_results
            
    except Exception as e:
        print(f"Error during Whoosh search: {e}")
        traceback.print_exc()
        return []

# Funzione per verificare se l'indice esiste e è valido
def index_exists_and_valid(index_dir):
    """!
    @brief Check if Whoosh index exists and contains documents
    @param index_dir Path to the index directory
    @return True if valid index with documents exists, False otherwise
    @details Verifies directory existence, index validity, and document count
    """
    
    if not os.path.exists(index_dir):
        return False
    try:
        # Prova ad aprire l'indice
        ix = whoosh_module_index.open_dir(index_dir) # Use aliased import
        with ix.searcher() as searcher:
            # Verifica che ci siano documenti
            return searcher.doc_count() > 0
    except:
        return False

def create_or_get_index(index_dir, json_file, force_rebuild=False):
    """!
    @brief Create new index or open existing Whoosh index
    @param index_dir Path to the index directory
    @param json_file Path to the JSON document file
    @param force_rebuild Force recreation of index even if it exists (default: False)
    @return Index object ready for searching
    @details Manages index lifecycle with lock file cleanup and rebuilding options
    """
    print(f"--- Whoosh create_or_get_index ---")
    print(f"Index dir: {index_dir}, JSON file: {json_file}, Force rebuild: {force_rebuild}")
    # Rimuovi eventuali lock residui
    lock_path = os.path.join(index_dir, 'LOCK')
    if os.path.exists(lock_path):
        os.remove(lock_path)

    try:
        if not force_rebuild and index_exists_and_valid(index_dir):
            print("🔄 Utilizzando l'indice Whoosh esistente...")
            return whoosh_module_index.open_dir(index_dir) # Use aliased import
        
        print(f"🔨 Creazione/Ricreazione indice Whoosh (force_rebuild={force_rebuild})...")
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
            
        # Indicizza i documenti e ritorna il nuovo indice
        return index_documents(index_dir, json_file)

    except Exception as e:
        print(f"❌ Errore durante la creazione/apertura dell'indice Whoosh: {e}")
        traceback.print_exc() # Print full traceback
        raise

def get_wordnet_pos(tag):
    """!
    @brief Map NLTK POS tag to WordNet POS tag for accurate lemmatization
    @param tag NLTK part-of-speech tag
    @return WordNet POS constant (NOUN, VERB, ADJ, ADV)
    @details Converts NLTK POS tags to WordNet format for proper lemmatization
    """
    tag_dict = {
        'N': wordnet.NOUN,
        'V': wordnet.VERB,
        'R': wordnet.ADV,
        'J': wordnet.ADJ
    }
    return tag_dict.get(tag[0], wordnet.NOUN)

def process_natural_query(query_string):
    """!
    @brief Process natural language query with NLP techniques
    @param query_string The natural language query to process
    @return Processed query string with expanded terms
    @details Uses YAKE keyword extraction, lemmatization, and WordNet expansion
             for synonyms, hypernyms, and hyponyms. Includes fallback mechanisms.
    """
    # Inizializza gli strumenti NLP
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))
    
    # 1. Keyword extraction with YAKE
    kw_extractor = yake.KeywordExtractor(
        lan="en",
        n=3, 
        dedupLim=0.9,
        dedupFunc='seqm',
        windowsSize=1,
        top=5, # Estrai le top 5 keyword
        features=None
    )
    keywords = [kw[0].lower() for kw in kw_extractor.extract_keywords(query_string)]

    # Tokenizzazione e rimozione stopwords dalla query originale
    tokens = word_tokenize(query_string.lower())
    
    # Combina keyword e token originali per la lemmatizzazione e l'espansione
    # per assicurarsi che le keyword multi-parola siano considerate
    base_terms_for_nlp = list(set(keywords + tokens))
    base_terms_for_nlp = [term for term in base_terms_for_nlp if term.isalnum() and term not in stop_words]

    pos_tags = pos_tag(base_terms_for_nlp)
    
    lemmatized = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) 
                  for word, tag in pos_tags]
    
    # Espansione con sinonimi, iperonimi e iponimi
    expanded_terms = set()
    # Aggiungi le keyword estratte da YAKE (già in minuscolo) e i termini lemmatizzati originali
    expanded_terms.update(keywords)
    expanded_terms.update(lemmatized)
        
    # Termini su cui basare l'espansione WordNet (keyword + lemmi originali)
    terms_for_wordnet_expansion = set(keywords + lemmatized)

    for term in terms_for_wordnet_expansion:
        # Aggiungi il termine stesso (già fatto, ma per sicurezza)
        expanded_terms.add(term)
        synsets = wordnet.synsets(term)
        for synset in synsets[:2]:  # Limita a 2 synset per termine per evitare rumore
            # Aggiungi sinonimi
            expanded_terms.update(lemma.name().lower().replace('_', ' ') for lemma in synset.lemmas() if lemma.name().lower() not in stop_words)
            
            # Aggiungi iperonimi
            for hypernym in synset.hypernyms():
                expanded_terms.update(lemma.name().lower().replace('_', ' ') for lemma in hypernym.lemmas() if lemma.name().lower() not in stop_words)

            # Aggiungi iponimi (termini più specifici)
            for hyponym in synset.hyponyms()[:1]: # Limita a 1 iponimo per synset per non allargare eccessivamente
                expanded_terms.update(lemma.name().lower().replace('_', ' ') for lemma in hyponym.lemmas() if lemma.name().lower() not in stop_words)
    
    # Pulisci i termini finali
    final_expanded_terms = {
        term.strip() for term in expanded_terms if term.strip() and term.strip() not in stop_words and len(term.strip()) > 1
    }
    
    if not final_expanded_terms: # Fallback se nessun termine è stato generato
        # Usa le keyword o i lemmi originali se disponibili
        fallback_terms = set(keywords + lemmatized)
        fallback_terms = {t for t in fallback_terms if t and t not in stop_words and len(t) > 1}
        if fallback_terms:
            processed_query = ' OR '.join(fallback_terms)
        else: # Fallback estremo: usa la query originale tokenizzata e senza stopwords
            original_tokens_no_stops = [token for token in word_tokenize(query_string.lower()) if token.isalnum() and token not in stop_words and len(token)>1]
            if original_tokens_no_stops:
                 processed_query = ' OR '.join(original_tokens_no_stops)
            else:
                 processed_query = query_string # Ultimo fallback, query originale
    else:
        processed_query = ' OR '.join(final_expanded_terms)
        
    print(f"Whoosh - Query elaborata: {processed_query}")
    return processed_query


#RIMUOVERE COMMENTO ED ESEGUIRE PER GENERARE INDICE
if __name__ == "__main__":
    setup_nltk()
    # Esempio di utilizzo
    current_script_path = Path(__file__).resolve()
    # /root/JuriScan/SearchEngine/Whoosh.py -> /root/JuriScan
    project_root_path = current_script_path.parent.parent 
    
    index_dir_path = str(project_root_path / "SearchEngine" / "WhooshIndex")  
    json_docs_path = str(project_root_path / "WebScraping" / "results" / "Docs_cleaned.json") 
    
    print("🚀 Avvio script Whoosh.py come main...")
    print(f"Percorso Indice Whoosh: {index_dir_path}")
    print(f"Percorso File JSON Documenti: {json_docs_path}")

    # Crea o ottieni l'indice. Forza la ricreazione per testare l'indicizzazione.
    # Cambia force_rebuild a False se vuoi solo aprire un indice esistente.
    ix = create_or_get_index(index_dir_path, json_docs_path, force_rebuild=True) 
    
    if ix:
        # Verifica il numero di documenti nell'indice
        with ix.searcher() as searcher:
            doc_count = searcher.doc_count()
            print(f"📊 Numero totale di documenti nell'indice Whoosh: {doc_count}")
        
        # Esempio di ricerca di test
        if doc_count > 0:
            print("\n🔍 Esempio di ricerca di test su Whoosh:")
            test_query = "neural networks" # Sostituisci con una query rilevante per il tuo dataset
            results = search_documents(index_dir_path, test_query, True, True, True, "BM25F")
            if results:
                print(f"Trovati {len(results)} risultati per '{test_query}':")
                for r in results[:2]: # Stampa i primi 2 risultati
                    print(f"  ID: {r[0]}, Titolo: {r[1][:50]}..., Score: {r[5]}")
            else:
                print(f"Nessun risultato per '{test_query}'.")
    else:
        print("❌ Fallimento nella creazione/apertura dell'indice Whoosh.")
