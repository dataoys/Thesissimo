import time
import requests
from bs4 import BeautifulSoup

BASE_URL= "https://arxiv.org/html/24"
MONTH_LIST = [i for i in range(1,2)]
ARTICLE_LIST= [i for i in range(1,102)]


urls= []
file=open("WebScraping/src/dates.txt", "w")


#cerco di accedere alla parte successiva del sito, strutturata in questo modo:  
# sito_base/anno/n_documento/section/num_sezione
def UrlGenerators():
    for m in MONTH_LIST:
        for a in ARTICLE_LIST:
            url=BASE_URL+str(m).zfill(2)+"."+str(a).zfill(5)+"v1"
            if CheckConn(url):
                urls.append(url)
                file.write(url + "\n")
                file.flush()
    file.close()
    return urls



def CheckConn(url):
    time.sleep(1)
    response = requests.get(url)
        #controllo che la connessione avvenga correttamente
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tag = soup.find('h1')
        if h1_tag is None:
            print(f"Nessun tag h1 trovato per {url}")
            return False 
        titolo = h1_tag.text.strip()
        if not titolo:
            print(f"Titolo vuoto trovato per {url}")
            return False
        return "No HTML" not in titolo
    else:
        return False


# def writer(url):
#     file.write(url)
#     file.write("\n") 

