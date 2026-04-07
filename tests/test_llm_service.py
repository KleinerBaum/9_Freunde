from __future__ import annotations

from config import OpenAIConfig
from services.llm_models import ParentReport
from services.llm_service import LLMService


class _FakeResponses:
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload
        self.last_kwargs: dict[str, object] | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs

        class _Response:
            output_parsed = self._payload

        return _Response()


class _FakeClient:
    def __init__(self, payload: dict[str, str]) -> None:
        self.responses = _FakeResponses(payload)


def _config(*, vector_store_id: str | None) -> OpenAIConfig:
    return OpenAIConfig(
        api_key="test-key",
        model_fast="gpt-4o-mini",
        model_precise="o3-mini",
        precision_mode="fast",
        timeout_seconds=30.0,
        max_retries=0,
        reasoning_effort="medium",
        base_url=None,
        vector_store_id=vector_store_id,
        enable_web_search=False,
    )


def test_generate_structured_uses_schema_and_model_validation() -> None:
    service = LLMService(_config(vector_store_id=None))
    fake_client = _FakeClient({"title": "Titel", "body": "Inhalt"})
    service.client = fake_client  # type: ignore[assignment]

    response = service.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        response_model=ParentReport,
        operation_name="parent_report",
    )

    assert isinstance(response, ParentReport)
    assert response.title == "Titel"
    assert fake_client.responses.last_kwargs is not None
    text_format = fake_client.responses.last_kwargs["text"]
    assert isinstance(text_format, dict)
    assert text_format["format"]["type"] == "json_schema"


def test_file_search_tool_only_when_vector_store_present() -> None:
    service_without_vector_store = LLMService(_config(vector_store_id=None))
    service_with_vector_store = LLMService(_config(vector_store_id="vs_123"))

    assert service_without_vector_store._build_tools() == []
    assert service_with_vector_store._build_tools() == [
        {"type": "file_search", "vector_store_ids": ["vs_123"]}
    ]
