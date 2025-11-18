# Automazione Gmail -> Gemini -> Google Calendar

Questo progetto contiene lo script `ControllaEmailCreaEvento.py` che:
- Legge le email non lette da Gmail
- Invia il testo all'API Gemini per decidere se creare un evento
- Crea l'evento su Google Calendar e marca l'email come letta
- Funziona sia localmente che tramite GitHub Actions (10 esecuzioni/giorno)

## � Requisiti di Sistema

- **Python**: 3.9+ (testato con Python 3.11)
- **Sistema Operativo**: Windows, macOS, Linux
- **Accesso Internet**: Per connessioni API Google e Gemini
- **Browser**: Per autorizzazione OAuth (solo prima configurazione locale)

## �🔧 Configurazione Completa delle API Google

### Passaggio 1: Creare un Progetto Google Cloud

1. **Vai alla Google Cloud Console**: https://console.cloud.google.com/
2. **Crea un nuovo progetto**:
   - Clicca su "Seleziona progetto" in alto
   - Clicca "NUOVO PROGETTO" 
   - Nome progetto: `Gmail-Calendar-Automation` (o a tua scelta)
   - Clicca "CREA"
3. **Seleziona il progetto appena creato** dalla dropdown

### Passaggio 2: Abilitare le API Necessarie

1. **Gmail API**:
   - Vai a: https://console.cloud.google.com/apis/library/gmail.googleapis.com
   - Clicca "ABILITA"
   - Attendi che si attivi (indicatore verde)

2. **Google Calendar API**:
   - Vai a: https://console.cloud.google.com/apis/library/calendar.googleapis.com
   - Clicca "ABILITA" 
   - Attendi che si attivi (indicatore verde)

3. **Generative AI API** (per Gemini):
   - Vai a: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
   - **IMPORTANTE**: Se l'URL sopra non funziona, cerca "Generative Language API" nella libreria API
   - In alternativa, vai direttamente alla libreria API: https://console.cloud.google.com/apis/library
   - Cerca "Generative Language" o "AI Platform" 
   - Clicca "ABILITA"
   - Attendi che si attivi (indicatore verde)
   - **Importante**: Questa API è necessaria per far funzionare le richieste a Gemini

### Passaggio 3: Configurare OAuth 2.0 Client ID

1. **Vai alla schermata di consenso OAuth**:
   - URL: https://console.cloud.google.com/apis/credentials/consent
   - Scegli "Esterno" se non hai G Suite
   - Clicca "CREA"

2. **Compila la schermata di consenso**:
   - **Nome dell'app**: `Gmail Calendar Automation`
   - **Email di supporto utenti**: La tua email
   - **Domini autorizzati**: Lascia vuoto per testing
   - **Email di contatto sviluppatore**: La tua email
   - Clicca "SALVA E CONTINUA"

3. **Aggiungi gli scope necessari**:
   - Clicca "AGGIUNGI O RIMUOVI SCOPE"
   - Cerca e aggiungi:
     - `https://www.googleapis.com/auth/gmail.modify`
     - `https://www.googleapis.com/auth/calendar.events`
   - Clicca "AGGIORNA" poi "SALVA E CONTINUA"

4. **Aggiungi utenti di test** (se app in testing):
   - Clicca "AGGIUNGI UTENTI"
   - Inserisci la tua email Gmail
   - Clicca "AGGIUNGI" poi "SALVA E CONTINUA"

### Passaggio 4: Creare le Credenziali OAuth 2.0

1. **Vai alla sezione Credenziali**:
   - URL: https://console.cloud.google.com/apis/credentials
   - Clicca "CREA CREDENZIALI" → "ID client OAuth 2.0"

2. **Configura il client OAuth**:
   - **Tipo di applicazione**: "App desktop"
   - **Nome**: `Gmail Calendar Desktop Client`
   - Clicca "CREA"

3. **Scarica il file JSON**:
   - Apparirà un popup con le credenziali
   - Clicca "SCARICA JSON"
   - **IMPORTANTE**: Rinomina il file scaricato in `client_secret.json`
   - Copia il file nella cartella del progetto

### Passaggio 5: Ottenere l'API Key di Gemini

1. **Vai a Google AI Studio**:
   - URL: https://aistudio.google.com/
   - Accedi con il tuo account Google

2. **Crea una API Key**:
   - Clicca su "Get API key" o "Ottieni chiave API"
   - Clicca "Create API key"
   - **Seleziona il progetto Google Cloud che hai creato** (dove hai abilitato l'API Generative AI)
   - Copia la chiave API generata
   - **Nota**: La chiave funzionerà solo se hai abilitato l'API Generative AI nel progetto

3. **Configura la variabile d'ambiente**:
   - Crea un file `.env` nella cartella del progetto:
   ```env
   GEMINI_API_KEY=la_tua_chiave_api_qui
   MAX_UNREAD_TO_PROCESS=5
   PER_EMAIL_SLEEP_SECS=10
   GEMINI_MODEL=gemini-2.5-pro
   ```

### Passaggio 6: Generare il token.json (Prima Esecuzione)

1. **Assicurati di avere**:
   - `client_secret.json` nella cartella del progetto
   - `.env` configurato con `GEMINI_API_KEY`
   - Dipendenze installate: `pip install -r requirements.txt`

2. **Esegui lo script per la prima volta**:
   ```powershell
   python ControllaEmailCreaEvento.py
   ```

3. **Autorizza l'applicazione**:
   - Si aprirà automaticamente il browser
   - Accedi con l'account Gmail che vuoi monitorare
   - Clicca "Avanzate" se appare un warning di sicurezza
   - Clicca "Vai a Gmail Calendar Automation (non sicuro)"
   - Autorizza l'accesso a Gmail e Calendar
   - Torna al terminale

4. **Verifica la creazione di token.json**:
   - Il file `token.json` sarà creato automaticamente
   - Contiene il refresh token per le future esecuzioni
   - **NON condividere questo file** (è in .gitignore)

### Passaggio 7: Test di Funzionamento

1. **Invia un'email di test** al tuo account Gmail con contenuto tipo:
   ```
   Oggetto: Appuntamento dentista
   
   Ciao,
   ho l'appuntamento dal dentista domani alle 15:30.
   Cordiali saluti
   ```

2. **Esegui lo script**:
   ```powershell
   python ControllaEmailCreaEvento.py
   ```

3. **Verifica i risultati**:
   - Controlla i log per confermare l'elaborazione
   - Verifica che l'evento sia stato creato in Google Calendar
   - Controlla che l'email sia stata marcata come letta

## 🚀 Installazione e Avvio

**Installazione dipendenze**:
```powershell
pip install -r requirements.txt
```

**Esecuzione manuale**:
```powershell
python ControllaEmailCreaEvento.py
```

**Configurazione ottimale** (file `.env`):
```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-pro
MAX_UNREAD_TO_PROCESS=5
PER_EMAIL_SLEEP_SECS=10
TIMEZONE=Europe/Rome
```

## 🔄 Automazione GitHub Actions

### Configurazione Secrets del Repository

Per far funzionare l'automazione su GitHub Actions, configura questi Secrets nel repository:

1. **Vai alle impostazioni del repository**: `Settings` → `Secrets and variables` → `Actions`

2. **Aggiungi i seguenti Secrets**:

   - **`GEMINI_API_KEY`**: La tua chiave API di Gemini
   
   - **`CLIENT_SECRET_JSON`**: Il contenuto completo del file `client_secret.json`
     ```json
     {
       "installed": {
         "client_id": "123456789.apps.googleusercontent.com",
         "client_secret": "GOCSPX-abcdefghijklmnop",
         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
         "token_uri": "https://oauth2.googleapis.com/token",
         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
         "redirect_uris": ["http://localhost"]
       }
     }
     ```
     **⚠️ NOTA**: I valori sopra sono ESEMPI FITTIZI - usa i tuoi dati reali
     
   - **`TOKEN_JSON`**: Il contenuto completo del file `token.json` (dopo prima autorizzazione locale)
     ```json
     {
       "token": "ya29.a0AX9GBdS...",
       "refresh_token": "1//0GWjp...",
       "token_uri": "https://oauth2.googleapis.com/token",
       "client_id": "123456789.apps.googleusercontent.com",
       "client_secret": "GOCSPX-abcdefghijklmnop",
       "scopes": [
         "https://www.googleapis.com/auth/gmail.modify",
         "https://www.googleapis.com/auth/calendar.events"
       ]
     }
     ```
     **⚠️ NOTA**: I valori sopra sono ESEMPI FITTIZI - usa i tuoi dati reali

### Schedule Automatico

Il workflow è configurato per eseguire l'automazione **10 volte al giorno**:

- **00:00** (01:00 Italia) - Mezzanotte
- **02:00** (03:00 Italia) - Notte  
- **05:00** (06:00 Italia) - Alba
- **07:00** (08:00 Italia) - Mattina
- **09:00** (10:00 Italia) - Metà mattina
- **12:00** (13:00 Italia) - Pranzo
- **14:00** (15:00 Italia) - Pomeriggio
- **16:00** (17:00 Italia) - Tardo pomeriggio
- **19:00** (20:00 Italia) - Sera
- **22:00** (23:00 Italia) - Notte

**Capacità**: 5 email per esecuzione × 10 esecuzioni = **max 50 email processate/giorno**

## ⚠️ Risoluzione Problemi Comuni

### Errore "invalid_scope"
- **Causa**: Gli scope in token.json non corrispondono a quelli richiesti
- **Soluzione**: Elimina `token.json` e riesegui lo script per riautorizzare

### Errore "invalid_client"
- **Causa**: Il file `client_secret.json` non è valido o mancante  
- **Soluzione**: Riscaricare le credenziali OAuth dalla Google Cloud Console

### Errore 429 "Quota exceeded"
- **Causa**: Troppe richieste a Gemini in poco tempo
- **Soluzione**: Aumenta `PER_EMAIL_SLEEP_SECS` nel file `.env`

### Errore "API key not valid" o "permission denied" per Gemini
- **Causa**: API Generative AI non abilitata nel progetto Google Cloud
- **Soluzione**: 
  1. Vai a: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
  2. Seleziona il progetto corretto
  3. Clicca "ABILITA" 
  4. Ricrea l'API key in AI Studio se necessario

### Browser non si apre per OAuth
- **Causa**: Ambiente headless o problemi di permessi
- **Soluzione**: Copia l'URL dal terminale e aprilo manualmente

### GitHub Actions fallisce
- **Causa**: Secrets mancanti o token.json scaduto
- **Soluzione**: Verifica tutti i Secrets e rigenera `token.json` localmente

### Script si blocca senza errori
- **Causa**: Credenziali scadute o problemi di rete
- **Soluzione**: Controlla `automation.log` per dettagli, rigenera token se necessario

## ✅ Test di Successo Completato

**Data ultimo test**: 15 Agosto 2025  
**Email testata**: "Amazon consegna"  
**Risultato**: ✅ Evento calendario creato con successo  

**Configurazione vincente**:
- `GEMINI_MODEL=gemini-2.5-pro` (modello top, fallback automatico a gemini-2.5-flash se non disponibile)
- `MAX_UNREAD_TO_PROCESS=5` 
- `PER_EMAIL_SLEEP_SECS=10`
- SDK `google-generativeai` (nessuna CLI necessaria)

**Log di successo**:
```
2025-08-15 00:47:16,441 [INFO] Invio email a Gemini per analisi…
2025-08-15 00:47:18,834 [INFO] Evento creato: Consegna Amazon (j4tvlu6jbkac6j3o7g9cpiskdo)
2025-08-15 00:47:19,274 [INFO] Email 198a31871c6c96d5 marcata come letta
```

**Miglioramenti architetturali**:
- ✅ **SDK diretto**: Rimossa dipendenza CLI Gemini (mai funzionante)
- ✅ **Avvio più veloce**: Eliminata ricerca PATH inutile
- ✅ **Log più puliti**: Nessun warning CLI
- ✅ **Codice semplificato**: Unico path di esecuzione stabile

## 📊 Quote e Limiti API

**Gemini API (Free Tier)**:
- Documentazione: https://ai.google.dev/gemini-api/docs/rate-limits
- **Configurazione testata**: `gemini-2.5-pro` + `PER_EMAIL_SLEEP_SECS=10` (fallback automatico a gemini-2.5-flash)
- **Risultato**: Nessun errore 429, elaborazione fluida
- **Capacità giornaliera**: 50 email con pause → ben sotto i limiti gratuiti

**Gmail API**:
- Limite: 1.000.000 quota units/giorno (Free)
- **Utilizzo**: ~50 email × 5 units = 250 units/giorno (0.025% del limite)

**Calendar API**:
- Limite: 1.000.000 richieste/giorno (Free)  
- **Utilizzo**: ~10-20 eventi creati/giorno (0.002% del limite)

## 📝 File di Log

Tutti i log vengono salvati in `automation.log` nella stessa cartella dello script. In GitHub Actions, il file viene caricato come artefatto scaricabile.

## 🔒 Sicurezza e Privacy

### Dati Trattati
- **Email**: Vengono lette solo email non lette, mai modificate o inoltrate
- **Calendar**: Vengono creati solo nuovi eventi, mai modificati eventi esistenti  
- **Gemini**: Riceve solo il testo dell'email per analisi, nessun dato personale aggiuntivo

### File Sensibili (Mai Committati)
- `.env` - Contiene API keys
- `client_secret.json` - Credenziali OAuth Google
- `token.json` - Token di accesso e refresh
- `automation.log` - Potrebbe contenere oggetti email

### Sicurezza GitHub Actions
- Tutti i secrets sono crittografati in GitHub
- Le variabili d'ambiente vengono cancellate dopo ogni esecuzione
- Nessun dato sensibile viene salvato nei log pubblici
