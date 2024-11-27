from bs4 import BeautifulSoup
from UrlGenerator import UrlGenerators
import requests
import json




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
for url in urls:   
    scraping(url)

