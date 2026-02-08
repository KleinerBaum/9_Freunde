import hashlib

import streamlit as st


class AuthAgent:
    def __init__(self) -> None:
        """Auth-Initialisierung ohne externe Provider."""

    def login(self, email: str, password: str) -> str | bool:
        email = email.strip()
        if not email or not password:
            return False

        auth_conf = st.secrets.get("auth", {})
        users = auth_conf.get("users", {})
        app_conf = st.secrets.get("app", {})
        admin_emails = auth_conf.get("admin_emails") or app_conf.get("admin_emails", [])

        if email not in users:
            return False

        stored_pw = users[email]
        if len(stored_pw) == 64 and all(
            char in "0123456789abcdef" for char in stored_pw.lower()
        ):
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            if pw_hash == stored_pw:
                return "admin" if email in admin_emails else "parent"
            return False

        if password == stored_pw:
            return "admin" if email in admin_emails else "parent"
        return False
