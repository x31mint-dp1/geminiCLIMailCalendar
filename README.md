# Automazione Gmail -> Gemini -> Google Calendar

Questo progeLimitazione elaborazione email (configurazione ottimizzata):
- Lo script elabora al massimo 1 email non letta per esecuzione (configurabile via `MAX_UNREAD_TO_PROCESS`).
- Con 3 esecuzioni giornaliere = max 3 email processate/giorno, ideale per il Free Tier.
- Configurazione testata e stabile per uso produttivo. contiene lo script `ControllaEmailCreaEvento.py` che:
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

Variabili opzionali (configurazione ottimale per produzione):
- `GEMINI_MODEL` (default `gemini-1.5-flash`): **RACCOMANDATO** per uso quotidiano - più economico e veloce
- `TIMEZONE` (default `Europe/Rome`)
- `MAX_UNREAD_TO_PROCESS` (default `1`): limita email elaborate per ridurre quota - **TESTATO CON SUCCESSO**
- `PER_EMAIL_SLEEP_SECS` (default `10`): pausa tra email per rispettare rate limits - **CONFIGURAZIONE STABILE**
- `GEMINI_CLI_PATH`: percorso esplicito dell'eseguibile `gemini` se non è nel PATH (utile su Windows)

Log: `automation.log` nella stessa cartella.

## ✅ Test di Successo Completato

**Data ultimo test**: 15 Agosto 2025  
**Email testata**: "Amazon consegna"  
**Risultato**: ✅ Evento calendario creato con successo  
**Configurazione vincente**:
- `GEMINI_MODEL=gemini-1.5-flash` (modello economico)
- `MAX_UNREAD_TO_PROCESS=1` 
- `PER_EMAIL_SLEEP_SECS=10`
- Fallback SDK `google-generativeai` funzionante

**Log di successo**:
```
2025-08-15 00:47:18,834 [INFO] Evento creato: Consegna Amazon (j4tvlu6jbkac6j3o7g9cpiskdo)
2025-08-15 00:47:19,274 [INFO] Email 198a31871c6c96d5 marcata come letta
```

## Esecuzione in GitHub Actions (CI)

Questo repo include un workflow: `.github/workflows/run-agent.yml` che:
- Esegue un precheck dei Secrets e cache di pip,
- Tenta l'installazione della Gemini CLI (best-effort) e imposta il PATH,
- Installa le dipendenze Python,
- Esegue lo script (con jitter di 5s),
- Carica l'artefatto `automation.log` e scrive un Job Summary.

Limitazione elaborazione email:
- Lo script elabora al massimo le 10 email non lette più recenti (configurabile via `MAX_UNREAD_TO_PROCESS`).
- Questo aiuta a rimanere entro i limiti del Free Tier dell’API di Gemini evitando errori 429.

Quote e limiti dell'API Gemini (configurazione ottimizzata):
- Documentazione ufficiale: https://ai.google.dev/gemini-api/docs/rate-limits
- **Configurazione testata**: `GEMINI_MODEL=gemini-1.5-flash` + `PER_EMAIL_SLEEP_SECS=10` 
- **Risultato**: Nessun errore 429, elaborazione fluida e veloce
- **Per uso locale**:
  - ✅ `MAX_UNREAD_TO_PROCESS=1` (testato con successo)
  - ✅ `PER_EMAIL_SLEEP_SECS=10` (previene rate limiting)
  - ✅ `GEMINI_MODEL=gemini-1.5-flash` (più economico e veloce)
- **Nel workflow CI**: stesse impostazioni ottimizzate per stabilità 24/7
- Al primo `429` lo script interrompe il batch automaticamente
- **Importante**: usa API Google AI Studio (non Vertex AI), limiti indipendenti da Google CloudConfigura i Secrets nel repository:
- `GEMINI_API_KEY`: chiave API di Gemini.
- `CLIENT_SECRET_JSON`: contenuto del file client_secret.json (raw JSON o base64).
- `TOKEN_JSON`: contenuto del token.json con refresh_token valido (raw JSON o base64).

Lo script, in CI, scrive `client_secret.json` e `token.json` dai Secrets. In ambiente CI, non viene avviato il browser per OAuth: serve un `TOKEN_JSON` già valido.

Se la CLI Gemini non è presente sul runner, lo script utilizza automaticamente il fallback SDK (`google-generativeai`) per generare la risposta JSON; la dipendenza è inclusa in `requirements.txt`.

### Rigenerare un TOKEN_JSON valido con gli scope corretti

Se vedi in `automation.log` un errore `invalid_scope` o messaggi di token non valido:
- Gli scope richiesti sono:
	- `https://www.googleapis.com/auth/gmail.modify`
	- `https://www.googleapis.com/auth/calendar.events`
- Come rigenerare localmente:
	1. Assicurati che `client_secret.json` sia nella cartella del progetto.
	2. Esegui una volta lo script in locale per attivare il flusso OAuth (si aprirà il browser per consentire gli scope richiesti):
		 ```powershell
		 python .\ControllaEmailCreaEvento.py
		 ```
	3. Al termine, in cartella sarà creato/aggiornato `token.json` con `refresh_token` e gli scope corretti.
	4. Copia il contenuto di `token.json` e incollalo nel Secret di GitHub `TOKEN_JSON` (puoi incollare il JSON puro oppure una versione Base64 del file).
	5. Ri-esegui il workflow.
