import streamlit as st
import subprocess

#Titolo
st.title("THESISSIMO")
motori_di_ricerca = ["Postgres", "Whoosh", "PyLucene"]

scelta = st.selectbox("Scegli un motore di ricerca:", motori_di_ricerca)


def esegui_streamlit(motore):
    """
    Multiple choice search engine UI function

    This function takes the user's choice of search engine and runs the corresponding Streamlit application.

    Arguments:
        motore (str): The user's choice of search engine.
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