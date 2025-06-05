"""!
@file DocManipulation.py
@brief Document processing and manipulation utilities for web scraping
@details Provides text cleaning, LaTeX removal, and JSON document management functions
@author Magni && Testoni
@date 2025
"""

import json 
import re

def remove_latex(text):
    """!
    @brief Remove LaTeX expressions from text content
    @param text Input text containing LaTeX expressions
    @return Cleaned text with LaTeX expressions removed
    @details Removes LaTeX commands starting with backslash and cleans whitespace.
             Performs light cleaning suitable for academic document processing.
    """
    # Rimuove qualsiasi stringa che inizia con \ fino al primo spazio o fine stringa
    text = re.sub(r'\\[^\s]*', '', text)
    
    # Rimuove spazi multipli che potrebbero essere rimasti
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def cleanText(text):
    """!
    @brief Comprehensive text cleaning for document content
    @param text Raw text content to clean
    @return Cleaned and normalized text
    @details Performs multiple cleaning operations:
             - LaTeX expression removal
             - Control character filtering
             - Whitespace normalization
             - Newline cleanup
    """
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
    """!
    @brief Add scraped documents to JSON file with incremental IDs
    @param results List of document dictionaries to add
    @param NOME_FILE Path to the output JSON file
    @details Creates structured JSON documents with auto-incremented IDs.
             Overwrites existing file with new complete dataset.
    @return None
    """
    data = []
    
    # Aggiungi tutti i nuovi documenti con ID incrementale
    start_id = 1
    for i, result in enumerate(results):
        new_document = {
            "id": start_id + i,
            "title": result['title'],
            "abstract": result['abstract'],
            "corpus": result['corpus'],
            "keywords": result['keywords'],
            "url": result['url']
        }
        data.append(new_document)
    
    with open(NOME_FILE, 'w') as file:
        json.dump(data, file, indent=4)