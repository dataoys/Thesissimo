import json
import re
import os

# Definizione dei percorsi
input_path = "WebScraping/results/Docs.json"
output_path = "WebScraping/results/Docs_cleaned.json"

def clean_mathematical_text(text):
    if not isinstance(text, str):
        return text
        
    # Rimuove i caratteri Unicode e le notazioni LaTeX
    replacements = {
        'italic_': '',
        'bold_': '',
        'blackboard_': '',
        'start_POSTSUBSCRIPT': '_',
        'end_POSTSUBSCRIPT': '',
        'start_POSTSUPERSCRIPT': '^',
        'end_POSTSUPERSCRIPT': '',
        'start_ARG': '',
        'end_ARG': '',
        'divide': '/',
        '\u011f': '',
        '\ufffd': '',
        '\u2018': '',
        '\u20ac': '',
        '\u00e2': '',
        '\u02c6': '',
        '\u0152': '',
        '\u201e': '',
        '\u00b4': '',
        '\u2013': '',
        '\u2014': '',
        '\u203a': '',
        '\u0178': '',
        '\u2019': '',
        '\u00c2': '',
        '\u00a2': '',
        '\u02dc': '',
        '\u0153': '',
        '\u00b8': '',
        '\u02dd': '',
        '\u0161': '',
        '\u2030': '',
        '\u00cf': '',
        '\u2021': ''
    }
    
    # Applica le sostituzioni
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Rimuove i pattern specifici
    text = re.sub(r'\(⋅\)', '', text)
    
    # Rimuove le formule matematiche tra $ $
    text = re.sub(r'\$[^\$]*\$', '', text)
    
    # Rimuove spazi multipli
    text = re.sub(r'\s+', ' ', text)
    
    # Rimuove parentesi vuote
    text = re.sub(r'\(\s*\)', '', text)
    
    return text.strip()

def clean_documents(documents):
    cleaned_docs = []
    
    for doc in documents:
        cleaned_doc = doc.copy()
        if 'abstract' in cleaned_doc:
            cleaned_doc['abstract'] = clean_mathematical_text(cleaned_doc['abstract'])
        if 'corpus' in cleaned_doc:
            cleaned_doc['corpus'] = clean_mathematical_text(cleaned_doc['corpus'])
        cleaned_docs.append(cleaned_doc)
    
    return cleaned_docs

try:
    # Lettura del file JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)  # Usa load invece di loads
    
    # Pulizia dei documenti
    cleaned_documents = clean_documents(documents)
    
    # Salvataggio del risultato
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_documents, f, indent=4, ensure_ascii=False)
    
    print(f"File pulito salvato in: {output_path}")

except FileNotFoundError:
    print(f"Errore: Il file {input_path} non è stato trovato")
except json.JSONDecodeError:
    print(f"Errore: Il file {input_path} non contiene un JSON valido")
except Exception as e:
    print(f"Si è verificato un errore: {str(e)}")