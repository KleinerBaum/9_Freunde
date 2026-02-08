from __future__ import annotations

import cv2
import numpy as np

VALID_CONSENT_MODES = {"pixelated", "unpixelated"}


def _decode_image(image_bytes: bytes) -> np.ndarray:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Bilddaten konnten nicht dekodiert werden.")
    return image


def _encode_image(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Bild konnte nicht kodiert werden.")
    return encoded.tobytes()


def pixelate_faces(image_bytes: bytes) -> bytes:
    """Erzeugt ein Bild mit verpixelten Gesichtern via Haar Cascade."""
    image = _decode_image(image_bytes)
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(
        grayscale,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(24, 24),
    )

    for x, y, width, height in faces:
        roi = image[y : y + height, x : x + width]
        if roi.size == 0:
            continue

        mosaic_w = max(1, width // 12)
        mosaic_h = max(1, height // 12)
        small = cv2.resize(roi, (mosaic_w, mosaic_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(
            small,
            (width, height),
            interpolation=cv2.INTER_NEAREST,
        )
        image[y : y + height, x : x + width] = pixelated

    return _encode_image(image)


def get_download_bytes(image_bytes: bytes, consent_mode: str) -> bytes:
    """Liefert Download-Bytes entsprechend Consent-Modus."""
    normalized_mode = consent_mode.strip().lower()
    if normalized_mode not in VALID_CONSENT_MODES:
        normalized_mode = "pixelated"

    if normalized_mode == "unpixelated":
        return image_bytes

    return pixelate_faces(image_bytes)
