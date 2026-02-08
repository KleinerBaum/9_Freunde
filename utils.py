import hashlib


def hash_password(password: str) -> str:
    """Erzeugt einen SHA256-Hash des übergebenen Passwort-Strings."""
    return hashlib.sha256(password.encode()).hexdigest()
