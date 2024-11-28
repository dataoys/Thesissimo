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
        print(titolo)
        addTitles(titolo)

        #estraiamo il corpo
        #corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
        
        return {"titolo": titolo}
        # else:
        #     print("Impossibile accedere a {url} stato {reposnse.status_code}")
        #     return None
    except Exception as e:
        print("Errore durante il parsing di {url}: {e} ")
        return None
    

urls = UrlGenerators()
#print(list(urls))
for url in urls:   
    scraping(url)

def addTitles(titolo):
    #Controllo sull'esistenza del file.
    if os.path.exists("/JuriScan/WebScraping/src/Doc.json"):
        #Apro in lettura ed eseguo controlli
        with open(NOME_FILE, "r", encoding ="utf-8") as file:
            try:
                titoli = json.load(file)
            except json.JSONDecodeError:
                #Se il file è vuoto o corrotto imposto titoli a urls
                titoli = urls
    else:
        #Se il file non esiste lo imposto uguale a urls
        titoli = urls

    #così da evitare duplicati (e se qualcuno dovesse per caso mancare lo aggiungiamo)
    if titolo not in titoli:
        titoli.append(titolo)

    with open(NOME_FILE, "w", encoding="utf-8") as file:
        json.dump(titoli, file, ensure_ascii=False, indent=4)