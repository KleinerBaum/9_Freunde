# 9 Freunde – Eltern- und Verwaltungsapp

Die **9 Freunde App** ist eine Streamlit-Webanwendung für die Großtagespflege *"9 Freunde"*. Sie unterstützt die Leitung bei organisatorischen Aufgaben und bietet Eltern einen geschützten Zugang zu Informationen rund um ihre Kinder. Kernfunktionen der App sind:
- **Getrennter Login für Eltern und Leitung:** Sichere Anmeldung mit unterschiedlichen Berechtigungen (Eltern sehen nur eigene Kind-Daten, Leitung hat vollen Verwaltungszugriff).
- **Stammdatenverwaltung:** Pflege der Kinder- und Eltern-Stammdaten durch die Leitung innerhalb der App.
- **Dokumenterstellung via KI:** Automatisches Generieren von Berichten/Briefen mit OpenAI sowie Download oder Ablage dieser Dokumente.
- **Branding mit Logo:** Die App nutzt `images/logo.png` als sichtbares UI-Logo sowie in erzeugten DOCX-Berichten.
- **Kalenderintegration:** Verwaltung wichtiger Termine über Google Calendar (inkl. Anzeige für Eltern) mit `services/calendar_service.py` (`add_event`, `list_events`, 60s Cache).
- **Fotoverwaltung (MVP):** Upload in kindspezifische Google-Drive-Ordner (`photos/<child_id>/`), sodass Eltern nur Fotos ihres Kindes sehen. In der App bleiben Vorschauen unverändert; beim Download gilt der pro Kind gespeicherte Consent (`pixelated` Standard, optional `unpixelated`) mit lokaler Verpixelung erkannter Gesichter.
- **Vertragsablage (Admin):** PDF/DOCX-Verträge werden in einen dedizierten Drive-Ordner (`gcp.drive_contracts_folder_id`) hochgeladen und als Liste angezeigt; Eltern sehen diesen Ordner nicht in der UI.
- **Infos-Seiten (Admin/Eltern):** Zentrale Inhalte wie Aushang/FAQ/Mitbringliste werden als Markdown-Seiten in `content_pages` gepflegt (Admin CRUD inkl. Preview, Eltern read-only auf veröffentlichte Inhalte).

Die App ist mobilfähig (Responsive Webdesign über Streamlit) und alle sensiblen Daten bleiben geschützt (keine öffentlichen Links, beschränkter Zugriff per Authentifizierung). 

## Installation und Voraussetzungen

Die App nutzt eine **Core-Installation** ohne optionale CV-Abhängigkeiten.

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

### Allgemeine Voraussetzungen

1. **Python installieren:** Stellen Sie sicher, dass Python 3.11+ installiert ist.
2. **Code beschaffen:** Klonen oder laden Sie das Repository mit dem App-Code.
3. **Virtuelle Umgebung:** Nutzen Sie idealerweise ein venv (`python -m venv .venv`).
4. **Streamlit testen:** `streamlit hello` ausführen, um die lokale Laufzeit zu prüfen.

## Prototyp-Modus (lokale Speicherung, einfache Konfiguration)

Für frühe Prototypen kann die App jetzt **ohne Google/Firebase** betrieben werden.
Standardmäßig läuft sie im lokalen Modus (`storage.mode = "local"`) und speichert Daten unter `./data/`:

- `data/children.json` für Stammdaten
- `data/content_pages.json` für Infos-Seiten (Fallback im Local-Mode)
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
   - **Streamlit Cloud:** Kopieren Sie den Inhalt der JSON in `.streamlit/secrets.toml` unter einem Eintrag `[gcp_service_account]`. Nutzen Sie für `private_key` bevorzugt einen mehrzeiligen TOML-String mit `"""..."""`, damit echte Zeilenumbrüche erhalten bleiben, und vermeiden Sie zusätzliche umschließende Quotes (z. B. `'"..."'`).
6. **Konfigurationswerte:** Hinterlegen Sie im Secrets-File außerdem:
   - `drive_photos_root_folder_id`: die ID des Drive-Hauptordners für Fotos.
   - `drive_contracts_folder_id`: die ID des Drive-Ordners für Verträge/Dokumente.
   - `stammdaten_sheet_id` (optional): überschreibt die Standard-Tabelle `Stammdaten_Eltern_2026` (`1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`).
   - `calendar_id` (optional): die Kalender-ID für den Google Kalender der Einrichtung.

### API-Inventur (Stand: aktuell im Code)

| API | Status | Nachweis im Code |
|---|---|---|
| Google Drive API (`drive.googleapis.com`) | **aktiv genutzt** | `storage.py`, `services/drive_service.py`, `app.py` |
| Google Calendar API (`calendar-json.googleapis.com`) | **aktiv genutzt** | `services/calendar_service.py`, `app.py` |
| Google Sheets API (`sheets.googleapis.com`) | **aktiv genutzt** | `services/google_clients.py`, `services/sheets_repo.py`, `stammdaten.py` |
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
  --filter="name:(drive.googleapis.com OR calendar-json.googleapis.com OR sheets.googleapis.com OR docs.googleapis.com OR forms.googleapis.com OR tasks.googleapis.com)"
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
Als Admin steht in der Sidebar der Button **„Google-Verbindung prüfen / Check Google connection“** zur Verfügung. Der Check führt drei Testaufrufe aus:

- **Drive-Test:** Ein kleiner List-Aufruf gegen die Drive API.
- **Calendar-Test:** Ein Leseaufruf auf Events des konfigurierten `calendar_id` (aus `st.secrets["gcp"]["calendar_id"]`).
- **Sheets-Test:** Ein minimaler Read-Call auf `<stammdaten_sheet_tab>!A1:A1` (A1-quoted, z. B. bei Leerzeichen im Tabnamen) des konfigurierten `gcp.stammdaten_sheet_id` inkl. kurzer Retries mit exponentiellem Backoff (bis zu 3 Versuche) bei transienten Fehlern.

Die App zeigt verständliche Fehlermeldungen (DE/EN) mit konkreten Hinweisen, falls Freigaben fehlen (z. B. kein Editor-Zugriff auf den Zielordner, Kalender nicht mit Service-Account geteilt, oder fehlende Sheet-Freigabe/ungültige `stammdaten_sheet_id` bei 403/404).

### OpenAI API (Textgenerierung)
Für die KI-gestützte Textgenerierung benötigen Sie einen OpenAI API-Schlüssel:
1. Legen Sie einen Account bei OpenAI an und erzeugen Sie einen persönlichen API Key im Dashboard.
2. Tragen Sie diesen Key in die Konfiguration ein (oder setzen Sie `OPENAI_API_KEY` als Umgebungsvariable).

Die Dokumentenerstellung nutzt die **OpenAI Responses API** mit strukturiertem JSON-Output und optionalen Tools (`file_search`, `web_search_preview`).

- Standardmodell (schnell/günstig): `gpt-4o-mini`
- Präzisionsmodus: `o3-mini` (für genauere Ergebnisse)
- Optionaler EU-Endpunkt: `https://eu.api.openai.com/v1`
- Timeouts + automatische Wiederholversuche mit exponentiellem Backoff sind integriert.

### Google Sheets prerequisites

Für Stammdaten wird Google Sheets als zentrale Quelle genutzt (Tabellenblätter `children`, `parents`, optional `consents`).

1. **Google Sheets API aktivieren**
2. **Service Account mit dem Stammdaten-Sheet teilen** (Editor-Rechte)
3. Optional **Sheet-ID über `gcp.stammdaten_sheet_id` setzen**, falls eine andere Tabelle als die Standard-Tabelle genutzt werden soll (`Stammdaten_Eltern_2026`, ID `1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`).
4. Optional **Tabname für die Admin-Ansicht** über `gcp.stammdaten_sheet_tab` setzen (Default: `Stammdaten_Eltern_2026`).
5. Optional **Tabnamen für Repository-Zugriffe** setzen:
   - `gcp.children_tab` (Default: `children`)
   - `gcp.parents_tab` (Default: `parents`)
   - `gcp.consents_tab` (Default: `consents`)
   - `gcp.content_pages_tab` (Default: `content_pages`)

Die App validiert diese Tabnamen beim Start (nicht leer, max. 100 Zeichen, keine verbotenen Zeichen `: \ / ? * [ ]`) und zeigt bei ungültigen Werten eine klare DE/EN-Fehlermeldung an.

Zusätzlich gibt es im Admin-Menü die read-only Ansicht **"Stammdaten Sheet"**, die den Bereich `A1:Z500` aus dem konfigurierten Tab als Tabelle rendert. Bei leerem Bereich oder falschem Tabnamen zeigt die App eine klare Hinweismeldung (DE/EN).

Pflicht-Tab für Kinder (`children`):
- Basis: `child_id`, `name`, `parent_email`
- Erweitert (automatisch ergänzt): `folder_id`, `photo_folder_id`, `download_consent`, `birthdate`, `start_date`, `group`, `primary_caregiver`, `allergies`, `notes_parent_visible`, `notes_internal`, `pickup_password`, `status`
- Admin-Formulare „Neues Kind anlegen“ und „Kind bearbeiten“ nutzen für `birthdate` und `start_date` den Streamlit-Datumspicker (`st.date_input`) und speichern ISO-Werte (`YYYY-MM-DD`) oder leer bei optionalen Feldern.

Empfohlener Eltern-Tab (`parents`):
- Basis: `parent_id`, `email`, `name`, `phone`
- Erweitert (automatisch ergänzt): `phone2`, `address`, `preferred_language`, `emergency_contact_name`, `emergency_contact_phone`, `notifications_opt_in`

Optional:
- `consents` (z. B. Consent-Flags für Foto-Downloads; alternativ Feld `download_consent` im `children`-Tab)

### Beispiel für das finale `secrets.toml`
Die App validiert beim Start zentral folgende Pflichtstruktur:

```toml
[gcp_service_account]
type = "service_account"
project_id = "my-project-id"
private_key_id = "abc123..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"""
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
stammdaten_sheet_id = "1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A" # optional; Default ist dieser Wert
children_tab = "children"   # optional; Default: children
parents_tab = "parents"     # optional; Default: parents
consents_tab = "consents"   # optional; Default: consents
content_pages_tab = "content_pages" # optional; Default: content_pages

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

### Vollständiges Secrets-Schema (Pflicht + Optional)

Pflicht (Google-Modus):
- `[gcp_service_account]` mit allen Service-Account-Feldern (`type`, `project_id`, `private_key_id`, `private_key`, `client_email`, `client_id`, `token_uri`)
- `[gcp]`
  - `drive_photos_root_folder_id`
  - `drive_contracts_folder_id`
  - `stammdaten_sheet_id` (optional, Default: `1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`)

Optional:
- `gcp.calendar_id`
- `gcp.stammdaten_sheet_tab`
- `[app].admin_emails` oder `[auth].admin_emails`
- `[openai]` (für KI-Dokumente)

### Setup-Hinweis zu Freigaben (sehr wichtig)

Wenn der Service-Account keine Rechte hat, schlagen API-Calls mit 403/404 fehl.
Stellen Sie sicher:
1. **Drive-Ordner ist mit dem Service-Account geteilt** (mindestens Editor/Bearbeiter).
2. **Stammdaten-Sheet ist mit dem Service-Account geteilt** (mindestens Editor/Bearbeiter).
3. **Kalender ist mit dem Service-Account geteilt**, falls `gcp.calendar_id` genutzt wird.

### Smoke-Check (Drive + Sheets)

Mit dem folgenden Script können Sie eine schnelle technische Prüfung ausführen:

```bash
python tools/smoke_check.py --secrets .streamlit/secrets.toml
```

Geprüft werden:
- Secrets laden und Pflichtfelder vorhanden
- Drive-List-Aufruf im `gcp.drive_contracts_folder_id`
- Sheets-Header-Lesen für `<stammdaten_sheet_tab>!1:1` (A1-quoted)

Ausgabe erfolgt je Schritt als `OK` oder `FAIL`.

### Typische Fehlerbilder

- **403 PERMISSION_DENIED / insufficient permissions**
  - Ursache: Ressource nicht mit Service-Account geteilt oder falsche Rolle.
  - Lösung: Drive-Ordner/Sheet/Kalender explizit mit `client_email` des Service-Accounts teilen.

- **404 File not found / Requested entity was not found**
  - Ursache: Falsche ID (`drive_contracts_folder_id`, `stammdaten_sheet_id`, `calendar_id`) oder Ressource nicht im Zugriffskontext.
  - Lösung: IDs prüfen und Freigaben erneut kontrollieren.

- **invalid_grant**
  - Ursache: Defekter Private Key, falsche Zeilenumbrüche in `private_key`, oder stark abweichende Serverzeit.
  - Lösung: Service-Account-JSON neu aus GCP exportieren, `private_key` unverändert (inkl. `\n`) übernehmen, Systemzeit/NTP prüfen.

- **`StreamlitSecretNotFoundError` / `TOMLDecodeError` beim App-Start**
  - Ursache: Syntaxfehler in `.streamlit/secrets.toml` (z. B. `key =` ohne Wert, fehlerhafte Inline-Tabelle, ungültige Quotes).
  - Lösung: TOML prüfen, z. B. mit `python -c "import tomllib, pathlib; tomllib.loads(pathlib.Path('.streamlit/secrets.toml').read_text(encoding='utf-8'))"`; fehlerhafte Zeile korrigieren.
