"""Zentraler Service für OpenAI Responses API Aufrufe."""

from __future__ import annotations

import logging
import random
import time
from typing import Any, TypeVar

from openai import (
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel

from config import OpenAIConfig

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMServiceError(RuntimeError):
    """Fehler bei Aufrufen an den LLM-Service."""

    def __init__(self, message: str, *, category: str = "unknown") -> None:
        super().__init__(message)
        self.category = category


class LLMService:
    """Kapselt Responses API, Tooling und Retry/Timeout-Handling."""

    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config
        self.client = self._build_client()

    def _build_client(self) -> OpenAI | None:
        if not self.config.api_key:
            return None

        kwargs: dict[str, Any] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout_seconds,
        }
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        return OpenAI(**kwargs)

    @property
    def selected_model(self) -> str:
        if self.config.precision_mode == "precise":
            return self.config.model_precise
        return self.config.model_fast

    def _build_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        if self.config.vector_store_id:
            tools.append(
                {
                    "type": "file_search",
                    "vector_store_ids": [self.config.vector_store_id],
                }
            )
        if self.config.enable_web_search:
            tools.append({"type": "web_search_preview"})
        return tools

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT],
        operation_name: str,
    ) -> ResponseModelT:
        if not self.client:
            raise LLMServiceError(
                "OpenAI API key is missing. Please set [openai].api_key in secrets.toml "
                "or OPENAI_API_KEY.",
                category="auth",
            )

        schema = response_model.model_json_schema()
        tools = self._build_tools()
        fallback_tools = [
            tool for tool in tools if str(tool.get("type", "")) != "web_search_preview"
        ]
        used_tool_fallback = False
        last_error: Exception | None = None
        error_category = "unknown"

        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=self.selected_model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    reasoning={"effort": self.config.reasoning_effort},
                    tools=tools,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": operation_name,
                            "schema": schema,
                            "strict": True,
                        }
                    },
                )
                payload = response.output_parsed
                if isinstance(payload, response_model):
                    return payload
                if not isinstance(payload, dict):
                    raise LLMServiceError(
                        "Die KI-Antwort konnte nicht strukturiert verarbeitet werden.",
                        category="invalid_response",
                    )
                return response_model.model_validate(payload)
            except (APITimeoutError, RateLimitError) as exc:
                last_error = exc
                error_category = "timeout_or_rate_limit"
            except (AuthenticationError, PermissionDeniedError) as exc:
                last_error = exc
                error_category = "auth"
                break
            except BadRequestError as exc:
                last_error = exc
                error_message = str(exc).lower()
                is_web_tool_error = "web_search_preview" in error_message or (
                    "tool" in error_message
                    and "not" in error_message
                    and "allow" in error_message
                )
                if is_web_tool_error:
                    error_category = "tool_not_allowed"
                    if (
                        not used_tool_fallback
                        and len(fallback_tools) != len(tools)
                        and any(
                            str(tool.get("type", "")) == "web_search_preview"
                            for tool in tools
                        )
                    ):
                        used_tool_fallback = True
                        tools = fallback_tools
                        continue
                else:
                    error_category = "invalid_request"
                break
            except OpenAIError as exc:
                last_error = exc
                error_category = "unknown"
                break

            if attempt < self.config.max_retries:
                delay_seconds = min(6.0, (2**attempt) + random.uniform(0.0, 0.4))
                time.sleep(delay_seconds)

        logger.warning(
            "LLM request failed [category=%s, attempt=%s, model=%s, operation=%s]",
            error_category,
            self.config.max_retries + 1,
            self.selected_model,
            operation_name,
        )
        raise LLMServiceError(
            "OpenAI request failed.",
            category=error_category,
        ) from last_error
