import psycopg2 as ps
import os
from pathlib import Path
import ijson

"""
Path to the project root directory variable.
"""
project_root = Path(__file__).parent.parent

"""
Path to the JSON file containing the documents.
"""
FILE_PATH = str(project_root / "WebScraping/results/Docs_cleaned.json")  

def dbConn():
    """
    Database connection function.
    """
    
    #Recuperiamo in modo sicuro la password dal file .env
    #password = os.getenv('MY_SECRET_PASSWORD')

    #connection_string = f"postgres://avnadmin:{password}@th-eso-thesissimo.i.aivencloud.com:15597/defaultdb?sslmode=require"

    # Connetti al database
    #connection = ps.connect(connection_string)
    #return connection

    try:
        conn = ps.connect(
            dbname="thesissimo",
            user="postgres",
            password="postgres",
            host="host.docker.internal",
            port="5432"
        )
        print("Connessione al database riuscita!")
        return conn
    except ps.Error as e:
        print("Errore durante la connessione al database:", e)
        return None

def createTable():
    """
    Database table creation funtction.
    """
    
    conn = dbConn()
    cur = conn.cursor()

    q = ''' 
    CREATE TABLE IF NOT EXISTS DOCS (
        id INTEGER PRIMARY KEY,
        title TEXT,
        abstract TEXT,
        corpus TEXT,
        keywords TEXT DEFAULT 'No keywords available',
        url TEXT,
        title_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title,''))) STORED,
        abstract_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(abstract,''))) STORED,
        corpus_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(corpus,''))) STORED
    );
    '''

    cur.execute(q)
    conn.commit()
    cur.close()
    conn.close()

def createIndex():
    conn = dbConn()
    cur = conn.cursor()
    q = '''
    CREATE INDEX idx_docs_title_tsv ON docs USING GiST (to_tsvector('english', title));
    CREATE INDEX idx_docs_abstract_tsv ON docs USING GiST (to_tsvector('english', abstract));
    CREATE INDEX idx_docs_corpus_tsv ON docs USING GiST (to_tsvector('english', corpus));
    CREATE INDEX IF NOT EXISTS idx_docs_title_tsv ON docs USING GIN (title_tsv);
    CREATE INDEX IF NOT EXISTS idx_docs_abstract_tsv ON docs USING GIN (abstract_tsv);
    CREATE INDEX IF NOT EXISTS idx_docs_corpus_tsv ON docs USING GIN (corpus_tsv);
    '''
    cur.execute(q)
    conn.commit()
    cur.close()
    conn.close()


#questo perchè alcuni documenti potrebbero non avere delle keywords 
def docInsert(id, title, abstract, corpus, url, keywords=None):
    """
    Field extraction and insertion function.

    Args:
        id (int): Document primary key.
        title (str): Document title.
        abstract (str): Document abstract.
        corpus (str): Document text.
        url (str): Document url.
        keywords (str, optional): Document keywords. Defaults to None.
    """
    conn = dbConn()
    cur = conn.cursor()

    if keywords is None:
        q = ''' 
        INSERT INTO DOCS (id, title, abstract, corpus, url)
        VALUES (%s, %s, %s, %s, %s)
        '''
        cur.execute(q, (id, title, abstract, corpus, url))
    else:
        q = ''' 
        INSERT INTO DOCS (id, title, abstract, corpus, keywords, url)
        VALUES (%s, %s, %s, %s, %s, %s)
        '''
        cur.execute(q, (id, title, abstract, corpus, keywords, url))

    conn.commit()
    cur.close()
    conn.close()

def insertBatch(cur, batch):
    """
    Helper function to insert a batch of documents into the database.
    
    Args:
        cur: Database cursor
        batch: List of document tuples to insert
    
    Returns:
        int: Number of documents successfully inserted
    """
    try:
        if len(batch[0]) == 5:  # Senza keywords
            q = ''' 
            INSERT INTO DOCS (id, title, abstract, corpus, url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
            '''
        else:  # Con keywords
            q = ''' 
            INSERT INTO DOCS (id, title, abstract, corpus, keywords, url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
            '''
        cur.executemany(q, batch)
        return cur.rowcount
    except Exception as e:
        print(f"Errore durante l'inserimento del batch: {e}")
        return 0

def jsonToPG(file):
    """
    JSON field extraction and batch insertion into postgres remote database function.
    """
    conn = None
    cur = None
    total_inserted = 0
    
    try:
        conn = dbConn()
        cur = conn.cursor()
        
        batch_size = 10
        batch = []

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            parser = ijson.parse(f)
            current_doc = {}
            
            for prefix, event, value in parser:
                if prefix.endswith('.id'):
                    current_doc['id'] = value
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
                    # Quando abbiamo l'URL, il documento è completo
                    
                    # Prepara il batch
                    id = int(current_doc['id'])
                    title = current_doc['title']
                    abstract = current_doc['abstract']
                    corpus = current_doc['corpus']
                    keywords = current_doc.get('keywords', None)
                    url = current_doc.get('url', '')

                    if keywords is None:
                        batch.append((id, title, abstract, corpus, url))
                    else:
                        batch.append((id, title, abstract, corpus, keywords, url))

                    # Reset del documento corrente
                    current_doc = {}

                    # Se il batch è pieno, inseriscilo nel database
                    if len(batch) >= batch_size:
                        inserted = insertBatch(cur, batch)
                        total_inserted += inserted
                        print(f"Inseriti {inserted} documenti nel database. Totale: {total_inserted}")
                        conn.commit()  # Commit dopo ogni batch
                        batch = []

        # Inserisci eventuali documenti rimanenti
        if batch:
            inserted = insertBatch(cur, batch)
            total_inserted += inserted
            print(f"Inseriti {inserted} documenti rimanenti. Totale finale: {total_inserted}")
            conn.commit()

    except Exception as e:
        print(f"Errore durante l'elaborazione del file: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def resetTable():
    """
    Database reset function to be aware of copies.
    """
    conn = dbConn()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS DOCS;")
    conn.commit()
    cur.close()
    conn.close()
    createTable()

def main():
    """
    Main routine called when the script is run.
    """
    if not Path(FILE_PATH).exists():
        print(f"Errore: Il file {FILE_PATH} non esiste!")
        return
        
    resetTable()
    jsonToPG(FILE_PATH)
    createIndex()

if __name__ == '__main__':
    main()

