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

## Konfiguration der APIs und Dienste

Vor dem Start der App müssen externe Dienste (Google APIs, OpenAI, Firebase) eingerichtet und Zugangsdaten hinterlegt werden. Diese sensiblen Informationen gehören **nicht** in den Code, sondern in die Konfiguration (z. B. `.streamlit/secrets.toml`).

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
   - `photos_folder_id`: die ID des in Schritt 4 erstellten Drive-Hauptordners für Fotos/Dokumente.
   - `calendar_id`: die Kalender-ID aus Schritt 4 für den Google Kalender der Einrichtung (z. B. die Kalender-E-Mail-Adresse oder die aus URL kopierte ID).

### OpenAI API (Textgenerierung)
Für die KI-gestützte Textgenerierung benötigen Sie einen OpenAI API-Schlüssel:
1. Legen Sie einen Account bei OpenAI an und erzeugen Sie einen persönlichen API Key im Dashboard.
2. Tragen Sie diesen Key in die Konfiguration ein, z. B.:
   ```toml
   [openai]
   api_key = "sk-XXXX...IhrOpenAIKey...XXXX"


## Fehlerbehebung

- **`ModuleNotFoundError: No module named 'firebase_admin'`**  
  Installieren Sie die Abhängigkeiten mit `pip install -r requirements.txt`.
  Falls `firebase-admin` im Laufzeitumfeld nicht verfügbar ist, startet die App jetzt weiterhin, zeigt aber für Stammdaten eine Hinweis-Meldung an, bis Firebase korrekt eingerichtet ist.
- **`ModuleNotFoundError: No module named 'face_recognition'`**  
  Die Gesichtserkennung ist optional. Die App startet und der Foto-Upload funktioniert weiterhin; es erscheint ein Hinweis, dass automatische Gesichtserkennung in dieser Bereitstellung deaktiviert ist.
