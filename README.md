# Calendario con Logging su Zoho

Questo progetto è un'applicazione desktop sviluppata in Python che fornisce un'interfaccia a calendario per creare e gestire eventi, con una funzionalità specifica per registrare il tempo speso su Zoho Projects.

## Indice

1. [Funzionalità](#funzionalità)
2. [Tecnologie Utilizzate](#tecnologie-utilizzate)
3. [Struttura del Progetto](#struttura-del-progetto)
4. [Logiche Chiave Implementate](#logiche-chiave-implementate)
    - [Rendering del Calendario](#rendering-del-calendario)
    - [Gestione API Zoho e Autenticazione](#gestione-api-zoho-e-autenticazione)
    - [Storage Sicuro delle Credenziali](#storage-sicuro-delle-credenziali)
5. [Installazione e Avvio](#installazione-e-avvio)
6. [Configurazione Iniziale](#configurazione-iniziale)
7. [Possibili Miglioramenti Futuri](#possibili-miglioramenti-futuri)

---

## Funzionalità

- **Visualizzazione a Calendario**: Mostra una griglia settimanale da Lunedì a Venerdì, con fasce orarie dalle 8:00 alle 18:00.
- **CRUD completo per gli Eventi**: È possibile Creare, Leggere, Modificare ed Eliminare eventi.
- **Persistenza Locale**: Tutti gli eventi vengono salvati in un database locale SQLite (`events.db`), garantendo che i dati non vengano persi tra le sessioni.
- **Integrazione con Zoho Projects**: Per gli eventi conclusi, è possibile registrare il tempo direttamente su Zoho Projects tramite un form dedicato.
- **Immutabilità degli Eventi Loggati**: Una volta che un evento è stato registrato su Zoho, viene bloccato e non può più essere modificato o eliminato.
- **Pannello Impostazioni**: Una finestra dedicata per inserire e salvare in modo sicuro le credenziali dell'API di Zoho.
- **Gestione Sicura delle Credenziali**: Le chiavi API non sono memorizzate in testo semplice, ma affidate al gestore di credenziali del sistema operativo.

---

## Tecnologie Utilizzate

- **Python 3**: Linguaggio di programmazione principale.
- **CustomTkinter**: Libreria scelta per la GUI. Offre widget moderni e un aspetto più gradevole rispetto a Tkinter standard, pur mantenendo una buona semplicità di sviluppo rispetto a framework più complessi come PyQt o PySide.
- **SQLite 3**: Motore del database. La scelta è ricaduta su SQLite perché è integrato in Python, non richiede un server separato (è basato su file) ed è perfetto per applicazioni desktop single-user.
- **Requests**: Libreria standard de-facto per effettuare chiamate HTTP. Utilizzata per tutte le comunicazioni con le API di Zoho.
- **Keyring**: Libreria fondamentale per la sicurezza. Si interfaccia con il gestore di credenziali nativo del sistema operativo (es. Windows Credential Manager, macOS Keychain) per salvare e recuperare dati sensibili come token e chiavi API. Questo evita di salvarli in file di testo o nel database, pratica altamente sconsigliata.

---

## Struttura del Progetto

Il codice è stato organizzato in una struttura a package per migliorare la manutenibilità e la chiarezza.

- `main.py`: (Root) Il punto di ingresso dell'applicazione. Ha il solo scopo di inizializzare e lanciare l'app.
- `calendar_logger/`: (Package) Contiene tutto il codice sorgente dell'applicazione.
  - `__init__.py`: Rende la cartella un package Python.
  - `app.py`: Il cuore dell'applicazione, gestisce la GUI e la logica principale.
  - `database.py`: Gestisce la persistenza dei dati su SQLite.
  - `settings_manager.py`: Gestisce il salvataggio e caricamento sicuro delle credenziali.
  - `zoho_api.py`: Contiene tutta la logica per comunicare con le API di Zoho.
- `scripts/`: Contiene script accessori.
  - `build.py`: Script per creare l'eseguibile dell'applicazione tramite PyInstaller.
- `requirements.txt`: Elenca le dipendenze Python.
- `.gitignore`: Specifica i file da ignorare nel controllo di versione.
- `events.db`: File del database (generato al primo avvio, ignorato da git).

---

## Logiche Chiave Implementate

### Rendering del Calendario

La visualizzazione degli eventi avviene nel metodo `refresh_events()` in `app.py`. La logica è la seguente:

1. **Pulizia**: Vengono distrutti tutti i widget degli eventi precedentemente disegnati per evitare duplicati.
2. **Fetch**: Vengono recuperati tutti gli eventi dal database.
3. **Iterazione e Disegno**: Per ogni evento, viene calcolata la sua posizione nella griglia (riga e colonna) basandosi su data e ora. La logica supporta la visualizzazione di più eventi nella stessa fascia oraria, affiancandoli.
4. **Dinamicità**: La griglia si adatta agli orari di inizio e fine giornata specificati nelle impostazioni e supporta una granularità di 30 minuti.

### Gestione API Zoho e Autenticazione

La logica risiede in `zoho_api.py` e segue il flusso OAuth 2.0 con Refresh Token.

1. **Token Refresh**: La funzione `refresh_access_token()` si occupa di richiedere un nuovo `access_token` a Zoho. Usa il `refresh_token`, `client_id` e `client_secret` (recuperati in modo sicuro da `settings_manager`) per effettuare una chiamata POST all'endpoint di autenticazione di Zoho. Il nuovo `access_token` viene salvato per le chiamate successive.

2. **Chiamata API con Retry Automatico**: La funzione `log_time_to_zoho()` è stata resa robusta:
    a. Tenta di effettuare la chiamata API usando l'`access_token` salvato.
    b. Se la chiamata fallisce con uno **status code 401 (Unauthorized)**, significa che il token è scaduto.
    c. In questo caso, chiama automaticamente `refresh_access_token()` per ottenerne uno nuovo.
    d. Se il rinnovo ha successo, **ripete la chiamata API originale una seconda volta** con il nuovo token.
    e. Se anche il secondo tentativo fallisce, o se il rinnovo non va a buon fine, restituisce un errore.

Questo meccanismo di "retry" rende l'integrazione molto più stabile, poiché gestisce autonomamente la scadenza dei token.

### Storage Sicuro delle Credenziali

In `settings_manager.py`, la libreria `keyring` viene usata per non esporre mai le credenziali nel codice o in file di testo. Viene definito un `SERVICE_NAME` univoco per l'applicazione. `keyring` usa questo nome per creare uno spazio isolato nel gestore di credenziali del sistema operativo dove salvare le varie chiavi (client_id, client_secret, etc.).

---

## Installazione e Avvio

1. Assicurati di avere Python 3 installato.
2. È consigliabile creare un ambiente virtuale: `python -m venv venv` e attivarlo.
3. Installa le dipendenze: `pip install -r requirements.txt`.
4. Avvia l'applicazione dalla cartella root del progetto: `python main.py`.

### Creare l'Eseguibile (Windows)

Per creare un file `.exe` standalone, esegui lo script di build dalla cartella root:

```bash
python scripts/build.py
```

L'applicazione compilata si troverà in `dist/CalendarLogger`.

---

## Configurazione Iniziale

Per far funzionare l'integrazione con Zoho, segui questi passi:

1. **Ottieni le credenziali da Zoho**: Vai sulla console API di Zoho (`https://api-console.zoho.eu/`) e crea un nuovo client di tipo **Self-Client**. Questo ti fornirà un `Client ID`, un `Client Secret` e un `Refresh Token`.
2. **Avvia l'app** e clicca sul pulsante **"Impostazioni"**.
3. **Inserisci le credenziali** ottenute al punto 1 nei rispettivi campi.
4. Nel campo **"Dominio API"**, inserisci l'URL base corretto per il tuo account Zoho (es. `https://projects.zoho.eu`).
5. Configura gli orari del calendario come preferisci.
6. Clicca su **"Salva Impostazioni"**.

Da questo momento, l'applicazione è pronta per comunicare con le API di Zoho.

---

## Possibili Miglioramenti Futuri

- **UI per Errori**: Mostrare i messaggi di errore (es. credenziali mancanti, fallimento API) in finestre di dialogo invece che sulla console.
- **Datepicker Widget**: Sostituire l'inserimento manuale delle date con un widget a calendario per migliorare l'usabilità.
- **Data di Log Dinamica**: In `zoho_api.py`, la data inviata a Zoho è statica. Renderla dinamica, usando ad esempio la data di fine dell'evento.
- **Fetch di Progetti/Task**: Invece di inserire manualmente ID di progetti e task, implementare chiamate API che recuperano la lista dei progetti e task esistenti e li mostrano in un menu a tendina.
- **Drag and Drop**: Implementare lo spostamento e il ridimensionamento degli eventi con il mouse.
- **Refactoring**: Se la classe `App` in `app.py` dovesse crescere ulteriormente, si potrebbe considerare di estrarre le varie finestre di dialogo in classi separate.
