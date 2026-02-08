# 9 Freunde – Eltern- und Verwaltungsapp

Die **9 Freunde App** ist eine Streamlit-Webanwendung für die Großtagespflege *"9 Freunde"*. Sie unterstützt die Leitung bei organisatorischen Aufgaben und bietet Eltern einen geschützten Zugang zu Informationen rund um ihre Kinder. Kernfunktionen der App sind:
- **Getrennter Login für Eltern und Leitung:** Sichere Anmeldung mit unterschiedlichen Berechtigungen (Eltern sehen nur eigene Kind-Daten, Leitung hat vollen Verwaltungszugriff).
- **Stammdatenverwaltung:** Pflege der Kinder- und Eltern-Stammdaten durch die Leitung innerhalb der App.
- **Dokumenterstellung via KI:** Automatisches Generieren von Berichten/Briefen mit OpenAI sowie Download oder Ablage dieser Dokumente.
- **Kalenderintegration:** Verwaltung wichtiger Termine über Google Calendar (inkl. Anzeige für Eltern).
- **Fotoverwaltung:** DSGVO-konformer Upload von Fotos auf Google Drive mit automatischer Gesichtserkennung, sodass Eltern nur relevante Fotos sehen.

Die App ist mobilfähig (Responsive Webdesign über Streamlit) und alle sensiblen Daten bleiben geschützt (keine öffentlichen Links, beschränkter Zugriff per Authentifizierung). 

## Installation und Voraussetzungen

Es gibt **zwei Installationsmodi**:

### 1) Core-Installation (Cloud/Deployment-sicher)
Für Streamlit Cloud und andere ressourcenbegrenzte Umgebungen:

```bash
pip install -r requirements.txt
```

Enthalten sind nur die Kernabhängigkeiten:
- Streamlit
- Firebase Admin SDK
- OpenAI SDK
- Google API Client
- Dokument-Bibliotheken (`python-docx`, `PyPDF2`)
- Pillow

### 2) CV-Installation (lokal / Full Environment)
Für lokale Setups mit optionaler Gesichtserkennung:

```bash
pip install -r requirements.txt
pip install -r requirements-cv.txt
```

`requirements-cv.txt` enthält die optionalen Computer-Vision-Pakete (u. a. `face-recognition` und kompatibles `dlib`).

### Allgemeine Voraussetzungen

1. **Python installieren:** Stellen Sie sicher, dass Python 3.11+ installiert ist.
2. **Code beschaffen:** Klonen oder laden Sie das Repository mit dem App-Code.
3. **Virtuelle Umgebung:** Nutzen Sie idealerweise ein venv (`python -m venv .venv`).
4. **Streamlit testen:** `streamlit hello` ausführen, um die lokale Laufzeit zu prüfen.

### Deployment-Hinweis für Streamlit Cloud (dlib/face_recognition)

Für Debian-basierte Build-Umgebungen liegt im Repo eine `packages.txt` mit minimalen nativen Build-Abhängigkeiten für `dlib`:

- `cmake`
- `build-essential`
- `libopenblas-dev`
- `liblapack-dev`
- `libjpeg-dev`
- `zlib1g-dev`
- `libpng-dev`

Wichtig:
- Die Kern-App bleibt ohne CV-Abhängigkeiten lauffähig (Gesichtserkennung ist optional).
- Wenn Builds in der Cloud wegen Zeit-/RAM-Limits instabil sind, installieren Sie **nur** `requirements.txt`.
- In diesem Fall zeigt die App einen Hinweis an und deaktiviert automatisch die Gesichtserkennung.


## Prototyp-Modus (lokale Speicherung, einfache Konfiguration)

Für frühe Prototypen kann die App jetzt **ohne Google/Firebase** betrieben werden.
Standardmäßig läuft sie im lokalen Modus (`storage.mode = "local"`) und speichert Daten unter `./data/`:

- `data/children.json` für Stammdaten
- `data/calendar_events.json` für Termine
- `data/drive/` für Dokumente und Fotos

Minimales `secrets.toml` für den Prototypen:

```toml
[storage]
mode = "local"

[local]
data_dir = "./data"

[auth]
admin_emails = ["leitung@example.org"]

[auth.users]
leitung@example.org = "demo123"
eltern@example.org = "demo123"
```

Optional können Sie später wieder auf Google umstellen:

```toml
[storage]
mode = "google"
```

Dann werden die bereits dokumentierten `gcp_service_account`- und `gcp`-Einträge wieder verpflichtend.

## Konfiguration der APIs und Dienste

Im Google-Modus müssen vor dem Start der App externe Dienste (Google APIs, OpenAI, Firebase) eingerichtet und Zugangsdaten hinterlegt werden. Im lokalen Prototyp-Modus sind Google/Firebase nicht erforderlich. Diese sensiblen Informationen gehören **nicht** in den Code, sondern in die Konfiguration (z. B. `.streamlit/secrets.toml`).

### Google Client Factory (Service Account)
Die Datei `services/google_clients.py` stellt gecachte Factory-Funktionen für Google-Clients bereit: `get_drive_client()`, `get_sheets_client()` und optional `get_calendar_client()`. Alle Clients werden mit `Credentials.from_service_account_info(st.secrets["gcp_service_account"])` erzeugt und via `@st.cache_resource` über Streamlit-Reruns hinweg wiederverwendet.

### Google Cloud / Dienstkonten (Drive & Calendar)
Die App nutzt Google Drive und Google Calendar über die Google API. Gehen Sie wie folgt vor:
1. **Google Cloud Projekt:** Erstellen Sie ein Google Cloud Projekt in der Google Cloud Console (oder verwenden Sie ein vorhandenes für die Einrichtung der APIs).
2. **APIs aktivieren:** Aktivieren Sie innerhalb dieses Projekts die **Google Drive API** und die **Google Calendar API**:contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}.
3. **Service Account anlegen:** Erstellen Sie im Cloud-Projekt einen **Service-Account** (Dienstkonto):contentReference[oaicite:2]{index=2}, der Zugriff auf Drive und Calendar erhalten soll. Laden Sie die **JSON-Schlüsseldatei** für dieses Dienstkonto herunter:contentReference[oaicite:3]{index=3}.
4. **Zugriff auf Drive gewähren:** Legen Sie in Ihrem persönlichen Google Drive einen Ordner für die App-Daten an (z. B. *"9FreundeApp"*). Teilen Sie diesen Ordner mit der E-Mail-Adresse des Service-Accounts und geben Sie ihm Bearbeitungsrechte:contentReference[oaicite:4]{index=4}:contentReference[oaicite:5]{index=5}. Notieren Sie sich die Drive-IDs:
   - **Hauptordner-ID:** Die ID des geteilten Ordners (aus der URL ersichtlich).
   - **Kalender-ID:** Erstellen Sie einen neuen Google Kalender für die Einrichtung (oder nutzen Sie einen vorhandenen). Teilen Sie diesen Kalender mit dem Service-Account (Lesen/Schreiben) **oder** notieren Sie die Kalender-ID, falls Sie Domain-Berechtigungen nutzen. Alternativ kann auch das Primary-Kalender-ID des Service-Accounts genutzt werden, sofern Domain-weite Delegierung konfiguriert ist.
5. **Service-Account Credentials einbinden:** Die heruntergeladene JSON-Datei enthält sensible Schlüssel. Diese können auf zwei Arten eingebunden werden:
   - **Lokal (Entwicklung):** Speichern Sie die JSON-Datei z. B. als `service_account.json` im Projekt (nicht einchecken in Git!). Legen Sie im `.streamlit/secrets.toml` eine Referenz oder die Inhalte ab.
   - **Streamlit Cloud:** Kopieren Sie den Inhalt der JSON in `.streamlit/secrets.toml` unter einem Eintrag `[gcp_service_account]`. Achten Sie darauf, multiline-Werte (insb. `private_key`) korrekt im TOML zu escapen (Zeilenumbrüche als `\\n` oder `"""` Syntax nutzen).
6. **Konfigurationswerte:** Hinterlegen Sie im Secrets-File außerdem:
   - `drive_photos_root_folder_id`: die ID des Drive-Hauptordners für Fotos.
   - `drive_contracts_folder_id`: die ID des Drive-Ordners für Verträge/Dokumente.
   - `stammdaten_sheet_id`: die ID des Google Sheets für Stammdaten.
   - `calendar_id` (optional): die Kalender-ID für den Google Kalender der Einrichtung.

### API-Inventur (Stand: aktuell im Code)

| API | Status | Nachweis im Code |
|---|---|---|
| Google Drive API (`drive.googleapis.com`) | **aktiv genutzt** | `storage.py`, `services/drive_service.py`, `app.py` |
| Google Calendar API (`calendar-json.googleapis.com`) | **aktiv genutzt** | `calendar_agent.py`, `app.py` |
| Firestore API (`firestore.googleapis.com`) | **aktiv genutzt** | `stammdaten.py`, `storage.py`, `scripts/check_firestore_prerequisites.py` |
| Google Sheets API (`sheets.googleapis.com`) | **optional/vorbereitet** | `services/google_clients.py` (`get_sheets_client`) |
| Google Docs API (`docs.googleapis.com`) | **aktuell ungenutzt** | keine aktive Referenz |
| Google Forms API (`forms.googleapis.com`) | **aktuell ungenutzt** | keine aktive Referenz |
| Google Tasks API (`tasks.googleapis.com`) | **aktuell ungenutzt** | keine aktive Referenz |

#### Ungenutzte APIs in GCP deaktivieren

Wenn kein kurzfristiger Bedarf besteht, deaktivieren Sie ungenutzte APIs projektweit:

```bash
gcloud services disable docs.googleapis.com --project "<PROJECT_ID>"
gcloud services disable forms.googleapis.com --project "<PROJECT_ID>"
gcloud services disable tasks.googleapis.com --project "<PROJECT_ID>"
```

Vorher/Nachher prüfen:

```bash
gcloud services list --enabled --project "<PROJECT_ID>" \
  --filter="name:(drive.googleapis.com OR calendar-json.googleapis.com OR firestore.googleapis.com OR sheets.googleapis.com OR docs.googleapis.com OR forms.googleapis.com OR tasks.googleapis.com)"
```

#### Optional vorbereitete APIs: Minimal-Healthchecks & Konfiguration

Wenn Sheets/Docs/Forms/Tasks bald genutzt werden sollen, kann ein minimaler Read-Healthcheck ausgeführt werden:

```bash
python scripts/check_google_api_inventory.py --secrets .streamlit/secrets.toml --run-optional-healthchecks
```

Erforderliche optionale Konfiguration in `.streamlit/secrets.toml`:

```toml
[gcp_optional_apis]
sheets_spreadsheet_id = "<SPREADSHEET_ID>"
docs_document_id = "<DOCUMENT_ID>"
forms_form_id = "<FORM_ID>"
```

Hinweise:
- Für Tasks ist kein Ressourcen-ID-Feld erforderlich; es wird ein minimaler `tasklists.list`-Read ausgeführt.
- Fehlende optionale IDs werden als `SKIP`/`WARN` protokolliert und blockieren den App-Start nicht.


#### Setup-Checkliste (Drive & Calendar Freigaben)
Nutzen Sie diese Checkliste exakt vor dem ersten App-Start:

1. **Service-Account-E-Mail kopieren**  
   Öffnen Sie in GCP den Service-Account und kopieren Sie `client_email` aus der JSON (`...@...iam.gserviceaccount.com`).
2. **Ziel-Drive-Ordner freigeben (Editor)**  
   In Google Drive den Zielordner öffnen → **Freigeben** → Service-Account-E-Mail eintragen → Rolle **Editor** (`Bearbeiter`) setzen → speichern.
3. **Ordner-ID übernehmen**  
   Die Ordner-ID aus der Drive-URL in `gcp.drive_photos_root_folder_id` eintragen.
4. **Kalender mit Service-Account teilen**  
   In Google Kalender den Einrichtungs-Kalender öffnen → **Einstellungen und Freigabe** → **Für bestimmte Personen freigeben** → Service-Account-E-Mail hinzufügen → Berechtigung mindestens **Änderungen an Terminen vornehmen** (`Make changes to events`) setzen.
5. **Kalender-ID übernehmen**  
   In den Kalender-Einstellungen die **Kalender-ID** kopieren und in `gcp.calendar_id` hinterlegen.
6. **Kurztest im Google UI**  
   Prüfen, dass der Service-Account in beiden Freigabelisten sichtbar ist (Drive-Ordner + Kalender).

#### Optionaler Laufzeit-Healthcheck in der App
Als Admin steht in der Sidebar der Button **„Google-Verbindung prüfen / Check Google connection“** zur Verfügung. Der Check führt zwei Testaufrufe aus:

- **Drive-Test:** Ein kleiner List-Aufruf gegen die Drive API.
- **Calendar-Test:** Ein Leseaufruf auf Events des konfigurierten `calendar_id`.

Die App zeigt verständliche Fehlermeldungen (DE/EN) mit konkreten Hinweisen, falls Freigaben fehlen (z. B. kein Editor-Zugriff auf den Zielordner oder Kalender nicht mit Service-Account geteilt).

### OpenAI API (Textgenerierung)
Für die KI-gestützte Textgenerierung benötigen Sie einen OpenAI API-Schlüssel:
1. Legen Sie einen Account bei OpenAI an und erzeugen Sie einen persönlichen API Key im Dashboard.
2. Tragen Sie diesen Key in die Konfiguration ein (oder setzen Sie `OPENAI_API_KEY` als Umgebungsvariable).

Die Dokumentenerstellung nutzt die **OpenAI Responses API** mit strukturiertem JSON-Output und optionalen Tools (`file_search`, `web_search_preview`).

- Standardmodell (schnell/günstig): `gpt-4o-mini`
- Präzisionsmodus: `o3-mini` (für genauere Ergebnisse)
- Optionaler EU-Endpunkt: `https://eu.api.openai.com/v1`
- Timeouts + automatische Wiederholversuche mit exponentiellem Backoff sind integriert.

### Firestore prerequisites

Für Stammdaten wird Firestore über `firebase-admin` angesprochen. Vor dem ersten produktiven Einsatz müssen diese Punkte erfüllt sein:

1. **Firestore ist im Native Mode aktiviert**

   ```bash
   gcloud firestore databases describe \
     --project "<PROJECT_ID>" \
     --database="(default)" \
     --format="value(type)"
   ```

   Erwartete Ausgabe: `FIRESTORE_NATIVE`

2. **Service Account hat Least-Privilege-Rolle für Firestore**

   Minimal erforderlich ist eine Firestore-User-Rolle (`roles/firestore.user`) oder die kompatible Datastore-User-Rolle (`roles/datastore.user`).

   Rollen prüfen:

   ```bash
   gcloud projects get-iam-policy "<PROJECT_ID>" \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
     --format="value(bindings.role)"
   ```

   Rolle zuweisen (Beispiel mit `roles/datastore.user`):

   ```bash
   gcloud projects add-iam-policy-binding "<PROJECT_ID>" \
     --member="serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
     --role="roles/datastore.user"
   ```

3. **`init_firebase()` nutzt dasselbe `gcp_service_account` aus `secrets.toml`**

   Automatischer Check (führt alle drei Firestore-Checks aus):

   ```bash
   python scripts/check_firestore_prerequisites.py --secrets .streamlit/secrets.toml
   ```

   Der Check verifiziert explizit:
   - Firestore-Datenbanktyp (`FIRESTORE_NATIVE`)
   - IAM-Rollen des Service Accounts
   - dass `storage.init_firebase()` mit demselben `client_email` initialisiert wurde wie in `gcp_service_account`

#### Typische Fehlermeldungen (Firestore) und Lösung

- **`google.api_core.exceptions.FailedPrecondition: The Cloud Firestore API is not available for Firestore in Datastore Mode`**  
  Firestore ist nicht im Native Mode. Datenbank in Native Mode anlegen oder bestehendes Projekt korrekt migrieren.

- **`google.api_core.exceptions.PermissionDenied: 403 Missing or insufficient permissions`**  
  Service Account hat keine passende IAM-Rolle. Mindestens `roles/datastore.user` oder `roles/firestore.user` zuweisen.

- **`ValueError: [gcp_service_account] fehlt in secrets.toml`** (aus dem Setup-Skript)  
  Abschnitt `[gcp_service_account]` in `.streamlit/secrets.toml` ergänzen und vollständige JSON-Felder übernehmen.

- **`[FAIL] init_firebase() nutzt ein anderes Service Account Credential`** (aus dem Setup-Skript)  
  Prüfen, ob in allen Umgebungen (lokal/Cloud) dieselben Secrets geladen werden und keine impliziten Default Credentials aktiv sind.

### Beispiel für das finale `secrets.toml`
Die App validiert beim Start zentral folgende Pflichtstruktur:

```toml
[gcp_service_account]
type = "service_account"
project_id = "my-project-id"
private_key_id = "abc123..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "service-account@my-project-id.iam.gserviceaccount.com"
client_id = "123456789012345678901"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40my-project-id.iam.gserviceaccount.com"
universe_domain = "googleapis.com"

[gcp]
calendar_id = "kita-kalender@group.calendar.google.com"
drive_photos_root_folder_id = "1AbCdEfGhIjKlMnOpQrStUvWxYz"
drive_contracts_folder_id = "1ZaYxWvUtSrQpOnMlKjIhGfEdCb"
stammdaten_sheet_id = "1SheetIdForStammdaten"

[gcp_optional_apis]
sheets_spreadsheet_id = "<optional>"
docs_document_id = "<optional>"
forms_form_id = "<optional>"

[app]
admin_emails = ["leitung@example.org"]  # optional, alternativ [auth].admin_emails

[auth]
admin_emails = ["leitung@example.org"]  # optional, alternativ [app].admin_emails

[openai]
api_key = "sk-XXXX...IhrOpenAIKey...XXXX"
model_fast = "gpt-4o-mini"
model_precise = "o3-mini"
precision_mode = "fast"            # fast | precise
reasoning_effort = "medium"        # low | medium | high
timeout_seconds = 30
max_retries = 3
base_url = "https://eu.api.openai.com/v1" # optional
vector_store_id = "vs_..."         # optional (RAG)
enable_web_search = true            # optional
```

Hinweis: Fehlende Schlüssel werden direkt in der UI mit konkreten Hinweisen (DE/EN) gemeldet.

## Fehlerbehebung

- **`ModuleNotFoundError: No module named 'firebase_admin'`**  
  Installieren Sie die Abhängigkeiten mit `pip install -r requirements.txt`.
  Falls `firebase-admin` im Laufzeitumfeld nicht verfügbar ist, startet die App jetzt weiterhin, zeigt aber für Stammdaten eine Hinweis-Meldung an, bis Firebase korrekt eingerichtet ist.
- **`ModuleNotFoundError: No module named 'face_recognition'`**  
  Die Gesichtserkennung ist optional. Die App startet und der Foto-Upload funktioniert weiterhin; es erscheint ein Hinweis, dass automatische Gesichtserkennung in dieser Bereitstellung deaktiviert ist.
