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


def addToJson(results, NOME_FILE):
    try:
        with open(NOME_FILE, 'r') as file:
            data = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    
    # Aggiungi tutti i nuovi documenti con ID incrementale
    start_id = len(data) + 1
    for i, result in enumerate(results):
        new_document = {
            "id": start_id + i,
            "title": result['title'],
            "corpus": result['corpus']
        }
        data.append(new_document)
    
    with open(NOME_FILE, 'w') as file:
        json.dump(data, file, indent=4)