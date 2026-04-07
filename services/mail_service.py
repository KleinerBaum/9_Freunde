from __future__ import annotations

import base64
from collections.abc import Mapping
from email.mime.text import MIMEText
from typing import Any, Literal

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_app_config

GMAIL_SEND_SCOPE = ["https://www.googleapis.com/auth/gmail.send"]
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class MailServiceError(RuntimeError):
    """Domänenspezifischer Fehler für Gmail-Versand."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        cause: str | None = None,
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.cause = cause
        self.transient = transient


def _translate_gmail_http_error(exc: HttpError) -> MailServiceError:
    status_code = int(getattr(exc.resp, "status", 0) or 0)
    transient = status_code in TRANSIENT_STATUS_CODES
    if status_code == 403:
        return MailServiceError(
            "Kein Zugriff auf Gmail. Bitte Delegation/Berechtigungen prüfen. / "
            "No Gmail access. Please verify delegation/permissions.",
            status_code=status_code,
            cause="forbidden",
            transient=False,
        )
    if status_code == 404:
        return MailServiceError(
            "Gmail-Konfiguration ungültig. / Gmail configuration is invalid.",
            status_code=status_code,
            cause="not_found",
            transient=False,
        )
    return MailServiceError(
        f"Gmail API Fehler / Gmail API error: {exc}",
        status_code=status_code if status_code else None,
        cause="api_error",
        transient=transient,
    )


@st.cache_resource(show_spinner=False)
def _get_gmail_client():
    app_config = get_app_config()
    if app_config.google is None:
        raise MailServiceError(
            "Google-Konfiguration fehlt. / Google configuration is missing.",
            cause="config_missing",
        )

    delegated_user = str(
        st.secrets.get("gcp", {}).get("gmail_delegated_user", "")
    ).strip()
    credentials = service_account.Credentials.from_service_account_info(
        app_config.google.service_account,
        scopes=GMAIL_SEND_SCOPE,
    )
    if delegated_user:
        credentials = credentials.with_subject(delegated_user)
    return build("gmail", "v1", credentials=credentials)


def build_parent_recipient_list(
    *,
    children: list[Mapping[str, Any]],
    parents: list[Mapping[str, Any]],
    audience: Literal["all_parents", "group", "single_child"],
    selected_group: str | None = None,
    selected_child_id: str | None = None,
) -> list[str]:
    """Erzeugt eine deduplizierte Empfängerliste für Eltern."""
    child_parent_emails: set[str] = set()

    if audience == "all_parents":
        child_parent_emails = {
            str(child.get("parent_email", "")).strip().lower()
            for child in children
            if str(child.get("parent_email", "")).strip()
        }
    elif audience == "group":
        normalized_group = str(selected_group or "").strip().lower()
        child_parent_emails = {
            str(child.get("parent_email", "")).strip().lower()
            for child in children
            if str(child.get("parent_email", "")).strip()
            and str(child.get("group", "")).strip().lower() == normalized_group
        }
    elif audience == "single_child":
        normalized_child_id = str(selected_child_id or "").strip()
        child_parent_emails = {
            str(child.get("parent_email", "")).strip().lower()
            for child in children
            if str(child.get("id", "")).strip() == normalized_child_id
            and str(child.get("parent_email", "")).strip()
        }

    parent_opt_in_lookup = {
        str(parent.get("email", "")).strip().lower(): str(
            parent.get("notifications_opt_in", "true")
        )
        .strip()
        .lower()
        in {"true", "1", "yes"}
        for parent in parents
        if str(parent.get("email", "")).strip()
    }

    recipients = [
        email
        for email in sorted(child_parent_emails)
        if parent_opt_in_lookup.get(email, True)
    ]
    return recipients


def send_message(
    *,
    recipient_email: str,
    subject: str,
    body_text: str,
) -> str:
    """Versendet eine Nachricht an genau eine Empfängeradresse."""
    normalized_recipient = recipient_email.strip().lower()
    normalized_subject = subject.strip()
    if not normalized_recipient:
        raise ValueError(
            "Empfänger darf nicht leer sein. / Recipient must not be empty."
        )
    if not normalized_subject:
        raise ValueError("Betreff darf nicht leer sein. / Subject must not be empty.")

    message = MIMEText(body_text.strip(), "plain", "utf-8")
    message["to"] = normalized_recipient
    message["subject"] = normalized_subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        response = (
            _get_gmail_client()
            .users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
    except HttpError as exc:
        raise _translate_gmail_http_error(exc) from exc

    return str(response.get("id", "")).strip()


def send_bulk_message(
    *,
    recipient_emails: list[str],
    subject: str,
    body_text: str,
) -> dict[str, int]:
    """Versendet eine Nachricht an mehrere Empfänger und liefert aggregierte Werte."""
    normalized_recipients = sorted(
        {email.strip().lower() for email in recipient_emails if email.strip()}
    )
    if not normalized_recipients:
        raise ValueError("Empfängerliste ist leer. / Recipient list must not be empty.")

    success_count = 0
    failure_count = 0
    for recipient in normalized_recipients:
        try:
            send_message(
                recipient_email=recipient,
                subject=subject,
                body_text=body_text,
            )
            success_count += 1
        except MailServiceError:
            failure_count += 1

    if success_count == 0 and failure_count > 0:
        raise MailServiceError(
            "Kein Versand erfolgreich. / No messages were sent successfully.",
            cause="bulk_failed",
            transient=False,
        )

    return {"success_count": success_count, "failure_count": failure_count}
