"""LLM client wrapper.

Kept behind a tiny interface so the SQL generator and summariser don't depend
on a specific provider. The Gemini adapter is selected via ``LLM_PROVIDER``.
"""

from __future__ import annotations

from typing import Protocol

from google import genai
from google.genai import errors, types

from .config import settings


class LLMError(Exception):
    """Raised when the LLM call fails or is misconfigured."""


Message = dict[str, str]


class LLM(Protocol):
    def complete(self, system: str, messages: list[Message], max_tokens: int) -> str:
        ...


class GeminiLLM:
    """Adapter over the Google Gemini generate-content API."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        if not api_key:
            raise LLMError("LLM client not configured. Set GEMINI_API_KEY.")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def complete(
        self, system: str, messages: list[Message], max_tokens: int = 1024
    ) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    types.Content(
                        role="model" if message["role"] == "assistant" else "user",
                        parts=[types.Part.from_text(text=message["content"])],
                    )
                    for message in messages
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                ),
            )
        except errors.APIError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        try:
            text = response.text
        except ValueError as exc:
            raise LLMError(f"LLM returned no text response: {exc}") from exc
        if not text or not text.strip():
            raise LLMError("LLM returned no text response.")
        return text.strip()


def get_llm() -> LLM:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return GeminiLLM(model=settings.llm_model, api_key=settings.gemini_api_key)
    raise LLMError(
        f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
        "Only 'gemini' is implemented."
    )
