"""!
@file mainPage.py
@brief Main entry point for JuriScan web application
@details Provides search engine selection interface and launches corresponding Streamlit apps
@author Magni && Testoni
@date 2025
"""

import streamlit as st
import subprocess

#Titolo
st.title("THESISSIMO")
motori_di_ricerca = ["Postgres", "Whoosh", "PyLucene"]

scelta = st.selectbox("Scegli un motore di ricerca:", motori_di_ricerca)


def esegui_streamlit(motore):
    """!
    @brief Launch specific search engine UI application
    @param motore String identifier for the chosen search engine
    @details Starts subprocess with appropriate Streamlit application based on user selection.
             Supports PostgreSQL, Whoosh, and PyLucene search engines.
    @return None
    """
    if motore == "Postgres":
        subprocess.Popen(["streamlit", "run", "./WebApp/PostgresUI.py"])  
    elif motore == "Whoosh":
        subprocess.Popen(["streamlit", "run", "./WebApp/WhooshUI.py"])  
    elif motore == "PyLucene":
        print("PyLucene")
        subprocess.Popen(["streamlit", "run", "./WebApp/PyLuceneUI.py"]) 

# Esegui il file corrispondente
if st.button("Esegui"):
    esegui_streamlit(scelta)
    st.success(f"Applicazione per {scelta} avviata con successo!")