"""HTTP API for the multi-agent orchestrator.

Exposes the fleet to a web portal with full workflow visibility:

* ``GET  /health``            — runtime status.
* ``GET  /agents``            — the 15 agents (id, name, KB, tools).
* ``GET  /agents/{id}``       — one agent's full definition + prompt.
* ``GET  /tools``             — OpenAI-format schemas for every tool.
* ``GET  /intents``           — intent → agent-chain routing table.
* ``POST /chat``              — run a request; returns the full structured
                                workflow (intent, chain, per-agent steps, every
                                tool call + result, final answer, event log).
* ``GET  /chat/stream``       — the SAME run as a live Server-Sent-Events stream,
                                one event per workflow step, for real-time UI.
* ``GET  /``                  — a self-contained reference UI that renders the
                                live workflow (served from ``web/index.html``).

Auto-generated OpenAPI docs live at ``/docs`` and ``/openapi.json`` — hand those
to whoever integrates the portal.

Requires ``fastapi`` + ``uvicorn`` (``pip install -r agents/requirements.txt``).
The core package never imports this module, so the CLI/smoke test stay
dependency-free.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .definitions import ALL_AGENTS, INTENT_ROUTING, get_agent
from .events import EVENT_TYPES, ListSink, QueueSink
from .llm import build_client
from .orchestrator import Orchestrator, OrchestratorResult
from .settings import SETTINGS
from .tools import TOOL_SCHEMAS
from . import __version__

_WEB_DIR = Path(__file__).resolve().parent / "web"


# ═══════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    message: str = Field(..., description="The customer's message.")
    session_id: Optional[str] = Field(
        None, description="Optional id to carry entities (PNR, name) across turns.")


class ToolCallModel(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: Any
    simulated: bool = False
    error: bool = False


class StepModel(BaseModel):
    agent_id: str
    agent_name: str
    content: str
    backend: str
    tools: list[ToolCallModel] = []


class ChatResponse(BaseModel):
    session_id: Optional[str] = None
    message: str
    intent: str
    chain: list[str]
    entities: dict[str, Any]
    escalation: str = ""
    backend: str
    steps: list[StepModel]
    final_answer: str
    events: list[dict[str, Any]]


class AgentInfo(BaseModel):
    id: str
    name: str
    kb: str
    reasoning: str
    description: str
    tools: list[str]


class AgentDetail(AgentInfo):
    system_prompt: str
    tool_schemas: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str
    backend: str
    mcp_mode: str
    agents: int
    intents: int
    event_types: list[str]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════
def _parse(result: str) -> Any:
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result


def _steps_from_result(result: OrchestratorResult) -> list[StepModel]:
    steps: list[StepModel] = []
    for r in result.results:
        tools = []
        for inv in r.tool_calls:
            simulated = '"simulated": true' in inv.result or '"simulated":true' in inv.result
            error = '"error"' in inv.result
            tools.append(ToolCallModel(name=inv.name, arguments=inv.arguments,
                                       result=_parse(inv.result), simulated=simulated,
                                       error=error))
        steps.append(StepModel(agent_id=r.agent_id, agent_name=r.agent_name,
                               content=r.content, backend=r.backend, tools=tools))
    return steps


def _agent_info(defn: Any) -> AgentInfo:
    return AgentInfo(id=defn.id, name=defn.name, kb=defn.kb, reasoning=defn.reasoning,
                     description=defn.description, tools=list(defn.tools))


# ─── lightweight in-memory session store (entity carry-over) ────────────
class _SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}

    def entities(self, session_id: Optional[str]) -> dict[str, Any]:
        if not session_id:
            return {}
        with self._lock:
            return dict(self._data.get(session_id, {}))

    def update(self, session_id: Optional[str], entities: dict[str, Any]) -> None:
        if not session_id:
            return
        with self._lock:
            self._data.setdefault(session_id, {}).update(entities)


# ═══════════════════════════════════════════════════════════════════════
# App factory
# ═══════════════════════════════════════════════════════════════════════
def build_app() -> FastAPI:
    app = FastAPI(
        title="Nevio Service Center — Multi-Agent Orchestrator API",
        version=__version__,
        description="REST + SSE API exposing the 15-agent airline service-center fleet.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=SETTINGS.cors_origin_list(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # A shared LLM client (constructed once); a fresh Orchestrator per request.
    shared_llm = build_client(SETTINGS)
    backend_label = shared_llm.model_label if shared_llm else "heuristic"
    sessions = _SessionStore()

    def _orchestrator() -> Orchestrator:
        return Orchestrator(llm=shared_llm)

    # ── optional bearer auth ────────────────────────────────────────────
    def _auth(authorization: str | None = Header(default=None)) -> None:
        if not SETTINGS.api_key:
            return
        expected = f"Bearer {SETTINGS.api_key}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    guard = [Depends(_auth)]

    # ── static reference UI ─────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        path = _WEB_DIR / "index.html"
        if path.is_file():
            return HTMLResponse(path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Nevio agents API</h1><p>See <a href='/docs'>/docs</a>.</p>")

    # ── introspection ───────────────────────────────────────────────────
    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="healthy", version=__version__, backend=backend_label,
            mcp_mode=SETTINGS.mcp_mode, agents=len(ALL_AGENTS),
            intents=len(INTENT_ROUTING), event_types=list(EVENT_TYPES),
        )

    @app.get("/agents", response_model=list[AgentInfo], dependencies=guard)
    def list_agents() -> list[AgentInfo]:
        return [_agent_info(a) for a in ALL_AGENTS]

    @app.get("/agents/{agent_id}", response_model=AgentDetail, dependencies=guard)
    def agent_detail(agent_id: str) -> AgentDetail:
        try:
            defn = get_agent(agent_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_id}'")
        base = _agent_info(defn)
        return AgentDetail(
            **base.model_dump(), system_prompt=defn.system_prompt,
            tool_schemas=[TOOL_SCHEMAS[t] for t in defn.tools if t in TOOL_SCHEMAS],
        )

    @app.get("/tools", dependencies=guard)
    def list_tools() -> dict[str, Any]:
        return {"total": len(TOOL_SCHEMAS), "tools": list(TOOL_SCHEMAS.values())}

    @app.get("/intents", dependencies=guard)
    def list_intents() -> dict[str, list[str]]:
        return INTENT_ROUTING

    # ── synchronous chat (full workflow in one response) ────────────────
    @app.post("/chat", response_model=ChatResponse, dependencies=guard)
    def chat(req: ChatRequest) -> ChatResponse:
        sink = ListSink()
        prior = sessions.entities(req.session_id)
        result = _orchestrator().handle(req.message, sink=sink, prior_entities=prior)
        sessions.update(req.session_id, result.entities)
        return ChatResponse(
            session_id=req.session_id, message=req.message, intent=result.intent,
            chain=result.chain, entities=result.entities, escalation=result.escalation,
            backend=result.backend, steps=_steps_from_result(result),
            final_answer=result.final_answer, events=sink.as_dicts(),
        )

    # ── streaming chat (live SSE workflow) ──────────────────────────────
    @app.get("/chat/stream", dependencies=guard)
    def chat_stream(message: str, session_id: str | None = None) -> StreamingResponse:
        def gen():
            q: queue.Queue = queue.Queue()
            sink = QueueSink(q)
            prior = sessions.entities(session_id)

            def run() -> None:
                try:
                    result = _orchestrator().handle(message, sink=sink, prior_entities=prior)
                    sessions.update(session_id, result.entities)
                except Exception as exc:  # noqa: BLE001
                    sink.emit("error", message=str(exc))
                finally:
                    q.put(None)

            threading.Thread(target=run, daemon=True).start()
            yield ": stream open\n\n"  # prime the connection
            while True:
                item = q.get()
                if item is None:
                    yield "event: done\ndata: {}\n\n"
                    break
                yield f"data: {json.dumps(item.to_dict(), ensure_ascii=False)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        })

    return app
