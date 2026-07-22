"""LLM backend abstraction.

Supports Azure OpenAI (the README's GPT-4o deployment) and standard OpenAI via
the same ``openai`` SDK and the same OpenAI tool-calling wire format. When no
backend is configured, :func:`build_client` returns ``None`` and the
orchestrator falls back to a deterministic heuristic engine so the whole fleet
still runs offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .settings import Settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AssistantTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    model_label: str

    def chat(self, messages: list[dict[str, Any]],
             tools: list[dict[str, Any]] | None = None) -> AssistantTurn: ...


# ═══════════════════════════════════════════════════════════════════════
# OpenAI-family client (Azure + standard OpenAI share this response parsing)
# ═══════════════════════════════════════════════════════════════════════


def _parse_openai_response(response: Any) -> AssistantTurn:
    import json

    choice = response.choices[0]
    msg = choice.message
    calls: list[ToolCall] = []
    for tc in (getattr(msg, "tool_calls", None) or []):
        try:
            args = json.loads(tc.function.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {}
        calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
    return AssistantTurn(content=msg.content, tool_calls=calls)


class _OpenAIFamilyClient:
    def __init__(self, client: Any, model: str, settings: Settings, label: str):
        self._client = client
        self._model = model
        self._settings = settings
        self.model_label = label

    def chat(self, messages: list[dict[str, Any]],
             tools: list[dict[str, Any]] | None = None) -> AssistantTurn:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._settings.temperature,
            "max_tokens": self._settings.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        response = self._client.chat.completions.create(**kwargs)
        return _parse_openai_response(response)


def _build_azure(settings: Settings) -> LLMClient:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key,
        api_version=settings.azure_api_version,
    )
    return _OpenAIFamilyClient(
        client, settings.azure_deployment, settings,
        label=f"azure:{settings.azure_deployment}",
    )


def _build_openai(settings: Settings) -> LLMClient:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    return _OpenAIFamilyClient(
        client, settings.openai_model, settings,
        label=f"openai:{settings.openai_model}",
    )


def build_client(settings: Settings) -> LLMClient | None:
    """Construct the configured LLM client, or ``None`` for heuristic mode.

    Never raises on a missing SDK — if the backend is selected but the ``openai``
    package or credentials are unavailable, returns ``None`` so the caller falls
    back to the heuristic engine.
    """
    backend = settings.resolved_backend()
    if backend == "heuristic":
        return None
    try:
        if backend == "azure":
            return _build_azure(settings)
        if backend == "openai":
            return _build_openai(settings)
    except Exception:  # noqa: BLE001 — missing SDK/creds -> heuristic fallback
        return None
    return None
