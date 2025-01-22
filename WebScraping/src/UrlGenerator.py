import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm 

BASE_URL= "https://arxiv.org/html/24"
urls= []
MONTH_LIST = [i for i in range(1, 13)]
ARTICLE_LIST = [i for i in range(1, 101)]
MAX_THREADS = 30
#cerco di accedere alla parte successiva del sito, strutturata in questo modo:  
# sito_base/anno/n_documento/section/num_sezione


def generate_url(m, a):
    url = BASE_URL + str(m).zfill(2) + "." + str(a).zfill(5) + "v1"
    return url


def UrlGenerators():
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
