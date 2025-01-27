import streamlit as st
import subprocess

#Titolo
st.title("THESISSIMO")

# Combobox per selezionare il motore di ricerca
motori_di_ricerca = ["Postgres", "Whoosh", "Pylucene"]
scelta = st.selectbox("Scegli un motore di ricerca:", motori_di_ricerca)


def esegui_streamlit(motore):
    if motore == "Postgres":
        subprocess.Popen(["streamlit", "run", "./PostgresUI.py"])  
    elif motore == "Whoosh":
        subprocess.Popen(["streamlit", "run", "./WhooshUI.py"])  
    elif motore == "PyLucene":
        subprocess.Popen(["streamlit", "run", "WebApp/sqlite_app.py"]) 

# Esegui il file corrispondente
if st.button("Esegui"):
    esegui_streamlit(scelta)
    st.success(f"Applicazione per {scelta} avviata con successo!")