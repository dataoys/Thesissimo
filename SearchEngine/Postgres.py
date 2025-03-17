import spacy
from Queries import dbConn

# Carica il modello di lingua inglese di spaCy
nlp = spacy.load("en_core_web_sm")

def extract_keywords(uin):

    """
    Keyword extraction function.

    This function takes the user's input string from the search bar and returns a list of keywords extracted from it.

    Arguments:
        uin (str): Search bar input.

    Returns:
        list: List of keywords extracted from the input string.
    """

    # Analizza la UIN con spaCy
    doc = nlp(uin)
    # Estrai le parole chiave (sostantivi e verbi)
    keywords = [token.text for token in doc if token.pos_ in ['NOUN', 'VERB']]
    return keywords



def search(search_query, title_true, abstract_true, corpus_true):
    """
    Search Engine Postgres Funcion.

    This function takes the user's input string from the search bar, and 3 boolean values that represent
    the user's choice of where to search (title, abstract, corpus) and returns a list of documents that match the search query.

    Arguments:
        search_query (str): The user's input.
        title_true (bool): First filter.
        abstract_true (bool): Second filter.
        corpus_true (bool): Third filter.

    Returns:
        list: list of the document matching the user query.

    Raises:
        ValueError: If the denominator (b) is zero, a ValueError is raised.
    """
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