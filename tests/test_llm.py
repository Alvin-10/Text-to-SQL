"""Gemini adapter tests without network access or an API key."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.genai import errors, types

import app.llm as llm_module
from app.llm import GeminiLLM, LLMError, get_llm


def test_complete_sends_system_instruction_and_maps_chat_roles(monkeypatch):
    generate_content = Mock(return_value=SimpleNamespace(text="  SELECT 1  "))
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(llm_module.genai, "Client", Mock(return_value=client))
    llm = GeminiLLM(model="gemini-test", api_key="test-key")

    result = llm.complete(
        "System prompt",
        [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Prior answer"},
        ],
        max_tokens=300,
    )

    assert result == "SELECT 1"
    kwargs = generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-test"
    assert kwargs["contents"] == [
        types.Content(role="user", parts=[types.Part.from_text(text="Question")]),
        types.Content(role="model", parts=[types.Part.from_text(text="Prior answer")]),
    ]
    assert kwargs["config"].system_instruction == "System prompt"
    assert kwargs["config"].max_output_tokens == 300


def test_missing_api_key_is_reported():
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        GeminiLLM(model="gemini-test")


def test_api_errors_are_wrapped_as_llm_errors(monkeypatch):
    generate_content = Mock(
        side_effect=errors.APIError(code=401, response_json={"message": "unauthorized"})
    )
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(llm_module.genai, "Client", Mock(return_value=client))
    llm = GeminiLLM(model="gemini-test", api_key="test-key")

    with pytest.raises(LLMError, match="LLM request failed"):
        llm.complete("System prompt", [{"role": "user", "content": "Question"}])


def test_get_llm_uses_gemini_settings(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "llm_provider", "gemini")
    monkeypatch.setattr(llm_module.settings, "llm_model", "gemini-test")
    monkeypatch.setattr(llm_module.settings, "gemini_api_key", "test-key")
    client = SimpleNamespace(models=SimpleNamespace())
    create_client = Mock(return_value=client)
    monkeypatch.setattr(llm_module.genai, "Client", create_client)

    llm = get_llm()

    assert isinstance(llm, GeminiLLM)
    create_client.assert_called_once_with(api_key="test-key")


def test_get_llm_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "llm_provider", "unknown")

    with pytest.raises(LLMError, match="Only 'gemini' is implemented"):
        get_llm()
