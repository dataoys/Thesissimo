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
        
    # Remove HTML conversion error message with flexible whitespace matching
    error_pattern = r'HTML conversions sometimes display errors.*?best practices\.'
    text = re.sub(error_pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove any remaining artifacts from the error message
    text = re.sub(r'Authors:.*?supported packages\.', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove specific unicode characters
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

def remove_control_characters(text):
    """
    Rimuove i caratteri di controllo non validi da un testo.

    Questo include i caratteri ASCII da 0x00 a 0x1F e 0x7F.
    
    Arguments:
        text (str): Il testo da pulire.
    
    Returns:
        str: Il testo senza i caratteri di controllo.
    """
    if not isinstance(text, str):
        return text

    # Rimuove i caratteri di controllo (da 0x00 a 0x1F e 0x7F)
    return re.sub(r'[\x00-\x1F\x7F]', '', text)

def clean_documents_in_batches(input_path, output_path="WebScraping/results/Docs_cleaned.json", batch_size=1000):
    """
    Clean documents in batches from a JSON file.

    This function reads documents from a JSON file incrementally, cleans them in batches, 
    and writes the cleaned documents to a new JSON file.

    Arguments:
        input_path (str): Path to the input JSON file.
        output_path (str): Path to the output JSON file.
        batch_size (int): Number of documents to process in each batch.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(input_path, 'r', encoding='utf-8', errors="ignore") as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            outfile.write("[\n")
            
            batch = []
            first = True
            total_docs = 0
            print("🔄 Inizio pulizia documenti...")
            
            # Itera sui documenti nel file JSON
            for document in ijson.items(infile, "item"):
                total_docs += 1
                
                # Stampa progresso ogni 50 documenti
                if total_docs % 50 == 0:
                    print(f"📝 Processati {total_docs} documenti...")
                
                # Pulisci il documento
                if 'abstract' in document:
                    document['abstract'] = clean_mathematical_text(document['abstract'])
                    document['abstract'] = remove_control_characters(document['abstract'])
                if 'corpus' in document:
                    document['corpus'] = clean_mathematical_text(document['corpus'])
                    document['corpus'] = remove_control_characters(document['corpus'])
                
                batch.append(document)
                
                # Se il batch raggiunge la dimensione specificata, scrivilo
                if len(batch) >= batch_size:
                    if not first:
                        outfile.write(",\n")
                    json.dump(batch, outfile, indent=4, ensure_ascii=False)
                    print(f"💾 Salvato batch di {len(batch)} documenti...")
                    batch = []
                    first = False
            
            # Scrivi eventuali documenti rimanenti
            if batch:
                if not first:
                    outfile.write(",\n")
                json.dump(batch, outfile, indent=4, ensure_ascii=False)
                print(f"💾 Salvato ultimo batch di {len(batch)} documenti...")
            
            outfile.write("\n]")
            print(f"✅ Completato! Totale documenti processati: {total_docs}")
            
    except FileNotFoundError:
        print(f"❌ Errore: Il file {input_path} non è stato trovato")
    except OSError as e:
        print(f"❌ Errore durante l'apertura o la scrittura del file: {e}")
    except Exception as e:
        print(f"❌ Si è verificato un errore: {e}")

try:
    print(f"File pulito salvato in: {output_path}")

except FileNotFoundError:
    print(f"Errore: Il file {input_path} non è stato trovato")
except json.JSONDecodeError:
    print(f"Errore: Il file {input_path} non contiene un JSON valido")
except Exception as e:
    print(f"Si è verificato un errore: {str(e)}")

if __name__ == "__main__":
    # Esegui la funzione di pulizia
    clean_documents_in_batches(input_path, output_path)
    print(f"File pulito salvato in: {output_path}")
    