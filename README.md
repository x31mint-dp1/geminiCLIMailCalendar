# Automazione Gmail -> Gemini -> Google Calendar

Questo progetto contiene lo script `ControllaEmailCreaEvento.py` che:
- Legge le email non lette da Gmail.
- Invia il testo alla CLI di Gemini per decidere se creare un evento.
- Crea l'evento su Google Calendar e marca l'email come letta.

Requisiti:
- File `client_secret.json` valido nella stessa cartella dello script.
- Il file `token.json` sarà creato al primo avvio dopo l'autorizzazione.
- Variabile d'ambiente `GEMINI_API_KEY` già presente (non forniamo `.env`).
- CLI di Gemini installata e disponibile nel PATH (comando `gemini`).
	- Nota: in CI l'installazione della CLI è "best-effort"; se non disponibile, lo script usa il fallback SDK `google-generativeai` automaticamente.

Installazione dipendenze (Windows PowerShell) senza venv:
```powershell
pip install -r requirements.txt
```

Esecuzione manuale:
```powershell
python .\ControllaEmailCreaEvento.py
```

Pianificazione (Utilità di pianificazione di Windows):
- Azione: avvia `python` con argomento `C:\\Users\\hp_wi\\Downloads\\gemini CLI\\Agent24event\\ControllaEmailCreaEvento.py` (o percorso completo).
- Imposta 3 trigger orari.
- Assicurati che l'ambiente abbia `GEMINI_API_KEY` configurata per l'utente o sistema.

Variabili opzionali:
- `GEMINI_MODEL` (default `gemini-1.5-pro`)
- `TIMEZONE` (default `Europe/Rome`)

Log: `automation.log` nella stessa cartella.

## Esecuzione in GitHub Actions (CI)

Questo repo include un workflow: `.github/workflows/run-agent.yml` che:
- Esegue un precheck dei Secrets e cache di pip,
- Tenta l'installazione della Gemini CLI (best-effort) e imposta il PATH,
- Installa le dipendenze Python,
- Esegue lo script (con jitter di 5s),
- Carica l'artefatto `automation.log` e scrive un Job Summary.

Configura i Secrets nel repository:
- `GEMINI_API_KEY`: chiave API di Gemini.
- `CLIENT_SECRET_JSON`: contenuto del file client_secret.json (raw JSON o base64).
- `TOKEN_JSON`: contenuto del token.json con refresh_token valido (raw JSON o base64).

Lo script, in CI, scrive `client_secret.json` e `token.json` dai Secrets. In ambiente CI, non viene avviato il browser per OAuth: serve un `TOKEN_JSON` già valido.

Se la CLI Gemini non è presente sul runner, lo script utilizza automaticamente il fallback SDK (`google-generativeai`) per generare la risposta JSON; la dipendenza è inclusa in `requirements.txt`.
