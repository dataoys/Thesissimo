import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm 

BASE_URL= "https://arxiv.org/html/24"
urls= []
MONTH_LIST = [i for i in range(1, 13)]
ARTICLE_LIST = [i for i in range(1, 4001)]
MAX_THREADS = 30
#cerco di accedere alla parte successiva del sito, strutturata in questo modo:  
# sito_base/anno/n_documento/section/num_sezione


def generate_url(m, a):
    """
    Url generator function.

    This function generates a URL for a given month and article number.

    Arguments:
        m (int): The month number.
        a (int): The article

    Returns:
        str: The generated URL.
    """
    url = BASE_URL + str(m).zfill(2) + "." + str(a).zfill(5) + "v1"
    return url


def UrlGenerators():
    """
    Url collapse function.

    This function generates all the URLs for the articles and months specified in the MONTH_LIST and ARTICLE_LIST lists using
    the previous function to generate the URLs, then it collapses all the URLs into a single list.

    Returns:
        list: The list of all generated URLs.
    """
    urls = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Crea una lista di task per ogni combinazione di mese e articolo
        tasks = [(m, a) for m in MONTH_LIST for a in ARTICLE_LIST]
        
        # Usa tqdm per mostrare la progress bar
        for result in tqdm(executor.map(lambda x: generate_url(*x), tasks), total=len(tasks)):
            if result:
                urls.append(result)
    
    return urls



def CheckConn(response):
    """
    Connection check function.

    This function checks if the connection to the URL was successful and if the HTML contains the "No HTML" string.

    Arguments:
        response (requests.models.Response): The response object from the request.
        
    Returns:
        bool: True if the connection was successful and the HTML does not contain the "No HTML" string, False otherwise.
    """
    time.sleep(1)
        #controllo che la connessione avvenga correttamente
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tag = soup.find('h1')
        if h1_tag is None:
            #debug
            #print(f"Nessun tag h1 trovato per {url}")
            return False 
        titolo = h1_tag.text.strip()
        if not titolo:
            #debug
            #print(f"Titolo vuoto trovato per {url}")
            return False
        return "No HTML" not in titolo
    else:
        return False
