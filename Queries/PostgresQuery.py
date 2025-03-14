import json 
import psycopg2 as ps
import os
from pathlib import Path
# Ottieni il percorso assoluto del progetto
project_root = Path(__file__).parent.parent

FILE_PATH = str(project_root / "WebScraping/results/Docs.json")  # Usa Docs.json invece di Docs_cleaned.json

def dbConn():
    """
    Funzione che ci permetterà di collegarci al nostro database remoto.
    """
    
    #Recuperiamo in modo sicuro la password dal file .env
    password = os.getenv('MY_SECRET_PASSWORD')
    connection_string = f"postgres://avnadmin:{password}@th-eso-thesissimo.i.aivencloud.com:15597/defaultdb?sslmode=require"

    # Connetti al database
    connection = ps.connect(connection_string)


def createTable():
    """
    Funzione che viene chiamata ogni volta che viene eseguito uno scraping in modo tale da
    poter resettare la tabella del database con i valori aggiornati
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
    Funzione che mi permette, estratti i campi dal file JSON di inserirli all'interno del db

    Args:
        id (int): Primary key nonchè identificatore del doc.
        title (str): Titolo del documento.
        abstract (str): Abstract del documento.
        corpus (str): Testo del documento.
        url (str): Url del documento.
        keywords (str, optional): Keywords del documento. Di default è assegnato a None perchè non è detto che siano presenti in ogni documento.
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
    Fuznione che estrae campi da file JSON.

    Args:
        arg1 (str): Nome del file su cui sono locati i documenti scrapeati.
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
    Funzione che resetta il database per non avere duplicati
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
    Routine principale effetuata al avvio dello script; Richiama altre funzioni.
    """
    if not Path(FILE_PATH).exists():
        print(f"Errore: Il file {FILE_PATH} non esiste!")
        return
        
    resetTable()
    jsonToPG(FILE_PATH)

if __name__ == '__main__':
    main()

