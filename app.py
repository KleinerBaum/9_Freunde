## app.py

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st
from googleapiclient.errors import HttpError
from auth import AuthAgent
from stammdaten import StammdatenManager
from documents import DocumentAgent, DocumentGenerationError
from photo import PhotoAgent
from storage import DriveAgent
from config import get_app_config, validate_config_or_stop
from services.calendar_service import (
    CalendarServiceError,
    _get_calendar_client,
    _get_calendar_id,
    add_event,
    list_events,
)
from services.drive_service import (
    DriveServiceError,
    ensure_child_photo_folder,
    list_files_in_folder,
    upload_bytes_to_folder,
)
from services.content_repo import ContentRepository, ContentRepositoryError
from services.sheets_repo import SheetsRepositoryError
from services.sheets_service import SheetsServiceError, read_sheet_values
from services.photos_service import get_download_bytes

# Streamlit page configuration
LOGO_PATH = Path(__file__).resolve().parent / "images" / "logo.png"
st.set_page_config(
    page_title="9 Freunde App",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🤱",
    layout="wide",
)


def _trigger_rerun() -> None:
    """Kompatibler Rerun für verschiedene Streamlit-Versionen."""
    rerun_fn = getattr(st, "rerun", None)
    if callable(rerun_fn):
        rerun_fn()
        return

    experimental_rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(experimental_rerun_fn):
        experimental_rerun_fn()


@st.cache_data(show_spinner=False)
def _get_photo_download_bytes(file_id: str, consent_mode: str) -> bytes:
    original_bytes = drive_agent.download_file(file_id)
    return get_download_bytes(original_bytes, consent_mode)


def _run_google_connection_check(
    drive: DriveAgent,
) -> list[tuple[str, bool, str]]:
    """Prüft Drive-, Calendar- und Sheets-Verbindung mit lesenden Testaufrufen."""
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
        calendar_client = _get_calendar_client()
        calendar_client.events().list(
            calendarId=_get_calendar_id(),
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

    def _quote_sheet_tab_for_a1(tab_name: str) -> str:
        escaped = tab_name.replace("'", "''")
        return f"'{escaped}'"

    app_config = get_app_config()
    if app_config.google is not None:
        sheet_id = app_config.google.stammdaten_sheet_id
        sheet_tab = app_config.google.stammdaten_sheet_tab or "children"
        quoted_tab = _quote_sheet_tab_for_a1(sheet_tab)
        check_range = f"{quoted_tab}!A1:A1"
        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                read_sheet_values(sheet_id=sheet_id, range_a1=check_range)
                checks.append(
                    (
                        "Google Sheets Zugriff / Google Sheets access",
                        True,
                        f"Sheets-Lesezugriff erfolgreich (Range {check_range}). / "
                        "Successfully read from Google Sheets "
                        f"(range {check_range}).",
                    )
                )
                break
            except HttpError as exc:  # pragma: no cover - runtime external dependency
                last_error = exc
                status_code = int(getattr(exc.resp, "status", 0) or 0)
                if status_code in (403, 404):
                    break
            except (
                SheetsServiceError
            ) as exc:  # pragma: no cover - runtime external dependency
                last_error = exc
                break
            except Exception as exc:  # pragma: no cover - runtime external dependency
                last_error = exc

            if attempt < max_attempts:
                time.sleep(2 ** (attempt - 1))

        if last_error is not None:
            status_code_value: int | None = None
            if isinstance(last_error, HttpError):
                status_code_value = int(getattr(last_error.resp, "status", 0) or 0)

            if status_code_value == 403:
                message = (
                    "Sheets-Test fehlgeschlagen (403). Die Tabelle ist vermutlich nicht "
                    "mit dem Service-Account geteilt oder die Berechtigung fehlt. / "
                    "Sheets check failed (403). The sheet is likely not shared with the "
                    "service account or permissions are missing."
                )
            elif status_code_value == 404:
                message = (
                    "Sheets-Test fehlgeschlagen (404). Die konfigurierte "
                    "`stammdaten_sheet_id` scheint falsch zu sein. / "
                    "Sheets check failed (404). The configured "
                    "`stammdaten_sheet_id` seems to be invalid."
                )
            else:
                message = (
                    "Sheets-Test fehlgeschlagen. Allgemeiner Google-Sheets-API-Fehler. / "
                    "Sheets check failed. Generic Google Sheets API error."
                )

            checks.append(
                (
                    "Google Sheets Zugriff / Google Sheets access",
                    False,
                    f"{message} Fehler / Error: {last_error}",
                )
            )

    return checks


def _page_title(page: object, language: str) -> str:
    title_de = str(getattr(page, "title_de", "")).strip()
    title_en = str(getattr(page, "title_en", "")).strip()
    if language == "en":
        return title_en or title_de or "Untitled"
    return title_de or title_en or "Ohne Titel"


def _page_body(page: object, language: str) -> str:
    body_de = str(getattr(page, "body_md_de", "")).strip()
    body_en = str(getattr(page, "body_md_en", "")).strip()
    if language == "en":
        return body_en or body_de
    return body_de or body_en


# Validate required secrets early and fail with clear UI guidance
validate_config_or_stop()
app_config = get_app_config()

if LOGO_PATH.exists():
    st.image(str(LOGO_PATH), width=180)

# Initialize agents (ensure single instance per session)
if "auth_agent" not in st.session_state:
    st.session_state.auth_agent = AuthAgent()
if "stammdaten_manager" not in st.session_state:
    st.session_state.stammdaten_manager = StammdatenManager()
if "drive_agent" not in st.session_state:
    st.session_state.drive_agent = DriveAgent()
if "doc_agent" not in st.session_state:
    st.session_state.doc_agent = DocumentAgent()
if "photo_agent" not in st.session_state:
    st.session_state.photo_agent = PhotoAgent()

auth = st.session_state.auth_agent
stammdaten_manager = st.session_state.stammdaten_manager
drive_agent = st.session_state.drive_agent
doc_agent = st.session_state.doc_agent
photo_agent = st.session_state.photo_agent
content_repo = ContentRepository()

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
            with st.spinner(
                "Prüfe Drive, Kalender & Sheets... / "
                "Checking drive, calendar & sheets..."
            ):
                check_results = _run_google_connection_check(drive_agent)
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
                "Infos verwalten",
                "Dokumente",
                "Verträge",
                "Fotos",
                "Kalender",
            ),
            index=0,
        )
    else:
        menu = st.sidebar.radio(
            "Menü", ("Mein Kind", "Infos", "Dokumente", "Fotos", "Termine"), index=0
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
            children: list[dict[str, str]] = []
            children_load_error = False
            try:
                children = stammdaten_manager.get_children()
            except SheetsRepositoryError as exc:
                children_load_error = True
                st.error(
                    "Stammdaten konnten nicht geladen werden. Bitte prüfen Sie, ob der "
                    "Service-Account Zugriff auf die konfigurierte Tabelle hat "
                    "(gcp.stammdaten_sheet_id). / Could not load master data. Please "
                    "verify that the service account has access to the configured "
                    "sheet (gcp.stammdaten_sheet_id)."
                )
                st.caption(f"Details / Details: {exc}")
            except Exception:
                children_load_error = True
                st.error(
                    "Stammdaten konnten aktuell nicht geladen werden. Bitte später "
                    "erneut versuchen. / Master data could not be loaded right now. "
                    "Please try again later."
                )

            # Anzeige der vorhandenen Kinder
            if not children_load_error and children:
                for child in children:
                    st.write(
                        f"- **{child.get('name')}** (Eltern: {child.get('parent_email')})"
                    )
            elif not children_load_error:
                st.write("*Noch keine Kinder registriert.*")

            # Formular zum Hinzufügen eines neuen Kindes
            st.write("**Neues Kind anlegen:**")
            with st.form(key="new_child_form"):
                name = st.text_input("Name des Kindes / Child name")
                parent_email = st.text_input("E-Mail Elternteil / Parent email")
                birthdate = st.text_input("Geburtsdatum (YYYY-MM-DD) / Birthdate")
                start_date = st.text_input("Startdatum (YYYY-MM-DD) / Start date")
                group = st.text_input("Gruppe / Group", value="Igel")
                primary_caregiver = st.text_input(
                    "Bezugserzieher:in / Primary caregiver"
                )
                allergies = st.text_input("Allergien / Allergies")
                notes_parent_visible = st.text_area(
                    "Hinweise für Eltern sichtbar / Parent-visible notes",
                    height=80,
                )
                notes_internal = st.text_area(
                    "Interne Hinweise (nur Leitung) / Internal notes",
                    height=80,
                )
                pickup_password = st.text_input(
                    "Abhol-Kennwort (optional) / Pickup password",
                    type="password",
                )
                status = st.selectbox("Status", options=["active", "archived"], index=0)
                submitted = st.form_submit_button("Hinzufügen / Add child")
            if submitted:
                if name.strip() == "" or parent_email.strip() == "":
                    st.error(
                        "Bitte Name und Eltern-E-Mail angeben. / Please provide child name and parent email."
                    )
                else:
                    try:
                        new_child_id = stammdaten_manager.add_child(
                            name.strip(), parent_email.strip()
                        )
                        stammdaten_manager.update_child(
                            new_child_id,
                            {
                                "birthdate": birthdate.strip(),
                                "start_date": start_date.strip(),
                                "group": group.strip(),
                                "primary_caregiver": primary_caregiver.strip(),
                                "allergies": allergies.strip(),
                                "notes_parent_visible": notes_parent_visible.strip(),
                                "notes_internal": notes_internal.strip(),
                                "pickup_password": pickup_password.strip(),
                                "status": status,
                            },
                        )
                        st.success(
                            f"Kind '{name}' hinzugefügt. / Child '{name}' added."
                        )
                        _trigger_rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Speichern / Save error: {e}")
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
                    edit_birthdate = st.text_input(
                        "Geburtsdatum (YYYY-MM-DD) / Birthdate",
                        value=selected_child.get("birthdate", ""),
                    )
                    edit_start_date = st.text_input(
                        "Startdatum (YYYY-MM-DD) / Start date",
                        value=selected_child.get("start_date", ""),
                    )
                    edit_group = st.text_input(
                        "Gruppe / Group",
                        value=selected_child.get("group", ""),
                    )
                    edit_primary_caregiver = st.text_input(
                        "Bezugserzieher:in / Primary caregiver",
                        value=selected_child.get("primary_caregiver", ""),
                    )
                    edit_allergies = st.text_input(
                        "Allergien / Allergies",
                        value=selected_child.get("allergies", ""),
                    )
                    edit_notes_parent_visible = st.text_area(
                        "Hinweise für Eltern sichtbar / Parent-visible notes",
                        value=selected_child.get("notes_parent_visible", ""),
                        height=80,
                    )
                    edit_notes_internal = st.text_area(
                        "Interne Hinweise (nur Leitung) / Internal notes",
                        value=selected_child.get("notes_internal", ""),
                        height=80,
                    )
                    edit_pickup_password = st.text_input(
                        "Abhol-Kennwort (optional) / Pickup password",
                        value=selected_child.get("pickup_password", ""),
                        type="password",
                    )
                    status_options = ["active", "archived"]
                    current_status = str(selected_child.get("status", "active")).strip()
                    if current_status not in status_options:
                        current_status = "active"
                    edit_status = st.selectbox(
                        "Status",
                        options=status_options,
                        index=status_options.index(current_status),
                    )
                    current_download_consent = (
                        str(selected_child.get("download_consent", "pixelated"))
                        .strip()
                        .lower()
                    )
                    consent_options = ["pixelated", "unpixelated"]
                    if current_download_consent not in consent_options:
                        current_download_consent = "pixelated"
                    edit_download_consent = st.selectbox(
                        "Download-Consent / Download consent",
                        options=consent_options,
                        index=consent_options.index(current_download_consent),
                        format_func=lambda mode: (
                            "Downloads verpixelt / Downloads pixelated"
                            if mode == "pixelated"
                            else "Downloads unverpixelt / Downloads unpixelated"
                        ),
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
                                    "birthdate": edit_birthdate.strip(),
                                    "start_date": edit_start_date.strip(),
                                    "group": edit_group.strip(),
                                    "primary_caregiver": edit_primary_caregiver.strip(),
                                    "allergies": edit_allergies.strip(),
                                    "notes_parent_visible": edit_notes_parent_visible.strip(),
                                    "notes_internal": edit_notes_internal.strip(),
                                    "pickup_password": edit_pickup_password.strip(),
                                    "status": edit_status,
                                    "download_consent": edit_download_consent,
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

        # ---- Admin: Infos verwalten ----
        elif menu == "Infos verwalten":
            st.subheader("Infos verwalten / Manage info pages")
            language = st.radio(
                "Sprache / Language",
                options=["de", "en"],
                horizontal=True,
                format_func=lambda value: "Deutsch" if value == "de" else "English",
            )

            try:
                pages = content_repo.list_pages()
            except ContentRepositoryError as exc:
                st.error(
                    "Inhalte konnten nicht geladen werden. / Could not load content pages."
                )
                st.info(str(exc))
                pages = []

            st.write("**Bestehende Seiten / Existing pages**")
            if pages:
                overview_df = pd.DataFrame(
                    [
                        {
                            "slug": page.slug,
                            "title": _page_title(page, language),
                            "audience": page.audience,
                            "published": page.published,
                            "updated_at": page.updated_at,
                        }
                        for page in pages
                    ]
                )
                st.dataframe(overview_df, use_container_width=True)
            else:
                st.caption("Noch keine Seiten vorhanden. / No pages yet.")

            selected_slug = st.selectbox(
                "Seite bearbeiten / Edit page",
                options=[""] + [page.slug for page in pages],
                format_func=lambda value: "Neue Seite anlegen / Create new page"
                if value == ""
                else value,
            )
            selected_page = (
                content_repo.get_page(selected_slug) if selected_slug else None
            )

            with st.form("content_page_form"):
                slug_value = st.text_input(
                    "Slug (z. B. packing_list)",
                    value=selected_page.slug if selected_page else "",
                    help="Eindeutige Kennung der Seite / Unique page identifier",
                )
                title_de = st.text_input(
                    "Titel (DE)",
                    value=selected_page.title_de if selected_page else "",
                )
                title_en = st.text_input(
                    "Title (EN)",
                    value=selected_page.title_en if selected_page else "",
                )
                body_md_de = st.text_area(
                    "Inhalt (Markdown, DE)",
                    value=selected_page.body_md_de if selected_page else "",
                    height=180,
                )
                body_md_en = st.text_area(
                    "Content (Markdown, EN)",
                    value=selected_page.body_md_en if selected_page else "",
                    height=180,
                )
                audience = st.selectbox(
                    "Zielgruppe / Audience",
                    options=["both", "parent", "admin"],
                    index=["both", "parent", "admin"].index(selected_page.audience)
                    if selected_page
                    else 0,
                )
                published = st.checkbox(
                    "Veröffentlicht / Published",
                    value=selected_page.published if selected_page else True,
                )
                save_page = st.form_submit_button("Speichern / Save")

            if save_page:
                try:
                    content_repo.upsert_page(
                        {
                            "slug": slug_value,
                            "title_de": title_de,
                            "title_en": title_en,
                            "body_md_de": body_md_de,
                            "body_md_en": body_md_en,
                            "audience": audience,
                            "published": published,
                        }
                    )
                    st.success("Seite gespeichert. / Page saved.")
                    _trigger_rerun()
                except ContentRepositoryError as exc:
                    st.error("Speichern fehlgeschlagen. / Save failed.")
                    st.info(str(exc))

            if selected_page is not None:
                if st.button("Seite löschen / Delete page"):
                    try:
                        content_repo.delete_page(selected_page.slug)
                        st.success("Seite gelöscht. / Page deleted.")
                        _trigger_rerun()
                    except ContentRepositoryError as exc:
                        st.error("Löschen fehlgeschlagen. / Delete failed.")
                        st.info(str(exc))

                st.write("**Vorschau / Preview**")
                st.markdown(f"### {_page_title(selected_page, language)}")
                body_preview = _page_body(selected_page, language)
                if body_preview:
                    st.markdown(body_preview)
                else:
                    st.caption("Kein Inhalt vorhanden. / No content available.")

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
            st.subheader("Kinder-Fotos hochladen und verwalten / Upload child photos")
            st.info(
                "MVP ohne Gesichtserkennung: Upload erfolgt in den kindspezifischen Foto-Ordner. / "
                "MVP without face recognition: uploads are stored in each child's photo folder."
            )
            children = stammdaten_manager.get_children()
            if not children:
                st.warning("Bitte legen Sie zuerst Kinder-Stammdaten an.")
            else:
                child_names = [child.get("name") for child in children]
                selected_name = st.selectbox(
                    "Foto hochladen für Kind / Upload photo for child", child_names
                )
                sel_child = next(
                    child for child in children if child.get("name") == selected_name
                )
                image_file = st.file_uploader(
                    "Foto auswählen / Select photo", type=["jpg", "jpeg", "png"]
                )
                if image_file and st.button("Upload Foto / Upload photo"):
                    try:
                        child_id = str(sel_child.get("id", "")).strip()
                        if app_config.storage_mode == "google":
                            photo_folder_id = ensure_child_photo_folder(child_id)
                        else:
                            photo_folder_id = str(
                                sel_child.get("photo_folder_id")
                                or sel_child.get("folder_id")
                                or ""
                            )
                        if not photo_folder_id:
                            raise ValueError(
                                "Kein Foto-Ordner für dieses Kind vorhanden. / No photo folder configured for this child."
                            )
                        photo_agent.upload_photo(image_file, photo_folder_id)
                        st.success(
                            f"Foto für {selected_name} hochgeladen. / Photo uploaded for {selected_name}."
                        )
                        st.image(
                            image_file,
                            caption=f"Hochgeladenes Foto / Uploaded photo: {image_file.name}",
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.error(
                            f"Fehler beim Foto-Upload / Photo upload failed: {exc}"
                        )
                if app_config.storage_mode == "google":
                    st.info(
                        "Fotos werden in `photos/<child_id>/`-Ordnern abgelegt. Eltern sehen nur den eigenen Ordner. / "
                        "Photos are stored in `photos/<child_id>/` folders. Parents only see their own folder."
                    )
                else:
                    st.info(
                        "Fotos werden lokal im Prototyp-Speicher abgelegt. / "
                        "Photos are stored in local prototype storage."
                    )

        # ---- Admin: Kalender ----
        elif menu == "Kalender":
            st.subheader("Neuer Termin / New event")
            title = st.text_input("Titel / Title")
            event_date = st.date_input("Datum / Date")
            event_time = st.time_input("Uhrzeit (Start) / Start time")
            description = st.text_area("Beschreibung / Description")
            if st.button("Termin hinzufügen / Add event"):
                if not title:
                    st.error("Bitte Titel eingeben. / Please enter a title.")
                else:
                    try:
                        add_event(
                            title=title,
                            event_date=event_date,
                            event_time=event_time,
                            description=description,
                        )
                        st.success("Termin wurde hinzugefügt. / Event created.")
                    except CalendarServiceError as exc:
                        st.error(f"Fehler beim Speichern / Failed to save event: {exc}")

            st.write("**Bevorstehende Termine / Upcoming events**")
            try:
                events = list_events(max_results=10)
            except CalendarServiceError as exc:
                events = []
                st.error(f"Fehler beim Laden / Failed to load events: {exc}")
            if events:
                for ev in events:
                    st.write(f"- {ev['start']} · **{ev['summary']}**")
                    if ev["description"]:
                        st.caption(ev["description"])
            else:
                st.write("Keine anstehenden Termine vorhanden. / No upcoming events.")

    else:
        # ---- Parent/Eltern View ----
        child = stammdaten_manager.get_child_by_parent(user_email)
        st.session_state.child = child
        if menu == "Mein Kind":
            st.subheader("Mein Kind - Übersicht")
            if child:
                st.write(f"**Name:** {child.get('name')}")
                if child.get("birthdate"):
                    st.write(f"**Geburtsdatum / Birthdate:** {child.get('birthdate')}")
                if child.get("start_date"):
                    st.write(f"**Startdatum / Start date:** {child.get('start_date')}")
                if child.get("group"):
                    st.write(f"**Gruppe / Group:** {child.get('group')}")
                if child.get("primary_caregiver"):
                    st.write(
                        f"**Bezugserzieher:in / Primary caregiver:** {child.get('primary_caregiver')}"
                    )
                if child.get("allergies"):
                    st.write(f"**Allergien / Allergies:** {child.get('allergies')}")
                if child.get("notes_parent_visible"):
                    st.info(f"Hinweise / Notes:\n\n{child.get('notes_parent_visible')}")
            else:
                st.write("Keine Kinderdaten gefunden. / No child data found.")
        elif menu == "Infos":
            st.subheader("Infos / Information")
            language = st.radio(
                "Sprache / Language",
                options=["de", "en"],
                horizontal=True,
                format_func=lambda value: "Deutsch" if value == "de" else "English",
                key="parent_infos_language",
            )
            try:
                pages = [
                    page
                    for page in content_repo.list_pages()
                    if page.published and page.audience in {"parent", "both"}
                ]
            except ContentRepositoryError as exc:
                pages = []
                st.error(
                    "Infos konnten nicht geladen werden. / Could not load info pages."
                )
                st.info(str(exc))

            if not pages:
                st.info(
                    "Derzeit sind keine veröffentlichten Infos verfügbar. / "
                    "No published info pages are currently available."
                )
            else:
                selected_slug = st.selectbox(
                    "Seite auswählen / Select page",
                    options=[page.slug for page in pages],
                )
                selected_page = next(
                    page for page in pages if page.slug == selected_slug
                )
                st.markdown(f"### {_page_title(selected_page, language)}")
                page_content = _page_body(selected_page, language)
                if page_content:
                    st.markdown(page_content)
                else:
                    st.caption("Kein Inhalt vorhanden. / No content available.")

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
            st.subheader("Fotos / Photos")
            if child and child.get("id"):
                try:
                    if app_config.storage_mode == "google":
                        photo_folder_id = ensure_child_photo_folder(str(child["id"]))
                    else:
                        photo_folder_id = str(
                            child.get("photo_folder_id") or child.get("folder_id") or ""
                        )
                    photos = (
                        drive_agent.list_files(
                            photo_folder_id, mime_type_filter="image/"
                        )
                        if photo_folder_id
                        else []
                    )
                except Exception as exc:
                    photos = []
                    st.error(
                        "Fotos konnten nicht geladen werden. / Could not load photos."
                    )
                    st.info(str(exc))

                if child:
                    current_download_consent = (
                        str(child.get("download_consent", "pixelated")).strip().lower()
                    )
                    consent_options = ["pixelated", "unpixelated"]
                    if current_download_consent not in consent_options:
                        current_download_consent = "pixelated"
                    selected_download_consent = st.selectbox(
                        "Foto-Download Consent / Photo download consent",
                        options=consent_options,
                        index=consent_options.index(current_download_consent),
                        format_func=lambda mode: (
                            "Downloads verpixelt / Downloads pixelated"
                            if mode == "pixelated"
                            else "Downloads unverpixelt / Downloads unpixelated"
                        ),
                        key="parent_download_consent_select",
                    )
                    if selected_download_consent != current_download_consent:
                        try:
                            stammdaten_manager.update_child(
                                str(child.get("id", "")),
                                {"download_consent": selected_download_consent},
                            )
                            st.success("Consent aktualisiert. / Consent updated.")
                            _trigger_rerun()
                        except Exception as exc:
                            st.error(
                                "Consent konnte nicht gespeichert werden. / Could not save consent."
                            )
                            st.info(str(exc))
                    st.caption(
                        "In der App bleibt die Vorschau unverändert. Der Consent betrifft nur den Download. / "
                        "In-app preview remains unchanged. Consent affects download only."
                    )
                if photos:
                    active_consent_mode = (
                        str((child or {}).get("download_consent", "pixelated"))
                        .strip()
                        .lower()
                    )
                    for photo in photos:
                        file_name = str(photo.get("name", "photo"))
                        file_id = str(photo.get("id", ""))
                        img_bytes = drive_agent.download_file(file_id)
                        st.image(
                            img_bytes,
                            caption=f"{file_name} · Vorschau / Preview",
                            use_container_width=True,
                        )
                        download_bytes = _get_photo_download_bytes(
                            file_id=file_id,
                            consent_mode=active_consent_mode,
                        )
                        st.download_button(
                            "Foto herunterladen / Download photo",
                            data=download_bytes,
                            file_name=file_name,
                            key=f"download_photo_{file_id}_{active_consent_mode}",
                        )
                else:
                    st.write("Keine Fotos vorhanden. / No photos available.")
            else:
                st.write("Keine Fotos verfügbar. / No photos available.")
        elif menu == "Termine":
            st.subheader("Termine / Events")
            try:
                events = list_events(max_results=10)
            except CalendarServiceError as exc:
                events = []
                st.error(f"Fehler beim Laden / Failed to load events: {exc}")
            if events:
                for ev in events:
                    st.write(f"- {ev['start']} · **{ev['summary']}**")
                    if ev["description"]:
                        st.caption(ev["description"])
            else:
                st.write(
                    "Zurzeit sind keine Termine eingetragen. / No events available right now."
                )
