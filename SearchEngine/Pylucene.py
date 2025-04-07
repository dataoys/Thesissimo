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
import json
import os
import ijson
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
    env = lucene.getVMEnv()
    env.attachCurrentThread()

    # Configurazione ottimizzata per l'IndexWriter
    directory = FSDirectory.open(Paths.get(index_file))
    config = IndexWriterConfig(StandardAnalyzer())
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    
    # Ottimizzazioni della configurazione
    config.setRAMBufferSizeMB(64.0)  # Riduce l'uso della RAM
    config.setUseCompoundFile(True)  # Riduce il numero di file aperti
    config.setMaxBufferedDocs(1000)  # Controlla il flushing su disco
    
    writer = IndexWriter(directory, config)
    
    # Riduce ulteriormente la dimensione del batch
    BATCH_SIZE = 10
    batch = []
    doc_count = 0
    total_docs = 0

    try:
        # Conta i documenti in modo efficiente
        print("📊 Conteggio documenti...")
        total_docs = sum(1 for line in open(json_file, 'rb') if b'"id":' in line)
        print(f"📊 Totale documenti da indicizzare: {total_docs}")

        # Processa i documenti in batch più piccoli
        with open(json_file, 'rb') as f:
            parser = ijson.parse(f, use_float=True)  # use_float=True per ottimizzare il parsing
            current_doc = {}
            
            for prefix, event, value in parser:
                try:
                    if prefix.endswith('.id'):
                        if current_doc:
                            doc = Document()
                            # Ottimizza l'aggiunta dei campi
                            for field, content in [
                                ("title", current_doc.get('title', '')),
                                ("abstract", current_doc.get('abstract', '')),
                                ("corpus", current_doc.get('corpus', '')),
                                ("keywords", current_doc.get('keywords', '')),
                                ("url", current_doc.get('url', ''))
                            ]:
                                if content:  # Aggiungi solo campi non vuoti
                                    doc.add(TextField(field, content, Field.Store.YES))
                            
                            batch.append(doc)
                            
                            if len(batch) >= BATCH_SIZE:
                                writer.addDocuments(batch)
                                doc_count += len(batch)
                                
                                # Commit solo ogni 100 batch per ridurre le operazioni I/O
                                if doc_count % (BATCH_SIZE * 100) == 0:
                                    writer.commit()
                                    print(f"📦 Progresso: {doc_count}/{total_docs} documenti ({(doc_count/total_docs)*100:.2f}%)")
                                    
                                batch.clear()
                                import gc
                                gc.collect()  # Forza il garbage collector
                                
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
                    print(f"⚠️ Errore nel processare un documento: {e}")
                    continue  # Salta al prossimo documento in caso di errore

        # Gestisci l'ultimo batch
        if batch:
            writer.addDocuments(batch)
            writer.commit()
            doc_count += len(batch)
            print(f"📦 Ultimo batch completato. Totale: {doc_count}/{total_docs}")

    except Exception as e:
        print(f"❌ Errore durante l'indicizzazione: {e}")
        raise
    finally:
        try:
            writer.close()
            print("✅ Writer chiuso correttamente")
        except Exception as e:
            print(f"⚠️ Errore nella chiusura del writer: {e}")

    print(f"✅ Indicizzazione completata! Documenti indicizzati: {doc_count}")

    # Apri l'indice e crea un IndexSearcher
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    return directory, searcher

if __name__ == "__main__":
    print("🚀 Inizializzazione del processo di indicizzazione...")
    
    # Verifica che il percorso dell'indice esista
    if not os.path.exists(index_file):
        os.makedirs(index_file)
        print(f"📁 Creata directory per l'indice: {index_file}")

    try:
        # Conta il numero totale di documenti nel JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            total_docs = len(json.load(f))
        print(f"📊 Totale documenti da indicizzare: {total_docs}")

        # Crea l'indice e l'IndexSearcher
        print("🏗️ Creazione dell'indice in corso...")
        directory, searcher = create_index()

        # Verifica il numero di documenti nell'indice
        reader = searcher.getIndexReader()
        indexed_docs = reader.numDocs()
        print(f"✅ Indicizzazione completata!")
        print(f"📈 Statistiche finali:")
        print(f"   - Documenti totali indicizzati: {indexed_docs}")
        print(f"   - Dimensione media dei documenti: {reader.getSumTotalTermFreq('contents') / indexed_docs:.2f} termini")
        print(f"   - Numero totale di termini unici: {reader.terms('contents').size()}")

        # Esegui una ricerca di test
        print("\n🔍 Esecuzione ricerca di test...")
        test_query = "machine learning"
        print(f"   Query di test: '{test_query}'")
        
        results = search_documents(searcher, True, True, True, test_query, "BM25")
        if results and results.totalHits.value > 0:
            print(f"   ✨ Trovati {results.totalHits.value} documenti")
            print("\n📑 Primi 3 risultati:")
            for i, score_doc in enumerate(results.scoreDocs[:3]):
                doc = searcher.doc(score_doc.doc)
                print(f"\n   {i+1}. Documento:")
                print(f"      Titolo: {doc.get('title')[:100]}...")
                print(f"      Score: {score_doc.score:.4f}")
        else:
            print("   ❌ Nessun documento trovato per la query di test")

    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {e}")
    finally:
        try:
            # Chiudi le risorse
            reader.close()
            directory.close()
            print("\n🔒 Risorse chiuse correttamente")
        except Exception as e:
            print(f"⚠️ Errore durante la chiusura delle risorse: {e}")

    print("\n✨ Processo completato!")