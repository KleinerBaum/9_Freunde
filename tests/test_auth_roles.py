from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_auth_module():
    module_path = Path(__file__).resolve().parents[1] / "auth.py"
    spec = importlib.util.spec_from_file_location("auth_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_agent_assigns_admin_and_parent_roles(monkeypatch) -> None:
    auth_module = _load_auth_module()
    monkeypatch.setattr(
        auth_module.st,
        "secrets",
        {
            "auth": {
                "users": {
                    "admin@example.org": "secret",
                    "parent@example.org": "secret",
                },
                "admin_emails": ["admin@example.org"],
            },
            "app": {},
        },
    )

    agent = auth_module.AuthAgent()

    assert agent.login("admin@example.org", "secret") == "admin"
    assert agent.login("parent@example.org", "secret") == "parent"


def test_communication_menu_available_only_for_admin() -> None:
    app_source = Path("app.py").read_text(encoding="utf-8")

    assert '"communication": "💬 Kommunikation / Communication"' in app_source
    parent_menu_fragment = app_source.split("parent_menu_labels", maxsplit=1)[1]
    assert (
        '"communication"'
        not in parent_menu_fragment.split("parent_options =", maxsplit=1)[0]
    )
