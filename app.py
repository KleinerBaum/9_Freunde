## app.py

import streamlit as st
from auth import AuthAgent
from stammdaten import StammdatenManager
from documents import DocumentAgent
from photo import PhotoAgent
from storage import DriveAgent
from calendar import CalendarAgent
from config import validate_config_or_stop

# Streamlit page configuration
st.set_page_config(page_title="9 Freunde App", page_icon="🤱", layout="wide")


# Validate required secrets early and fail with clear UI guidance
validate_config_or_stop()

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
            st.experimental_rerun()
        else:
            st.error("Login fehlgeschlagen. Bitte E-Mail/Passwort überprüfen.")
else:
    # --- Main Application (Post-Login) ---
    user_role = st.session_state.role
    user_email = st.session_state.user

    # Sidebar menu based on role
    st.sidebar.title("9 Freunde App")
    st.sidebar.write(f"Angemeldet als: `{user_email}`")
    if user_role == "admin":
        menu = st.sidebar.radio(
            "Navigationsmenü", ("Stammdaten", "Dokumente", "Fotos", "Kalender"), index=0
        )
    else:
        menu = st.sidebar.radio(
            "Menü", ("Mein Kind", "Dokumente", "Fotos", "Termine"), index=0
        )

    # Logout button at bottom of sidebar
    if st.sidebar.button("Logout"):
        # Clear session state and rerun to show login
        st.session_state.clear()
        st.experimental_rerun()

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
                        st.success(f"Kind '{name}' hinzugefügt.")
                    except Exception as e:
                        st.error(f"Fehler beim Speichern: {e}")
            st.info(
                "Beim Anlegen eines Kindes wird automatisch ein zugehöriger Drive-Ordner erstellt und verknüpft."
            )

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
                st.info(
                    "Fotos werden sicher auf Google Drive gespeichert und nur den berechtigten Eltern angezeigt."
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
        child = st.session_state.get("child")
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
