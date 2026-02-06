import streamlit as st
import io
from PIL import Image
import face_recognition
from storage import DriveAgent

class PhotoAgent:
    def __init__(self):
        # Hier könnte man bekannte Gesichter (Embeddings) pro Kind laden
        self.known_faces = {}  # z.B. {child_id: embedding}

    def upload_photo(self, image_file, child_id=None, folder_id=None):
        """Speichert ein hochgeladenes Foto im Drive (im Ordner des Kindes) und nutzt Gesichtserkennung für Notizen."""
        # Bilddaten einlesen
        img_bytes = image_file.getvalue()
        # Gesichter erkennen
        try:
            img = face_recognition.load_image_file(io.BytesIO(img_bytes))
            faces = face_recognition.face_locations(img)
        except Exception as e:
            faces = []
            print("Fehler bei Gesichtserkennung:", e)
        if len(faces) > 1:
            st.warning("Mehrere Gesichter auf dem Foto erkannt. Stellen Sie sicher, dass keine unbefugten Personen abgebildet sind.")
        elif len(faces) == 0:
            st.warning("Kein Gesicht auf dem Foto erkannt – überprüfen Sie das Bild.")
        # (Optional: hier könnte man face_encodings berechnen und mit known_faces vergleichen)
        # Datei in Drive hochladen
        drive_agent = DriveAgent()
        target_folder = folder_id or st.secrets.get('gcp', {}).get('photos_folder_id')
        if not target_folder:
            raise RuntimeError("Kein Zielordner für Fotos definiert.")
        # Dateiname bestimmen
        file_name = image_file.name or f"foto_{child_id}.jpg"
        # MIME-Type bestimmen
        mime_type = "image/jpeg" if file_name.lower().endswith(('.jpg', '.jpeg')) else "image/png"
        drive_agent.upload_file(file_name, img_bytes, mime_type, target_folder)
        return True
