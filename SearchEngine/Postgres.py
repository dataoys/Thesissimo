import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from Queries import dbConn

# Scarica le risorse necessarie di NLTK (se non sono già scaricate)
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('stopwords')

def extract_keywords(uin):
    """
    Keyword extraction function using NLTK.

    This function takes the user's input string from the search bar and returns a list of keywords extracted from it.

    Arguments:
        uin (str): Search bar input.

    Returns:
        list: List of keywords extracted from the input string.
    """

    # Tokenizza la stringa di input
    tokens = word_tokenize(uin)
    
    # Esegui il POS tagging per identificare il tipo di parola (sostantivo, verbo, ecc.)
    tagged = pos_tag(tokens)
    
    # Estrai solo sostantivi e verbi (per ora ignoriamo le stopwords)
    keywords = [word for word, tag in tagged if tag in ['NN', 'VB', 'NNS', 'VBD', 'VBG', 'VBN', 'VBZ']]
    
    # Filtra le parole chiave rimuovendo le stopwords
    stop_words = set(stopwords.words('english'))
    filtered_keywords = [word for word in keywords if word.lower() not in stop_words]
    
    return filtered_keywords


def search(search_query, title_true, abstract_true, corpus_true, ranking_type):
    """
    Search Engine Postgres Function.

    This function takes the user's input string from the search bar, and 3 boolean values that represent
    the user's choice of where to search (title, abstract, corpus) and returns a list of documents that match the search query.

    Arguments:
        search_query (str): The user's input.
        title_true (bool): First filter.
        abstract_true (bool): Second filter.
        corpus_true (bool): Third filter.

    Returns:
        list: list of the documents matching the user query.

    Raises:
        ValueError: If the denominator (b) is zero, a ValueError is raised.
    """
    conn = dbConn()
    cur = conn.cursor()
    
    keywords = extract_keywords(search_query)
    if not keywords:
        return []
    
    # Converte la lista di parole chiave in una stringa separata da ' & '
    search_query = ' & '.join(keywords) 
    
    if search_query:
        if ranking_type == 'ts_rank':
            # ricerca su tutti i campi dei documenti
            if title_true and abstract_true and corpus_true:
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
            
            # ricerca solamente sul titolo dei documenti
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
            
            # ricerca sull'abstract dei documenti
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
            
            # ricerca solo sul corpo del testo dei documenti
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
        elif ranking_type == 'ts_rank_cd':
            # ricerca su tutti i campi dei documenti
            if title_true and abstract_true and corpus_true:
                q = '''
                SELECT id, title, abstract, corpus, keywords, url,
                       ts_rank_cd(to_tsvector(title) || 
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
            
            # ricerca solamente sul titolo dei documenti
            if title_true and not abstract_true and not corpus_true:
                q = '''
                SELECT id, title, abstract, corpus, keywords, url,
                       ts_rank_cd(to_tsvector(title),
                                 plainto_tsquery(%s)) as rank
                FROM docs 
                WHERE to_tsvector(title) @@ plainto_tsquery(%s)
                ORDER BY rank DESC
                '''
                cur.execute(q, (search_query, search_query))
            
            # ricerca sull'abstract dei documenti
            if abstract_true and not title_true and not corpus_true:
                q = '''
                SELECT id, title, abstract, corpus, keywords, url,
                       ts_rank_cd(to_tsvector(abstract),
                                 plainto_tsquery(%s)) as rank
                FROM docs 
                WHERE to_tsvector(abstract) @@ plainto_tsquery(%s)
                ORDER BY rank DESC
                '''
                cur.execute(q, (search_query, search_query))
            
            # ricerca solo sul corpo del testo dei documenti
            if corpus_true and not title_true and not abstract_true:
                q = '''
                SELECT id, title, abstract, corpus, keywords, url,
                       ts_rank_cd(to_tsvector(corpus),
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
