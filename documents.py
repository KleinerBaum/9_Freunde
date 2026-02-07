"""DocumentAgent für KI-gestützte Berichte via OpenAI Responses API."""

from __future__ import annotations

import random
import time
from datetime import datetime
from io import BytesIO
from typing import Any

from docx import Document
from openai import APITimeoutError, OpenAI, OpenAIError, RateLimitError

from config import OpenAIConfig, get_app_config


class DocumentGenerationError(RuntimeError):
    """Domänenspezifischer Fehler bei Dokumentenerstellung."""


class DocumentAgent:
    """Erstellt Berichte auf Basis von Notizen und Kinddaten."""

    def __init__(self) -> None:
        app_config = get_app_config()
        self.openai_config: OpenAIConfig = app_config.openai
        self.client = self._build_client()

    def _build_client(self) -> OpenAI | None:
        if not self.openai_config.api_key:
            return None

        kwargs: dict[str, Any] = {
            "api_key": self.openai_config.api_key,
            "timeout": self.openai_config.timeout_seconds,
        }
        if self.openai_config.base_url:
            kwargs["base_url"] = self.openai_config.base_url
        return OpenAI(**kwargs)

    @property
    def selected_model(self) -> str:
        if self.openai_config.precision_mode == "precise":
            return self.openai_config.model_precise
        return self.openai_config.model_fast

    def _build_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        if self.openai_config.vector_store_id:
            tools.append(
                {
                    "type": "file_search",
                    "vector_store_ids": [self.openai_config.vector_store_id],
                }
            )
        if self.openai_config.enable_web_search:
            tools.append({"type": "web_search_preview"})
        return tools

    def _response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": "parent_report",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def _generate_with_retry(self, prompt: str) -> dict[str, str]:
        if not self.client:
            raise DocumentGenerationError(
                "OpenAI API-Schlüssel fehlt. Bitte [openai].api_key in secrets.toml "
                "oder OPENAI_API_KEY setzen.\n"
                "OpenAI API key is missing. Please set [openai].api_key in secrets.toml "
                "or OPENAI_API_KEY."
            )

        tools = self._build_tools()
        last_error: Exception | None = None

        for attempt in range(self.openai_config.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=self.selected_model,
                    input=[
                        {
                            "role": "system",
                            "content": "Du bist eine professionelle pädagogische Assistenz. "
                            "Schreibe warmherzige, klare Elternkommunikation.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    reasoning={"effort": self.openai_config.reasoning_effort},
                    tools=tools,
                    text={"format": self._response_format()},
                )

                payload = response.output_parsed
                if not isinstance(payload, dict):
                    raise DocumentGenerationError(
                        "Die KI-Antwort konnte nicht strukturiert verarbeitet werden."
                    )

                title = str(payload.get("title", "")).strip()
                body = str(payload.get("body", "")).strip()
                if not title or not body:
                    raise DocumentGenerationError(
                        "Die KI-Antwort ist unvollständig. Bitte erneut versuchen."
                    )
                return {"title": title, "body": body}
            except (APITimeoutError, RateLimitError) as exc:
                last_error = exc
            except OpenAIError as exc:
                last_error = exc
                break

            if attempt < self.openai_config.max_retries:
                delay_seconds = min(6.0, (2**attempt) + random.uniform(0.0, 0.4))
                time.sleep(delay_seconds)

        raise DocumentGenerationError(
            "Die Dokumentenerstellung mit OpenAI ist fehlgeschlagen. Bitte später erneut "
            "versuchen oder Konfiguration prüfen.\n"
            "OpenAI document generation failed. Please retry later or verify configuration."
        ) from last_error

    def generate_document(
        self, child_data: dict[str, Any], notes: str
    ) -> tuple[bytes, str]:
        """Generiert einen Dokumenttext mit OpenAI und erstellt ein Word-Dokument."""
        child_name = str(child_data.get("name", "Ihr Kind")).strip() or "Ihr Kind"
        prompt = (
            f"Erstelle einen Elternbericht für {child_name}.\n"
            f"Notizen der Betreuungsperson:\n{notes.strip()}\n\n"
            "Nutze einen positiven, klaren Stil. Gib nur valides JSON gemäß Schema zurück."
        )

        result = self._generate_with_retry(prompt)

        doc = Document()
        doc.add_heading(result["title"], level=1)
        today_str = datetime.now().strftime("%d.%m.%Y")
        doc.add_paragraph(f"Datum: {today_str}")
        doc.add_paragraph("")
        doc.add_paragraph(result["body"])

        output = BytesIO()
        doc.save(output)
        doc_bytes = output.getvalue()

        safe_name = child_name.replace(" ", "_")
        date_stamp = datetime.now().strftime("%Y%m%d")
        file_name = f"Bericht_{safe_name}_{date_stamp}.docx"
        return doc_bytes, file_name
