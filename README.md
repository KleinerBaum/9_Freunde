# 9 Freunde – Eltern- und Verwaltungsapp

> **New Sites app (recommended):** The repository now includes a low-cost TypeScript portal for staff and parents, a ChatGPT Apps SDK MCP server, deterministic invoice/contract PDFs, Google Sheets/Drive/Calendar adapters, and a private ChatGPT Sites deployment path. Start with [docs/SITES_APP.md](docs/SITES_APP.md). The original Streamlit implementation remains below for reference and migration support.

> **Produktfokus (Juli 2026):** Die App fokussiert auf Stammdaten, Dokumente/Verträge, Gmail-Kommunikation, Kalender und einen kleinen Foto-Upload-MVP. Der Foto-MVP umfasst Upload und Anzeige in geschützten Kind-Ordnern, ohne Gesichtserkennung oder automatisches Tagging.

Die **9 Freunde App** ist eine Streamlit-Webanwendung für die Großtagespflege *"9 Freunde"*. Sie unterstützt die Leitung bei organisatorischen Aufgaben und bietet Eltern einen geschützten Zugang zu Informationen rund um ihre Kinder. Kernfunktionen der App sind:
- **Getrennter Login für Eltern und Leitung:** Sichere Anmeldung mit unterschiedlichen Berechtigungen (Eltern sehen nur eigene Kind-Daten, Leitung hat vollen Verwaltungszugriff).
- **Sidebar-Sprach-Toggle (DE/EN):** Oberhalb von **„Angemeldet als / Logged in as“** kann die UI-Sprache umgeschaltet werden; zweisprachige Labels im Format `DE / EN` werden app-weit automatisch auf die aktive Sprache reduziert (inkl. Toggle-Beschriftungen, Navigation und Inhaltsbereiche) und blenden den nicht gewählten Teil inklusive Trennzeichen aus.
- **Stammdatenverwaltung:** Pflege der Kinder- und Eltern-Stammdaten durch die Leitung innerhalb der App.
- **Kinder-Übersicht (Admin):** In „Stammdaten“ wird eine sortierbare Tabelle mit Name, Eltern-E-Mail, Gruppe, Geburtsdatum und Drive-Ordnerstatus (`✅ Ready`/`⚠️ Missing`) angezeigt.
- **Foto-Upload-MVP (Admin + Eltern):** Der Bereich **„Fotos & Medien / Photos & media“** erlaubt Upload und Anzeige von Bildern im bestehenden Drive-Ordner des jeweiligen Kindes (`folder_id`).
- **Admin-Start mit Gesamtübersicht:** Das Dashboard zeigt nach dem Login eine kompakte Tabelle mit Kind, Elternkontakt, `folder_id` und Ordnerstatus zur schnellen Datenkontrolle.
- **Admin-Dashboard neu strukturiert:** Persönliche Begrüßung (aus Login-E-Mail abgeleitet), KPI-Karten, zweispaltiges Layout (Schnellaktionen + Termine) sowie ausklappbare Bereiche für Kinderübersicht und Kalender reduzieren Scrollen und erhöhen die Informationsdichte.
- **Kalender-Workflow im Dashboard vereinfacht:** Der separate Admin-Navigationspunkt **„Kalender / Calendar“** entfällt. Das Formular **„Neuer Termin / New event“** ist direkt im Dashboard unter **„Bevorstehende Termine / Upcoming events“** integriert; die Kalenderansicht wird darunter dauerhaft (ohne Dropdown) angezeigt. Optional können Admins hinterlegte User-E-Mails auswählen, die beim Erstellen als Kalender-Teilnehmende eingeladen und per Mail benachrichtigt werden.
- **Dokumente & Verträge übersichtlicher:** Formulare und Dateilisten sind gruppiert, in Spalten angeordnet und enthalten aufklappbare Detailbereiche für gespeicherte Dateien und Vorschauen.
- **Kommunikation / Communication (Admin):** Neuer Bereich für E-Mail-Kommunikation mit Zielgruppensteuerung (alle Eltern, Gruppe, einzelnes Kind), Vorlagen (Info/Rückfrage/Erinnerung), Vorschau, Versandprotokoll ohne PII sowie verständlichen DE/EN-Fehlermeldungen mit Retry (exponentielles Backoff) bei transienten Gmail-API-Fehlern.
- **Kommunikation (Gmail) als Kernfeature:** Admins senden Elternnachrichten zielgruppengenau (alle Eltern/Gruppe/ein Kind) mit Vorlagen, Vorschau und Versandprotokoll ohne PII.
- **Kalender + Dokumente im Fokus:** Verträge/Abrechnungen und Kalenderprozesse sind zentrale Admin-Workflows; Eltern erhalten nur die für sie freigegebenen Informationen.
- **DriveAgent mit OneDrive-Backend (optional):** Sobald `[onedrive].enabled = true` aktiv ist, nutzt `services/drive_service.py` für Upload, Download, Listing und Ordneranlage Microsoft Graph statt Google Drive. So können bestehende Drive-Aufrufe ohne UI-Änderung auf OneDrive laufen.
- **UI-/Domain-Basisstruktur (minimal-invasiv):** Neue Module `ui/layout.py`, `ui/state_keys.py`, `ui/media_gallery.py` und `domain/models.py` kapseln Darstellung, Session-Keys und Datamodelle, ohne bestehende Service-/Storage-Logik unter `services/` zu verändern.
- **Eindeutige Auswahl in Admin-Formularen:** Kind- und Abholberechtigten-Auswahl nutzt interne Datensatz-IDs (Anzeige weiter über Namen), damit gleichnamige Einträge sicher bearbeitet werden.
- **Geführtes Bearbeiten in Stammdaten:** Editierfelder für Kinder und Abholberechtigungen werden erst nach aktiver Auswahl eines Eintrags angezeigt; die Bereiche **„Neues Kind anlegen / Add child“**, **„Abholberechtigte / Pickup authorizations“** und **„Medikationen“** sind standardmäßig eingeklappt.
- **Medikamentengabe-Log (auditierbar):** Admins können pro Kind Medikamentengaben als minimales Log erfassen (Zeitpunkt, Medikament, Dosis, verabreicht von, Notiz) inkl. optionalem Consent-Dokument-Link; Eltern sehen die Einträge read-only für ihr eigenes Kind.
- **Dokumenterstellung via KI:** Automatisches Generieren von Berichten/Briefen mit OpenAI sowie Download oder Ablage dieser Dokumente.
- **Dokumenten-Wizard (4 Schritte):** Neuer Wizard in **Dokumente & Verträge** mit Schrittfolge **Kind/Vertragspartner → Parameter → KI-Vorschlag → Export/Versand**, inkl. zweisprachiger UI-Texte.
- **Einheitliche Vorlagenbibliothek & Exporte:** Zentrale Vorlagen `contract`, `addendum`, `monthly_invoice` sowie standardisierte Dateinamen `YYYYMMDD_<child_id>_<document_type>.<ext>` für DOCX/PDF/JSON/Markdown und optionalen Gmail-Versand.
- **Dokumentvorlagen aus Stammdaten:** Im Bereich „Dokumente“ lassen sich zusätzlich ein **Betreuungsvertrag** sowie eine **Abrechnung der Lebensmittelpauschale** (frei wählbarer Zeitraum, aktuelles Datum, Logo) je Kind erzeugen. Die Vertragssprache kann dabei aus einer erweiterten Liste typischer Sprachen in Düsseldorf gewählt werden (u. a. DE/EN/TR/AR/RU/UK/PL/RO/BG/EL/IT/ES/FR/NL/FA/KU/SQ/SR/HR/BS).
- **Dokumentsprache & Entwurfsstatus (Admin):** Beim Erstellen von Berichten und Betreuungsverträgen kann die Sprache gezielt auf **DE/EN** gesetzt werden (Standard: **Deutsch**) und ein **Entwurf/Draft**-Status über Checkbox aktiviert werden; dieser wird im Inhalt und Dateinamen markiert.
- **Dokumentvorschau vor Download:** Im Admin-Bereich „Dokumente“ werden neue und bereits in Drive gespeicherte DOCX-Dateien als Textvorschau in aufklappbaren Bereichen angezeigt, bevor der Download gestartet wird.
- **PDF-Registrierungsparser (Schema v1):** Neues Service-Modul `services/registration_form_service.py` liest ACROForm-Felder aus dem Anmeldeformular robust aus, normalisiert Checkbox-/Textwerte und validiert Pflichtangaben für die Weiterverarbeitung.
- **PDF-Import in Admin-Stammdaten:** Im Bereich **„Stammdaten“** gibt es jetzt den aufklappbaren Abschnitt **„Anmeldung importieren (PDF) / Import registration (PDF)“** mit Download der Blanko-Vorlage (`assets/forms/9Freunde_Anmeldeformular_v1.pdf`), PDF-Upload, Vorschau (Kind/Eltern/Abholberechtigte/Einwilligungen), Validierungsfehlern mit Save-Blockade und primärem Speicher-CTA inklusive Rückmeldung der `child_id`.
- **Formulare mit Single-Submit (Admin):** Bearbeiten-/Upload-Aktionen in **Stammdaten (Import)**, **Verträge** und **Fotos** verwenden konsequent `st.form(..., border=True)` mit genau einem Submit-Button; damit folgt die UI dem Streamlit-Form-Prinzip „Widgets sammeln → ein Rerun beim Submit“.
- **Schema-v1 Mapping idempotent erweitert:** `services/sheets_repo.py` mappt Registrierungs-Payloads jetzt mit stabiler `child_id`-Auflösung (`child__child_id` bevorzugt, sonst `uuid4`), erweitertem Kinderfeld-Mapping (inkl. Gesundheits-/Betreuungsfeldern), Eltern-Upsert-Struktur pro E-Mail, Consent-Feldern sowie `pa1..pa4`-Mapping nur bei aktivierter und benannter Abholberechtigung.
- **Branding mit Logo:** Die App nutzt `images/logo.png` als sichtbares UI-Logo sowie in erzeugten DOCX-Berichten.
- **Landing-Page-Branding:** Oberhalb der Inhalte wird zusätzlich `images/Herz.png` zentriert dargestellt; `images/Hintergrund.png` wird als globales Hintergrundbild der gesamten App verwendet.
- **Überarbeitetes Dark-Element-Theme (DE/EN):** Dunkle UI-Elemente (Buttons, Inputs, Sidebar) wurden auf eine kontraststarke, nutzerfreundliche und stylische Farbpalette umgestellt; helle Eingabeflächen mit klaren Fokuszuständen verbessern die Lesbarkeit deutlich. / Dark UI elements (buttons, inputs, sidebar) now use a higher-contrast, user-friendly, stylish palette; lighter input surfaces and clear focus states significantly improve readability.
- **Theme-first Styling mit Streamlit-Konfiguration:** Die App nutzt `.streamlit/config.toml` für zentrale Theme-Werte (Farben, Radius, Sidebar-Rand), sodass Container/Forms/Dialogs konsistent ohne umfangreiche CSS-Hacks gestylt sind.
- **Card-Layout über Container mit Border:** Wichtige Bereiche wie Admin-Dashboard, Admin-Übersicht und Elternansicht „Mein Kind“ sind als `st.container(border=True)` umgesetzt, um Abschnitte klar zu gliedern.
- **Dashboard mit integrierter Admin-Übersicht:** Die Kinder-Übersicht für Admins wird direkt im Bereich **Dashboard / Dashboard** angezeigt; darunter steht ein optional einblendbarer Google-Kalender (inkl. „Kalender im Browser öffnen / Open calendar in browser").
- **Admin-Aktionen im Dashboard gebündelt:** Die Bereiche **„Neues Kind anlegen / Add child“** und **„Anmeldung importieren (PDF) / Import registration (PDF)“** wurden in die **Admin-Übersicht / Admin overview** verschoben und stehen dort oberhalb der **Kinder-Übersicht / Children overview** bereit.
- **Dashboard mit Terminvorschau:** **"Bevorstehende Termine / Upcoming events"** wird im Admin-Dashboard unter der **Admin-Übersicht / Admin overview** API-basiert angezeigt; die IFrame-Ansicht ist optional zuschaltbar.
- **Kalenderintegration:** Verwaltung wichtiger Termine über Google Calendar (inkl. Anzeige für Eltern) mit `services/calendar_service.py` (`add_event`, `list_events`, 60s Cache). Primär wird die API-basierte Terminliste genutzt; die IFrame-Ansicht verwendet eine aus `gcp.calendar_id` erzeugte, URL-encodete Embed-URL und bleibt optional.
- **Vertragsablage (Admin):** PDF/DOCX-Verträge werden in einen dedizierten Drive-Ordner (`gcp.drive_contracts_folder_id`) hochgeladen und als Liste angezeigt; Eltern sehen diesen Ordner nicht in der UI.
- **Einheitliche Drive-Schicht:** Google-Drive-Operationen (`upload/list/download/create_folder`) laufen konsistent über `services/drive_service.py` (inkl. Shared-Drive-Flags `supportsAllDrives`/`includeItemsFromAllDrives` und klarer 403/404-Fehlerübersetzung).
- **Infos-Seiten (Admin/Eltern):** Zentrale Inhalte wie Aushang/FAQ/Mitbringliste werden als Markdown-Seiten in `content_pages` gepflegt (Admin CRUD inkl. Preview, Eltern read-only auf veröffentlichte Inhalte).
- **Admin-Navigation modernisiert:** Die Sidebar führt jetzt nur noch Hauptbereiche (**Dashboard**, **Stammdaten & Infos**, **Fotos & Medien**, **Dokumente & Verträge**, **Kalender**, **System / Healthchecks**). Der Google-Verbindungscheck ist im Bereich **„System / Healthchecks“** gebündelt; **„Medikationen“** bleibt als eingeklappter Abschnitt in **„Stammdaten“** integriert.
- **Navigationsstruktur vereinfacht (DE/EN + Icons):** Die Hauptnavigation bleibt auf maximal 6 klar benannten Bereichen und nutzt eindeutige Icons für schnellere Orientierung (Admin + Eltern).
- **Dashboard-Kacheln geschärft:** Das Admin-Dashboard zeigt jetzt die vier Kern-KPIs **Offene Verträge**, **Fällige Abrechnungen**, **Ungelesene Elternanfragen** und **Nächste Termine**.
- **Form-Pattern vereinheitlicht:** Neue Formbereiche folgen konsistenten Section-Cards, optionaler Progression via Expander, Inline-Validierung sowie klaren Success-/Error-States.
- **Erweiterte UI-Bausteine in `ui/layout.py`:** `section_card`, `render_kpi_widgets`, `table_toolbar`, `empty_state`, `form_feedback` ergänzen die bestehenden Layout-Helfer und reduzieren UI-Duplikate in `app.py`.

Die App ist mobilfähig (Responsive Webdesign über Streamlit) und alle sensiblen Daten bleiben geschützt (keine öffentlichen Links, beschränkter Zugriff per Authentifizierung).

## Foto-Upload / Photo upload

- Admins können Fotos für jedes Kind hochladen und ansehen.
- Eltern können Fotos nur für ihr eigenes Kind hochladen und ansehen.
- Die Speicherung erfolgt im bestehenden Drive-Ordner des Kindes (`folder_id`).
- Im Google-Modus nutzt die App Google Drive über den vorhandenen `DriveAgent`/Drive-Service.
- Im Local-Modus nutzt die App die lokale `DriveAgent`-Ablage unter `data/drive/`.
- Es werden keine öffentlichen Google-Drive-Links erzeugt.
- Es werden keine Drive-Permissions pro Foto erstellt.
- Erlaubte Formate: JPG/JPEG, PNG, WebP.
- Maximale Dateigröße: 15 MB pro Datei.
- Der MVP enthält keine Gesichtserkennung, kein automatisches Tagging und keine automatische Consent-Pixelierung.
- Secrets gehören in `.streamlit/secrets.toml` und nicht ins Repo.

### Konfiguration: OpenAI, Gmail, Calendar

Für die produktiven Kernfunktionen sollten folgende Secrets gesetzt sein:

```toml
[gcp]
calendar_id = "<google-calendar-id>"
gmail_delegated_user = "leitung@example.org" # optional, empfohlen bei Domain-Delegation

[openai]
api_key = "<openai-api-key>"
model_fast = "gpt-4o-mini"
model_precise = "o3-mini"
```

Hinweis: Für Gmail-Versand benötigt der Service-Account Scope `https://www.googleapis.com/auth/gmail.send` und ggf. Domain-Wide Delegation.

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

- `data/stammdaten.ods` als zentrale Stammdaten-Datei mit Sheets `children`, `parents`, `consents`, `pickup_authorizations`, `medications`
- `data/content_pages.json` für Infos-Seiten (Fallback im Local-Mode)
- `data/calendar_events.json` für Termine
- `data/drive/` für Dokumente und Fotos

Minimales `secrets.toml` für den Prototypen:

```toml
[storage]
mode = "local"

[local]
data_dir = "./data"
stammdaten_file = "./data/stammdaten.ods" # optional

[auth]
admin_emails = ["leitung@example.org"]

[auth.users]
leitung@example.org = "demo123"
eltern@example.org = "demo123"

# Optional: OneDrive (Einbettung + Graph API für Upload/Galerie)
[onedrive]
enabled = true
shared_folder_url = "https://1drv.ms/f/..."
folder_path = "Documents/9 Freunde"
# App-only Ziel: entweder Benutzerlaufwerk ODER konkrete Drive-ID
drive_user_id = "kita-admin@tenant.onmicrosoft.com"
# drive_id = "b!abcDEF..."
client_id = "<azure-app-client-id>"
client_secret = "<azure-app-client-secret>"
tenant_id = "<azure-tenant-id>"
```

Optional können Sie später wieder auf Google umstellen:

```toml
[storage]
mode = "google"
```

Dann werden die bereits dokumentierten `gcp_service_account`- und `gcp`-Einträge wieder verpflichtend.


### OneDrive über Microsoft Graph (Azure App)

Für die direkte Upload-/Download-Integration via Graph API braucht die App eine Azure-App-Registrierung:

1. **Azure App registrieren** im Microsoft Entra Portal.
2. Unter **API permissions** mindestens **Microsoft Graph → Application → `Files.ReadWrite.All`** hinzufügen und Admin-Consent erteilen (für `acquire_token_for_client`).
3. In Streamlit-Secrets den Abschnitt `[onedrive]` mit `enabled`, `client_id`, `client_secret`, `tenant_id`, `folder_path` und **entweder** `drive_user_id` **oder** `drive_id` setzen.
4. Die App prüft den Zielordner über app-kompatible Graph-Endpunkte (`/users/{user-id}/drive/...` oder `/drives/{drive-id}/...`) und nutzt danach diese Endpunkte:
   - Listing: `GET /users/{user-id}/drive/items/{folder_id}/children` (bzw. `/drives/{drive-id}/items/...`)
   - Upload: `PUT /users/{user-id}/drive/root:/Documents/9 Freunde/{file_name}:/content`
   - Download: `GET /users/{user-id}/drive/items/{item_id}/content`

Hinweis: Falls Listing/Upload leer oder mit 403 fehlschlägt, sind Berechtigungen oder Consent in Azure meist noch nicht vollständig.

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
   - **Streamlit Cloud:** Kopieren Sie den Inhalt der JSON in `.streamlit/secrets.toml` unter einem Eintrag `[gcp_service_account]`. Nutzen Sie für `private_key` bevorzugt einen mehrzeiligen TOML-String mit `"""..."""`, damit echte Zeilenumbrüche erhalten bleiben, und vermeiden Sie zusätzliche umschließende Quotes (z. B. `'"..."'`).
6. **Konfigurationswerte:** Hinterlegen Sie im Secrets-File außerdem:
   - `drive_photos_root_folder_id`: die ID des Drive-Hauptordners, unter dem neue Kind-Ordner erstellt werden (alternativ akzeptiert die App auch eine vollständige Drive-Ordner-URL und extrahiert die ID automatisch). Foto-Uploads nutzen danach den `folder_id` des jeweiligen Kindes.
   - `drive_contracts_folder_id`: die ID des Drive-Ordners für Verträge/Dokumente (alternativ auch als vollständige Drive-Ordner-URL möglich).
   - `stammdaten_sheet_id` (optional): überschreibt die Standard-Tabelle `Stammdaten_Eltern_2026` (`1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`).
   - `calendar_id` (optional): die Kalender-ID für den Google Kalender der Einrichtung.

### API-Inventur (Stand: aktuell im Code)

| API | Status | Nachweis im Code |
|---|---|---|
| Google Drive API (`drive.googleapis.com`) | **aktiv genutzt (Fallback)** | `storage.py`, `services/drive_service.py`, `app.py` |
| Microsoft Graph Drive (`graph.microsoft.com`) | **aktiv genutzt (bei `[onedrive].enabled = true`)** | `services/drive_service.py`, `onedrive_auth.py`, `storage.py`, `ui/photos.py` |
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
- **Calendar-Test:** Ein Leseaufruf auf Events des konfigurierten `calendar_id` (aus der Mapping-kompatiblen Secrets-Sektion `gcp`, z. B. `st.secrets["gcp"].get("calendar_id")`).
- **Sheets-Test:** Ein minimaler Read-Call auf `<stammdaten_sheet_tab>!A1:A1` (A1-quoted, z. B. bei Leerzeichen im Tabnamen) des konfigurierten `gcp.stammdaten_sheet_id` inkl. kurzer Retries mit exponentiellem Backoff (bis zu 3 Versuche) bei transienten Fehlern.

Die App zeigt verständliche Fehlermeldungen (DE/EN) mit konkreten Hinweisen, falls Freigaben fehlen (z. B. kein Editor-Zugriff auf den Zielordner, Kalender nicht mit Service-Account geteilt, oder fehlende Sheet-Freigabe/ungültige `stammdaten_sheet_id` bei 403/404).


### UI-Theming (Streamlit)

Die wichtigsten Designwerte werden in `.streamlit/config.toml` gepflegt (u. a. Farben und Border-Radius):

```toml
[theme]
base = "light"
primaryColor = "#2F6FED"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F6F7FB"
textColor = "#111827"
baseRadius = "10px"
buttonRadius = "10px"
showSidebarBorder = true
```

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

Für Stammdaten wird Google Sheets als zentrale Quelle genutzt (Tabellenblätter `children`, `parents`, optional `consents`, sowie `pickup_authorizations` für Abholberechtigungen).

1. **Google Sheets API aktivieren**
2. **Service Account mit dem Stammdaten-Sheet teilen** (Editor-Rechte)
3. Optional **Sheet-ID über `gcp.stammdaten_sheet_id` setzen**, falls eine andere Tabelle als die Standard-Tabelle genutzt werden soll (`Stammdaten_Eltern_2026`, ID `1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`).
4. Optional **Tabname für die Admin-Ansicht** über `gcp.stammdaten_sheet_tab` setzen (Default: `Stammdaten_Eltern_2026`).
5. Optional **Tabnamen für Repository-Zugriffe** setzen:
   - `gcp.children_tab` (Default: `children`)
   - `gcp.parents_tab` (Default: `parents`)
   - `gcp.consents_tab` (Default: `consents`)
   - `gcp.pickup_authorizations_tab` (Default: `pickup_authorizations`)

Der Tab `pickup_authorizations` wird bei Bedarf automatisch erstellt, wenn er im Spreadsheet noch fehlt. Bei nicht auflösbaren Range-/Tab-Problemen zeigt die App eine klare DE/EN-Fehlermeldung mit Hinweis auf `gcp.pickup_authorizations_tab`.
   - `gcp.medications_tab` (Default: `medications`)
   - `gcp.content_pages_tab` (Default: `content_pages`)

Die App validiert diese Tabnamen beim Start (nicht leer, max. 100 Zeichen, keine verbotenen Zeichen `: \ / ? * [ ]`) und zeigt bei ungültigen Werten eine klare DE/EN-Fehlermeldung an.

Im Admin-Bereich **"Stammdaten"** steht zuerst die Tabelle **"Kind bearbeiten / Edit child"** mit der Spalte **"Auswahl / Select"** (Checkboxen). Für alle ausgewählten Kinder erscheinen direkt darunter parallel editierbare Stammdaten-Formulare (nebeneinander) inklusive Elternfeldern. Die reine **Kinder-Übersicht / Children overview** folgt unterhalb dieses Bearbeitungsblocks.

Unterhalb dieses Bereichs steht zusätzlich ein **Export/Backup-Block (CSV + JSON)** bereit. Für die zentralen Tabs (`children`, `parents`) werden Download-Buttons angeboten. Leere Tabs werden als Hinweis angezeigt (kein Crash), und CSV-Exporte enthalten konsistente Header-/Spaltenreihenfolge basierend auf der Header-Zeile des jeweiligen Tabs.

Pflicht-Tab für Kinder (`children`):
- Basis: `child_id`, `name`, `parent_email`
- Erweitert (automatisch ergänzt): `folder_id`, `download_consent`, `birthdate`, `start_date`, `group`, `primary_caregiver`, `allergies`, `notes_parent_visible`, `notes_internal`, `pickup_password`, `status`, `doctor_name`, `doctor_phone`, `health_insurance`, `medication_regular`, `dietary`, `languages_at_home`, `sleep_habits`, `care_notes_optional`
- Mapping-Regel: Falls `parent1__email` gesetzt ist, wird `children.parent_email` automatisch auf diesen Wert synchronisiert.
- Consent-Regel: `children.download_consent` wird direkt aus dem Feld `download_consent` übernommen (Default: `pixelated` bei ungültigem/leerem Wert). Der Foto-Upload-MVP wertet dieses Feld nicht für automatische Pixelierung aus.
- Admin-Formulare „Neues Kind anlegen“ und „Kind bearbeiten“ nutzen für `birthdate` und `start_date` den Streamlit-Datumspicker (`st.date_input`) und speichern ISO-Werte (`YYYY-MM-DD`) oder leer bei optionalen Feldern.

Empfohlener Eltern-Tab (`parents`):
- Basis: `parent_id`, `email`, `name`, `phone`
- Erweitert (automatisch ergänzt): `phone2`, `address`, `preferred_language`, `emergency_contact_name`, `emergency_contact_phone`, `notifications_opt_in`
- Admin kann diese Elternfelder in **"Neues Kind anlegen / Add child"** und **"Kind bearbeiten / Edit child"** pflegen; Datensätze werden per E-Mail als Upsert in `parents` gespeichert.
- Eltern sehen die Felder read-only in **"Mein Kind - Übersicht"**: Name, Geburtsdatum, Gruppe, Notfallkontakt, bevorzugte Sprache und Benachrichtigungs-Opt-in.

Optional:
- `consents` (projektspezifische Consent-Flags; alternativ Feld `download_consent` im `children`-Tab)

## Schema v1 → Tab-Mapping

Die folgende Zuordnung dokumentiert, wie Felder aus dem bisherigen Schema-v1-Format (`<prefix>__<field>`) auf die Google-Sheets-Tabs gemappt werden. Die zentrale Mapping-Funktion `map_schema_v1_payload_to_tab_records()` in `services/sheets_repo.py` bildet `children`, `parents`, `pickup_authorizations` und `consents` konsistent ab.

Serialisierung von Mehrfachstrukturen: `pa1__*` bis `pa4__*` werden als geordnete Liste (`pa1`→`pa4`) in `pickup_authorizations` ausgegeben. Pro Präfix wird genau ein Eintrag erzeugt, sobald mindestens eines der Kernfelder (`name`, `relationship`, `phone`, `valid_from`, `valid_to`, `created_at`, `created_by`) befüllt ist.

| Quelle | Ziel-Tab | Ziel-Spalte | Transformationsregel |
|---|---|---|---|
| `meta__record_id` | `children` | `child_id` | Falls vorhanden direkte Übernahme; sonst wird `child_id` als UUID erzeugt. |
| `meta__created_at`, `meta__updated_at` | `children` | `notes_internal` | **Out of scope** als eigene Spalten; als JSON-Metablock in `notes_internal` angehängt. |
| `meta__import_source`, `meta__version` | `children` | `notes_internal` | **Out of scope** als eigene Spalten; als JSON-Fallback (`meta`) in `notes_internal`. |
| `child__name` | `children` | `name` | Direkte String-Übernahme (trim). |
| `child__birthdate` | `children` | `birthdate` | Datum auf ISO-8601 (`YYYY-MM-DD`) normalisieren; ungültige Werte leer speichern. |
| `child__start_date` | `children` | `start_date` | Datum auf ISO-8601 (`YYYY-MM-DD`) normalisieren. |
| `child__group` | `children` | `group` | Direkte Übernahme (trim). |
| `child__allergies` | `children` | `allergies` | Mehrfachwerte als kommagetrennter String speichern. |
| `child__notes_parent_visible` | `children` | `notes_parent_visible` | Direkte Übernahme, für Eltern sichtbar. |
| `child__notes_internal` | `children` | `notes_internal` | Direkte Übernahme; kann JSON-Fallback für nicht persistierte Felder enthalten. |
| `child__pickup_password` | `children` | `pickup_password` | Direkte Übernahme (trim). |
| `child__status` | `children` | `status` | Direkte Übernahme; erwartete Werte z. B. `active`/`inactive`/`archived`. |
| `parent1__email` | `parents` + `children` | `parents.email` + `children.parent_email` | Upsert in `parents`; gleichzeitig Synchronisierung auf `children.parent_email` (Primärkontakt). |
| `parent1__name` | `parents` | `name` | Upsert per E-Mail; Name aktualisieren. |
| `parent1__phone` | `parents` | `phone` | String-Normalisierung (trim). |
| `parent1__phone2` | `parents` | `phone2` | Optionales Zweittelefon, leer erlaubt. |
| `parent1__address` | `parents` | `address` | Direkte Übernahme (trim). |
| `parent1__preferred_language` | `parents` | `preferred_language` | Sprachkürzel/Freitext übernehmen. |
| `parent1__emergency_contact_name` | `parents` | `emergency_contact_name` | Direkte Übernahme. |
| `parent1__emergency_contact_phone` | `parents` | `emergency_contact_phone` | Direkte Übernahme. |
| `parent1__notifications_opt_in` | `parents` | `notifications_opt_in` | Bool-Normalisierung (`true/1/ja` → `true`, sonst `false`). |
| `parent2__*` | `parents` | wie `parent1__*` | Zweiter Eltern-Datensatz als eigener Upsert; Beziehung zum Kind über `parent_email`-Logik und/oder interne Zuordnung. |
| `pa1__*`, `pa2__*`, `pa3__*`, `pa4__*` | `pickup_authorizations` | `name`, `phone`, `relationship`, `active`, `valid_from`, `valid_to`, `created_at`, `created_by` | Je Präfix ein Datensatz. Bool-Normalisierung für `active`; `notes` ist **out of scope** (keine Persistenz im Pickup-Schema). |
| `download_consent` | `children` | `download_consent` | Direkte Übernahme (zulässig: `pixelated`, `unpixelated`, `denied`; sonst Fallback `pixelated`). Im Foto-Upload-MVP gibt es keine automatische Pixelierung. |
| weitere `consent__*` (z. B. Ausflüge, Medien) | optional `consents` | projektspezifische Spalten | **Out of scope** für das produktive Pflichtschema; optional im `consents`-Tab oder JSON-Fallback in `children.notes_internal`. |
| `sign__parent1_name`, `sign__parent1_date` | optional `consents` | z. B. `sign_parent1_name`, `sign_parent1_date` | **Out of scope** (Signatur-Workflow noch nicht produktiv); bevorzugt im `consents`-Tab ablegen. |
| `sign__parent2_name`, `sign__parent2_date` | optional `consents` | z. B. `sign_parent2_name`, `sign_parent2_date` | **Out of scope** (Signatur-Workflow noch nicht produktiv); alternativ JSON-Fallback in `children.notes_internal`. |
| `sign__place`, `sign__signature_ref` | optional `consents` | z. B. `sign_place`, `sign_signature_ref` | **Out of scope** bis zur finalen Signatur-Implementierung; in separatem Tab oder JSON-Fallback führen. |

### Nicht persistierte Felder (explizit)

Aktuell gelten folgende Gruppen als **nicht Teil des Pflichtschemas** und werden deshalb interimistisch behandelt:

- Erweiterte `meta__*`-Felder (außer einer möglichen ID-Übernahme für `child_id`)
  → Speicherung als JSON-Fallback in `children.notes_internal`.
- Erweiterte `consent__*`-Felder jenseits der Pflicht-Flags (`privacy_notice_ack`, `excursions`, `emergency_treatment`, `whatsapp_group`)
  → bevorzugt eigener Tab `consents`; alternativ JSON-Fallback in `children.notes_internal`.

### Migration bestehender Sheets auf das neue Schema (ohne Datenverlust)

1. **Backup erstellen**: komplette Tabelle als XLSX/CSV exportieren.
2. **Header migrieren**:
   - Tab `children`: Spalte `photo_folder_id` aus Header entfernen (Daten bleiben in Backup erhalten). Der MVP nutzt `children.folder_id`.
   - Tab `consents`: Spalte `photo_download` aus Header entfernen.
   - Tab `photo_meta`: Tab ist für den Foto-Upload-MVP nicht erforderlich (kann archiviert oder gelöscht werden).
3. **Werte übernehmen**:
   - Falls bisher nur alte PDF-Felder genutzt wurden, `children.download_consent` einmalig aus Altdaten befüllen (z. B. mit vorhandenen Werten aus `consents.photo_download`).
4. **App starten**: Header-Selbstheilung ergänzt fehlende Pflichtspalten automatisch (`children`, `parents`, `pickup_authorizations`, `medications`, `consents`).
- Alle `sign__*`-Felder (Signatur-/Ort-/Datum-Metadaten)
  → bevorzugt eigener Tab `consents`; falls nicht vorhanden, JSON-Fallback in `children.notes_internal`.

Empfehlung: Für produktive Nachvollziehbarkeit sollte der optionale Tab `consents` aktiviert und um explizite Spalten für `consent__*`/`sign__*` erweitert werden, damit weniger Daten in Freitextfeldern (`notes_internal`) liegen.

Hinweis zu CRUD-Parität: Das Löschen eines Kindes ist nun auch im Google-Modus implementiert (Zeile wird im `children`-Tab entfernt).

Pflicht-Tab für Medikamenten-Log (`medications`):
- `med_id` (uuid), `child_id`, `date_time`, `med_name`, `dose`, `given_by`, `notes`, `consent_doc_file_id` (optional), `created_at`, `created_by`
- Fehlende Header-Spalten werden beim ersten Zugriff automatisch ergänzt.
- Soft-Gate: Fehlt `consent_doc_file_id`, wird nur ein Hinweis angezeigt (kein Blocker beim Speichern).

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
children_tab = "children"                       # optional; Default: children
parents_tab = "parents"                         # optional; Default: parents
consents_tab = "consents"                       # optional; Default: consents
pickup_authorizations_tab = "pickup_authorizations"  # optional; Default: pickup_authorizations
medications_tab = "medications" # optional; Default: medications
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
# Hinweis / Note: true erfordert Web-Search-Freischaltung im OpenAI-Projekt;
# bei Problemen testweise false setzen / requires project entitlement;
# if issues occur, try false temporarily.
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


### Quick Fix: Fehlendes `gcp.calendar_id` (Google-Modus)

Wenn in der Sidebar der Google-Check beim Kalender fehlschlägt und auf ein fehlendes `gcp.calendar_id` hinweist:

1. Öffnen Sie **Settings → Secrets** in Streamlit Cloud.
2. Ergänzen Sie im Bereich `[gcp]` den Eintrag `calendar_id = "<ihre-kalender-id>"`.
3. Speichern Sie die Secrets und starten Sie die App neu.

EN: If the Google sidebar check reports missing `gcp.calendar_id`, open **Settings → Secrets**, add `calendar_id` under `[gcp]`, save, and restart the app.

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

- **Admin-Foto-Upload zeigt jetzt gezielte Drive-Hinweise**
  - Bei 403/404 meldet die UI Freigabe-/ID-Probleme aus dem Upload in den Kind-Ordner (`folder_id`).
  - Fehlt der Kind-Ordner (`folder_id`), zeigt die Foto-Seite einen Hinweis. Für neu angelegte Kinder muss im Google-Modus zusätzlich `gcp.drive_photos_root_folder_id` korrekt freigegeben sein, damit der Kind-Ordner erstellt werden kann.

- **System / Healthchecks zeigt Drive-Ordner-ID je Check**
  - Bei Drive-Fehlern zeigt die UI den konkreten betroffenen Ordner (aktuell `gcp.drive_contracts_folder_id`) und differenziert 403 (fehlende Freigabe) vs. 404 (ungültige ID).
  - Dadurch kann die Freigabe direkt auf dem richtigen Ordner korrigiert werden, ohne Secrets/PII offenzulegen.

- **System / Healthchecks zeigt Kalender-Kontext bei Fehlern**
  - Bei Kalender-Fehlern zeigt die UI explizit die verwendete `calendar_id` und die benötigte Freigabe für `gcp_service_account.client_email` (mindestens „Änderungen an Terminen vornehmen“ / “Make changes to events”).
  - Zusätzlich wird 403 (fehlende Berechtigung) von 404 (ungültige `calendar_id`) getrennt angezeigt.


- **404 File not found / Requested entity was not found**
  - Ursache: Falsche ID (`drive_contracts_folder_id`, `stammdaten_sheet_id`, `calendar_id`) oder Ressource nicht im Zugriffskontext.
  - Lösung: IDs prüfen und Freigaben erneut kontrollieren.

- **Fotos hochgeladen, aber Liste bleibt leer**
  - Ursache: Uneinheitlicher MIME-Filter in Drive-Abfragen (z. B. `image/`) kann je nach API-Antwort dazu führen, dass Bilder beim Listing nicht zurückkommen.
  - Lösung: Auf aktuelle Version aktualisieren; die App normalisiert den Filter jetzt robust und prüft Bild-MIME-Typen zusätzlich clientseitig.

- **invalid_grant**
  - Ursache: Defekter Private Key, falsche Zeilenumbrüche in `private_key`, oder stark abweichende Serverzeit.
  - Lösung: Service-Account-JSON neu aus GCP exportieren, `private_key` unverändert (inkl. `\n`) übernehmen, Systemzeit/NTP prüfen.

- **`StreamlitSecretNotFoundError` / `TOMLDecodeError` beim App-Start**
  - Ursache: Syntaxfehler in `.streamlit/secrets.toml` (z. B. `key =` ohne Wert, fehlerhafte Inline-Tabelle, ungültige Quotes).
  - Lösung: TOML prüfen, z. B. mit `python -c "import tomllib, pathlib; tomllib.loads(pathlib.Path('.streamlit/secrets.toml').read_text(encoding='utf-8'))"`; fehlerhafte Zeile korrigieren.
