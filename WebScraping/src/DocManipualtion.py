import json 
import re

def remove_latex(text):
    # Rimuove qualsiasi stringa che inizia con \ fino al primo spazio o fine stringa
    text = re.sub(r'\\[^\s]*', '', text)
    
    # Rimuove spazi multipli che potrebbero essere rimasti
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def cleanText(text):
    # Prima rimuovi il LaTeX
    text = remove_latex(text)
    
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
    data = []
    
    # Aggiungi tutti i nuovi documenti con ID incrementale
    start_id = 1
    for i, result in enumerate(results):
        new_document = {
            "id": start_id + i,
            "title": result['title'],
            "abstract": result['abstract'],
            "corpus": result['corpus'],
            "keywords": result['keywords']
        }
        data.append(new_document)
    
    with open(NOME_FILE, 'w') as file:
        json.dump(data, file, indent=4)