from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators, CheckConn
from DocManipualtion import addToJson, cleanText
from concurrent.futures import ThreadPoolExecutor
import requests
import time
from tqdm import tqdm
import random

NOME_FILE = "WebScraping/results/Doc.json"

#Numero massimo di documenti da web scrapeare.
DOCUMENTI_MAX = 100000

documenti = []
MAX_THREADS = 20


def scraping(url):

    try:
        time.sleep(2)
        response = requests.get(url)
        response.encoding = 'utf-8'
        if CheckConn(response):
            soup = BeautifulSoup(response.text, 'html.parser')
            h1_tag = soup.find('h1')
            if not h1_tag:
                return None
                
            titolo = h1_tag.text.strip()
            corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
            corpo = cleanText(corpo)
            return {'title': titolo, 'corpus': corpo}
        
    except Exception as e:
        print(f"Errore per {url}: {e}")
        return None

def process_urls_parallel(urls):
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Usa tqdm per mostrare la progress bar
        futures = list(tqdm(executor.map(scraping, urls), total=len(urls)))
        
        for result in futures:
            if result:
                results.append(result)
                
    return results

def init():

    urls = list(UrlGenerators())
    
    print(f"Inizio scraping di {len(urls)} URL...")
    start_time = time.time()
    
    results = process_urls_parallel(urls)
    addToJson(results, NOME_FILE)
    
    end_time = time.time()
    print(f"Scraping completato in {end_time - start_time:.2f} secondi")



init()