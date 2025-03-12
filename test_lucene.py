import lucene
from java.nio.file import Paths
from org.apache.lucene.store import RAMDirectory, FSDirectory
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, TextField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser

def test_lucene():
    # Inizializza la JVM
    print("Inizializzazione JVM...")
    lucene.initVM()
    
    # Crea un indice in memoria
    print("Creazione indice in memoria...")
    directory = RAMDirectory()
    analyzer = StandardAnalyzer()
    config = IndexWriterConfig(analyzer)
    writer = IndexWriter(directory, config)
    
    # Crea e aggiungi un documento di test
    print("Aggiunta documento di test...")
    doc = Document()
    doc.add(TextField("content", "Questo è un test di PyLucene per l'esame", Field.Store.YES))
    writer.addDocument(doc)
    writer.close()
    
    # Esegui una ricerca di test
    print("Esecuzione ricerca di test...")
    reader = DirectoryReader.open(directory)
    searcher = IndexSearcher(reader)
    query = QueryParser("content", analyzer).parse("test")
    hits = searcher.search(query, 1).scoreDocs
    
    # Verifica i risultati
    if len(hits) > 0:
        doc = searcher.doc(hits[0].doc)
        print("\nTest completato con successo!")
        print(f"Documento trovato: {doc.get('content')}")
    else:
        print("Errore: nessun documento trovato")
    
    reader.close()
    directory.close()

if __name__ == "__main__":
    try:
        test_lucene()
    except Exception as e:
        print(f"Errore durante il test: {str(e)}") 