import streamlit as st
import hashlib
# Optional: Firebase Auth könnte beintegriert werden

class AuthAgent:
    def __init__(self):
        # Initialisierung (z.B. Firebase App, falls nicht bereits erfolgt)
        try:
            from storage import init_firebase
            init_firebase()
        except Exception:
            pass

    def login(self, email: str, password: str):
        email = email.strip()
        if not email or not password:
            return False
        # Zuerst in lokalen Secrets nachschauen
        auth_conf = st.secrets.get('auth', {})
        users = auth_conf.get('users', {})
        admin_emails = auth_conf.get('admin_emails', [])
        if email in users:
            stored_pw = users[email]
            # Unterstützt Klartext oder SHA256-Hash
            if len(stored_pw) == 64 and all(c in '0123456789abcdef' for c in stored_pw.lower()):
                # als Hash gespeichert
                pw_hash = hashlib.sha256(password.encode()).hexdigest()
                if pw_hash == stored_pw:
                    return 'admin' if email in admin_emails else 'parent'
            else:
                # als Klartext gespeichert
                if password == stored_pw:
                    return 'admin' if email in admin_emails else 'parent'
            # Passwort stimmt nicht
            return False
        else:
            # Wenn kein Eintrag in users: hier könnte Firebase-Auth Prüfung erfolgen
            # (z.B. via firebase_admin.auth oder REST API), derzeit nicht implementiert.
            return False
