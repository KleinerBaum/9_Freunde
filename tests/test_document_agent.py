from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import date, datetime
import json

from docx import Document
import pytest

from config import AppConfig, LocalConfig, OpenAIConfig
from documents import DocumentAgent, DocumentGenerationError


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


def test_build_standardized_filename(monkeypatch) -> None:
    agent = _agent(monkeypatch)
    file_name = agent.build_standardized_filename(
        child_id="child-1",
        document_type="monthly_invoice",
        extension="pdf",
        generated_on=datetime(2026, 4, 7),
    )
    assert file_name == "20260407_child-1_monthly_invoice.pdf"


def test_wizard_exports(monkeypatch) -> None:
    agent = _agent(monkeypatch)
    payload = agent.build_wizard_payload(
        child_data={"id": "c1", "name": "Mia", "parent_email": "mia@example.org"},
        document_type="contract",
        contract_partner="Mia Familie",
        billing_month="2026-04",
        monthly_amount_eur=250.0,
        language="de",
        ai_text_suggestion="Entwurfstext",
    )

    docx_bytes, docx_name = agent.export_wizard_docx(payload)
    pdf_bytes, pdf_name = agent.export_wizard_pdf(payload)
    json_bytes, json_name = agent.export_wizard_json(payload)
    md_bytes, md_name = agent.export_wizard_markdown(payload)

    assert docx_name.endswith("_contract.docx")
    assert pdf_name.endswith("_contract.pdf")
    assert json_name.endswith("_contract.json")
    assert md_name.endswith("_contract.md")
    assert len(docx_bytes) > 100
    assert len(pdf_bytes) > 100
    assert json.loads(json_bytes.decode("utf-8"))["child"]["id"] == "c1"
    assert "AI Draft" in md_bytes.decode("utf-8")


def test_generate_food_allowance_invoice_validates_period(monkeypatch) -> None:
    agent = _agent(monkeypatch)

    with pytest.raises(DocumentGenerationError):
        agent.generate_food_allowance_invoice(
            {"name": "Mia"},
            period_start=date(2026, 5, 1),
            period_end=date(2026, 4, 1),
            monthly_amount_eur=120.0,
        )


def test_generate_food_allowance_invoice_contains_billing_content(monkeypatch) -> None:
    agent = _agent(monkeypatch)

    doc_bytes, filename = agent.generate_food_allowance_invoice(
        {"name": "Mia", "parent_email": "eltern@example.org"},
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        monthly_amount_eur=120.0,
    )

    text = _doc_text(doc_bytes)
    assert "Food allowance invoice" in text
    assert "eltern@example.org" in text
    assert filename.startswith("Lebensmittelpauschale_Mia_")
