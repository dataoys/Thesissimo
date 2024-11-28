from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
import requests
import json
import os


NOME_FILE = "Doc.json"

#Numero massimo di documenti da web scrapeare.
DOCUMENTI_MAX = 100000

documenti = []


def scraping(url):

    try:
        #in response viene salvato il sito
        response = requests.get(url)
        #controllo che la connessione avvenga correttamente
        # if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        #estraiamo il titolo
        titolo = soup.find('h1').text.strip()
        #debug
        print(titolo)
        #estraiamo il corpo
        corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
        addToJson(titolo,corpo)

    except Exception as e:
        print("Errore durante il parsing di {url}: {e} ")
        return None
    
def init():
    urls = UrlGenerators()
    #debug
    #print(list(urls))
    for url in urls:   
        scraping(url)


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