import requests
from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
from DocManipualtion import addToJson, cleanText
import sys
from pathlib import Path
import time
from tqdm import tqdm
import random
from Proxies import PROXY_LIST
import json
import threading


# Ottieniamo il percorso assoluto della directory root del progetto
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Per debug, verifica il path
print("Project root:", project_root)
print("Python path:", sys.path)

from Queries import jsonToPG, resetTable
from WebScraping.results.CleanDocuments import clean_documents

NOME_FILE = str(project_root / "WebScraping/results/Docs.json")
FILE_PULITO = str(project_root / "WebScraping/results/Docs_cleaned.json")
DOCUMENTI_MAX = 100000

# Variabile globale per controllare la pausa
pause_flag = False

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    ]
    return random.choice(user_agents)

#Thread sempre in ascolto in input che in base all'input ricevuto mette in pausa o riprende lo scraping
def input_listener():
    global pause_flag
    while True:
        user_input = input("Digita 'pause' per mettere in pausa o 'resume' per riprendere: ")
        if user_input.lower() == 'pause':
            pause_flag = True
            print("Scraping in pausa...")
        elif user_input.lower() == 'resume':
            pause_flag = False
            print("Scraping ripreso...")

def scraping(url):
    try:
        print(f"Scraping URL: {url}")
        time.sleep(2)  # Simula il tempo di scraping

        # Controlla se è in pausa
        while pause_flag:
            time.sleep(1)  # Aspetta mentre è in pausa

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

        result = {
            'title': titolo, 
            'abstract': abstract, 
            'corpus': corpo, 
            'keywords': keywords,
            'url': url
        }
        
        return result
    
    except Exception as e:
        print("Link non trovato, passiamo al prossimo")

    return None

def process_urls_sequential(urls):
    results = []
    
    for url in tqdm(urls):
        result = scraping(url)
        if result:
            print(f"URL nel risultato: {result['url']}")
            results.append(result)

    return results

def init():
    # Crea un thread per ascoltare l'input dell'utente
    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()

    # Crea le directory se non esistono
    results_dir = project_root / "WebScraping/results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Crea il file Docs.json se non esiste
    if not Path(NOME_FILE).exists():
        with open(NOME_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    # Inizio del processo di scraping
    urls = list(UrlGenerators())
    print(f"Inizio scraping di {len(urls)} URL...")
    start_time = time.time()
    results = process_urls_sequential(urls)
    
    addToJson(results, NOME_FILE)
    
    end_time = time.time()
    print(f"Scraping completato in {end_time - start_time:.2f} secondi")

    #Prima leggi il file JSON
    with open(NOME_FILE, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    #Pulisco i documenti dai vari caratteri unicode etc...
    cleaned_docs = clean_documents(documents)
    
    #Infine salva i documenti puliti
    with open(FILE_PULITO, 'w', encoding='utf-8') as f:
        json.dump(cleaned_docs, f, indent=4, ensure_ascii=False)
    
    #Passa il file pulito a jsonToPG dopo aver resettato la tabella del db 
    #per assicurarci che ogni volta vengano inseriti i risultati.
    resetTable()
    jsonToPG(FILE_PULITO)


if __name__ == '__main__':
    init()

