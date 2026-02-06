import io
from typing import Any

import streamlit as st
from config import get_app_config
from storage import DriveAgent

try:
    import face_recognition
except Exception:
    face_recognition = None


def is_face_detection_available() -> bool:
    """Return whether optional face detection dependencies are available."""
    return face_recognition is not None


class PhotoAgent:
    def __init__(self) -> None:
        # Hier könnte man bekannte Gesichter (Embeddings) pro Kind laden
        self.known_faces: dict[str, Any] = {}  # z.B. {child_id: embedding}

    def upload_photo(
        self, image_file: Any, child_id: str | None = None, folder_id: str | None = None
    ) -> bool:
        """Speichert ein hochgeladenes Foto im Drive (im Ordner des Kindes) und nutzt optional Gesichtserkennung."""
        # Bilddaten einlesen
        img_bytes = image_file.getvalue()

        if is_face_detection_available():
            # Gesichter erkennen
            try:
                img = face_recognition.load_image_file(io.BytesIO(img_bytes))
                faces = face_recognition.face_locations(img)
            except Exception as error:
                faces = []
                print("Fehler bei Gesichtserkennung:", error)

            if len(faces) > 1:
                st.warning(
                    "Mehrere Gesichter auf dem Foto erkannt. "
                    "Stellen Sie sicher, dass keine unbefugten Personen abgebildet sind."
                )
            elif len(faces) == 0:
                st.warning(
                    "Kein Gesicht auf dem Foto erkannt – überprüfen Sie das Bild."
                )
        else:
            st.info(
                "Gesichtserkennung ist in dieser Bereitstellung deaktiviert. "
                "Das Foto wird ohne automatische Erkennung hochgeladen.\n"
                "Face detection is disabled in this deployment. "
                "The photo will be uploaded without automatic detection."
            )

        # Datei in Drive hochladen
        drive_agent = DriveAgent()
        target_folder = folder_id or get_app_config().google.photos_folder_id
        if not target_folder:
            raise RuntimeError("Kein Zielordner für Fotos definiert.")

        # Dateiname bestimmen
        file_name = image_file.name or f"foto_{child_id}.jpg"

        # MIME-Type bestimmen
        mime_type = (
            "image/jpeg"
            if file_name.lower().endswith((".jpg", ".jpeg"))
            else "image/png"
        )
        drive_agent.upload_file(file_name, img_bytes, mime_type, target_folder)
        return True

    def face_detection_enabled(self) -> bool:
        """Expose whether automatic face detection is active in this runtime."""
        return is_face_detection_available()
