import streamlit as st
from firebase_admin import firestore
from storage import init_firebase, DriveAgent

class StammdatenManager:
    def __init__(self):
        # Firebase Initialisierung (Firestore)
        init_firebase()
        try:
            self.db = firestore.client()
        except Exception as e:
            st.error(f"Datenbank-Verbindung fehlgeschlagen: {e}")
            self.db = None

    def get_children(self):
        """Lädt alle Kinder-Datensätze aus der Datenbank."""
        children = []
        if not self.db:
            return children
        docs = self.db.collection('children').stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            children.append(data)
        # Optional: sort by name
        children.sort(key=lambda x: x.get('name', ''))
        return children

    def add_child(self, name, parent_email):
        """Fügt ein neues Kind mit zugehörigem Eltern-Email zur Datenbank hinzu und erstellt einen Drive-Ordner."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")
        # Neuen Dokument-Eintrag anlegen
        child_data = {'name': name, 'parent_email': parent_email}
        doc_ref = self.db.collection('children').document()  # generiert eine neue ID
        doc_ref.set(child_data)
        child_id = doc_ref.id
        # Drive-Ordner für das Kind erstellen
        folder_id = None
        try:
            drive_agent = DriveAgent()
            main_folder = st.secrets.get('gcp', {}).get('photos_folder_id')
            folder_id = drive_agent.create_folder(name, parent_folder_id=main_folder)
        except Exception as e:
            print("Fehler beim Anlegen des Drive-Ordners:", e)
        if folder_id:
            try:
                doc_ref.update({'folder_id': folder_id})
            except Exception as e:
                print("Fehler beim Speichern der Ordner-ID:", e)
        return child_id

    def get_child_by_parent(self, parent_email):
        """Liefert den Datensatz des Kindes, das mit der gegebenen Eltern-Email verknüpft ist (oder None)."""
        if not self.db:
            return None
        query = self.db.collection('children').where('parent_email', '==', parent_email).stream()
        for doc in query:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def update_child(self, child_id, new_data: dict):
        """Aktualisiert Felder des Kindes mit der ID child_id."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")
        self.db.collection('children').document(child_id).update(new_data)

    def delete_child(self, child_id):
        """Löscht den Kind-Datensatz (und evtl. verknüpfte Daten)."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")
        # Hinweis: Verknüpfte Drive-Ordner oder Dateien müssten manuell gelöscht werden.
        self.db.collection('children').document(child_id).delete()
