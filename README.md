# 🌐 **THESISSIMO** - Sistema Avanzato di Ricerca Documentale Scientifica

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![PyLucene](https://img.shields.io/badge/PyLucene-9.7+-orange.svg)](https://lucene.apache.org/pylucene/)
[![Whoosh](https://img.shields.io/badge/Whoosh-2.7+-green.svg)](https://whoosh.readthedocs.io)
[![Licenza MIT](https://img.shields.io/github/license/dataoys/Thesissimo)](https://github.com/dataoys/Thesissimo/blob/main/LICENSE)

![Thesissimo Logo](forces-7427867e0c0aa40128b3f01dd26a1945c3c08359-doc-doxygen-awesome-css/doc/doxygen-awesome-css/Logo.png)

**THESISSIMO** è un sistema avanzato di ricerca documentale progettato per permettere agli studenti, ricercatori e professionisti di cercare tra decine di migliaia di documenti scientifici. Il sistema implementa tre motori di ricerca differenti (PostgreSQL, PyLucene, Whoosh) con algoritmi di ranking avanzati e tecniche di Natural Language Processing per garantire risultati precisi e rilevanti.

## 🎯 **Caratteristiche Principali**

### 🔍 **Ricerca Multi-Engine**
- **PostgreSQL**: Full-text search con `ts_rank` e `ts_rank_cd`.
- **PyLucene**: Motore basato su Apache Lucene con `BM25Similarity` e `ClassicSimilarity` (TF-IDF).
- **Whoosh**: Search engine Python puro con `BM25F` e `TF_IDF`.

### 🧠 **Natural Language Processing Avanzato**
- **Espansione Semantica delle Query**: Utilizzo di WordNet per arricchire le query con sinonimi, iperonimi e iponimi.
- **Estrazione Automatica di Keyword**: YAKE! (Yet Another Keyword Extractor) per identificare i termini più significativi.
- **Lemmatizzazione e POS Tagging**: NLTK per normalizzare le parole alla loro forma base e identificarne il ruolo grammaticale, migliorando la qualità dell'espansione e della ricerca.
- **Analizzatori Personalizzati**: StemmingAnalyzer in Whoosh per una migliore corrispondenza morfologica.

### 📊 **Sistema di Valutazione Rigoroso (Benchmark)**
- **Metriche Standard IR**: Calcolo di Precision@k, Recall@k e Mean Average Precision (MAP).
- **Pooling Method**: Creazione di un ground truth affidabile aggregando i top N risultati da tutti i motori e algoritmi di ranking.
- **Analisi Comparativa**: Visualizzazioni dettagliate delle performance dei motori (precision-recall curves, box plots, bar charts) generate con Matplotlib e Seaborn.
- **Analisi dei Tempi di Risposta**: Misurazione e confronto della velocità di ricerca dei diversi motori.

### 🌐 **Interfaccia Web Intuitiva (Streamlit)**
- **Dashboard Multi-Engine**: Selezione facile del motore di ricerca desiderato.
- **Filtri Dinamici**: Possibilità di restringere la ricerca a campi specifici (titolo, abstract, corpus).
- **Visualizzazione Metriche in Real-Time**: Grafici precision-recall direttamente nell'interfaccia utente per Whoosh e PyLucene (se implementato).
- **Design Responsive**: Accessibile e facile da usare su diversi dispositivi.

### 🕷️ **Web Scraping Flessibile e Robusto**
- **Generazione URL Dinamica**: Modulo `UrlGenerator.py` per creare liste di URL da sorgenti accademiche.
- **Scraping Multi-Threaded con Pause/Resume**: `Scraper.py` permette di interrompere e riprendere il processo di scraping.
- **Rotazione User-Agent e Rate Limiting**: Tecniche per evitare il blocco da parte dei server.
- **Pulizia Avanzata dei Dati**: `CleanDocuments.py` e `DocManipulation.py` per normalizzare il testo, rimuovere artefatti LaTeX, caratteri Unicode problematici e formule matematiche, operando in batch per efficienza.

## 📁 **Struttura del Progetto**

```plaintext
THESISSIMO/
│
├── Benchmark/                          # Sistema di valutazione e benchmark
│   ├── Results/                        # Risultati dei benchmark (es. benchmark_results.json) e grafici generati
│   ├── benchmark.py                    # Script principale per l'esecuzione dei benchmark e generazione grafici
│   └── create_pool.py                  # Script per creare il pool di documenti per la relevance judgment (ground truth)
│
├── SearchEngine/                       # Implementazioni dei motori di ricerca
│   ├── index/                          # Directory per gli indici di PyLucene
│   ├── WhooshIndex/                    # Directory per gli indici di Whoosh
│   ├── Pylucene.py                     # Implementazione del motore di ricerca PyLucene
│   ├── Whoosh.py                       # Implementazione del motore di ricerca Whoosh
│   ├── Postgres.py                     # Implementazione della ricerca full-text con PostgreSQL
│   └── Queries.py                      # Utility per la connessione e gestione query al DB PostgreSQL
│
├── WebApp/                             # Interfaccia utente web basata su Streamlit
│   ├── mainPage.py                     # Pagina principale per la selezione del motore di ricerca
│   ├── PyLuceneUI.py                   # Interfaccia utente per PyLucene
│   ├── WhooshUI.py                     # Interfaccia utente per Whoosh
│   └── PostgresUI.py                   # Interfaccia utente per PostgreSQL
│
├── WebScraping/                        # Moduli per il web scraping e processamento dati
│   ├── results/                        # File JSON contenenti i dati grezzi e puliti
│   │   ├── Docs.json                   # Documenti grezzi estratti dallo scraping
│   │   ├── Docs_cleaned.json           # Documenti puliti pronti per l'indicizzazione
│   │   └── CleanDocuments.py           # Script per la pulizia avanzata dei documenti
│   └── src/                            # Codice sorgente per lo scraping
│       ├── Scraper.py                  # Scraper principale con gestione multi-threading e pause/resume
│       ├── DocManipulation.py          # Funzioni per la manipolazione e salvataggio dei documenti
│       └── UrlGenerator.py             # Generatore di URL per lo scraping
│
├── forces-*/                           # File relativi alla documentazione (es. Doxygen)
│   └── doc/doxygen-awesome-css/
│       ├── Doxyfile
│       └── Logo.png
│
├── uin.txt                             # User Information Needs: query di test per il benchmark
├── requirements.txt                    # Dipendenze Python del progetto
└── README.md                           # Questo file
```

## ⚙️ **Flusso di Lavoro del Progetto**

Il progetto THESISSIMO segue un flusso di lavoro strutturato, dalla raccolta dei dati alla loro valutazione.

### 1. 🕸️ **Web Scraping e Preparazione dei Dati (`WebScraping/`)**

La fase iniziale consiste nella raccolta dei documenti scientifici.

*   **Generazione degli URL (`UrlGenerator.py`)**: Questo script è responsabile della creazione della lista di URL target da cui verranno estratti i documenti.
*   **Estrazione dei Contenuti (`Scraper.py`)**:
    *   Utilizza `requests` e `BeautifulSoup` per scaricare e parsare le pagine HTML.
    *   Implementa la **rotazione degli User-Agent** (`get_random_user_agent`) per simulare accessi da browser diversi e ridurre il rischio di blocco.
    *   Introduce **pause (`time.sleep(2)`)** tra le richieste per non sovraccaricare i server.
    *   Supporta la funzionalità di **pause e resume** tramite un `threading.Event` (`pause_event`), permettendo all'utente di controllare il processo di scraping in tempo reale tramite input da console (`monitor_input`).
    *   Estrae campi chiave come titolo (da `<h1>`), abstract (da `<div class_='ltx_abstract'>`), corpo del testo (da `<p>`) e keywords (da `ltx_keywords` o `ltx_classification`).
    *   Gestisce eccezioni come errori di connessione o status code HTTP problematici (es. 403).
    *   I risultati grezzi vengono salvati in `WebScraping/results/Docs.json` tramite `DocManipulation.addToJson`.
*   **Pulizia Avanzata dei Documenti (`CleanDocuments.py`)**:
    *   Legge i documenti da `Docs.json` in batch utilizzando `ijson` per un processamento efficiente in termini di memoria.
    *   La funzione `clean_mathematical_text` rimuove:
        *   Artefatti di conversione HTML e messaggi di errore.
        *   Sequenze specifiche Unicode e caratteri di controllo (`remove_control_characters`).
        *   Espressioni LaTeX e formule matematiche (es. testo tra `$ $`).
        *   Spazi multipli e parentesi vuote.
    *   I documenti puliti vengono salvati in `WebScraping/results/Docs_cleaned.json`, pronti per l'indicizzazione da parte dei motori di ricerca.
    *   Lo script `Scraper.py` orchestra anche l'importazione dei dati puliti in PostgreSQL tramite `jsonToPG` dopo aver resettato la tabella con `resetTable`.

### 2. 🔍 **Indicizzazione e Motori di Ricerca (`SearchEngine/`)**

Una volta puliti, i documenti vengono indicizzati dai tre motori di ricerca implementati.

#### 🔥 **PyLucene (`Pylucene.py`)**
Basato su Apache Lucene, offre performance elevate e funzionalità di ricerca avanzate.
*   **Inizializzazione JVM**: `initialize_jvm()` assicura che la Java Virtual Machine sia avviata correttamente.
*   **Indicizzazione**:
    *   `create_index()`: Crea un nuovo indice in `SearchEngine/index/` se non esiste, altrimenti apre quello esistente.
    *   Utilizza `StandardAnalyzer` per l'analisi del testo.
    *   I documenti da `Docs_cleaned.json` vengono letti con `ijson` e aggiunti all'indice come `Document` Lucene, con campi `StringField` (per ID) e `TextField` (per titolo, abstract, corpus, keywords, url).
    *   Supporta commit periodici durante l'indicizzazione di grandi volumi di dati.
*   **Ricerca**:
    *   `search_documents()`: Permette la ricerca specificando i campi (titolo, abstract, corpus) e il tipo di ranking.
    *   **NLP Query Expansion**: `expand_query()` arricchisce la query dell'utente utilizzando:
        *   **YAKE!**: Per estrarre le keyword principali.
        *   **NLTK**: Tokenizzazione, POS tagging (`get_wordnet_pos`), lemmatizzazione (`WordNetLemmatizer`) e rimozione di stopwords.
        *   **WordNet**: Per trovare sinonimi, iperonimi e iponimi, espandendo la portata semantica della ricerca.
        *   La query espansa viene formattata per Lucene (termini uniti da `OR`, keyword originali con boost `^2`).
    *   Costruisce una `BooleanQuery` combinando le clausole per i campi selezionati con `BooleanClause.Occur.SHOULD`.
*   **Ranking**:
    *   Supporta `BM25Similarity` (default) e `ClassicSimilarity` (TF-IDF).
*   **Metriche**: `calculate_precision_recall()` calcola precision e recall basandosi su uno score threshold adattivo, e `plot_precision_recall_curve()` (commentata nel codice fornito, ma l'intenzione c'è) visualizzerebbe questi dati.

#### 🐍 **Whoosh (`Whoosh.py`)**
Un motore di ricerca interamente scritto in Python, facile da integrare e configurare.
*   **Setup NLTK**: `setup_nltk()` scarica le risorse NLTK necessarie (WordNet, tagger, stopwords).
*   **Schema e Indicizzazione**:
    *   `create_schema()`: Definisce la struttura dei documenti nell'indice, utilizzando `StemmingAnalyzer` per i campi testuali per migliorare il matching.
    *   `create_or_get_index()`: Gestisce la creazione o l'apertura dell'indice in `SearchEngine/WhooshIndex/`. Può forzare la ricostruzione dell'indice.
    *   `index_documents()`: Popola l'indice leggendo i dati da `Docs_cleaned.json` in batch (usando `ijson`) per efficienza.
*   **Ricerca**:
    *   `search_documents()`: Funzione principale per la ricerca.
    *   **NLP Query Expansion**: `process_natural_query()` espande la query in modo simile a PyLucene, usando YAKE, NLTK (tokenizzazione, POS tagging, lemmatizzazione) e WordNet (sinonimi, iperonimi, iponimi). La query risultante è una stringa di termini uniti da `OR`.
    *   **Query Parsing Avanzato**: `parse_advanced_query()` gestisce query complesse che includono specificatori di campo (es. `title:"deep learning" AND corpus:python`) e operatori booleani. Per query semplici senza operatori, utilizza `MultifieldParser`.
    *   Utilizza `OrGroup` per combinare i termini di ricerca sui campi selezionati.
*   **Ranking**:
    *   Supporta `BM25F` (default, adatto per campi multipli) e `TF_IDF`.

#### 🐘 **PostgreSQL (`Postgres.py`)**
Sfrutta le capacità di full-text search del database relazionale PostgreSQL.
*   **Connessione al DB**: Utilizza `dbConn()` da `Queries.py` per stabilire la connessione.
*   **Preparazione Testo per Ricerca**: PostgreSQL gestisce internamente la tokenizzazione e lo stemming tramite `tsvector` e `to_tsquery` con dizionario 'english'.
*   **Ricerca**:
    *   `search()`: Funzione principale che gestisce due modalità di query:
        1.  **Query Avanzate con Campi Specifici**: `parse_advanced_query()` interpreta query come `title:space AND corpus:python`, costruendo la clausola `WHERE` appropriata per SQL.
        2.  **Query Basate su Checkbox e NLP**: Se la query è in linguaggio naturale, `extract_keywords()` (utilizzando NLTK POS tagging e rimozione di stopwords) estrae i termini significativi. `build_search_query()` costruisce quindi la query SQL.
    *   Utilizza `phraseto_tsquery` per ricerche di frasi e `to_tsquery` per termini singoli (spesso combinati con `&` per AND logico).
*   **Ranking**:
    *   Supporta le funzioni di ranking di PostgreSQL `ts_rank` e `ts_rank_cd`.
    *   La clausola `ORDER BY rank DESC` ordina i risultati per rilevanza.

### 3. 📊 **Benchmarking e Valutazione (`Benchmark/`)**

Per valutare oggettivamente le performance dei motori di ricerca, è stato implementato un sistema di benchmark.

*   **User Information Needs (`uin.txt`)**:
    *   Contiene un set di 10 query di test rappresentative di diverse aree scientifiche. Ogni UIN è accompagnata da una query strutturata di esempio (es. `abstract:"symmetry" AND corpus:"field theory"`).
*   **Creazione del Ground Truth (Processo a Due Fasi)**:
    1.  **Generazione del Pool Iniziale (`create_pool.py`)**:
        *   Implementa il **pooling method**.
        *   Carica le query da `uin.txt`.
        *   Esegue ogni query su tutti e tre i motori di ricerca (PyLucene, Whoosh, PostgreSQL) utilizzando i loro diversi algoritmi di ranking (es. BM25, TF-IDF per PyLucene/Whoosh; ts_rank, ts_rank_cd per PostgreSQL).
        *   Colleziona i **top N risultati** (default `TOP_N_FOR_POOLING = 20`) da ogni combinazione motore/ranking.
        *   Unisce tutti i documenti recuperati per una data query in un set unico (`unique_doc_ids_for_query`).
        *   Salva questi "pool" di documenti in `GroundTruth/Pool.json`. Questo file contiene la lista dei documenti da giudicare.
    2.  **Creazione dei Giudizi di Rilevanza (Manuale)**:
        *   Il file `GroundTruth/Pool.json` deve essere **revisionato manualmente** da un esperto.
        *   Per ogni query nel `Pool.json`, l'esperto deve giudicare la rilevanza di ciascun documento associato.
        *   I risultati di questa valutazione manuale devono essere salvati in un nuovo file chiamato `GroundTruth/JudgedPool.json`. Questo file conterrà, per ogni query, una mappa di ID documento e il relativo giudizio di rilevanza (es. 1 per rilevante, 0 per non rilevante).
*   **Esecuzione dei Benchmark (`benchmark.py`)**:
    *   Carica le query da `uin.txt` e i giudizi di rilevanza dal file `GroundTruth/JudgedPool.json` (creato manualmente).
    *   Per ogni query e per ogni motore/algoritmo di ranking:
        *   Esegue la ricerca.
        *   Misura il tempo di risposta.
        *   Calcola le metriche di Information Retrieval:
            *   **Precision@k** (P@5, P@10, P@20)
            *   **Recall@k** (R@5, R@10, R@20)
            *   **Average Precision (AP)** per ogni query.
    *   Calcola il **Mean Average Precision (MAP)** per ogni motore/configurazione.
    *   Salva i risultati aggregati in `Benchmark/Results/benchmark_results.json`.
    *   **Generazione Grafici**:
        *   `plot_precision_recall_metrics()`: Crea grafici (box plot, bar plot, istogrammi) per P@k, R@k, AP e tempi di risposta per ogni singolo motore, salvandoli in `Plots/[EngineName]/`.
        *   `plot_comparative_analysis()`: Genera grafici comparativi (bar chart per MAP, P@k, R@k; heatmap) tra tutti i motori, salvandoli in `Plots/Comparative/`.

### 4. 🖥️ **Interfaccia Utente (`WebApp/`)**

L'applicazione web, costruita con Streamlit, permette agli utenti di interagire con i motori di ricerca.

*   **`mainPage.py`**: Pagina di ingresso che permette all'utente di selezionare quale motore di ricerca utilizzare (Postgres, Whoosh, PyLucene). Avvia l'interfaccia specifica come subprocess.
*   **`PostgresUI.py`**, **`WhooshUI.py`**, **`PyLuceneUI.py`**:
    *   Forniscono un'interfaccia dedicata per ogni motore.
    *   Consentono all'utente di inserire una query di ricerca.
    *   Offrono la possibilità di selezionare il tipo di algoritmo di ranking (es. "TF_IDF" o "BM25" per PyLucene/Whoosh, "ts_rank" o "ts_rank_cd" per PostgreSQL).
    *   Permettono di filtrare la ricerca per campi specifici (titolo, abstract, corpus) tramite checkbox.
    *   Visualizzano i risultati della ricerca, includendo titolo, abstract (espandibile), keywords, punteggio di rilevanza e un link al documento originale.
    *   `WhooshUI.py` e `PyLuceneUI.py` includono (o sono predisposti per includere) la visualizzazione di grafici precision-recall per la query corrente.

## 🚀 **Installazione e Setup**

### **1. Requisiti di Sistema**
*   Python 3.8+
*   Java 11+ (per PyLucene)
*   PostgreSQL 13+ (per il motore di ricerca PostgreSQL)
*   Git

### **2. Clonazione Repository**
```bash
git clone https://github.com/dataoys/Thesissimo.git # Sostituisci con il tuo URL effettivo
cd Thesissimo
```

### **3. Setup Ambiente Python**
È consigliato utilizzare un ambiente virtuale:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### **4. Setup Database PostgreSQL (se si usa il motore PostgreSQL)**
1.  Installa PostgreSQL (consulta la documentazione ufficiale per il tuo OS).
2.  Crea un database e un utente per THESISSIMO:
    ```sql
    CREATE DATABASE juriscan;
    CREATE USER juriscan_user WITH PASSWORD 'password'; -- Scegli una password sicura
    GRANT ALL PRIVILEGES ON DATABASE juriscan TO juriscan_user;
    ```
3.  Assicurati che le credenziali in `SearchEngine/Queries.py` (o dove sono definite) corrispondano.

### **5. Setup PyLucene (se si usa il motore PyLucene)**
1.  Installa un JDK (Java Development Kit), versione 11 o superiore. Assicurati che `JAVA_HOME` sia configurato.
2.  L'installazione di PyLucene tramite `pip install PyLucene` dovrebbe funzionare se l'ambiente Java è configurato correttamente. Potrebbero essere necessari passaggi aggiuntivi a seconda del sistema operativo (vedi documentazione PyLucene).

### **6. Download Risorse NLTK**
Esegui uno script Python una tantum o integra nel setup:
```python
import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger') # o 'averaged_perceptron_tagger_eng'
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4') # Open Multilingual WordNet, spesso richiesto da WordNet
```
Gli script `SearchEngine/Whoosh.py` e `SearchEngine/Pylucene.py` tentano di scaricare queste risorse se mancanti.

## 🛠️ **Utilizzo del Sistema**

### **1. Esecuzione del Web Scraping (una tantum o per aggiornare i dati)**
```bash
python WebScraping/src/Scraper.py
```
Questo script eseguirà lo scraping, la pulizia e l'importazione in PostgreSQL.

### **2. Creazione/Aggiornamento Indici dei Motori di Ricerca**
*   **PyLucene**:
    ```bash
    python SearchEngine/Pylucene.py
    ```
    (Rimuovere il commento da `if __name__ == "__main__":` nel file per eseguirlo)
*   **Whoosh**:
    ```bash
    python SearchEngine/Whoosh.py
    ```
    (Lo script è già configurato per creare/aggiornare l'indice se eseguito direttamente)

### **3. Avvio dell'Applicazione Web**
```bash
streamlit run WebApp/mainPage.py
```
Questo avvierà la pagina principale da cui potrai selezionare e lanciare le interfacce dei singoli motori di ricerca.

### **4. Esecuzione dei Benchmark**
1.  **Crea il Pool Iniziale per il Ground Truth**:
    ```bash
    python Benchmark/create_pool.py
    ```
    Questo genererà `GroundTruth/Pool.json`.
2.  **Crea Manualmente `JudgedPool.json`**:
    Dopo aver eseguito `create_pool.py`, apri `GroundTruth/Pool.json`. Per ogni query, valuta la rilevanza dei documenti elencati. Crea un nuovo file, `GroundTruth/JudgedPool.json`, e inserisci i tuoi giudizi seguendo il formato:
    ```json
    {
        "query text from uin.txt": {
            "doc_id_1": 1,  // 1 per rilevante, 0 per non rilevante
            "doc_id_2": 0
        },
        "altra query...": {
            "doc_id_x": 1
        }
    }
    ```
3.  **Esegui i Benchmark**:
    ```bash
    python Benchmark/benchmark.py
    ```
    Questo script utilizzerà `JudgedPool.json` per calcolare le metriche e genererà i grafici comparativi e specifici per motore in `Plots/` e i risultati numerici dettagliati (incluse le metriche per query) in `Benchmark/Results/benchmark_results.json`.
 

---

**THESISSIMO** - *Rivoluzionando la ricerca documentale scientifica con AI e tecnologie avanzate* 🚀

