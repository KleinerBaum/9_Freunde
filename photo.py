from __future__ import annotations

from typing import Any

from storage import DriveAgent


class PhotoAgent:
    def upload_photo(self, image_file: Any, folder_id: str) -> str:
        """Speichert ein hochgeladenes Foto im zugewiesenen Kind-Ordner."""
        img_bytes = image_file.getvalue()

        file_name = image_file.name or "foto.jpg"
        lower_name = file_name.lower()
        mime_type = "image/png"
        if lower_name.endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"

        drive_agent = DriveAgent()
        file_id = drive_agent.upload_file(file_name, img_bytes, mime_type, folder_id)
        if not file_id:
            raise RuntimeError("Upload fehlgeschlagen: keine file_id erhalten.")
        return str(file_id)

    def face_detection_enabled(self) -> bool:
        """Face-Recognition ist im MVP deaktiviert."""
        return False
