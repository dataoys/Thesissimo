import requests
from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
from DocManipualtion import addToJson, cleanText
import sys
from pathlib import Path
import time
from tqdm import tqdm
import random
import json


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

def get_random_user_agent():
    """
    Function to get a random user agent string.

    This function returns a random user agent string from a list of user agents to improve the scraping method.
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def scraping(url):
    """
    Function to scrape a list of URL.

    This function scrapes a list of URL and returns the title, abstract, corpus, and keywords of the page.

    Arguments:
        url (str): The URL to scrape

    Returns:
        dict: A dictionary containing the title, abstract, corpus, keywords, and URL of the page.

    Raises:
        StatusCode: If the status code is 403, an exception is raised.
        LinkNotFound: If the link is not found, the function will pass to the next URL.
    """

    try:
        # Aggiungi debug print
        print(f"Scraping URL: {url}")
        
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
    """
    Function to process a list of URLs sequentially.

    This function processes a list of URLs sequentially and returns the results.

    Arguments:
        urls (list): The list of URLs to process.

    Returns:
        list: The list of results.
    """
    results = []
    
    for url in tqdm(urls):
        result = scraping(url)
        if result:
            # Debug print
            print(f"URL nel risultato: {result['url']}")
            results.append(result)

    return results

def init():
    """
    Main function of the Web Scraping application.

    This function initializes the Web Scraping application by scraping a list of URLs, 
    cleaning the documents, and saving the cleaned documents to a JSON file.
    """
    # Crea le directory se non esistono
    results_dir = project_root / "WebScraping/results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Crea il file Docs.json se non esiste
    if not Path(NOME_FILE).exists():
        with open(NOME_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    urls = list(UrlGenerators())
    print(f"Inizio scraping di {len(urls)} URL...")
    start_time = time.time()
    
    # Usa scraping sequenziale invece che parallelo
    results = process_urls_sequential(urls)
    
    addToJson(results, NOME_FILE)
    
    end_time = time.time()
    print(f"Scraping completato in {end_time - start_time:.2f} secondi")

    # Prima leggi il file JSON
    with open(NOME_FILE, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    # Poi passa i documenti alla funzione clean_documents
    cleaned_docs = clean_documents(documents)
    
    # Infine salva i documenti puliti
    with open(FILE_PULITO, 'w', encoding='utf-8') as f:
        json.dump(cleaned_docs, f, indent=4, ensure_ascii=False)
    
    # Si connette al db e passa il file pulito a jsonToPG
    resetTable()
    jsonToPG(FILE_PULITO)


if __name__ == '__main__':
    init()

