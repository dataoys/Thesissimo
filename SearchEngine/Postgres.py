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

def parse_advanced_query(query_string):
    """
    Parse a query string that may contain field-specific searches.
    Example: "title:space AND corpus:python" or "abstract:law OR title:justice"
    Supports multi-word searches like: title:"machine learning" AND corpus:"neural networks"
    """
    parts = query_string.split(' AND ')
    query_parts = []
    params = []
    fields_used = {'title': False, 'abstract': False, 'corpus': False}
    
    for part in parts:
        if ' OR ' in part:
            or_parts = part.split(' OR ')
            or_query_parts = []
            
            for or_part in or_parts:
                if ':' in or_part:
                    field, term = or_part.split(':', 1)
                    field = field.lower().strip()
                    term = term.strip().strip('"').strip("'").strip()
                    
                    if field in fields_used:
                        fields_used[field] = True
                        or_query_parts.append(f"{field}_tsv @@ phraseto_tsquery('english', %s)")
                        params.append(term)
            
            if or_query_parts:
                query_parts.append('(' + ' OR '.join(or_query_parts) + ')')
        else:
            # Gestione diretta dei termini AND senza OR
            if ':' in part:
                field, term = part.split(':', 1)
                field = field.lower().strip()
                term = term.strip().strip('"').strip("'").strip()
                
                if field in fields_used:
                    fields_used[field] = True
                    query_parts.append(f"{field}_tsv @@ phraseto_tsquery('english', %s)")
                    params.append(term)
            else:
                # Se nessun campo è specificato, cerca in tutti i campi usando phraseto_tsquery
                part = part.strip().strip('"').strip("'").strip()
                all_fields_query = []
                for field in fields_used:
                    fields_used[field] = True
                    all_fields_query.append(f"{field}_tsv @@ phraseto_tsquery('english', %s)")
                    params.append(part)
                if all_fields_query:
                    query_parts.append('(' + ' OR '.join(all_fields_query) + ')')

    
    if query_parts:
        # Combina tutte le parti con AND
        return ' AND '.join(query_parts), params, fields_used
    return None, [], fields_used

def build_search_query(search_terms, title_true, abstract_true, corpus_true, ranking_type='ts_rank_cd'):
    """
    Build a PostgreSQL query based on search terms and selected fields.
    
    Args:
        search_terms (str): The search terms to look for
        title_true (bool): Whether to search in title field
        abstract_true (bool): Whether to search in abstract field
        corpus_true (bool): Whether to search in corpus field
        ranking_type (str): The ranking function to use ('ts_rank' or 'ts_rank_cd')
        
    Returns:
        tuple: (query_string, params) for executing the PostgreSQL query
    """
    # Build the ranking expression based on selected fields
    rank_fields = []
    where_conditions = []
    if title_true:
        rank_fields.append('title_tsv')
        where_conditions.append('title_tsv @@ to_tsquery(\'english\', %s)')
    if abstract_true:
        rank_fields.append('abstract_tsv')
        where_conditions.append('abstract_tsv @@ to_tsquery(\'english\', %s)')
    if corpus_true:
        rank_fields.append('corpus_tsv')
        where_conditions.append('corpus_tsv @@ to_tsquery(\'english\', %s)')
    
    if not rank_fields:
        return None, []
        
    rank_expr = ' || '.join(rank_fields)
    where_clause = ' OR '.join(where_conditions)
    
    query = f"""
    SELECT id, title, abstract, corpus, keywords, url,
           {ranking_type}({rank_expr}, to_tsquery('english', %s)) as rank
    FROM docs 
    WHERE {where_clause}
    ORDER BY rank DESC
    LIMIT 100
    """
    
    # Parameters for the query - one for ranking and one for each where condition
    params = [search_terms] * (len(where_conditions) + 1)
    return query, params

def search(search_query, title_true, abstract_true, corpus_true, ranking_type='ts_rank_cd'):
    """
    Search Engine Postgres Function.

    This function supports two types of searches:
    1. Field-specific searches using syntax like "title:word AND abstract:phrase"
    2. Checkbox-based searches that look for terms in selected fields

    Args:
        search_query (str): The user's input query
        title_true (bool): Whether to search in title field
        abstract_true (bool): Whether to search in abstract field
        corpus_true (bool): Whether to search in corpus field
        ranking_type (str): The ranking function to use ('ts_rank' or 'ts_rank_cd')

    Returns:
        list: List of matching documents, ordered by relevance
    """
    conn = dbConn()
    cur = conn.cursor()
    
    try:
        # Check if the query contains field-specific searches
        if 'AND' in search_query or 'OR' in search_query:
            where_clause, params, fields_used = parse_advanced_query(search_query)
            if where_clause:
                # Override checkbox selections with fields explicitly used in the query
                title_true = title_true or fields_used['title']
                abstract_true = abstract_true or fields_used['abstract']
                corpus_true = corpus_true or fields_used['corpus']
                
                # Build query with both explicit field searches and checkbox selections
                q = f'''
                SELECT id, title, abstract, corpus, keywords, url,
                       {ranking_type}(
                           CASE WHEN {title_true} THEN title_tsv ELSE ''::tsvector END ||
                           CASE WHEN {abstract_true} THEN abstract_tsv ELSE ''::tsvector END ||
                           CASE WHEN {corpus_true} THEN corpus_tsv ELSE ''::tsvector END,
                           phraseto_tsquery('english', %s)
                       ) as rank
                FROM docs 
                WHERE {where_clause}
                ORDER BY rank DESC
                LIMIT 100
                '''
                # Add parameter for ranking calculation
                if params:
                    execution_params = [params[0]] + params
                else:
                    execution_params = []

                # DEBUG PRINTS:
                print(f"DEBUG: Original search_query: {search_query}")
                print(f"DEBUG: Parsed where_clause: {where_clause}")
                print(f"DEBUG: Params from parse_advanced_query: {params}")
                print(f"DEBUG: Final execution_params: {execution_params}")
                # Puoi anche stampare q se non è troppo lungo, o parti di esso.
                # print(f"DEBUG: SQL Query: {q}")

                cur.execute(q, execution_params)
                return cur.fetchall()
        else:
            # Use the checkbox-based search
            keywords = extract_keywords(search_query)
            if not keywords:
                return []
            
            search_terms = ' & '.join(keywords)
            query, params = build_search_query(
                search_terms, 
                title_true, 
                abstract_true, 
                corpus_true, 
                ranking_type
            )
            
            if query and params:
                cur.execute(query, params)
                return cur.fetchall()
        
        return []
    
    finally:
        cur.close()
        conn.close()
