# Changelog

## Unreleased

### Changed
- Admin-Hauptnavigation bereinigt: Der separate Menüpunkt **„Kalender / Calendar“** wurde entfernt. Die Funktion **„Neuer Termin / New event“** ist jetzt im Dashboard direkt unter **„Bevorstehende Termine / Upcoming events“** integriert; die Kalenderansicht wird dort ohne Dropdown angezeigt.
- Kalendererstellung erweitert: Beim Anlegen eines Termins können Admins hinterlegte User-E-Mails auswählen. Diese werden als `attendees` an Google Calendar übergeben; bei vorhandenen Empfängern wird `sendUpdates="all"` genutzt, damit Einladungen per Mail versendet werden.

- OneDrive-Medienfluss erweitert: optionale Microsoft-Graph-Authentifizierung (MSAL über `[onedrive].client_id/client_secret/tenant_id`), Verzeichnisprüfung für `Documents/9 Freunde`, Bild-Listing/Upload/Download über Graph-Endpoints und direkte Gallery-Einbindung mit Byte-Preview-Caching.
- OneDrive-Karte im Foto-Bereich angepasst: standardmäßig wird nur der Link-Button angezeigt; die iFrame-Einbettung ist optional per Toggle **„Einbettung anzeigen / Show embed“**. Klarer Hinweistext für blockierte iFrames ergänzt, und die Karte wird bei `[onedrive].enabled = false` vollständig ausgeblendet, ohne Upload-/Galerie-Logik im Google-Modus zu beeinflussen.
- Admin-UI überarbeitet: Branding kompakter (Logo + Herzgrafik in einer Zeile), Dashboard-Header-Doppelung entfernt und durch personalisierte Begrüßung ersetzt; Dashboard sowie Bereich **Dokumente & Verträge** wurden mit Spaltenlayout, gruppierten Karten und zusätzlichen Expandern deutlich verdichtet.
- `DocumentAgent._generate_with_retry()` behandelt OpenAI-Fehler jetzt differenziert (Authentifizierung/Berechtigung, ungültige Anfrage, Tool-nicht-erlaubt, Timeout/Rate-Limit) mit klaren DE/EN-Fehlermeldungen; bei `web_search_preview`-Toolfehlern wird einmalig automatisch ohne Web-Tool erneut versucht. Interne Logs enthalten nur nicht-sensitive Diagnosedaten ohne Prompt-/PII-Dump oder Secrets.
- Google-Healthcheck in `app.py` erweitert: getrennte Drive-Checks für Foto-/Vertragsordner mit expliziter Anzeige der betroffenen Ordner-ID und differenzierten 403/404-Hinweisen; Kalender-Checks zeigen jetzt zusätzlich verwendete `calendar_id` sowie erforderliche Freigabe für `gcp_service_account.client_email`.
- `DriveServiceError` und `CalendarServiceError` transportieren jetzt strukturierte Fehlerdetails (`status_code`, `cause`) für präzisere UI-Hinweise bei Google-API-Fehlern.
- Foto-Fehlerbanner zeigen bei Drive-Fehlern jetzt zusätzlich strukturierte Details aus `DriveServiceError` (`status_code`, `cause`), damit Upload-/Listen-Fehler leichter mit Healthchecks korreliert werden können.

### Added
- Neue UI-/Domain-Bausteine eingeführt: `ui/layout.py`, `ui/state_keys.py`, `ui/media_gallery.py` und `domain/models.py` für eine schlanke Trennung von Darstellung und Modellen ohne Änderungen an `services/`.
- Foto-Galerie auf das neue `MediaItem`-Domain-Modell und die wiederverwendbare Galerie-Komponente umgestellt (Filter, Pagination, Vorschau, Auswahlzustand über zentrale UI-Keys).
- OneDrive-Integration im Foto-Bereich ergänzt: Admin- und Elternansicht zeigen jetzt einen eingebetteten OneDrive-Ordner plus Direktlink, damit alle Nutzer (nach OneDrive-Passwort) Medien hoch- und herunterladen können; der Link ist optional über `[onedrive].shared_folder_url` konfigurierbar.

- Admin-Bereich **Dokumente** erweitert: Berichte und Betreuungsverträge unterstützen jetzt eine explizite Sprachwahl (`de`/`en`, Default `de`) sowie einen optionalen Entwurfsstatus (`ENTWURF / DRAFT`) per Checkbox inklusive Dateinamen-Markierung.
- Admin-UI in **„Stammdaten“** um den Expander **„Anmeldung importieren (PDF) / Import registration (PDF)“** erweitert: Download der Blanko-PDF-Vorlage aus `assets/forms/`, Upload eines ausgefüllten Formulars, Parsing via `registration_form_service`, strukturierte Vorschau (Kind/Eltern/Abholberechtigte/Einwilligungen), Validierungsanzeige mit Speicher-Blockade bei Fehlern sowie Speichern in bestehende Stammdaten-Upsert-Flows inkl. Success-Feedback mit `child_id` und direkter Vorauswahl für die Bearbeitung.
- Neues Modul `services/registration_form_service.py` ergänzt: `extract_acroform_fields(pdf_bytes)` liest ACROForm-Felder via `PyPDF2.PdfReader(...).get_fields()`, normalisiert Strings/Checkboxen und bricht mit klaren Fehlern bei fehlenden Feldern oder fehlender/nicht unterstützter `meta__schema_version` ab.
- Neues Dataclass-Modell `RegistrationPayload` plus Parser `parse_registration_payload(fields)` ergänzt, das strukturierte Bereiche (`child`, `parents`, `pickup_authorizations`, `consents`, `meta`, `errors`) liefert und Pflichtfeld-Validierung ohne Schreiboperationen durchführt.
- Unit-Tests `tests/test_registration_form_service.py` ergänzt (Normalisierung, Schema-Validierung, Fehlerpfade, Pflichtfeldprüfung).

- Admin-Bereich **Fotos & Medien** als Gallery-Pattern umgestellt: neue Tabs **Galerie / Gallery**, **Upload** und **Status**.
- Galerie nutzt jetzt klickbare Thumbnail-Kacheln (`st-clickable-images`) mit Pagination (24 Medien/Seite), Preview und Download-Aktion für Bilder und Videos.
- Upload in **Fotos & Medien** akzeptiert zusätzlich Videoformate (`mp4`, `mov`, `webm`) und legt Metadaten weiterhin mit Status `draft` ab.

### Changed
- Admin-Bereich **"Stammdaten"**: Reihenfolge der beiden Tabellen getauscht – die Auswahl-/Bearbeitungstabelle (**"Kind bearbeiten / Edit child"**) steht nun oberhalb der reinen **Kinder-Übersicht / Children overview**.
- Fotoablage auf zentralen Drive-Ordner vereinfacht: Child-spezifische Fotoordner werden nicht mehr vorausgesetzt. Admin-Upload, Galerie, Statusverwaltung und Elternansicht lesen/schreiben jetzt über `gcp.drive_photos_root_folder_id`; die Kind-Auswahl filtert Medien dabei über `photo_meta.child_id`.
- Admin-Bereich **Dokumente & Verträge**: Die Auswahl **„Vertragssprache / Contract language“** für Betreuungsverträge wurde auf eine erweiterte Liste in Düsseldorf realistischer Vertragssprachen ausgebaut (u. a. DE/EN/TR/AR/RU/UK/PL/RO/BG/EL/IT/ES/FR/NL/FA/KU/SQ/SR/HR/BS). Für nicht explizit unterstützte Sprachen bleibt die Vertragsgenerierung weiterhin auf DE/EN-Fallback.
- Sidebar um einen kompakten Sprachumschalter **„Sprache / Language“** oberhalb von **„Angemeldet als / Logged in as“** erweitert; bei DE/EN-Auswahl werden kombinierte UI-Labels im Format `DE / EN` sprachspezifisch ohne verbleibendes `/` gerendert.
- Sprachumschaltung erweitert: Die gewählte Sprache wird jetzt auch auf die Toggle-Einträge selbst sowie app-weit auf weitere UI-Texte (z. B. Header, Subheader, Hinweise, Navigations- und Formularlabels im Format `DE / EN`) angewendet.
- Admin-Ansicht umgestellt: **"Admin-Übersicht / Admin overview"** wurde in den Bereich **"Dashboard / Dashboard"** integriert. Der bisherige Hinweistext wurde durch eine neue Dashboard-Beschreibung ersetzt.
- Admin-Dashboard-Layout angepasst: Die Expander **„Neues Kind anlegen / Add child“** und **„Anmeldung importieren (PDF) / Import registration (PDF)“** wurden aus **„Stammdaten“** in die **Admin-Übersicht / Admin overview** verschoben und dort oberhalb der **Kinder-Übersicht / Children overview** positioniert.
- Bereich **"Bevorstehende Termine / Upcoming events"** aus **"Kalender / Calendar"** in das **Admin-Dashboard** verschoben, damit die Terminübersicht direkt in der **Admin-Übersicht / Admin overview** sichtbar ist.
- Admin-Dashboard zeigt jetzt unterhalb der Terminliste eine eingebettete **Kalenderansicht / Calendar view**; die bisherige Dashboard-Info-Textbox wurde entfernt.
- Admin-Bereich **"Kalender / Calendar"** fokussiert nun auf **"Neuer Termin / New event"** ohne zusätzliche eingebettete Kalenderansicht.
- Styling auf Theme-first umgestellt: neue Streamlit-Theme-Konfiguration in `.streamlit/config.toml` (u. a. `primaryColor`, `secondaryBackgroundColor`, `baseRadius`, `buttonRadius`, `showSidebarBorder`) statt umfangreicher Inline-CSS-Overrides.
- UI-Abschnitte als Cards vereinheitlicht: Admin-**Dashboard**, Admin-**Übersicht** und Eltern-**Mein Kind** werden jetzt in `st.container(border=True)` gerendert.
- Globales Hintergrund-Styling reduziert auf ein minimales CSS-Overlay für `images/Hintergrund.png`, damit Theme-Farben und Radius-Einstellungen konsistent greifen.
- Streamlit-Form-UX konsolidiert: In den Admin-Bereichen **Stammdaten (PDF-Import)**, **Verträge** und **Fotos** werden Upload-/Speicheraktionen jetzt konsequent über `st.form(..., border=True)` mit genau einem Submit ausgelöst. Dadurch entstehen keine zusätzlichen Reruns durch separate `st.button`-Klicks, und die Abläufe folgen dem Muster „Widgets sammeln → ein Submit“.
- Admin-Navigation modernisiert: Die Sidebar enthält jetzt ausschließlich Hauptbereiche (**Dashboard**, **Stammdaten & Infos**, **Fotos & Medien**, **Dokumente & Verträge**, **Kalender**, **System / Healthchecks**). Der Google-Integrationscheck wurde in den neuen System-Bereich verlagert.
- Schema-v1 Mapping für Registrierungsdaten idempotent ausgebaut: `child__child_id` steuert Update-Pfade, ansonsten wird eine neue `uuid4` vergeben; `children` enthält jetzt zusätzlich optionale Gesundheits-/Betreuungsfelder (`doctor_*`, `health_insurance`, `medication_regular`, `dietary`, `languages_at_home`, `sleep_habits`, `care_notes_optional`), `parents`-Datensätze werden nur bei vorhandener E-Mail erzeugt (inkl. `parent_id`), `pickup_authorizations` berücksichtigt `pa{i}__enabled` + `pa{i}__name`, und das `consents`-Schema schreibt explizite Bool-Felder plus `photo_download`-Status. Außerdem wurde Logging für Mapping-Eingaben um PII-Redaction ergänzt.
- Mapping-Schicht für Schema-v1 erweitert: neue zentrale Funktion `map_schema_v1_payload_to_tab_records()` mappt Payloads vollständig auf `children`, `parents`, `pickup_authorizations` und `consents` (inkl. `parent2__*`, `pa1..pa4__*`, `consent__privacy_notice_ack`, `consent__excursions`, `consent__emergency_treatment`, `consent__whatsapp_group`, `sign__*`, `meta__*`). `pa1..pa4` werden als geordnete Liste von Abholberechtigungen serialisiert; pro Präfix entsteht ein Datensatz bei befüllten Kernfeldern. Unit-Tests für Prioritäten und Defaults ergänzt.
- Schema-v1/Pflichtspalten konsolidiert: `CONSENTS_REQUIRED_COLUMNS` und ein zentrales `REQUIRED_COLUMNS_BY_SHEET` wurden im Google-Sheets-Repository ergänzt; das lokale ODS-Repository verwendet nun exakt dieselbe Feldabdeckung und Reihenfolge. README-Mapping für `pa*`, `consent__*`, `sign__*` und `meta__*` präzisiert (inkl. explizitem **out of scope**-Status nicht-produktiv unterstützter Felder).
- Stammdaten-Schema (children) erweitert: neue optionale Felder `doctor_name`, `doctor_phone`, `health_insurance`, `medication_regular`, `dietary`, `languages_at_home`, `sleep_habits`, `care_notes_optional` werden in Google Sheets und lokalem ODS automatisch als Header ergänzt.
- Mapping für Elternkontakt vereinheitlicht: Wenn `parent1__email` im Kinderdatensatz gesetzt ist, wird `children.parent_email` automatisch darauf synchronisiert.
- Foto-Download-Consent harmonisiert: `children.download_consent` wird aus den Consent-Checkboxen (`consent__photo_download_pixelated`, `consent__photo_download_unpixelated`, `consent__photo_download_denied`) abgeleitet; Priorität ist `denied` > `unpixelated` > `pixelated`.
- Eltern-/Admin-UI für Foto-Consent unterstützt jetzt zusätzlich den Modus `denied`; bei `denied` wird der Foto-Download in der Elternansicht deaktiviert.
- Stammdaten-Workflow vereinfacht: Die Kinder-Übersicht enthält jetzt links eine Checkbox-Spalte **„Auswahl / Select“**; ausgewählte Kinder werden darunter parallel (nebeneinander) editierbar angezeigt. Der Export/Backup-Block (CSV/JSON für `children` und `parents`) wurde in diesen Bereich integriert, und der frühere Tab **„Stammdaten Sheet“** wurde entfernt.
- Admin-UX in **„Stammdaten & Infos“** angepasst: Der separate Unterbereich **„Medikationen“** wurde entfernt und als neuer, standardmäßig eingeklappter Abschnitt **„Medikationen“** direkt in **„Stammdaten“** unterhalb von **„Abholberechtigte / Pickup authorizations“** integriert.
- Kalender-Secrets robuster gelesen: `services/calendar_service._get_calendar_id()` akzeptiert jetzt allgemein Mapping-kompatible `gcp`-Sektionen (nicht nur `dict`) und trimmt `calendar_id` weiterhin, inkl. unverändertem Fehlertext bei fehlendem Wert.
- Admin-Unterbereich **„Infos verwalten“** aus der App entfernt: Unter **„Stammdaten & Infos“** sind jetzt nur noch **„Übersicht“**, **„Stammdaten“**, **„Stammdaten Sheet“** und **„Medikationen“** verfügbar.
- Admin-Bereich **Dokumente** erweitert: Für neu erstellte Berichte/Verträge/Abrechnungen sowie bereits gespeicherte DOCX-Dateien wird nun vor dem Download eine aufklappbare Textvorschau angezeigt (DE/EN-UI).
- Drive-Fehlerbehandlung im Admin-Flow verbessert: `StammdatenManager.add_child()` zeigt beim fehlgeschlagenen Ordner-Anlegen jetzt sichtbare DE/EN-UI-Fehler inkl. Detailhinweis; Foto-Upload/Foto-Ordner-Load unterscheiden `DriveServiceError` gezielt (inkl. 403/404-Hinweis) und geben zusätzlich Troubleshooting-Tipps mit `child_id` aus.
- Google-Fotoordner-Konfiguration vereinheitlicht: `StammdatenManager.add_child()` nutzt jetzt explizit `gcp.drive_photos_root_folder_id` (statt Alias), und der Admin-Hinweis in **Fotos** beschreibt neutral den konfigurierten Drive-Hauptordner mit Unterordnern pro Kind (DE/EN), ohne irreführenden Pseudo-Pfad `photos/<child_id>/`.
- UI/Design-Refresh: Alle dunklen Elemente (Sidebar, Buttons, Form-Controls) auf eine kontraststarke und stylische Palette umgestellt; Inputs sind jetzt hell mit klaren Hover-/Fokuszuständen, wodurch Text in Login- und Formularbereichen deutlich besser lesbar ist (DE/EN-UX-Verbesserung).
- Stammdaten: Elternfelder `emergency_contact_name`, `emergency_contact_phone`, `preferred_language` und `notifications_opt_in` sind jetzt vollständig in der UI angebunden (Admin-Formulare Add/Edit mit Upsert nach `parents`, Elternansicht "Mein Kind" read-only mit DE/EN-Labels).
- Admin-Bereich **Stammdaten** zeigt jetzt eine sortierbare **Kinder-Übersicht** als Tabelle (Name, Parent Email, Group, Birthdate, Folder Status mit `✅ Ready`/`⚠️ Missing`) statt nur einer einfachen Liste; Elternansicht **Mein Kind** zeigt Name/Geburtsdatum/Gruppe jetzt konsistent mit Fallback `-` sowie die bevorzugte Sprache aus den Elternstammdaten.
- Stammdaten-UX überarbeitet: Der Bearbeitungsbereich zeigt Felder erst nach expliziter Kind-Auswahl (`selectbox` ohne Vorauswahl); außerdem sind **„Neues Kind anlegen / Add child“** und **„Abholberechtigte / Pickup authorizations“** per Default eingeklappt, um die Seite übersichtlicher zu halten.
- Landing-Page-Branding erweitert: `images/Herz.png` wird als zentriertes oberstes Element gerendert, und `images/Hintergrund.png` dient app-weit als fixes Hintergrundbild.
- Admin-Navigation erweitert: Unter **„Stammdaten & Infos“** gibt es jetzt den neuen Bereich **„Übersicht“** mit einer tabellarischen Kinder-Gesamtübersicht (Name, Eltern-E-Mail, Fotoanzahl, letzte Aktivität, `photo_folder_id`, `folder_id`, Ordnerstatus).
- Admin-Fotoverwaltung verbessert: Nach Auswahl eines Kindes wird im Bereich **„Fotos“** ein direkter Link zum jeweiligen Google-Drive-Fotoordner eingeblendet (`📂 Ordner auf Google Drive öffnen / Open folder on Google Drive`).
- Admin-Fotoverwaltung erweitert: Im Bereich **„Fotos → Foto-Status verwalten / Manage photo status“** gibt es jetzt zusätzlich einen Link auf den zentralen Google-Drive-Foto-Hauptordner (`🗂️ Gesamtordner auf Google Drive öffnen / Open all-children folder on Google Drive`) sowie eine DE/EN-Vorschau-Liste mit Bildern aus allen Kinder-Ordnern.

- Kalenderbereich (Admin **Kalender** und Eltern **Termine / Events**) zeigt jetzt zusätzlich eine eingebettete Google-Kalender-Ansicht per IFrame (DE/EN UI bleibt erhalten).
- Kalender-Embed in `app.py` auf konfigurationsbasierte URL-Erzeugung umgestellt: `gcp.calendar_id` wird URL-encodet in die Google-Embed-URL eingebettet (statt statischer `src`-ID).
- Kalender-UI priorisiert die API-Terminliste (`list_events`) und zeigt den IFrame nur noch optional über **„Kalender einbetten / Show embedded calendar“** sowie einen direkten Browser-Link.
- Fehlende `gcp.calendar_id` wird in Kalender-Ansichten mit klarer DE/EN-Fehlermeldung ausgewiesen (analog zu bestehenden Konfigurationschecks).
- Admin-Ansicht **"Stammdaten Sheet"** zeigt im Export/Backup-Bereich nur noch die Tabs `children` und `parents`; optionale Exportkarten für `attendance`, `daily_logs` und `messages` wurden entfernt.
- Google-Ordnerkonfiguration robuster gemacht: `gcp.drive_photos_root_folder_id` und `gcp.drive_contracts_folder_id` akzeptieren jetzt zusätzlich vollständige Drive-Ordner-URLs (`.../folders/<ID>` oder `...?id=<ID>`); die App extrahiert automatisch die Ordner-ID und liefert bei ungültigen URLs eine klare Fehlermeldung.
- Google-Verbindungscheck in `app.py` prüft `gcp.calendar_id` jetzt explizit vor dem API-Aufruf und zeigt bei fehlender Kalender-ID eine konkrete DE/EN-Quick-Fix-Meldung mit Zielpfad `Settings → Secrets → [gcp].calendar_id`.
- `tools/smoke_check.py` weist `gcp.calendar_id` jetzt als optionalen, aber geprüften Key aus (`[WARN]` statt Fehler bei Fehlen) mit verständlichem Quick-Fix-Hinweis.
- README-Fehlerbehebung um einen Quick-Fix-Abschnitt für fehlendes `gcp.calendar_id` ergänzt.
- Drive-Foto-Listing robuster gemacht: `services/drive_service.list_files_in_folder()` normalisiert MIME-Filter (z. B. `image/` → `image`) und filtert Ergebnisse zusätzlich defensiv in Python, sodass hochgeladene JPG/PNG-Dateien in Admin- und Eltern-Fotoansichten zuverlässig erscheinen.

### Added
- Admin-Bereich **Dokumente** um zwei neue Stammdaten-basierte Vorlagen erweitert: **Betreuungsvertrag / Childcare contract** und **Lebensmittelpauschale-Abrechnung / Food allowance invoice** mit Download-Option.

### Changed
- Admin-Navigation logisch gebündelt: Sidebar-Menüpunkte **„Stammdaten“, „Stammdaten Sheet“, „Medikationen“** (inkl. damals vorhandenem Info-Unterbereich) wurden unter **„Stammdaten & Infos“** zusammengeführt; **„Dokumente“** und **„Verträge“** wurden unter **„Dokumente & Verträge“** zusammengeführt. Die Unterbereiche sind als horizontaler Umschalter (`Bereich / Section`) verfügbar.

- `DocumentAgent` erzeugt neue DOCX-Vorlagen mit eingebettetem Logo (`images/logo.png`), aktuellem Erstellungsdatum und vorausgefüllten Kinddaten; die Abrechnung unterstützt einen frei wählbaren Zeitraum inklusive validierter Datumsgrenzen.
- Admin-Bereich **Fotos → Foto-Status verwalten / Manage photo status** zeigt pro Datei jetzt eine eingebettete DE/EN-Bildvorschau in einer aufklappbaren Detailansicht; fehlerhafte Downloads werden pro Foto abgefangen, damit die Statuspflege der übrigen Einträge weiter funktioniert.


### Changed
- Stammdaten-Lokalspeicher von mehreren JSON-Dateien auf eine zentrale ODS-Arbeitsmappe umgestellt (`data/stammdaten.ods`); lokale Reads/Writes für `children`, `parents`, `consents`, `pickup_authorizations`, `medications` und `photo_meta` laufen jetzt über `odfpy` + `pandas` mit Header-Selbstheilung.
- `StammdatenManager` migriert beim ersten Start bestehende Legacy-JSON-Dateien automatisch in die ODS-Datei, sodass vorhandene lokale Daten erhalten bleiben.
- Stammdaten-UI verwendet bei Kind-/Abholberechtigten-Auswahl jetzt Datensatzobjekte statt reiner Namen (`selectbox(..., options=<records>, format_func=...)`), damit gleichnamige Einträge eindeutig bearbeitet werden können.
- Kind-Anlage im `StammdatenManager` kann zusätzliche Felder jetzt direkt in einem Schritt speichern (`add_child(..., extra_data=...)`), wodurch der bisherige direkte Add-then-Update-Flow in der Admin-UI entfällt.

### Added
- Local-Storage-Parität für Stammdaten erweitert: neue lokale Dateien `data/parents.json` und `data/consents.json` werden über `LocalConfig` bereitgestellt und im `StammdatenManager` initialisiert.

### Changed
- `StammdatenManager.delete_child()` unterstützt im Google-Modus jetzt echtes Löschen über Google Sheets (`deleteDimension` auf der gefundenen Kinder-Zeile) statt nur einer Warnung; damit sind CRUD-Operationen für Kinder in beiden Speicher-Modi konsistenter.


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
- Neuer Admin-Bereich für Info-Seiten mit einfachem CRUD-Flow (Liste → Edit/Create → Preview) für Markdown-Inhalte (`title_*`, `body_md_*`, `audience`, `published`).
- Neues Repository `services/content_repo.py` für `content_pages` inkl. Google-Sheets-Header-Auto-Setup und lokalem JSON-Fallback (`data/content_pages.json`).

### Changed
- Konfiguration erweitert um `gcp.content_pages_tab` (Default `content_pages`) und lokalen Pfad `local.content_pages_file`.
- Admin-Stammdatenformulare nutzen jetzt zweispaltige Layouts und Streamlit-Datumspicker für optionale Felder `birthdate`/`start_date` (Speicherung als `YYYY-MM-DD`), damit die neuen Kinderfelder konsistent in UI und Sheets gepflegt werden.

### Added
- Admin-Healthcheck in der Sidebar um **Google Sheets Zugriff / Google Sheets access** erweitert: der Connection-Check prüft jetzt zusätzlich einen minimalen Read auf `children!A1:A1` gegen `gcp.stammdaten_sheet_id`.
- UI-Bereinigung: Mehrere reine Hinweis-Textboxen in den Admin-Bereichen **Übersicht**, **Stammdaten**, **Stammdaten Sheet** (leerem Bereich) und **Fotos** wurden entfernt, um die Ansichten kompakter zu halten.

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
