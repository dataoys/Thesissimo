import requests
from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators, CheckConn
from DocManipualtion import addToJson, cleanText
import time
from tqdm import tqdm
import random
from Proxies import PROXY_LIST

NOME_FILE = "WebScraping/results/Docs.json"
DOCUMENTI_MAX = 100000

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def scraping(url):
    #max_retries = 3
    #current_retry = 0
    

    try:
        # Pausa tra le richieste
        time.sleep(2)
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
            'Sec-GPC': '1'
        }
        
        # Prova senza proxy
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True
        )
        
        if response.status_code == 403:
            raise Exception("Access forbidden - waiting longer before retry")
        
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estrai il titolo
        h1_tag = soup.find('h1')
        if not h1_tag:
            return None
            
        titolo = h1_tag.text.strip()
        
        # Estrazione dell'abstract
        page_div = soup.find('div', class_='ltx_abstract')
        abstract = ""
        if page_div:
            abstract = page_div.get_text(strip=True)
        
        # Corpo del contenuto
        corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
        corpo = cleanText(corpo)
        
        # Estrazione delle parole chiave
        ltx_keywords = soup.find('div', class_='ltx_keywords')
        if ltx_keywords is None:
            ltx_keywords = soup.find('div', class_='ltx_classification')

        keywords = ltx_keywords.text.strip() if ltx_keywords else ''

        return {'title': titolo, 'abstract': abstract, 'corpus': corpo, 'keywords': keywords}
    
    except Exception as e:

        print("Link non trovato, passiamo al prossimo")

    return None

def process_urls_sequential(urls):
    results = []
    
    for url in tqdm(urls):
        result = scraping(url)
        if result:
            results.append(result)

    return results

def init():
    urls = list(UrlGenerators())
    print(f"Inizio scraping di {len(urls)} URL...")
    start_time = time.time()
    
    # Usa scraping sequenziale invece che parallelo
    results = process_urls_sequential(urls)
    
    addToJson(results, NOME_FILE)
    
    end_time = time.time()
    print(f"Scraping completato in {end_time - start_time:.2f} secondi")

if __name__ == '__main__':
    init()
