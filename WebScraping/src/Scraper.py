from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
from DocManipualtion import addToJson, cleanText
from concurrent.futures import ThreadPoolExecutor
import requests
import time
from tqdm import tqdm

NOME_FILE = "Doc.json"

#Numero massimo di documenti da web scrapeare.
DOCUMENTI_MAX = 100000

documenti = []



def scraping(url):

    cleanText()

    try:
        #in response viene salvato il sito
        response = requests.get(url)
        response.encoding = 'utf-8'
        #controllo che la connessione avvenga correttamente
        soup = BeautifulSoup(response.text, 'html.parser')

        #estraiamo il titolo
        titolo = soup.find('h1').text.strip()
        #debug
        print(titolo)
        #estraiamo il corpo
        corpo = " ".join([p.text.strip() for p in soup.find_all('p')])
        corpo = cleanText(corpo)
        addToJson(titolo,corpo, NOME_FILE)

    except Exception as e:
        print("Errore durante il parsing di {url}: {e} ")
        return None
    
def init():
    urls = UrlGenerators()
    #debug
    #print(list(urls))
    for url in urls:   
        scraping(url)


init()