import os
import json
import base64
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # Fallback gestito sotto

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup


# Ambiti richiesti: Gmail (modify) e Calendar (events)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
]

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Rome")


def setup_logging() -> None:
    log_path = os.path.join(os.path.dirname(__file__), "automation.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_env() -> None:
    """Carica variabili d'ambiente.
    - In locale: legge .env nella cartella dello script (se presente).
    - In CI: usa direttamente le environment variables fornite come Secrets.
    - Allinea GEMINI_API_KEY/GOOGLE_API_KEY se una sola è presente.
    """
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.isfile(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    # Normalizzazione chiavi API
    env = os.environ
    key_gemini = env.get("GEMINI_API_KEY")
    key_google = env.get("GOOGLE_API_KEY")
    if not key_gemini and key_google:
        env["GEMINI_API_KEY"] = key_google
    if not key_google and key_gemini:
        env["GOOGLE_API_KEY"] = key_gemini


def _decode_maybe_b64(s: str) -> str:
    if not s:
        return s
    s_stripped = s.strip()
    if s_stripped.startswith("{") or s_stripped.startswith("["):
        return s_stripped
    try:
        decoded = base64.b64decode(s_stripped, validate=True)
        try:
            return decoded.decode("utf-8")
        except Exception:
            return decoded.decode("utf-8", errors="replace")
    except Exception:
        return s


def _write_json_file(path: str, content: str) -> None:
    # Valida JSON minimo
    json.loads(content)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp_path, path)


def setup_credentials_from_ci_env() -> bool:
    """Scrive client_secret.json e token.json da variabili d'ambiente (es. GitHub Secrets).
    Restituisce True se ha scritto almeno un file.
    """
    wrote_any = False
    client_secret_raw = os.environ.get("CLIENT_SECRET_JSON") or os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    token_raw = os.environ.get("TOKEN_JSON")
    base_dir = os.path.dirname(__file__)
    client_path = os.path.join(base_dir, "client_secret.json")
    token_path = os.path.join(base_dir, "token.json")
    if client_secret_raw:
        try:
            content = _decode_maybe_b64(client_secret_raw)
            _write_json_file(client_path, content)
            wrote_any = True
        except Exception as e:
            logging.warning("Impossibile scrivere client_secret.json dai Secrets: %s", e)
    if token_raw:
        try:
            content = _decode_maybe_b64(token_raw)
            _write_json_file(token_path, content)
            wrote_any = True
        except Exception as e:
            logging.warning("Impossibile scrivere token.json dai Secrets: %s", e)
    if wrote_any:
        logging.info("Credenziali inizializzate da variabili d'ambiente (CI Secrets).")
    return wrote_any


def get_credentials() -> Credentials:
    token_path = os.path.join(os.path.dirname(__file__), "token.json")
    client_secret_path = os.path.join(os.path.dirname(__file__), "client_secret.json")

    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh o nuovo flusso
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Token scaduto: eseguo refresh…")
            creds.refresh(Request())
        else:
            # Se in CI non possiamo aprire browser: richiedi TOKEN_JSON valido
            running_in_ci = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(
                    f"File client_secret.json non trovato in: {client_secret_path}"
                )
            if running_in_ci:
                raise RuntimeError(
                    "Token OAuth non valido in ambiente CI. Fornire TOKEN_JSON con refresh_token nei Secrets."
                )
            logging.info("Avvio flusso OAuth per ottenere un nuovo token (ambiente locale)…")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Salva token
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def build_services(creds: Credentials):
    gmail = build("gmail", "v1", credentials=creds)
    calendar = build("calendar", "v3", credentials=creds)
    return gmail, calendar


def list_unread_messages(gmail) -> List[Dict]:
    messages: List[Dict] = []
    page_token: Optional[str] = None
    while True:
        resp = (
            gmail.users()
            .messages()
            .list(userId="me", q="is:unread", pageToken=page_token, maxResults=50)
            .execute()
        )
        messages.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return messages


def _decode_b64url(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_text_from_payload(payload: Dict) -> str:
    # Prova a leggere direttamente il body
    body = payload.get("body", {})
    data = body.get("data")
    mime = payload.get("mimeType", "")
    if data:
        raw = _decode_b64url(data)
        if "html" in mime:
            soup = BeautifulSoup(raw, "html.parser")
            return soup.get_text("\n", strip=True)
        return raw

    # Altrimenti naviga le parti
    parts = payload.get("parts", [])
    texts = []
    for part in parts:
        texts.append(_extract_text_from_payload(part))
    return "\n".join([t for t in texts if t])


def get_email_subject_and_body(gmail, msg_id: str) -> Tuple[str, str]:
    msg = gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()

    headers = msg.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers if h.get("name") == "Subject"), "(senza oggetto)")

    text = _extract_text_from_payload(msg.get("payload", {}))
    if not text:
        # fallback: prova snippet
        text = msg.get("snippet", "")
    return subject, text


def _try_parse_json(text: str) -> Optional[Dict]:
    text = text.strip()
    # Prova diretto
    try:
        return json.loads(text)
    except Exception:
        pass

    # Estrazione best-effort del primo blocco JSON
    import re

    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None


def call_gemini_cli(prompt: str, model: str = MODEL) -> Dict:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY non impostata (manca .env o variabile d'ambiente)")

    env = os.environ.copy()
    candidates = [
        ["gemini", "prompt", "-m", model, "--json", prompt],
        ["gemini", "-m", model, "-p", prompt, "--json"],
        ["gemini", "-m", model, "--json"],  # con stdin
        ["gemini", prompt],
    ]

    for cmd in candidates:
        try:
            if cmd == candidates[2]:  # stdin
                res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env)
            else:
                res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            if res.returncode != 0:
                logging.warning("gemini cli ha restituito codice %s. stderr: %s", res.returncode, err)
                continue
            data = _try_parse_json(out)
            if data is not None:
                return data
            # A volte il JSON è su stderr
            data = _try_parse_json(err)
            if data is not None:
                return data
        except FileNotFoundError:
            logging.warning("CLI 'gemini' non trovata: provo fallback SDK google-generativeai…")
            data = call_gemini_sdk(prompt, model)
            if data is not None:
                return data
            raise FileNotFoundError(
                "Comando 'gemini' non trovato e fallback SDK non disponibile. Installa la CLI o la libreria google-generativeai."
            )
        except Exception as e:
            logging.warning("Errore chiamando gemini cli con %s: %s", cmd, e)

    raise ValueError("Impossibile ottenere una risposta JSON valida dalla CLI di Gemini.")


def call_gemini_sdk(prompt: str, model: str = MODEL) -> Optional[Dict]:
    """Fallback: usa google-generativeai se la CLI non è disponibile."""
    try:
        import google.generativeai as genai
    except Exception as e:
        logging.warning("SDK Gemini non disponibile: %s", e)
        return None

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logging.warning("API key Gemini mancante per SDK.")
        return None

    try:
        genai.configure(api_key=api_key)
        mdl = genai.GenerativeModel(model)
        resp = mdl.generate_content(prompt)
        text = getattr(resp, "text", None) or ""
        data = _try_parse_json(text)
        return data
    except Exception as e:
        logging.warning("Errore nel fallback SDK: %s", e)
        return None


def parse_event_decision(data: Dict) -> Tuple[bool, str, Optional[str], Optional[str], str]:
    # Normalizza chiavi/valori
    creare = str(data.get("creare_evento", "no")).strip().lower()
    titolo = str(data.get("titolo", "")).strip() or "Evento"
    data_str = data.get("data")
    ora_inizio = data.get("ora_inizio")
    descrizione = str(data.get("descrizione", "")).strip()

    if data_str:
        data_str = str(data_str).strip()
    if ora_inizio:
        ora_inizio = str(ora_inizio).strip()

    return (
        creare == "si",
        titolo,
        data_str if data_str and data_str.lower() != "null" else None,
        ora_inizio if ora_inizio and ora_inizio.lower() != "null" else None,
        descrizione,
    )


def _normalize_date(date_str: str) -> str:
    """Accetta 'YYYY-MM-DD' o 'DD-MM-YYYY' (anche con '/') e restituisce 'YYYY-MM-DD'."""
    date_str = date_str.strip()
    # Sostituisci / con -
    date_str = date_str.replace("/", "-")
    # Prova ISO
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        pass
    # Prova DD-MM-YYYY
    try:
        d = datetime.strptime(date_str, "%d-%m-%Y").date()
        return d.isoformat()
    except ValueError:
        pass
    raise ValueError(f"Formato data non riconosciuto: {date_str}")


def _ensure_timezone() -> str:
    # Se zoneinfo non disponibile o tz non valida, torna Europe/Rome
    tz = TIMEZONE or "Europe/Rome"
    if ZoneInfo is None:
        return tz
    try:
        ZoneInfo(tz)
        return tz
    except Exception:
        return "Europe/Rome"


def create_calendar_event(calendar, title: str, date_str: str, time_str: Optional[str], description: str = "") -> Dict:
    tz = _ensure_timezone()

    # Normalizza data in formato YYYY-MM-DD
    date_str = _normalize_date(date_str)

    if time_str:
        # Evento con orario: durata default 1h
        try:
            start_dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            # Ritenta con H:M senza zeri
            try:
                start_dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except Exception:
                raise ValueError(f"Formato data/ora non valido: {date_str} {time_str}")
        if ZoneInfo is not None:
            start_dt = start_dt_naive.replace(tzinfo=ZoneInfo(tz))
        else:
            start_dt = start_dt_naive  # Senza tzinfo: Calendar userà tz passato
        end_dt = start_dt + timedelta(hours=1)

        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
        }
    else:
        # Evento giornata intera: end esclusivo (giorno successivo)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        next_day = d + timedelta(days=1)

        event_body = {
            "summary": title,
            "description": description,
            "start": {"date": d.isoformat(), "timeZone": tz},
            "end": {"date": next_day.isoformat(), "timeZone": tz},
        }

    created = calendar.events().insert(calendarId="primary", body=event_body).execute()
    return created


def mark_email_as_read(gmail, msg_id: str) -> None:
    gmail.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def build_prompt(email_text: str, email_subject: Optional[str] = None) -> str:
    subject_block = f"Oggetto: {email_subject}\n" if email_subject else ""
    return f"""
Sei un assistente che analizza email in italiano per capire se contengono un evento, appuntamento o scadenza da aggiungere al calendario.

Istruzioni e vincoli:
- Luogo/Fuso orario: Italia. Usa sempre il fuso Europe/Rome (CET/CEST) e considera l'ora legale alla data indicata.
- Se la mail contiene solo una data (senza orario), crea un evento di GIORNATA INTERA per quella data.
- Se è presente anche un orario, crea un evento con orario (l'inizio coincide con l'orario indicato). Se l'orario non specifica fuso, interpretalo come orario italiano. Se è indicato un fuso diverso, converti all'ora italiana per la data specifica.
- Riconosci anche espressioni relative: "oggi", "domani", "dopodomani", "questo venerdì", "la prossima settimana", ecc. Calcola la data assoluta rispetto a oggi in Italia.
- Ignora firme, disclaimer e contenuti non rilevanti. Se ci sono più date, scegli quella più plausibile per l'azione richiesta.
- Restituisci SOLO un oggetto JSON, nessun testo aggiuntivo, nessun commento, nessun backtick.

Formato della risposta JSON (campi obbligatori):
- "creare_evento": "si" o "no".
- "titolo": titolo breve e descrittivo.
- "descrizione": breve descrizione dell'evento (max 200 caratteri); stringa vuota se non disponibile.
- "data": data in formato GG-MM-AAAA; "null" se non determinabile.
- "ora_inizio": orario 24h HH:MM in ora italiana; "null" se evento di giornata intera.

Contenuto da analizzare:
{subject_block}
Testo:
---
{email_text}
---
""".strip()


def process_email(gmail, calendar, msg_id: str) -> None:
    subject, body = get_email_subject_and_body(gmail, msg_id)
    if not body:
        logging.info("Email %s senza corpo: salto", msg_id)
        return

    prompt = build_prompt(body, subject)

    logging.info("Invio email %s a Gemini per analisi…", msg_id)
    result = call_gemini_cli(prompt)
    creare, titolo, data_str, ora_inizio, descrizione = parse_event_decision(result)

    if not creare:
        logging.info("Gemini: nessun evento da creare per email %s", msg_id)
        return
    if not data_str:
        logging.info("Gemini ha deciso di creare evento ma senza data: salto email %s", msg_id)
        return

    # Descrizione: usa quella generata da Gemini, altrimenti fallback con oggetto
    description = descrizione or f"Generato automaticamente da email con oggetto: {subject}"

    created = create_calendar_event(calendar, titolo, data_str, ora_inizio, description)
    event_id = created.get("id")
    logging.info("Evento creato: %s (%s)", titolo, event_id)

    # Solo dopo la creazione, marca come letta
    mark_email_as_read(gmail, msg_id)
    logging.info("Email %s marcata come letta", msg_id)


def main() -> None:
    setup_logging()
    load_env()
    # Scrive i file credenziali da Secrets (se presenti, tipicamente in CI)
    setup_credentials_from_ci_env()

    # Pre-check chiave Gemini
    if not os.getenv("GEMINI_API_KEY"):
        logging.error("Variabile GEMINI_API_KEY mancante. Inserirla in .env o nell'ambiente.")
        return

    try:
        creds = get_credentials()
    except Exception as e:
        logging.exception("Errore durante autenticazione Google: %s", e)
        return

    gmail, calendar = build_services(creds)

    try:
        messages = list_unread_messages(gmail)
    except Exception as e:
        logging.exception("Errore leggendo le email: %s", e)
        return

    if not messages:
        logging.info("Nessuna email non letta: nulla da fare.")
        return

    logging.info("%d email non lette da elaborare…", len(messages))
    for m in messages:
        msg_id = m.get("id")
        if not msg_id:
            continue
        try:
            process_email(gmail, calendar, msg_id)
        except Exception as e:
            logging.exception("Errore elaborando email %s: %s", msg_id, e)
            # Non marcata come letta in caso di errore


if __name__ == "__main__":
    main()
