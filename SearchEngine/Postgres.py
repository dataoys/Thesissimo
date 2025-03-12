import spacy
from Queries import dbConn

# Carica il modello di lingua inglese di spaCy
nlp = spacy.load("en_core_web_sm")

def extract_keywords(uin):
    # Analizza la UIN con spaCy
    doc = nlp(uin)
    # Estrai le parole chiave (sostantivi e verbi)
    keywords = [token.text for token in doc if token.pos_ in ['NOUN', 'VERB']]
    return keywords



def search(search_query, title_true, abstract_true, corpus_true):
    conn = dbConn()
    cur = conn.cursor()
    
    
    
    keywords = extract_keywords(search_query)
    if not keywords:
        return []
    search_query = ' & '.join(keywords) 
    if search_query:
        #ricerca su tutti i campi dei documenti
        if title_true & abstract_true & corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords, url,
                   ts_rank(to_tsvector(title) || 
                          to_tsvector(abstract) || 
                          to_tsvector(corpus),
                          plainto_tsquery(%s)) as rank
            FROM docs 
            WHERE to_tsvector(title) @@ plainto_tsquery(%s)
            OR to_tsvector(abstract) @@ plainto_tsquery(%s)
            OR to_tsvector(corpus) @@ plainto_tsquery(%s)
            ORDER BY rank DESC
            '''
            cur.execute(q, (search_query, search_query, search_query, search_query))
        #ricerca solamente sul titolo dei nostri documenti
        if title_true and not abstract_true and not corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords, url,
                   ts_rank(to_tsvector(title),
                          plainto_tsquery(%s)) as rank
            FROM docs 
            WHERE to_tsvector(title) @@ plainto_tsquery(%s)
            ORDER BY rank DESC
            '''
            cur.execute(q, (search_query, search_query))
        #ricerca sull'abstract dei documenti
        if abstract_true and not title_true and not corpus_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords, url,
                   ts_rank(to_tsvector(abstract),
                          plainto_tsquery(%s)) as rank
            FROM docs 
            WHERE to_tsvector(abstract) @@ plainto_tsquery(%s)
            ORDER BY rank DESC
            '''
            cur.execute(q, (search_query, search_query))
        #ricerca solo sul corpo del testo dei nostri documenti
        if corpus_true and not title_true and not abstract_true:
            q = '''
            SELECT id, title, abstract, corpus, keywords, url,
                   ts_rank(to_tsvector(corpus),
                          plainto_tsquery(%s)) as rank
            FROM docs 
            WHERE to_tsvector(corpus) @@ plainto_tsquery(%s)
            ORDER BY rank DESC
            '''
            cur.execute(q, (search_query, search_query))
                
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results