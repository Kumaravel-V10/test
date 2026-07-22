# Nevio Service Center — Multi-Agent Orchestrator

A runnable implementation of the **15-agent airline service-center fleet** described
in the repository's top-level [`README.md`](../README.md). It is the missing
"Phase 7" piece — the Python orchestrator that ties the agents, the knowledge
base, and the Create-Booking MCP server together.

```
                          customer message
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │  Supervisor-Orchestrator-Agent │  intent + entities + escalation
                 └───────────────┬───────────────┘
                                 │ routes / chains
   ┌───────────────┬─────────────┼─────────────┬───────────────┐
   ▼               ▼             ▼             ▼               ▼
Booking-        Create-       Name-         Refund →        Disruption-   … 14 specialists
Retrieval       Booking       Change        Refund-workflow  Rebooking
   │               │             │             │               │
   └───────────────┴─────────────┴─────────────┴───────────────┘
                                 │ tools
              ┌──────────────────┴──────────────────┐
              ▼                                      ▼
   Create-Booking MCP server (../mcp)      Knowledge base (../knowledge-docs-v1)
   10 live booking tools via APIM          19 docs, retrieved per request
```

## What it does

- **Supervisor** classifies the customer's intent, extracts entities (PNR, last
  name, route, date), detects escalation triggers (fraud/legal/VIP), and routes to
  the correct specialist — chaining several when needed (e.g. name change =
  Booking-Retrieval → Name-Change; cancel+refund = Booking-Retrieval → RefundAgent
  → Refund-workflow).
- **14 specialist agents** each carry the system prompt, knowledge base, and tool
  set from the top-level README.
- **Booking tools are real**: `search_flights … confirm_booking … retrieve_order`
  bridge in-process to `../mcp` and hit the live APIM gateway.
- **Post-order tools** (name change, refund GraphQL, SSR, cases, email, …) are
  wired as **schema-correct simulated handlers** — tagged `"simulated": true` —
  because the MCP server does not expose them yet. Swap each handler body for a
  real API call as those backends come online (see [Extending](#extending)).
- **Runs with no keys and no network** in heuristic + mock mode, so you can see the
  whole fleet route and chain immediately.

## Quick start

```bash
# from the repo root
python -m agents.smoke_test          # offline self-test (no keys, no network)

python -m agents --list              # list the 15 agents
python -m agents --diagnostics       # show backend / KB / MCP status

# one-shot (offline demo: heuristic routing + mock booking data)
MCP_MODE=mock python -m agents -m "Retrieve PNR 9DVWPJ, last name Ibrahim"

# interactive
python -m agents
```

On Windows PowerShell, set env vars per line:

```powershell
$env:MCP_MODE = "mock"; python -m agents -m "I want to cancel booking 9DVWPJ and get a refund"
```

## Web API & portal integration

This is what you wire your web portal to. The HTTP layer exposes the fleet over
REST + Server-Sent-Events so the portal can **show the live workflow** — which
agent is running, every tool call and result, the routing chain — as it happens.

```bash
pip install -r agents/requirements.txt        # fastapi + uvicorn + openai
python -m agents.api_smoke_test                # verify the API offline
python -m agents.server                        # http://127.0.0.1:8100
```

Open **`/`** for the built-in live-workflow console (a reference UI you can copy
from), **`/docs`** for interactive OpenAPI, and **`/openapi.json`** for the spec
to hand your frontend team.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Status, backend, MCP mode, agent/intent counts, event catalogue. |
| `GET` | `/agents` | The 15 agents (id, name, KB, reasoning, tools). |
| `GET` | `/agents/{id}` | One agent's full definition, system prompt, and tool schemas. |
| `GET` | `/tools` | OpenAI-format schema for every tool. |
| `GET` | `/intents` | Intent → agent-chain routing table. |
| `POST` | `/chat` | Run a request; returns the **whole workflow** in one JSON response. |
| `GET` | `/chat/stream` | The same run as a **live SSE stream**, one event per step. |
| `GET` | `/` | Reference live-workflow UI. |

### `POST /chat` — full workflow in one response

```bash
curl -s http://127.0.0.1:8100/chat -H 'Content-Type: application/json' \
  -d '{"message":"Cancel booking 9DVWPJ, last name Ibrahim, and refund me","session_id":"u-42"}'
```

Returns `{ intent, chain, entities, escalation, backend, steps[], final_answer, events[] }`
where each `step` is `{ agent_id, agent_name, content, tools[] }` and each tool is
`{ name, arguments, result, simulated, error }`. Use this if your portal renders
the result after the run completes.

### `GET /chat/stream` — live SSE for the workflow UI

`EventSource`-friendly (GET + query params). Each `data:` frame is one event
`{ type, seq, ts, data }`. Drive your UI straight off the stream:

```js
const es = new EventSource(
  `/chat/stream?message=${encodeURIComponent(text)}&session_id=${sid}`);

es.onmessage = (e) => {
  const { type, data } = JSON.parse(e.data);
  switch (type) {
    case "intent.classified": renderPipeline(data.intent, data.chain); break;
    case "agent.started":     markAgentActive(data.agent_id, data.step, data.total); break;
    case "tool.called":       addToolRow(data.agent_id, data.tool, data.arguments); break;
    case "tool.result":       fillToolRow(data.tool, data.result, data.simulated); break;
    case "agent.completed":   markAgentDone(data.agent_id, data.content); break;
    case "run.completed":     showFinal(data.final_answer); break;
  }
};
es.addEventListener("done", () => es.close());
```

### Event catalogue (the order they fire)

| Event | Key fields | Fires |
|---|---|---|
| `run.started` | `message`, `backend` | once, at start |
| `entities.extracted` | `entities` | after parsing PNR/name/route/date |
| `escalation.detected` | `reason` | only on fraud/legal/VIP triggers |
| `intent.classified` | `intent`, `chain`, `backend` | once routing is decided |
| `agent.started` | `agent_id`, `agent_name`, `step`, `total` | per agent in the chain |
| `tool.called` | `agent_id`, `tool`, `arguments` | per tool invocation |
| `tool.result` | `tool`, `result`, `simulated`, `error` | after each tool returns |
| `agent.completed` | `agent_id`, `content`, `tool_count` | per agent |
| `run.completed` | `final_answer`, `intent`, `chain`, `steps` | once, at end |
| `error` | `message` | on failure |

### Sessions, CORS, auth

- **Sessions**: pass a `session_id` on `/chat` and `/chat/stream`. Entities (PNR,
  last name) carry across turns — a follow-up "cancel it" reuses the earlier PNR.
- **CORS**: set `AGENTS_CORS_ORIGINS=https://portal.example.com` (comma-separated,
  or `*`). Your browser portal on another origin needs this.
- **Auth**: set `AGENTS_API_KEY=…` to require `Authorization: Bearer …` on all
  data endpoints (the UI and `/health` stay open).

## Configuration

Copy [`.env.example`](.env.example) to `agents/.env` (auto-loaded). Everything is
optional — with no config the fleet runs in **heuristic + in-process** mode.

| Setting | Values | Meaning |
|---|---|---|
| `LLM_BACKEND` | `auto` · `azure` · `openai` · `heuristic` | Reasoning engine. `auto` = Azure if `AZURE_OPENAI_*` set, else OpenAI, else heuristic. |
| `AZURE_OPENAI_ENDPOINT` / `_API_KEY` / `_DEPLOYMENT` | — | Azure OpenAI GPT-4o (matches the top-level README). |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — | Standard OpenAI fallback. |
| `MCP_MODE` | `inprocess` · `http` · `mock` | Booking backend. `inprocess` = import `../mcp` (live APIM). `http` = call a running SSE server. `mock` = canned offline data. |
| `MCP_HTTP_URL` / `MCP_API_KEY` | — | For `MCP_MODE=http`. |
| `KB_TOP_K` | int | Knowledge chunks injected per agent turn. |

### The three run modes

| Mode | LLM | Booking tools | Use for |
|---|---|---|---|
| **Offline demo** | heuristic | `MCP_MODE=mock` | Instant, no dependencies. See routing + chaining. |
| **Full reasoning** | Azure/OpenAI | `MCP_MODE=mock` | Natural-language handling, still no live bookings. |
| **Production** | Azure/OpenAI | `MCP_MODE=inprocess` | Real bookings against APIM (`pip install -r ../mcp/requirements.txt`). |

> `confirm_booking` in the MCP server is guarded by `ALLOW_MUTATIONS` (default
> off). Keep it off unless you intend to create real PNRs.

## The 15 agents

| # | Agent | Knowledge base | Key tools |
|---|---|---|---|
| 1 | Supervisor-Orchestrator-Agent | kb-supervisor-orchestrator | `route_to_agent` |
| 2 | Booking-Retrieval-Agent | kb-booking-retrieval | `retrieve_order` |
| 3 | Create-Booking-Agent | kb-create-booking | 10 booking tools (real) |
| 4 | Name-Change-Agent | kb-name-change | `retrieve_order`, `update_passenger_name` |
| 5 | Change-Booking-Agent | kb-change-booking | `quote_change`, `confirm_change` |
| 6 | RefundAgent | kb-refund-agent | `check_refund_eligibility` |
| 7 | Refund-workflow | kb-refund-workflow | `process_refund` |
| 8 | Rebooking-Agent | kb-rebooking | `search_flights`, `create_cart`, `confirm_booking` |
| 9 | Disruption-Rebooking-Agent | kb-disruption-rebooking | `search_alternatives`, `auto_rebook`, `apply_waiver` |
| 10 | Ancillary-Sales-Agent | kb-ancillary-sales | `get_service_catalog`, `add_ancillaries`, seats |
| 11 | Passenger-SSR-Agent | kb-passenger-ssr | `add_ssr`, `remove_ssr`, `list_ssr` |
| 12 | Medical-Exception-Agent | kb-medical-exception | `submit_medical_request`, `check_medical_status` |
| 13 | Payment-Agent | kb-payment | `validate_card`, `process_payment` |
| 14 | Case-Management-Agent | kb-case-management | `create_case`, `update_case`, `close_case` |
| 15 | Communication-Case-Summary-Agent | kb-communication-summary | `generate_summary`, `send_email` |

## Module map

| File | Responsibility |
|---|---|
| `settings.py` | Env/config resolution and repo paths. |
| `knowledge.py` | Dependency-free retrieval over `../knowledge-docs-v1`; KB → doc mapping. |
| `definitions.py` | The 15 agent definitions, intent routing table, keyword classifier. |
| `tools.py` | Tool schemas + implementations; MCP booking bridge; simulated handlers. |
| `llm.py` | Azure OpenAI / OpenAI clients; heuristic fallback selection. |
| `agent.py` | Agent runtime: prompt assembly, KB injection, tool-call loop, event emission. |
| `orchestrator.py` | Supervisor: entity extraction, classification, escalation, chaining. |
| `events.py` | Workflow event stream (types + sinks) consumed by the API/UI. |
| `api.py` | FastAPI app: REST + SSE endpoints, sessions, CORS, auth. |
| `server.py` | `python -m agents.server` — uvicorn entry point. |
| `web/index.html` | Reference live-workflow console served at `/`. |
| `cli.py` / `__main__.py` | `python -m agents` entry point. |
| `smoke_test.py` / `api_smoke_test.py` | Offline end-to-end self-tests (core / API). |

## Extending

**Make a simulated tool real.** Each post-order tool lives in `tools.py` as a
`_t_*` handler returning `"simulated": true`. When the backend exists (e.g. a
name-change or cancel/refund endpoint on the MCP server), replace the handler body
with a real call — the schema, the agent wiring, and the orchestration stay the
same:

```python
def _t_check_refund_eligibility(a: dict) -> str:
    return _call_booking("cancel_and_refund_eligibility", a)   # once the MCP tool exists
```

**Add an agent.** Add an `AgentDefinition` in `definitions.py`, list its tools,
map its intent in `INTENT_ROUTING`, and (optionally) add keyword hints in
`INTENT_KEYWORDS`.

**Move to Azure AI Foundry.** This orchestrator mirrors the top-level README's
Foundry design (same agents, KBs, prompts, and tool schemas). To run the agents as
Foundry-hosted agents instead, point `knowledge.KnowledgeBase.retrieve` at a
Foundry knowledge base and register `tools.TOOL_SCHEMAS` as Foundry function
tools; the routing logic is unchanged.

## Relationship to the rest of the repo

- [`../mcp`](../mcp) — the Create-Booking MCP server (10 live tools). This
  orchestrator is one of its clients.
- [`../knowledge-docs-v1`](../knowledge-docs-v1) — the 19 knowledge documents that
  back the 15 knowledge bases.
- [`../README.md`](../README.md) — the Azure AI Foundry design this implements.
