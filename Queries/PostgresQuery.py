import json 
import psycopg2 as ps
import os
from pathlib import Path
"""
Path to the project root directory variable.
"""
project_root = Path(__file__).parent.parent

"""
Path to the JSON file containing the documents.
"""
FILE_PATH = str(project_root / "WebScraping/results/Docs.json")  

def dbConn():
    """
    Database connection function.
    """
    
    #Recuperiamo in modo sicuro la password dal file .env
    password = os.getenv('MY_SECRET_PASSWORD')

    connection_string = f"postgres://avnadmin:{password}@th-eso-thesissimo.i.aivencloud.com:15597/defaultdb?sslmode=require"

    # Connetti al database
    connection = ps.connect(connection_string)
    return connection

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
    
    -- Creiamo gli indici sulle colonne tsvector
    CREATE INDEX IF NOT EXISTS idx_docs_title ON DOCS USING GIN (title_tsv);
    CREATE INDEX IF NOT EXISTS idx_docs_abstract ON DOCS USING GIN (abstract_tsv);
    CREATE INDEX IF NOT EXISTS idx_docs_corpus ON DOCS USING GIN (corpus_tsv);
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

def jsonToPG(file):
    """
    JSON field extraction and insertion into postgres remote database function.

    Args:
        arg1 (str): File name.
    """
    with open(file, 'r') as f:
        data = json.load(f)

    for documento in data:
        id = documento['id']
        title = documento['title']
        abstract = documento['abstract']
        corpus = documento['corpus']
        keywords = documento.get('keywords', None)
        url = documento.get('url', '')

        docInsert(id, title, abstract, corpus, url, keywords)

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

if __name__ == '__main__':
    main()

