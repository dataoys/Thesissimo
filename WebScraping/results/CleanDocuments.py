import os
import ijson
import json
import re

"""
Path to the input JSON file.
"""
input_path = "WebScraping/results/Docs.json"
"""
Path to the output JSON file.
"""
output_path = "WebScraping/results/Docs_cleaned.json"

def clean_mathematical_text(text):
    """
    Clean a text containing mathematical expressions.

    This function cleans a text containing mathematical expressions by removing Unicode characters and LaTeX notations.

    Arguments:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
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

def clean_documents_in_batches(input_path, output_path="WebScraping/results/Docs_cleaned.json", batch_size=1000):
    """
    Clean documents in batches from a JSON file.

    This function reads documents from a JSON file incrementally, cleans them in batches, and writes the cleaned documents to a new JSON file.

    Arguments:
        input_path (str): Path to the input JSON file.
        output_path (str): Path to the output JSON file.
        batch_size (int): Number of documents to process in each batch.
    """
    # Verifica che la directory di output esista
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Crea la directory se non esiste

    try:
        with open(input_path, 'r', encoding='utf-8', errors="ignore") as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            # Scrivi l'inizio dell'array JSON
            outfile.write("[\n")
            
            batch = []
            first = True
            
            # Itera sui documenti nel file JSON
            for document in ijson.items(infile, "item"):
                # Pulisci il documento
                if 'abstract' in document:
                    document['abstract'] = clean_mathematical_text(document['abstract'])
                if 'corpus' in document:
                    document['corpus'] = clean_mathematical_text(document['corpus'])
                
                batch.append(document)
                
                # Se il batch raggiunge la dimensione specificata, scrivilo nel file di output
                if len(batch) >= batch_size:
                    if not first:
                        outfile.write(",\n")
                    json.dump(batch, outfile, indent=4, ensure_ascii=False)
                    batch = []
                    first = False
            
            # Scrivi eventuali documenti rimanenti
            if batch:
                if not first:
                    outfile.write(",\n")
                json.dump(batch, outfile, indent=4, ensure_ascii=False)
            
            # Scrivi la fine dell'array JSON
            outfile.write("\n]")
    except FileNotFoundError:
        print(f"Errore: Il file {input_path} non è stato trovato")
    except OSError as e:
        print(f"Errore durante l'apertura o la scrittura del file: {e}")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")

try:
    # Pulizia dei documenti in batch
    clean_documents_in_batches(input_path, output_path, batch_size=1000)
    print(f"File pulito salvato in: {output_path}")

except FileNotFoundError:
    print(f"Errore: Il file {input_path} non è stato trovato")
except json.JSONDecodeError:
    print(f"Errore: Il file {input_path} non contiene un JSON valido")
except Exception as e:
    print(f"Si è verificato un errore: {str(e)}")
