# Changelog

## Unreleased

### Added
- Optionalen Admin-Healthcheck in `app.py` ergänzt: Sidebar-Button „Google-Verbindung prüfen / Check Google connection“ testet Drive-Listing und Calendar-Event-Lesen mit verständlichen DE/EN-Fehlermeldungen.
- README um eine exakte Setup-Checkliste für Freigaben erweitert (Service-Account als Editor auf Drive-Ordner, Kalenderfreigabe für `calendar_id`) sowie um die Beschreibung des Laufzeit-Healthchecks.
- `packages.txt` im Repository-Root ergänzt, damit Debian-basierte Deployments die nativen Build-Abhängigkeiten für `dlib` installieren können (`cmake`, `build-essential`, BLAS/LAPACK- sowie JPEG/PNG/Zlib-Header).
- `requirements-cv.txt` als optionale Zusatzabhängigkeit für Gesichtserkennung eingeführt, um CV-Features bei knappen Cloud-Ressourcen gezielt deaktivieren zu können.
- README um Deployment-Hinweise für stabile Cloud-Builds (optionaler CV-Stack, Umgang mit RAM-/Zeitlimits) erweitert.

### Changed
- Zentrale Secret-Validierung in `config.py` ergänzt: Pflichtschema mit `[gcp_service_account]` und `[gcp]` wird beim App-Start geprüft und einheitlich bereitgestellt.
- Google-Integrationen (`calendar.py`, `storage.py`, `stammdaten.py`, `photo.py`, `services/google_clients.py`) auf zentrale Konfigurationsquelle umgestellt.
- README um ein vollständiges Beispiel für das finale `secrets.toml` erweitert.
- `requirements.txt` auf deployment-sichere Kernabhängigkeiten fokussiert (Streamlit, Firebase, OpenAI, Google API Client, Dokument-Bibliotheken, Pillow).
- `requirements-cv.txt` für lokale/full Installationen präzisiert und CV-Pakete kompatibel gepinnt (`face-recognition==1.3.0`, `dlib==19.24.6`).
- Admin-Fotobereich in `app.py` zeigt jetzt zweisprachig den Status der Gesichtserkennung (aktiv/deaktiviert), damit das Upload-Verhalten transparent ist.
- README-Installationsanleitung in zwei Modi aufgeteilt: Core (Cloud) und CV (lokal/full).

### Fixed
- Frühe UI-Fehlermeldungen (DE/EN) für fehlende oder unvollständige Secrets hinzugefügt; die App stoppt kontrolliert mit konkretem Hinweis auf `README.md`.
- App-Start robuster gemacht: fehlendes `firebase-admin` führt nicht mehr zu einem Import-Abbruch in `stammdaten.py`/`storage.py`.
- Typing-Hints ergänzt und Fehlerbehandlung rund um Firebase-Initialisierung verbessert.
- `face-recognition` als optionale Laufzeitabhängigkeit umgesetzt: Foto-Upload funktioniert auch ohne CV-Stack, inklusive Hinweis in der UI, wenn Gesichtserkennung deaktiviert ist.

