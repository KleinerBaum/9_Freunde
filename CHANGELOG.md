# Changelog

## Unreleased

### Added
- Foto-Freigabe-Workflow erweitert: neuer Schema-Tab `photo_meta` (konfigurierbar über `gcp.photo_meta_tab`, Default `photo_meta`) inkl. lokalem Fallback `data/photo_meta.json`.
- Admin-Bereich **Fotos** um Statusverwaltung pro Datei erweitert (`draft`/`published`/`archived`).

### Changed
- Google-Sheets-Fehlerbehandlung für Abholberechtigungen robuster gemacht: fehlt der konfigurierte Tab `pickup_authorizations`, wird er automatisch angelegt und die Header-Zeile initialisiert, statt mit `HttpError 400` abzustürzen; zusätzlich klare DE/EN-Hinweise für 400-Range-Parse-Fehler und 404-Sheet-ID-Fehler ergänzt.
- Eltern sehen in **Fotos** nur noch Bilder mit Status `published`; bestehende Bilder ohne Metadaten bleiben kompatibel und werden als `draft` behandelt.
- Foto-Upload legt jetzt automatisch Metadaten (`file_id`, `child_id`, `status`, `uploaded_at`, `uploaded_by`) an; Consent/Verpixelungs-Download bleibt unverändert.
- Admin-Ansicht **"Stammdaten Sheet"** um Export/Backup-Funktionen erweitert: zentrale Tabs (`children`, `parents`) sowie optionale Tabs (`attendance`, `daily_logs`, `messages`) können jetzt direkt als **CSV** und **JSON** heruntergeladen werden.
- Export-Handling für Google-Sheets-Tabellen robust gemacht: leere Tabs oder fehlende Header führen zu klaren DE/EN-Hinweisen statt Absturz; CSV-Dateien nutzen konsistente Spaltenreihenfolge anhand der Header-Zeile.

### Changed
- Drive-Konsolidierung umgesetzt: `storage.py` (`DriveAgent`) nutzt im Google-Modus jetzt vollständig `services/drive_service.py` als primäre Schicht für `upload/list/download/create_folder`; dadurch greifen konsistente 403/404-Fehlermeldungen und Shared-Drive-Optionen (`supportsAllDrives`, `includeItemsFromAllDrives`) app-weit.
- Vertragsablage und Google-Connection-Check in `app.py` auf die vereinheitlichte Drive-Schicht umgestellt (keine direkte Parallel-Abstraktion mehr für Upload/Listing in Google-Mode).

### Added
- Medikamentengabe-Log als neues Teilschema ergänzt: neuer Google-Sheets-Tab `medications` (konfigurierbar über `gcp.medications_tab`, Header-Auto-Setup) und lokaler Fallback `data/medications.json`.
- Neuer Admin-Menüpunkt **"Medikationen"**: Einträge pro Kind erstellen und anzeigen (`date_time`, `med_name`, `dose`, `given_by`, `notes`, optional `consent_doc_file_id`) inkl. auditierbarer Felder `created_at`/`created_by`.
- Eltern-Menüpunkt **"Medikationen"** (read-only): zeigt nur Einträge des eigenen Kindes.

### Changed
- Soft-Gate für Consent-Link implementiert: Fehlt `consent_doc_file_id`, zeigt die UI einen Hinweis (DE/EN), blockiert das Speichern jedoch nicht.

### Changed
- App-Branding ergänzt: `images/logo.png` wird jetzt als Streamlit-Seitenlogo angezeigt und zusätzlich in generierte DOCX-Dokumente (Berichte/Verträge) eingebettet, sofern die Datei vorhanden ist.
- Abholberechtigte als neues Stammdaten-Teilschema ergänzt: neuer Google-Sheets-Tab `pickup_authorizations` (konfigurierbar über `gcp.pickup_authorizations_tab`, Header-Auto-Setup), lokaler Fallback `data/pickup_authorizations.json`, Admin-CRUD (Add/Edit/Aktiv-Inaktiv) pro Kind sowie Eltern-Read-only-Ansicht aktiver Einträge in „Mein Kind“.

### Added
- Neuer Infos-Bereich für Eltern (`Infos`) mit read-only Darstellung veröffentlichter Seiten aus `content_pages` (Filter: `published=true` und `audience in {parent,both}`) inkl. DE/EN-Sprachumschaltung.
- Neuer Admin-Bereich `Infos verwalten` mit einfachem CRUD-Flow (Liste → Edit/Create → Preview) für Markdown-Inhalte (`title_*`, `body_md_*`, `audience`, `published`).
- Neues Repository `services/content_repo.py` für `content_pages` inkl. Google-Sheets-Header-Auto-Setup und lokalem JSON-Fallback (`data/content_pages.json`).

### Changed
- Konfiguration erweitert um `gcp.content_pages_tab` (Default `content_pages`) und lokalen Pfad `local.content_pages_file`.
- Admin-Stammdatenformulare nutzen jetzt zweispaltige Layouts und Streamlit-Datumspicker für optionale Felder `birthdate`/`start_date` (Speicherung als `YYYY-MM-DD`), damit die neuen Kinderfelder konsistent in UI und Sheets gepflegt werden.

### Added
- Admin-Healthcheck in der Sidebar um **Google Sheets Zugriff / Google Sheets access** erweitert: der Connection-Check prüft jetzt zusätzlich einen minimalen Read auf `children!A1:A1` gegen `gcp.stammdaten_sheet_id`.

### Changed
- Stammdaten-Schema für Google Sheets erweitert: `children` ergänzt um `birthdate`, `start_date`, `group`, `primary_caregiver`, `allergies`, `notes_parent_visible`, `notes_internal`, `pickup_password`, `status` sowie `parents` um `phone2`, `address`, `preferred_language`, `emergency_contact_name`, `emergency_contact_phone`, `notifications_opt_in`; fehlende Header werden automatisch ergänzt.
- Admin-UI „Stammdaten“ erweitert: Neue Kinderfelder sind beim Anlegen/Bearbeiten jetzt direkt pflegbar; Elternansicht „Mein Kind“ zeigt parent-sichtbare Zusatzfelder (z. B. Gruppe, Allergien, Hinweise) an.
- Google-Sheets-Konfiguration erweitert: `gcp.children_tab`, `gcp.parents_tab` und `gcp.consents_tab` sind jetzt optional konfigurierbar (Defaults: `children`, `parents`, `consents`) und werden vom Sheets-Repository statt harter Konstanten verwendet.
- Start-Validierung für konfigurierbare Sheet-Tabnamen ergänzt: leere/ungültige Werte werden mit klaren DE/EN-Fehlermeldungen abgefangen (nicht leer, max. 100 Zeichen, keine verbotenen Zeichen).
- Google-Sheets-Healthcheck nutzt jetzt den konfigurierten Tab `gcp.stammdaten_sheet_tab` (statt hartcodiert `children`) und quotet den A1-Range robust für Tabs mit Leerzeichen/Sonderzeichen, z. B. `'Stammdaten Eltern'!A1:A1`.
- Fehlerdiagnose für den Google-Sheets-Check verbessert (DE/EN): `403` weist jetzt explizit auf fehlende Sheet-Freigabe/Berechtigung für den Service-Account hin, `404` auf eine wahrscheinlich falsche `stammdaten_sheet_id`, andere Fehler werden als generischer Sheets-API-Fehler ausgewiesen.
- Google-Connection-Check nutzt für den Sheets-Aufruf einen kurzen Retry mit exponentiellem Backoff (bis zu 3 Versuche), um transiente API-Fehler robuster abzufangen.
- Google-Konfiguration nutzt für Stammdaten jetzt standardmäßig die Tabelle **Stammdaten_Eltern_2026** (`1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A`), wenn `gcp.stammdaten_sheet_id` nicht gesetzt ist; das Feld bleibt als Override verfügbar.

### Fixed
- Google-Service-Account-Private-Key wird beim Laden jetzt robust normalisiert: äußere Zusatz-Quotes werden entfernt, `\n`-Escapes in echte Zeilenumbrüche umgewandelt und das PEM-Format (`BEGIN/END PRIVATE KEY`) strikt validiert, bevor `from_service_account_info(...)` aufgerufen wird.

### Fixed
- Konfigurationsvalidierung verbessert: TOML-Parsing-Fehler in `.streamlit/secrets.toml` (z. B. `StreamlitSecretNotFoundError`/`TOMLDecodeError`) werden jetzt mit klaren, zweisprachigen UI-Hinweisen (DE/EN) abgefangen, statt einen unklaren Stacktrace im App-Start zu zeigen.

### Added
- Neues Script `tools/smoke_check.py` ergänzt: validiert `secrets.toml`, führt einen Drive-List-Check auf `gcp.drive_contracts_folder_id` aus und liest den `children`-Header aus Google Sheets mit `OK`/`FAIL`-Ausgabe.

### Changed
- `requirements.txt` bereinigt und auf den aktuellen Core-Stack für Streamlit Cloud ausgerichtet (Google Auth-Pakete, `pandas`, `reportlab`, `opencv-python-headless`, keine Firebase/Face-Recognition-Altlasten).
- README um vollständiges Secrets-Schema, explizite Freigabe-Hinweise (Ordner/Sheet mit Service-Account teilen) und Troubleshooting für `403`, `404` und `invalid_grant` erweitert.

### Added
- Neuer Kalender-Service `services/calendar_service.py` mit `add_event(...)` und gecachtem `list_events(...)` (TTL 60s) für Google- und Local-Storage-Modus.

### Changed
- Kalender-UI in `app.py` überarbeitet: Admin-Formular **"Neuer Termin / New event"** (Titel, Datum, Uhrzeit, Beschreibung) erstellt Events über Google Calendar (`gcp.calendar_id` aus `st.secrets`); Eltern sehen eine read-only Liste **"Termine / Events"** mit kommenden Terminen.

### Added
- Neuer Foto-Consent-Flow für Downloads: Eltern können pro Kind in der Foto-Ansicht zwischen `Downloads verpixelt / Downloads pixelated` (Default) und `Downloads unverpixelt / Downloads unpixelated` wechseln; Admins können den Wert zusätzlich im Stammdaten-Edit-Formular überschreiben.
- Neuer Service `services/photos_service.py` mit lokaler Gesichtsverpixelung (`opencv-python-headless`, Haar-Cascade), inkl. `get_download_bytes(image_bytes, consent_mode)` und `pixelate_faces(image_bytes)`.

### Changed
- Foto-Downloads in der Elternansicht respektieren jetzt den gespeicherten Consent (`download_consent` im `children`-Tab, Default `pixelated`) und cachen das Ergebnis per `st.cache_data` anhand von `(file_id, consent_mode)`.
- `services/sheets_repo.py` und `stammdaten.py` normalisieren und persistieren das neue Feld `download_consent` konsistent in Google- und Local-Storage.

### Added
- Neue Admin-Ansicht **"Stammdaten Sheet"** in `app.py`: lädt read-only den konfigurierten Bereich `A1:Z500` aus Google Sheets (`gcp.stammdaten_sheet_id`, optional `gcp.stammdaten_sheet_tab` mit Default `Stammdaten_Eltern_2026`) und zeigt die Daten als `st.dataframe` an; Eltern sehen den Menüpunkt nicht.
- Neuer Service `services/sheets_service.py` mit `read_sheet_values(sheet_id, range_a1)` für generisches Lesen von Sheet-Daten inkl. Validierung und normalisiertem Rückgabeformat.

### Changed
- `config.py` erweitert um `GoogleConfig.stammdaten_sheet_tab` (optional, Default `Stammdaten_Eltern_2026`).

### Changed
- Stammdaten-Backend von Firebase/Firestore auf Google Sheets umgestellt: neuer `services/sheets_repo.py` (Read/Append/Update inkl. Cache + Cache-Invalidierung), `StammdatenManager` liest/schreibt im Google-Modus über Sheets (`children`/`parents`), Parent-Ansicht lädt ausschließlich das zugeordnete Kind über E-Mail, und die Admin-UI unterstützt jetzt zusätzlich das Bearbeiten bestehender Kind-Datensätze.
- Firebase-Initialisierung aus Auth/Storage entfernt und `firebase-admin` aus `requirements.txt` entfernt, damit die App ohne Firebase-Abhängigkeit lauffähig ist.
### Changed
- Zentrale Secrets-Validierung erweitert: Im Google-Modus werden jetzt `gcp.drive_photos_root_folder_id`, `gcp.drive_contracts_folder_id` und `gcp.stammdaten_sheet_id` als Pflicht-Keys geprüft; `gcp.calendar_id` sowie `app.admin_emails`/`auth.admin_emails` bleiben optional (mit Formatprüfung).
- README-Secrets-Vorlage auf die neue GCP-Key-Struktur aktualisiert (inkl. Drive-Ordner-IDs und Stammdaten-Sheet-ID, ohne echte Werte).

### Changed
- Prototyp-Betrieb auf lokale Speicherung umgestellt: neuer `storage.mode` (`local`/`google`) mit Default `local`, lokale Datenablage für Stammdaten, Kalender-Events sowie Dokumente/Fotos unter `./data`.
- `StammdatenManager`, `DriveAgent` und `CalendarAgent` unterstützen jetzt einen lokalen Backend-Modus ohne Google/Firebase-Setup; Google-Integrationen bleiben optional per `storage.mode = "google"` erhalten.
- `app.py` und `README.md` um Hinweise für den lokalen Prototyp-Modus ergänzt (einschließlich minimaler `secrets.toml`-Konfiguration).

### Fixed
- Import-Kollision mit dem Python-Standardmodul `calendar` behoben: `CalendarAgent` wird nun aus `calendar_agent.py` importiert (statt `calendar.py`), damit der App-Start unter Streamlit stabil funktioniert.


### Added
- Admin-Bereich um einen separaten Menüpunkt **"Verträge / Contracts"** erweitert: Upload von PDF/DOCX direkt in den konfigurierten Drive-Ordner `gcp.drive_contracts_folder_id` sowie direkte Dateiliste nach dem Upload.
- Neuer Drive-Service (`services/drive_service.py`) mit Funktionen für Upload, Listing und Download inkl. verständlicher 403/404-Fehlerhinweise (Ordnerfreigabe für Service-Account).

- API-Inventur in `README.md` ergänzt (aktiv genutzt: Drive/Calendar/Firestore, optional: Sheets, ungenutzt: Docs/Forms/Tasks).
- Neues Skript `scripts/check_google_api_inventory.py` ergänzt, das die Inventur ausgibt und optionale Minimal-Healthchecks für Sheets/Docs/Forms/Tasks unterstützt.

### Changed
- OpenAI-Integration in `documents.py` auf die aktuelle Responses API umgestellt (strukturierter JSON-Output, optional `file_search` via `VECTOR_STORE_ID`, optional `web_search_preview`).
- OpenAI-Konfiguration in `config.py` modernisiert: Standardmodell `gpt-4o-mini`, Präzisionsmodus mit `o3-mini`, `reasoning_effort`, Timeouts, Retries und optionale `base_url`/EU-Endpunkt.
- UI-Fehlerbehandlung in `app.py` für Dokumentgenerierung verbessert (klare zweisprachige Hinweise DE/EN bei OpenAI-Fehlern).
- README um neue OpenAI-Konfigurationslogik (Responses API, Modelle, Präzisionsmodus, Timeout/Retry, RAG-Optionen) ergänzt.
- README um konkrete `gcloud services disable`-Kommandos erweitert, um ungenutzte APIs (Docs/Forms/Tasks) bei fehlendem kurzfristigem Bedarf in GCP zu deaktivieren.
- README um optionale Secrets-Sektion `[gcp_optional_apis]` erweitert, damit vorbereitete APIs mit Read-Healthchecks geprüft werden können.

### Added
- Firestore-Prüfskript `scripts/check_firestore_prerequisites.py` ergänzt, das Native-Mode, IAM-Rollen (Least Privilege) und die Nutzung desselben `gcp_service_account` durch `init_firebase()` validiert.
- Optionalen Admin-Healthcheck in `app.py` ergänzt: Sidebar-Button „Google-Verbindung prüfen / Check Google connection“ testet Drive-Listing und Calendar-Event-Lesen mit verständlichen DE/EN-Fehlermeldungen.
- README um eine exakte Setup-Checkliste für Freigaben erweitert (Service-Account als Editor auf Drive-Ordner, Kalenderfreigabe für `calendar_id`) sowie um die Beschreibung des Laufzeit-Healthchecks.
- `packages.txt` im Repository-Root ergänzt, damit Debian-basierte Deployments die nativen Build-Abhängigkeiten für `dlib` installieren können (`cmake`, `build-essential`, BLAS/LAPACK- sowie JPEG/PNG/Zlib-Header).
- `requirements-cv.txt` als optionale Zusatzabhängigkeit für Gesichtserkennung eingeführt, um CV-Features bei knappen Cloud-Ressourcen gezielt deaktivieren zu können.
- README um Deployment-Hinweise für stabile Cloud-Builds (optionaler CV-Stack, Umgang mit RAM-/Zeitlimits) erweitert.

### Changed
- README um den Abschnitt **Firestore prerequisites** ergänzt (Aktivierung im Native Mode, IAM-Rollen für Service Account, `init_firebase()`-Verifikation sowie typische Fehlermeldungen mit Lösung).
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
- Fotoablage-MVP auf child-spezifische Drive-Ordner umgestellt: `services/drive_service.py` ergänzt um `create_folder(...)` und `ensure_child_photo_folder(...)`; `children`-Datensätze verwenden das neue Feld `photo_folder_id` (automatische Anlage + Persistenz in Google Sheets). Admin-Upload speichert in `photos/<child_id>/`, Elternansicht zeigt nur eigene Bilder inkl. Vorschau und Download-Button.
- Face-Recognition-Abhängigkeiten aus dem MVP entfernt (`photo.py` vereinfacht; `requirements-cv.txt` enthält keine CV-Pakete mehr).
