import json 
import psycopg2 as ps
from psycopg2 import sql

FILE_PATH = "WebScraping/results/Docs.json"

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
        id SERIAL PRIMARY KEY,
        title TEXT,
        abstract TEXT,
        corpus TEXT,
        keywords TEXT    
    );
    '''

    cur.execute(q)
    conn.commit()
    cur.close()
    conn.close()

def docInsert(id, title, abstract, corpus, keywords):
    conn = dbConn()
    cur = conn.cursor()

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
        title  = documento['title']
        abstract = documento['abstract']
        corpus = documento['corpus']
        keywords = documento['keywords']

    docInsert(id,title,abstract,corpus,keywords)

def main():
        createTable()
        jsonToPG(FILE_PATH)

if __name__ == '__main__':
    main()
