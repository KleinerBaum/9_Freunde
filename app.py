## app.py

from __future__ import annotations

import pandas as pd
import streamlit as st
from auth import AuthAgent
from stammdaten import StammdatenManager
from documents import DocumentAgent, DocumentGenerationError
from photo import PhotoAgent
from storage import DriveAgent
from calendar_agent import CalendarAgent
from config import get_app_config, validate_config_or_stop
from services.drive_service import (
    DriveServiceError,
    list_files_in_folder,
    upload_bytes_to_folder,
)
from services.sheets_service import SheetsServiceError, read_sheet_values

# Streamlit page configuration
st.set_page_config(page_title="9 Freunde App", page_icon="🤱", layout="wide")


def _trigger_rerun() -> None:
    """Kompatibler Rerun für verschiedene Streamlit-Versionen."""
    rerun_fn = getattr(st, "rerun", None)
    if callable(rerun_fn):
        rerun_fn()
        return

    experimental_rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(experimental_rerun_fn):
        experimental_rerun_fn()


def _run_google_connection_check(
    drive: DriveAgent,
    calendar_agent: CalendarAgent,
) -> list[tuple[str, bool, str]]:
    """Prüft Drive- und Calendar-Verbindung mit lesenden Testaufrufen."""
    checks: list[tuple[str, bool, str]] = []

    try:
        drive.service.files().list(pageSize=1, fields="files(id,name)").execute()
        checks.append(
            (
                "Google Drive Zugriff / Google Drive access",
                True,
                "Drive-Liste erfolgreich gelesen. / Successfully read drive listing.",
            )
        )
    except Exception as exc:  # pragma: no cover - runtime external dependency
        checks.append(
            (
                "Google Drive Zugriff / Google Drive access",
                False,
                "Drive-Test fehlgeschlagen. Prüfen Sie, ob der Service-Account als "
                "Editor auf dem Zielordner eingetragen ist. "
                f"Fehler: {exc}",
            )
        )

    try:
        calendar_agent.service.events().list(
            calendarId=calendar_agent.calendar_id,
            maxResults=1,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        checks.append(
            (
                "Google Kalender Zugriff / Google Calendar access",
                True,
                "Kalender-Events erfolgreich gelesen. / Successfully read calendar events.",
            )
        )
    except Exception as exc:  # pragma: no cover - runtime external dependency
        checks.append(
            (
                "Google Kalender Zugriff / Google Calendar access",
                False,
                "Kalender-Test fehlgeschlagen. Prüfen Sie, ob die in `calendar_id` "
                "konfigurierte Kalender-ID mit dem Service-Account geteilt ist "
                "(mindestens "
                '"Änderungen an Terminen vornehmen"/"Make changes to events"). '
                f"Fehler: {exc}",
            )
        )

    return checks


# Validate required secrets early and fail with clear UI guidance
validate_config_or_stop()
app_config = get_app_config()

# Initialize agents (ensure single instance per session)
if "auth_agent" not in st.session_state:
    st.session_state.auth_agent = AuthAgent()
if "stammdaten_manager" not in st.session_state:
    st.session_state.stammdaten_manager = StammdatenManager()
if "drive_agent" not in st.session_state:
    st.session_state.drive_agent = DriveAgent()
if "doc_agent" not in st.session_state:
    st.session_state.doc_agent = DocumentAgent()
if "calendar_agent" not in st.session_state:
    st.session_state.calendar_agent = CalendarAgent()
if "photo_agent" not in st.session_state:
    st.session_state.photo_agent = PhotoAgent()

auth = st.session_state.auth_agent
stammdaten_manager = st.session_state.stammdaten_manager
drive_agent = st.session_state.drive_agent
doc_agent = st.session_state.doc_agent
cal_agent = st.session_state.calendar_agent
photo_agent = st.session_state.photo_agent

# Check if user is logged in
if "user" not in st.session_state or st.session_state.get("user") is None:
    # --- Login Screen ---
    st.title("9 Freunde – Login")
    email = st.text_input("E-Mail")
    password = st.text_input("Passwort", type="password")
    if st.button("Anmelden"):
        user_role = auth.login(email, password)
        if user_role:
            # Successful login
            st.session_state.user = email
            st.session_state.role = user_role  # "admin" oder "parent"
            # Wenn Elternrolle: zugehöriges Kind ermitteln
            if user_role == "parent":
                child = stammdaten_manager.get_child_by_parent(email)
                if child:
                    st.session_state.child = child
                else:
                    st.session_state.child = None
            _trigger_rerun()
        else:
            st.error("Login fehlgeschlagen. Bitte E-Mail/Passwort überprüfen.")
else:
    # --- Main Application (Post-Login) ---
    user_role = st.session_state.role
    user_email = st.session_state.user

    # Sidebar menu based on role
    st.sidebar.title("9 Freunde App")
    st.sidebar.write(f"Angemeldet als: `{user_email}`")
    if (
        user_role == "admin"
        and app_config.storage_mode == "google"
        and st.sidebar.button("Google-Verbindung prüfen / Check Google connection")
    ):
        with st.sidebar:
            with st.spinner("Prüfe Drive & Kalender... / Checking drive & calendar..."):
                check_results = _run_google_connection_check(drive_agent, cal_agent)
            for check_title, ok, message in check_results:
                if ok:
                    st.success(f"{check_title}: {message}")
                else:
                    st.error(f"{check_title}: {message}")

    if user_role == "admin":
        menu = st.sidebar.radio(
            "Navigationsmenü",
            (
                "Stammdaten",
                "Stammdaten Sheet",
                "Dokumente",
                "Verträge",
                "Fotos",
                "Kalender",
            ),
            index=0,
        )
    else:
        menu = st.sidebar.radio(
            "Menü", ("Mein Kind", "Dokumente", "Fotos", "Termine"), index=0
        )

    # Logout button at bottom of sidebar
    if st.sidebar.button("Logout"):
        # Clear session state and rerun to show login
        st.session_state.clear()
        _trigger_rerun()

    # Content area:
    st.header(menu)
    if user_role == "admin":
        # ---- Admin: Stammdaten ----
        if menu == "Stammdaten":
            st.subheader("Kinder-Stammdaten verwalten")
            children = stammdaten_manager.get_children()
            # Anzeige der vorhandenen Kinder
            if children:
                for child in children:
                    st.write(
                        f"- **{child.get('name')}** (Eltern: {child.get('parent_email')})"
                    )
            else:
                st.write("*Noch keine Kinder registriert.*")

            # Formular zum Hinzufügen eines neuen Kindes
            st.write("**Neues Kind anlegen:**")
            with st.form(key="new_child_form"):
                name = st.text_input("Name des Kindes")
                parent_email = st.text_input("E-Mail Elternteil")
                submitted = st.form_submit_button("Hinzufügen")
            if submitted:
                if name.strip() == "" or parent_email.strip() == "":
                    st.error("Bitte Name und Eltern-E-Mail angeben.")
                else:
                    try:
                        stammdaten_manager.add_child(name.strip(), parent_email.strip())
                        st.success(
                            f"Kind '{name}' hinzugefügt. / Child '{name}' added."
                        )
                        _trigger_rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Speichern: {e}")
            if children:
                st.write("**Kind bearbeiten / Edit child:**")
                selected_child_name = st.selectbox(
                    "Kind auswählen / Select child",
                    options=[child.get("name", "") for child in children],
                    key="edit_child_select",
                )
                selected_child = next(
                    child
                    for child in children
                    if child.get("name") == selected_child_name
                )
                with st.form(key="edit_child_form"):
                    edit_name = st.text_input(
                        "Name des Kindes / Child name",
                        value=selected_child.get("name", ""),
                    )
                    edit_parent_email = st.text_input(
                        "E-Mail Elternteil / Parent email",
                        value=selected_child.get("parent_email", ""),
                    )
                    edit_submitted = st.form_submit_button(
                        "Änderungen speichern / Save"
                    )
                if edit_submitted:
                    if not edit_name.strip() or not edit_parent_email.strip():
                        st.error(
                            "Bitte Name und Eltern-E-Mail angeben. / Please provide child name and parent email."
                        )
                    else:
                        try:
                            stammdaten_manager.update_child(
                                selected_child.get("id", ""),
                                {
                                    "name": edit_name.strip(),
                                    "parent_email": edit_parent_email.strip(),
                                },
                            )
                            st.success(
                                "Kind wurde aktualisiert. / Child record updated."
                            )
                            _trigger_rerun()
                        except Exception as exc:
                            st.error(f"Speichern fehlgeschlagen / Save failed: {exc}")

            if app_config.storage_mode == "google":
                st.info(
                    "Beim Anlegen eines Kindes wird automatisch ein zugehöriger Drive-Ordner erstellt und verknüpft."
                )
            else:
                st.info(
                    "Beim Anlegen eines Kindes wird lokal ein Prototyp-Ordner erstellt. / "
                    "A local prototype folder is created automatically."
                )

        # ---- Admin: Stammdaten Sheet ----
        elif menu == "Stammdaten Sheet":
            st.subheader(
                "Stammdaten aus Google Sheets (read-only) / Master data from Google Sheets (read-only)"
            )
            if app_config.storage_mode != "google" or app_config.google is None:
                st.info(
                    "Google-Sheets-Ansicht ist nur im Google-Modus verfügbar. / "
                    "Google Sheets view is only available in Google mode."
                )
            else:
                tab_name = app_config.google.stammdaten_sheet_tab
                range_a1 = f"{tab_name}!A1:Z500"
                try:
                    rows = read_sheet_values(
                        sheet_id=app_config.google.stammdaten_sheet_id,
                        range_a1=range_a1,
                    )
                except SheetsServiceError as exc:
                    st.error(
                        "Stammdaten konnten nicht geladen werden. Bitte Konfiguration prüfen. / "
                        "Could not load master data. Please verify configuration."
                    )
                    st.info(str(exc))
                except Exception as exc:
                    st.error(
                        "Fehler beim Laden des Sheets. Prüfen Sie Tabnamen und Berechtigungen. / "
                        "Failed to load sheet. Please verify tab name and permissions."
                    )
                    st.info(str(exc))
                else:
                    if not rows:
                        st.info(
                            "Der ausgewählte Bereich ist leer. / The selected range is empty."
                        )
                    elif not rows[0]:
                        st.info(
                            "Header-Zeile fehlt oder ist leer. / Header row is missing or empty."
                        )
                    else:
                        header = [str(column).strip() for column in rows[0]]
                        data_rows = rows[1:]
                        if not data_rows:
                            st.info(
                                "Es wurden nur Header gefunden, aber keine Datenzeilen. / "
                                "Only headers were found, but no data rows."
                            )
                        else:
                            normalized_rows: list[list[str]] = []
                            for row in data_rows:
                                padded_row = row + [""] * max(0, len(header) - len(row))
                                normalized_rows.append(padded_row[: len(header)])

                            dataframe = pd.DataFrame(normalized_rows, columns=header)
                            st.dataframe(dataframe, use_container_width=True)

        # ---- Admin: Dokumente ----
        elif menu == "Dokumente":
            st.subheader("Dokumente generieren und verwalten")
            children = stammdaten_manager.get_children()
            if not children:
                st.warning("Keine Kinder vorhanden. Bitte zuerst Stammdaten anlegen.")
            else:
                # Formular für Dokumentenerstellung
                child_names = [child.get("name") for child in children]
                selected_name = st.selectbox(
                    "Für welches Kind soll ein Dokument erstellt werden?", child_names
                )
                # find selected child data
                sel_child = next(
                    child for child in children if child.get("name") == selected_name
                )
                doc_notes = st.text_area("Stichpunkte oder Notizen für das Dokument:")
                save_to_drive = st.checkbox(
                    "Dokument im Drive-Ordner des Kindes speichern?"
                )
                if st.button("Dokument erstellen"):
                    with st.spinner("Generiere Dokument mit OpenAI..."):
                        try:
                            doc_bytes, file_name = doc_agent.generate_document(
                                sel_child, doc_notes
                            )
                            st.success("Dokument erstellt: " + file_name)
                            # Download-Button anzeigen
                            st.download_button(
                                "📄 Dokument herunterladen",
                                data=doc_bytes,
                                file_name=file_name,
                            )
                            # Optional: in Drive speichern
                            if save_to_drive:
                                folder_id = sel_child.get("folder_id")
                                if folder_id:
                                    drive_agent.upload_file(
                                        file_name,
                                        doc_bytes,
                                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        folder_id,
                                    )
                                    st.info(
                                        "Dokument wurde im Drive-Ordner gespeichert."
                                    )
                                else:
                                    st.error(
                                        "Kein Drive-Ordner für dieses Kind vorhanden."
                                    )
                        except DocumentGenerationError as e:
                            st.error(
                                "Dokument konnte nicht erstellt werden. Bitte Hinweise prüfen und erneut versuchen."
                            )
                            st.error(
                                "Document could not be generated. Please review the message and retry."
                            )
                            st.info(str(e))
                        except Exception as e:
                            st.error(f"Fehler bei der Dokumentenerstellung: {e}")

                # Optionale Liste vorhandener Dokumente im Drive
                if sel_child.get("folder_id"):
                    docs_list = drive_agent.list_files(
                        sel_child["folder_id"],
                        mime_type_filter="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                    if docs_list:
                        st.write("**Bereits gespeicherte Dokumente für dieses Kind:**")
                        for doc in docs_list:
                            file_name = doc.get("name")
                            file_id = doc.get("id")
                            st.markdown(f"- {file_name} ")
                            st.download_button(
                                "Download",
                                data=drive_agent.download_file(file_id),
                                file_name=file_name,
                                key=file_id,
                            )
                    else:
                        st.write("(Keine gespeicherten Dokumente vorhanden.)")

        # ---- Admin: Verträge ----
        elif menu == "Verträge":
            st.subheader("Vertragsablage / Contract storage")
            if app_config.storage_mode != "google" or app_config.google is None:
                st.info(
                    "Die Vertragsablage ist nur im Google-Modus verfügbar. / "
                    "Contract storage is only available in Google mode."
                )
            else:
                contracts_folder_id = app_config.google.drive_contracts_folder_id
                contract_file = st.file_uploader(
                    "Vertrag hochladen (PDF/DOCX) / Upload contract (PDF/DOCX)",
                    type=["pdf", "docx"],
                    key="contracts_uploader",
                )
                if st.button("In Drive speichern / Save to Drive"):
                    if contract_file is None:
                        st.warning(
                            "Bitte zuerst eine PDF- oder DOCX-Datei auswählen. / "
                            "Please select a PDF or DOCX file first."
                        )
                    else:
                        try:
                            file_id = upload_bytes_to_folder(
                                contracts_folder_id,
                                contract_file.name,
                                contract_file.getvalue(),
                                contract_file.type or "application/octet-stream",
                            )
                            st.success(
                                "Datei in Google Drive gespeichert. / "
                                f"File saved to Google Drive (ID: {file_id})."
                            )
                        except DriveServiceError as exc:
                            st.error(
                                "Upload fehlgeschlagen. Prüfen Sie die Ordnerfreigabe für "
                                "den Service-Account (403/404). / Upload failed. "
                                "Please verify folder sharing with the service account "
                                "(403/404)."
                            )
                            st.info(str(exc))

                st.write("**Vorhandene Vertragsdateien / Existing contract files**")
                try:
                    contract_files = list_files_in_folder(contracts_folder_id)
                    if contract_files:
                        for file_meta in contract_files:
                            st.markdown(
                                f"- **{file_meta.get('name', '-')}** "
                                f"`{file_meta.get('mimeType', '-')}` · "
                                f"{file_meta.get('modifiedTime', '-')}"
                            )
                    else:
                        st.caption(
                            "Noch keine Dateien vorhanden. / No files available yet."
                        )
                except DriveServiceError as exc:
                    st.error(
                        "Dateiliste konnte nicht geladen werden. Stellen Sie sicher, "
                        "dass der Zielordner mit dem Service-Account geteilt ist. / "
                        "Could not load file list. Ensure the folder is shared with "
                        "the service account."
                    )
                    st.info(str(exc))

        # ---- Admin: Fotos ----
        elif menu == "Fotos":
            st.subheader("Kinder-Fotos hochladen und verwalten")
            if photo_agent.face_detection_enabled():
                st.success("Gesichtserkennung aktiv. / Face detection active.")
            else:
                st.info(
                    "Gesichtserkennung deaktiviert (optionale CV-Abhängigkeiten fehlen). / "
                    "Face detection disabled (optional CV dependencies are missing)."
                )
            children = stammdaten_manager.get_children()
            if not children:
                st.warning("Bitte legen Sie zuerst Kinder-Stammdaten an.")
            else:
                child_names = [child.get("name") for child in children]
                selected_name = st.selectbox("Foto hochladen für Kind:", child_names)
                sel_child = next(
                    child for child in children if child.get("name") == selected_name
                )
                image_file = st.file_uploader(
                    "Foto auswählen", type=["jpg", "jpeg", "png"]
                )
                if image_file and st.button("Upload Foto"):
                    try:
                        # Upload via PhotoAgent (speichert in Drive)
                        photo_agent.upload_photo(
                            image_file,
                            sel_child.get("id") if sel_child else None,
                            sel_child.get("folder_id"),
                        )
                        st.success(f"Foto für {selected_name} hochgeladen.")
                        st.image(
                            image_file,
                            caption=f"Hochgeladenes Foto: {image_file.name}",
                            use_column_width=True,
                        )
                    except Exception as e:
                        st.error(f"Fehler beim Foto-Upload: {e}")
                if app_config.storage_mode == "google":
                    st.info(
                        "Fotos werden sicher auf Google Drive gespeichert und nur den berechtigten Eltern angezeigt."
                    )
                else:
                    st.info(
                        "Fotos werden lokal im Prototyp-Speicher abgelegt. / "
                        "Photos are stored in local prototype storage."
                    )

        # ---- Admin: Kalender ----
        elif menu == "Kalender":
            st.subheader("Termine verwalten")
            # Formular für neuen Termin
            title = st.text_input("Titel des Termins")
            date = st.date_input("Datum")
            all_day = st.checkbox("Ganztägig?")
            time = None
            if not all_day:
                time = st.time_input("Uhrzeit (Start)", value=None)
            description = st.text_area("Beschreibung/Details")
            if st.button("Termin hinzufügen"):
                if not title:
                    st.error("Bitte einen Termin-Titel eingeben.")
                else:
                    try:
                        cal_agent.add_event(
                            title, date, time, description, all_day=all_day
                        )
                        st.success("Termin wurde hinzugefügt.")
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Termins: {e}")
            # Kommende Termine anzeigen
            try:
                events = cal_agent.list_events(max_results=10)
            except Exception as e:
                events = []
                st.error(f"Fehler beim Laden der Termine: {e}")
            if events:
                st.write("**Bevorstehende Termine:**")
                for ev in events:
                    st.write(f"- {ev}")
            else:
                st.write("Keine anstehenden Termine vorhanden.")

    else:
        # ---- Parent/Eltern View ----
        child = stammdaten_manager.get_child_by_parent(user_email)
        st.session_state.child = child
        if menu == "Mein Kind":
            st.subheader("Mein Kind - Übersicht")
            if child:
                st.write(f"**Name:** {child.get('name')}")
                # Weitere Infos könnten hier angezeigt werden (z.B. Geburtstag, Notizen)
            else:
                st.write("Keine Kinderdaten gefunden.")
        elif menu == "Dokumente":
            st.subheader("Dokumente Ihres Kindes")
            if child and child.get("folder_id"):
                docs_list = drive_agent.list_files(
                    child["folder_id"],
                    mime_type_filter="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                if docs_list:
                    for doc in docs_list:
                        file_name = doc.get("name")
                        file_id = doc.get("id")
                        st.markdown(f"**{file_name}** ")
                        st.download_button(
                            "Herunterladen",
                            data=drive_agent.download_file(file_id),
                            file_name=file_name,
                            key=file_id,
                        )
                else:
                    st.write("Keine Dokumente vorhanden.")
            else:
                st.write("Keine Dokumente verfügbar.")
        elif menu == "Fotos":
            st.subheader("Fotos")
            if child and child.get("folder_id"):
                photos = drive_agent.list_files(
                    child["folder_id"], mime_type_filter="image/"
                )
                if photos:
                    for photo in photos:
                        img_bytes = drive_agent.download_file(photo["id"])
                        st.image(
                            img_bytes, caption=photo.get("name"), use_column_width=True
                        )
                else:
                    st.write("Keine Fotos vorhanden.")
            else:
                st.write("Keine Fotos verfügbar.")
        elif menu == "Termine":
            st.subheader("Anstehende Termine")
            try:
                events = cal_agent.list_events(max_results=10)
            except Exception as e:
                events = []
                st.error(f"Fehler beim Laden der Termine: {e}")
            if events:
                for ev in events:
                    st.write(f"- {ev}")
            else:
                st.write("Zurzeit sind keine Termine eingetragen.")
