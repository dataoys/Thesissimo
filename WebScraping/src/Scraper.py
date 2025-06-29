"""!
@file Scraper.py
@brief Main web scraping module for JuriScan document collection
@details Implements automated document scraping from academic sources with pause/resume functionality
@author Magni && Testoni
@date 2025
"""

import requests
from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
from DocManipulation import addToJson, cleanText
import sys
from pathlib import Path
import time
from tqdm import tqdm
import random
import json
import threading

"""
Path to the project root directory.
"""
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from Queries import jsonToPG, resetTable
from WebScraping.results.CleanDocuments import clean_documents_in_batches
"""
Path to the JSON file containing the documents.
"""
NOME_FILE = str(project_root / "WebScraping/results/Docs.json")
"""
Path to the cleaned JSON file.
"""
FILE_PULITO = str(project_root / "WebScraping/results/Docs_cleaned.json")


"""
Evento per mettere in pausa il thread di scraping.
"""
pause_event = threading.Event()
pause_event.set()  #Imposta inizialmente l'evento come "non in pausa"

def get_random_user_agent():
    """!
    @brief Generate random user agent string for web requests
    @return Random user agent string from predefined list
    @details Provides browser rotation to avoid detection and blocking.
             Includes Chrome, Firefox, and Safari user agents for different platforms.
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def scraping(url):
    """!
    @brief Scrape document content from a single URL
    @param url The URL to scrape for document content
    @return Dictionary containing extracted document fields or None if failed
    @details Extracts title, abstract, corpus, keywords, and URL from academic papers.
             Handles LaTeX content, implements error recovery, and respects rate limiting.
    """
    try:
        print(f"Scraping URL: {url}")
        time.sleep(2)  # Pausa tra le richieste
        
        # Controllo per la pausa
        pause_event.wait()  # Questo blocca il thread fino a quando non è stato rilasciato il flag di pausa
        
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
    """!
    @brief Process list of URLs sequentially with progress tracking
    @param urls List of URLs to scrape
    @return List of successfully scraped document dictionaries
    @details Implements sequential processing with progress bar and error handling.
             Respects pause events and provides real-time feedback.
    """
    results = []
    
    for url in tqdm(urls):
        result = scraping(url)
        if result:
            print(f"URL nel risultato: {result['url']}")
            results.append(result)

    return results

def monitor_input():
    """!
    @brief Monitor user input for pause/resume commands during scraping
    @details Runs in separate thread to handle real-time pause/resume functionality.
             Accepts 'pause' and 'resume' commands to control scraping process.
    @return None
    """
    global pause_event
    while True:
        user_input = input("Enter 'pause' to pause scraping, 'resume' to resume scraping: ").strip().lower()
        if user_input == "pause":
            print("Pausing scraping...")
            pause_event.clear()  # Mette in pausa lo scraping
        elif user_input == "resume":
            print("Resuming scraping...")
            pause_event.set()  # Riprende lo scraping

def init():
    """!
    @brief Initialize and orchestrate the complete web scraping pipeline
    @details Main function that coordinates the entire scraping workflow:
             1. Creates necessary directories and files
             2. Generates URLs for scraping
             3. Starts monitoring thread for user commands
             4. Executes sequential scraping with progress tracking
             5. Processes and cleans scraped documents
             6. Imports cleaned data into PostgreSQL database
    @return None
    @throws Exception if directory creation, file I/O, or database operations fail
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
    
    # Inizia il thread di monitoraggio dell'input
    input_thread = threading.Thread(target=monitor_input, daemon=True)
    input_thread.start()

    # Usa scraping sequenziale
    results = process_urls_sequential(urls)
    
    addToJson(results, NOME_FILE)
    
    end_time = time.time()
    print(f"Scraping completato in {end_time - start_time:.2f} secondi")
    
    cleaned_docs = clean_documents_in_batches(NOME_FILE,"WebScraping/results/Docs_cleaned.json", 1000)
    
    with open(FILE_PULITO, 'w', encoding='utf-8') as f:
        json.dump(cleaned_docs, f, indent=4, ensure_ascii=False)
    
    resetTable()
    jsonToPG(FILE_PULITO)

if __name__ == '__main__':
    init()
