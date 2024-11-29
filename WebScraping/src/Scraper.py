from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
import requests
import json
import re
import time
import random

NOME_FILE = "WebScraping/JSON/Doc.json"

#Numero massimo di documenti da web scrapeare.
DOCUMENTI_MAX = 100000

documenti = []

# try:
#     # Leggi il file esistente
#     with open("WebScraping/JSON/proxies.json", 'r') as file:
#         proxyList = json.load(file)
# except (FileNotFoundError, json.JSONDecodeError):
#     # Se il file non esiste o è vuoto
#     print("errore del cazzo")


def clean_text(text):
    # Pulizia base
    text = re.sub(r'\s+', ' ', text)
    text = ''.join(char for char in text if char.isprintable())
    
    # Pulizie aggiuntive
    text = re.sub(r'\n+', '\n', text)  # Rimuove linee vuote multiple
    text = re.sub(r'[\t\r\f\v]', '', text)  # Rimuove altri caratteri di spaziatura
    text = re.sub(r'\s*\n\s*', '\n', text)  # Pulisce gli spazi intorno ai newline
    text = re.sub(r' +', ' ', text)  # Rimuove spazi multipli
    
    return text.strip()

def random_sleep():
    time.sleep(random.uniform(1, 3))



def scraping(url):
    random_sleep()
    for proxy in proxyList:
        try:
            # Prova a fare la richiesta con il proxy corrente
            response = requests.get(url, proxies=proxy, timeout=5)
            if response.status_code == 200:
                print(f"Successo con proxy {proxy}")
                break  # Esci dal ciclo una volta ottenuta una risposta valida
        except Exception as e:
            print(f"Errore proxy {proxy}: {e}")
    else:
        print(f"Nessun proxy funzionante per l'URL: {url}")
        return None

    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # Estrai titolo e corpo
    try:
        titolo = soup.find('h1').text.strip()
        #debug
        print(titolo)
        corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
        corpo = clean_text(corpo)
        addToJson(titolo, corpo)
    except Exception as e:
        print(f"Errore durante il parsing di {url}: {e}")
        
def init():
    urls = UrlGenerators()
    print(urls)
    #debug
    #print(list(urls))
    #for url in urls:   
    #    scraping(url)


def addToJson(title,corpus):
    try:
        #Leggiamo il file esistente
        with open(NOME_FILE, 'r') as file:
            data = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        # Se il file è vuoto o non è valido o non viene trovato, creiamo una nuova struttura di dati
        data = []
    
    # Calcola il nuovo ID
    new_id = len(data) + 1

    # Creiamo la struttura del nuovo documento
    new_document = {
        "id": new_id,
        "title": title,
        "corpus": corpus
    }
    
    # Aggiungiamo il nuovo documento alla struttura di dati
    data.append(new_document)
    
    # Scriviamo la struttura di dati aggiornata nel file JSON
    with open(NOME_FILE, 'w') as file:
        json.dump(data, file, indent=4)

    return new_id

init()