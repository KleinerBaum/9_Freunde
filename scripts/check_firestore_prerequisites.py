from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import tomllib


def _run_gcloud(command: list[str]) -> tuple[int, str, str]:
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return process.returncode, process.stdout.strip(), process.stderr.strip()


def _load_service_account(secrets_path: Path) -> dict[str, Any]:
    with secrets_path.open("rb") as file:
        secrets = tomllib.load(file)

    service_account = secrets.get("gcp_service_account")
    if not isinstance(service_account, dict):
        raise ValueError("[gcp_service_account] fehlt in secrets.toml.")

    required_keys = {"project_id", "client_email", "private_key", "token_uri"}
    missing_keys = sorted(key for key in required_keys if not service_account.get(key))
    if missing_keys:
        missing_joined = ", ".join(missing_keys)
        raise ValueError(
            "gcp_service_account ist unvollständig. "
            f"Fehlende Felder: {missing_joined}."
        )

    return service_account


def _check_firestore_native_mode(project_id: str) -> bool:
    command = [
        "gcloud",
        "firestore",
        "databases",
        "describe",
        "--project",
        project_id,
        "--database=(default)",
        "--format=json",
    ]
    code, stdout, stderr = _run_gcloud(command)
    if code != 0:
        print(
            "[FAIL] Firestore-Status konnte nicht abgefragt werden. "
            f"gcloud Fehler: {stderr or stdout}"
        )
        return False

    payload = json.loads(stdout)
    database_type = payload.get("type")
    if database_type == "FIRESTORE_NATIVE":
        print("[PASS] Firestore ist im Native Mode aktiviert.")
        return True

    print(
        "[FAIL] Firestore ist nicht im Native Mode aktiviert. "
        f"Aktueller Typ: {database_type!r}"
    )
    return False


def _check_service_account_roles(project_id: str, service_account_email: str) -> bool:
    command = [
        "gcloud",
        "projects",
        "get-iam-policy",
        project_id,
        "--flatten=bindings[].members",
        f"--filter=bindings.members:serviceAccount:{service_account_email}",
        "--format=value(bindings.role)",
    ]
    code, stdout, stderr = _run_gcloud(command)
    if code != 0:
        print(
            "[FAIL] IAM-Rollen konnten nicht abgefragt werden. "
            f"gcloud Fehler: {stderr or stdout}"
        )
        return False

    roles = {line.strip() for line in stdout.splitlines() if line.strip()}
    least_privilege_roles = {
        "roles/datastore.user",
        "roles/firestore.user",
    }

    if roles & least_privilege_roles:
        matched_roles = ", ".join(sorted(roles & least_privilege_roles))
        print(
            "[PASS] Least-Privilege Firestore-Rolle vorhanden: "
            f"{matched_roles}."
        )
        return True

    print(
        "[FAIL] Keine passende Firestore-Rolle gefunden. "
        "Erwartet mindestens eine der Rollen "
        "roles/datastore.user oder roles/firestore.user. "
        f"Gefunden: {', '.join(sorted(roles)) or 'keine'}"
    )
    return False


def _check_init_firebase_service_account(service_account: dict[str, Any]) -> bool:
    try:
        import firebase_admin
    except ImportError:
        print(
            "[FAIL] firebase_admin ist nicht installiert. "
            "Bitte `pip install -r requirements.txt` ausführen."
        )
        return False

    from storage import init_firebase

    init_firebase()
    app = firebase_admin.get_app()
    google_credential = app.credential.get_credential()

    current_email = getattr(google_credential, "service_account_email", "")
    expected_email = str(service_account["client_email"])

    if current_email == expected_email:
        print(
            "[PASS] init_firebase() nutzt dasselbe gcp_service_account "
            f"({expected_email})."
        )
        return True

    print(
        "[FAIL] init_firebase() nutzt ein anderes Service Account Credential. "
        f"Erwartet: {expected_email}, tatsächlich: {current_email or 'unbekannt'}"
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prüft Firestore-Prerequisites für 9 Freunde.",
    )
    parser.add_argument(
        "--secrets",
        default=".streamlit/secrets.toml",
        help="Pfad zur secrets.toml (Default: .streamlit/secrets.toml)",
    )
    args = parser.parse_args()

    secrets_path = Path(args.secrets)
    if not secrets_path.exists():
        print(f"[FAIL] secrets.toml nicht gefunden: {secrets_path}")
        return 1

    try:
        service_account = _load_service_account(secrets_path)
    except ValueError as error:
        print(f"[FAIL] {error}")
        return 1

    project_id = str(service_account["project_id"])
    service_account_email = str(service_account["client_email"])

    checks = [
        _check_firestore_native_mode(project_id),
        _check_service_account_roles(project_id, service_account_email),
        _check_init_firebase_service_account(service_account),
    ]

    if all(checks):
        print("\nAlle Firestore-Prerequisites sind erfüllt.")
        return 0

    print("\nMindestens ein Firestore-Check ist fehlgeschlagen.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
