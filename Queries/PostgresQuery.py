import json 
import psycopg2 as ps
from psycopg2 import sql
from pathlib import Path

# Ottieni il percorso assoluto del progetto
project_root = Path(__file__).parent.parent
FILE_PATH = str(project_root / "WebScraping/results/Docs.json")  # Usa Docs.json invece di Docs_cleaned.json

def dbConn():
    return ps.connect(
        dbname = "Thesissimo",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )

def createTable():
    conn = dbConn()
    cur = conn.cursor()

    q = ''' 
    CREATE TABLE IF NOT EXISTS DOCS (
        id INTEGER PRIMARY KEY,
        title TEXT,
        abstract TEXT,
        corpus TEXT,
        keywords TEXT DEFAULT 'No keywords available'    
    );
    '''

    cur.execute(q)
    conn.commit()
    cur.close()
    conn.close()

#questo perchè alcuni documenti potrebbero non avere delle keywords 
def docInsert(id, title, abstract, corpus, keywords=None):
    conn = dbConn()
    cur = conn.cursor()

    if keywords is None:
        q = ''' 
        INSERT INTO DOCS (id, title, abstract, corpus)
        VALUES (%s, %s, %s, %s)
        '''
        cur.execute(q, (id, title, abstract, corpus))
    else:
        q = ''' 
        INSERT INTO DOCS (id, title, abstract, corpus, keywords)
        VALUES (%s, %s, %s, %s, %s)
        '''
        cur.execute(q, (id, title, abstract, corpus, keywords))

    conn.commit()
    cur.close()
    conn.close()

def jsonToPG(file):
    with open(file, 'r') as f:
        data = json.load(f)

    for documento in data:
        id = documento['id']
        title = documento['title']
        abstract = documento['abstract']
        corpus = documento['corpus']
        keywords = documento.get('keywords', None)

        docInsert(id, title, abstract, corpus, keywords)

def resetTable():
    conn = dbConn()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS DOCS;")
    conn.commit()
    cur.close()
    conn.close()
    createTable()

def main():
    # Assicurati che il file esista prima di procedere
    if not Path(FILE_PATH).exists():
        print(f"Errore: Il file {FILE_PATH} non esiste!")
        return
        
    resetTable()
    jsonToPG(FILE_PATH)

if __name__ == '__main__':
    main()



#ESEMPIO DI QUERY
#--SELECT id, corpus FROM docs WHERE to_tsvector(corpus) @@ to_tsquery('parola/frase');