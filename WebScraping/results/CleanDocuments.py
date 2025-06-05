"""!
@file CleanDocuments.py
@brief Advanced document cleaning module for mathematical and scientific text
@details Implements batch processing for cleaning academic documents with mathematical content
@author JuriScan Team
@date 2024
"""

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
    """!
    @brief Clean text containing mathematical expressions and Unicode artifacts
    @param text Input text with mathematical notation and Unicode characters
    @return Cleaned text with mathematical expressions normalized
    @details Removes specific Unicode characters, LaTeX artifacts, HTML conversion errors,
             and mathematical notation while preserving readable content
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
        '\u00CF': '',
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
    """!
    @brief Remove invalid control characters from text
    @param text Input text potentially containing control characters
    @return Text with control characters removed
    @details Removes ASCII control characters (0x00-0x1F and 0x7F) that can
             cause issues in text processing and database storage
    """
    if not isinstance(text, str):
        return text

    # Rimuove i caratteri di controllo (da 0x00 a 0x1F e 0x7F)
    return re.sub(r'[\x00-\x1F\x7F]', '', text)

def clean_documents_in_batches(input_path, output_path="WebScraping/results/Docs_cleaned.json", batch_size=1000):
    """!
    @brief Process and clean documents in memory-efficient batches
    @param input_path Path to the input JSON file with raw documents
    @param output_path Path to the output JSON file for cleaned documents
    @param batch_size Number of documents to process in each batch (default: 1000)
    @details Implements incremental JSON parsing and batch processing for large datasets.
             Provides progress tracking and error handling for robust document cleaning.
    @return None
    @throws FileNotFoundError if input file doesn't exist
    @throws OSError for file I/O errors
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
