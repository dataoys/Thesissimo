import json 
import re

def cleanText(text):
    # Pulizia base
    text = re.sub(r'\s+', ' ', text)
    text = ''.join(char for char in text if char.isprintable())
    
    # Pulizie aggiuntive
    text = re.sub(r'\n+', '\n', text)  # Rimuove linee vuote multiple
    text = re.sub(r'[\t\r\f\v]', '', text)  # Rimuove altri caratteri di spaziatura
    text = re.sub(r'\s*\n\s*', '\n', text)  # Pulisce gli spazi intorno ai newline
    text = re.sub(r' +', ' ', text)  # Rimuove spazi multipli
    
    return text.strip()


def addToJson(title,corpus,filename):
    try:
        #Leggiamo il file esistente
        with open(filename, 'r') as file:
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
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

    return new_id