from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document

from config import AppConfig, LocalConfig, OpenAIConfig
from documents import DocumentAgent


def _doc_text(doc_bytes: bytes) -> str:
    document = Document(BytesIO(doc_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _agent(monkeypatch) -> DocumentAgent:
    app_config = AppConfig(
        storage_mode="local",
        google=None,
        local=LocalConfig(
            data_dir=Path("data"),
            stammdaten_file=Path("data/Stammdaten_Eltern_2026.ods"),
            content_pages_file=Path("data/content_pages.json"),
            calendar_file=Path("data/calendar.json"),
            drive_root=Path("data/drive"),
        ),
        openai=OpenAIConfig(
            api_key=None,
            model_fast="gpt-4o-mini",
            model_precise="o3-mini",
            precision_mode="fast",
            timeout_seconds=60.0,
            max_retries=1,
            reasoning_effort="low",
            base_url=None,
            vector_store_id=None,
            enable_web_search=False,
        ),
    )
    monkeypatch.setattr("documents.get_app_config", lambda: app_config)
    return DocumentAgent()


def test_generate_care_contract_defaults_to_german(monkeypatch) -> None:
    agent = _agent(monkeypatch)

    doc_bytes, filename = agent.generate_care_contract({"name": "Mia"})

    text = _doc_text(doc_bytes)
    assert "Betreuungsvertrag" in text
    assert "Childcare Contract" not in text
    assert filename.startswith("Betreuungsvertrag_Mia_")


def test_generate_care_contract_in_english_and_draft(monkeypatch) -> None:
    agent = _agent(monkeypatch)

    doc_bytes, filename = agent.generate_care_contract(
        {"name": "Mia", "notes_parent_visible": "Bring raincoat"},
        language="en",
        is_draft=True,
    )

    text = _doc_text(doc_bytes)
    assert "ENTWURF / DRAFT" in text
    assert "Childcare Contract" in text
    assert "Betreuungsvertrag" not in text
    assert filename.startswith("Contract_Mia_")
    assert filename.endswith("_Entwurf.docx")


def test_generate_document_supports_language_and_draft(monkeypatch) -> None:
    agent = _agent(monkeypatch)

    def _fake_generate_with_retry(prompt: str) -> dict[str, str]:
        assert "Write the report fully in English." in prompt
        return {"title": "Weekly report", "body": "Everything went well."}

    monkeypatch.setattr(agent, "_generate_with_retry", _fake_generate_with_retry)

    doc_bytes, filename = agent.generate_document(
        {"name": "Luca"},
        "Had a great day.",
        language="en",
        is_draft=True,
    )

    text = _doc_text(doc_bytes)
    assert "ENTWURF / DRAFT" in text
    assert "Date:" in text
    assert "Weekly report" in text
    assert filename.startswith("Report_Luca_")
    assert filename.endswith("_Entwurf.docx")
