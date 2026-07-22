"""Runtime configuration for the multi-agent orchestrator.

All settings are read from environment variables (a local ``.env`` is loaded
automatically if present). Nothing here requires credentials to *import* — the
orchestrator degrades gracefully to a heuristic, offline mode when no LLM
backend is configured, so the fleet can be demonstrated without any keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ─── Repo layout ────────────────────────────────────────────────────────
# agents/settings.py  ->  repo root is the parent of the agents package.
REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge-docs-v1"
MCP_DIR = REPO_ROOT / "mcp"


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency).

    Looks for ``agents/.env`` then repo-root ``.env``. Existing environment
    variables always win, so real env config is never clobbered.
    """
    for candidate in (Path(__file__).resolve().parent / ".env", REPO_ROOT / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    return _env(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Resolved orchestrator settings."""

    # ── LLM backend selection ───────────────────────────────────────────
    # "azure" | "openai" | "auto" | "heuristic"
    # "auto" picks azure if AZURE_OPENAI_* is set, else openai if OPENAI_API_KEY
    # is set, else falls back to the dependency-free heuristic engine.
    llm_backend: str = field(default_factory=lambda: _env("LLM_BACKEND", "auto").lower())

    # Azure OpenAI (matches the README's GPT-4o deployment)
    azure_endpoint: str = field(default_factory=lambda: _env("AZURE_OPENAI_ENDPOINT"))
    azure_api_key: str = field(default_factory=lambda: _env("AZURE_OPENAI_API_KEY"))
    azure_deployment: str = field(default_factory=lambda: _env("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"))
    azure_api_version: str = field(
        default_factory=lambda: _env("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    )

    # Standard OpenAI (fallback backend)
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o"))

    # Sampling
    temperature: float = field(default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.2")))
    max_tokens: int = field(default_factory=lambda: int(_env("LLM_MAX_TOKENS", "1024")))
    max_tool_iterations: int = field(default_factory=lambda: int(_env("MAX_TOOL_ITERATIONS", "6")))

    # ── MCP booking bridge ──────────────────────────────────────────────
    # "inprocess" imports mcp/src/tools/booking_tools.py directly (real APIM).
    # "http" calls a running SSE server's REST API (MCP_HTTP_URL).
    # "mock" returns canned sample data so the flow runs fully offline.
    mcp_mode: str = field(default_factory=lambda: _env("MCP_MODE", "inprocess").lower())
    mcp_http_url: str = field(default_factory=lambda: _env("MCP_HTTP_URL", "http://127.0.0.1:3100"))
    mcp_api_key: str = field(default_factory=lambda: _env("MCP_API_KEY"))

    # Knowledge retrieval
    kb_top_k: int = field(default_factory=lambda: int(_env("KB_TOP_K", "4")))

    # ── HTTP API ────────────────────────────────────────────────────────
    api_host: str = field(default_factory=lambda: _env("AGENTS_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(_env("AGENTS_API_PORT", "8100")))
    # Comma-separated allowed origins for browser portals; "*" allows all.
    cors_origins: str = field(default_factory=lambda: _env("AGENTS_CORS_ORIGINS", "*"))
    # Optional bearer token to protect the API (empty = open).
    api_key: str = field(default_factory=lambda: _env("AGENTS_API_KEY"))

    verbose: bool = field(default_factory=lambda: _env_bool("AGENTS_VERBOSE", False))

    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    def resolved_backend(self) -> str:
        """Resolve the effective backend, honoring 'auto'."""
        if self.llm_backend == "auto":
            if self.azure_endpoint and self.azure_api_key:
                return "azure"
            if self.openai_api_key:
                return "openai"
            return "heuristic"
        return self.llm_backend


SETTINGS = Settings()
