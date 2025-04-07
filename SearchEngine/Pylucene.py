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
from org.apache.lucene.search.similarities import BM25Similarity, ClassicSimilarity

from pathlib import Path
import sys
import os
import ijson
import gc
project_root = Path(__file__).parent.parent
json_file = str(project_root / "WebScraping/results/Docs_cleaned.json") 
index_file= str(project_root / "SearchEngine/index")

import yake
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords

# Scarico le risorse di NLTK necessarie
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    nltk.download('stopwords')


# Funzione di espansione della query
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


# Funzione per creare l'indice con l'aggiunta di documenti in batch
def create_index():
    """
    Creating Lucene index with batch processing and memory management.
    """
    print("🔄 Inizializzazione JVM...")
    env = lucene.getVMEnv()
    env.attachCurrentThread()

    print("📁 Apertura directory dell'indice...")
    directory = FSDirectory.open(Paths.get(index_file))
    
    print("⚙️ Configurazione IndexWriter...")
    config = IndexWriterConfig(StandardAnalyzer())
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    
    # Ottimizzazioni della configurazione
    config.setRAMBufferSizeMB(32.0)  # Ridotto per minimizzare l'uso della memoria
    config.setUseCompoundFile(True)
    config.setMaxBufferedDocs(100)
    
    writer = IndexWriter(directory, config)
    print("✅ IndexWriter creato correttamente")
    
    BATCH_SIZE = 50  # Aumentato per ridurre il numero di commit
    batch = []
    doc_count = 0
    error_count = 0

    try:
        print("📊 Verifica esistenza file JSON...")
        if not os.path.exists(json_file):
            raise FileNotFoundError(f"File non trovato: {json_file}")
            
        print("📖 Apertura file JSON...")
        with open(json_file, 'rb') as f:
            print("🔍 Inizio parsing JSON...")
            parser = ijson.parse(f, use_float=True)
            current_doc = {}
            
            for prefix, event, value in parser:
                try:
                    if prefix.endswith('.id'):
                        if current_doc:  # Se abbiamo un documento completo
                            try:
                                doc = Document()
                                # Verifica che i campi obbligatori siano presenti
                                if not current_doc.get('id'):
                                    raise ValueError("ID mancante nel documento")
                                
                                for field, content in [
                                    ("id", str(current_doc.get('id', ''))),
                                    ("title", current_doc.get('title', '')),
                                    ("abstract", current_doc.get('abstract', '')),
                                    ("corpus", current_doc.get('corpus', '')),
                                    ("keywords", current_doc.get('keywords', '')),
                                    ("url", current_doc.get('url', ''))
                                ]:
                                    if content:
                                        doc.add(TextField(field, content, Field.Store.YES))
                                
                                batch.append(doc)
                                
                                if len(batch) >= BATCH_SIZE:
                                    writer.addDocuments(batch)
                                    doc_count += len(batch)
                                    
                                    # Commit ogni 1000 documenti
                                    if doc_count % 1000 == 0:
                                        writer.commit()
                                        print(f"✅ Progresso: {doc_count} documenti indicizzati ({error_count} errori)")
                                        gc.collect()
                                    
                                    batch.clear()
                                
                            except Exception as doc_error:
                                error_count += 1
                                if error_count <= 5:  # Mostra solo i primi 5 errori in dettaglio
                                    print(f"⚠️ Errore nel documento {current_doc.get('id', 'ID sconosciuto')}: {str(doc_error)}")
                                
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
                        
                except Exception as e:
                    error_count += 1
                    continue

        # Gestisci l'ultimo batch
        if batch:
            writer.addDocuments(batch)
            writer.commit()
            doc_count += len(batch)

    except Exception as e:
        print(f"❌ Errore critico durante l'indicizzazione: {str(e)}")
        raise
    finally:
        try:
            writer.close()
            print(f"\n📊 Riepilogo finale:")
            print(f"✅ Documenti indicizzati con successo: {doc_count}")
            print(f"⚠️ Errori riscontrati: {error_count}")
        except Exception as e:
            print(f"❌ Errore durante la chiusura del writer: {str(e)}")

    print("📖 Apertura indice per ricerca...")
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    return directory, searcher

if __name__ == "__main__":
    print("🚀 Inizializzazione del processo di indicizzazione...")
    
    # Verifica percorsi
    print(f"📁 File JSON: {json_file}")
    print(f"📁 Directory indice: {index_file}")
    
    if not os.path.exists(json_file):
        print(f"❌ File JSON non trovato: {json_file}")
        sys.exit(1)
        
    if not os.path.exists(index_file):
        print(f"📁 Creazione directory indice: {index_file}")
        os.makedirs(index_file)

    local_reader = None
    local_directory = None
    
    try:
        print("🏗️ Avvio creazione indice...")
        directory, searcher = create_index()
        local_reader = searcher.getIndexReader()
        local_directory = directory
        
        indexed_docs = local_reader.numDocs()
        print(f"📈 Documenti totali indicizzati: {indexed_docs}")
        print(f"📊 Dimensione indice: {os.path.getsize(index_file) / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {str(e)}")
        print(f"Stack trace completo:")
        import traceback
        print(traceback.format_exc())
    finally:
        try:
            if local_reader:
                local_reader.close()
            if local_directory:
                local_directory.close()
            print("🔒 Risorse chiuse correttamente")
        except Exception as e:
            print(f"⚠️ Errore durante la chiusura delle risorse: {str(e)}")

    print("✨ Processo completato!")