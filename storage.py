import streamlit as st
import firebase_admin
from firebase_admin import credentials

# Firebase initialisieren (einmalig)
firebase_app = None
def init_firebase():
    global firebase_app
    if not firebase_app:
        try:
            # Versuche, Dienstkonto-Daten aus Secrets zu laden
            cred_info = st.secrets.get('gcp_service_account')
            if cred_info:
                cred = credentials.Certificate(cred_info)
                firebase_app = firebase_admin.initialize_app(cred)
            else:
                # Falls keine separaten Credentials vorliegen, überprüfen, ob App bereits initialisiert
                if not firebase_admin._apps:
                    firebase_app = firebase_admin.initialize_app()
                else:
                    firebase_app = firebase_admin.get_app()
        except Exception as e:
            print("Firebase Initialisierung fehlgeschlagen:", e)

# Google Drive API Anbindung
from google.oauth2 import service_account
from googleapiclient.discovery import build

class DriveAgent:
    def __init__(self):
        # Authentifizierung für Google Drive API
        service_account_info = st.secrets.get('gcp_service_account') or st.secrets.get('gcp')
        if not service_account_info:
            raise RuntimeError("Drive Service-Account nicht konfiguriert.")
        scopes = ["https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
        self.service = build('drive', 'v3', credentials=credentials)

    def list_files(self, folder_id, mime_type_filter=None):
        """Gibt eine Liste der Dateien in einem Ordner (nach ID) zurück. Optional kann nach MIME-Type gefiltert werden."""
        query = f"'{folder_id}' in parents and trashed=false"
        if mime_type_filter:
            query += f" and mimeType contains '{mime_type_filter}'"
        results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    @st.cache_data(show_spinner=False)
    def download_file(self, file_id):
        """Lädt eine Datei von Drive herunter und gibt deren Inhalt als Bytes zurück."""
        request = self.service.files().get_media(fileId=file_id)
        data = request.execute()
        return data

    def upload_file(self, name, content_bytes, mime_type, parent_folder_id):
        """Lädt eine Datei (Bytes-Inhalt) nach Google Drive hoch (in angegebenen Ordner). Gibt die File-ID zurück."""
        from io import BytesIO
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(BytesIO(content_bytes), mimetype=mime_type, resumable=False)
        metadata = {'name': name}
        if parent_folder_id:
            metadata['parents'] = [parent_folder_id]
        file = self.service.files().create(body=metadata, media_body=media, fields='id').execute()
        return file.get('id')

    def create_folder(self, name, parent_folder_id=None):
        """Erstellt einen neuen Ordner in Drive (unter parent_folder, falls angegeben) und gibt die ID zurück."""
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
        folder = self.service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
