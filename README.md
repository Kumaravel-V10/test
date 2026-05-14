 # 🧪 QUBE — Unified AI-Powered Quality Engineering Platform
AIzaSyCNnaAcCbWgBuiauioikhBfEzH5PI14T8kSMJk000000000
> One platform. Every test. Every insight. One release decision.
> Powered by **GPT-4o + Claude Sonnet 4.6 + Claude Opus 4.6** — each model routed to the task it does best.

QUBE (Quality Unified Baseline Engine) is a single, fully integrated testing platform that connects to your GitHub codebase, orchestrates Playwright · k6 · ZAP · API testing, and delivers AI-powered analysis via LangGraph agents — intelligently switching between GPT-4o, Claude Sonnet 4.6, and Claude Opus 4.6 based on task type, token load, and reasoning depth required.

---

## Table of Contents

- [Vision](#vision)
- [Core Capabilities](#core-capabilities)
- [Architecture Overview](#architecture-overview)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [LangGraph AI Agent System](#langgraph-ai-agent-system)
- [AI Model Strategy — Dual Provider Routing](#ai-model-strategy--dual-provider-routing)
- [GitHub Integration](#github-integration)
- [Test Orchestration Engine](#test-orchestration-engine)
- [Report & Bug System](#report--bug-system)
- [Data Contracts & Schemas](#data-contracts--schemas)
- [Configuration Reference](#configuration-reference)
- [Folder Structure](#folder-structure)
- [Setup & Installation](#setup--installation)
- [Roadmap](#roadmap)

---

## Vision

> Every production release decision is backed by reproducible multi-stage test evidence, AI-generated insight from the right model for each task, human ownership, and a single auditable report — fetched directly from your GitHub repository, run in one command, stored in one place.

QUBE removes the need for:
- Manual test stitching across Slack, spreadsheets, or CI logs
- Separate portals for security, performance, and functional test results
- Picking one AI vendor and being locked in — QUBE routes to the best model per task

---

## Core Capabilities

| Capability | Description |
|---|---|
| **GitHub Sync** | Connect any repo, branch, or commit SHA; auto-pull before each run |
| **Script Analyzer** | AI reads your test scripts and codebase and suggests improvements |
| **Multi-Stage Test Runner** | Run Playwright, k6, OWASP ZAP, and API tests in one orchestrated pipeline |
| **LangGraph AI Agents** | Specialized agents triage failures, recommend fixes, and generate release decisions |
| **Dual-Model AI Routing** | GPT-4o for structured JSON output; Claude Sonnet 4.6 for deep code + long context; Claude Opus 4.6 for complex multi-step reasoning |
| **Unified Report** | Single merged JSON + HTML report per run, indexed by run_id |
| **Bug Tracker** | Auto-generated bug cards from failed tests with AI fix recommendations + diffs |
| **Blocker Management** | Critical/High findings automatically flagged with owner assignment |
| **AI Chat Interface** | Ask anything about the test run, codebase, or failure patterns |
| **Dashboard** | Real-time test progress, trends, quality score, and release gate status |
| **Configurable Gates** | Define block/warn/observe thresholds per project via UI or YAML |
| **Model Config UI** | Configure which model handles which agent — per project, overridable |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            QUBE PLATFORM                                 │
│                                                                          │
│  ┌───────────────┐    ┌──────────────────────────────────────────────┐  │
│  │   Frontend    │    │               Backend Services                │  │
│  │  (Next.js 14) │◄──►│                                              │  │
│  │               │    │  ┌─────────────┐  ┌──────────────────────┐  │  │
│  │  Dashboard    │    │  │  API GW     │  │  Orchestrator Svc    │  │  │
│  │  Run Console  │    │  │ (FastAPI)   │  │  (Python / Celery)   │  │  │
│  │  Bug Tracker  │    │  └─────────────┘  └──────────────────────┘  │  │
│  │  AI Chat      │    │  ┌─────────────┐  ┌──────────────────────┐  │  │
│  │  Config UI    │    │  │ GitHub Svc  │  │  LangGraph Agent     │  │  │
│  │  Model Router │    │  │             │  │  Engine              │  │  │
│  └───────────────┘    │  └─────────────┘  └──────────────────────┘  │  │
│                       │  ┌─────────────┐  ┌──────────────────────┐  │  │
│                       │  │ Report Svc  │  │  AI Model Router     │  │  │
│                       │  │             │  │  GPT-4o /            │  │  │
│                       │  └─────────────┘  │  Sonnet 4.6 /        │  │  │
│                       │                   │  Opus 4.6            │  │  │
│                       │                   └──────────────────────┘  │  │
│                       └──────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                       Test Runner Layer                            │  │
│  │   Playwright Worker │ k6 Worker │ ZAP Worker │ API Worker         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         Data Layer                                 │  │
│  │  PostgreSQL (runs/bugs/config) │ Redis (queues/cache/sessions)    │  │
│  │  MinIO / S3 (artifacts/reports)│ GitHub API                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

**Stack:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Zustand · React Query · Recharts · Xterm.js · Monaco Editor

### Page Structure

```
app/
├── (auth)/
│   └── login/                    # GitHub OAuth login
├── dashboard/
│   ├── page.tsx                  # Quality score, recent runs, trend charts
│   └── [projectId]/
│       ├── page.tsx              # Project overview + active model config display
│       ├── runs/
│       │   ├── page.tsx          # Run history list with gate decision badges
│       │   ├── new/page.tsx      # Configure & trigger new run
│       │   └── [runId]/
│       │       ├── page.tsx      # Live console + stage tabs + model usage panel
│       │       ├── report/       # Merged HTML/JSON report viewer
│       │       ├── bugs/         # Auto-generated bug cards for this run
│       │       └── ai/           # AI insights + chat (shows which model answered)
│       ├── bugs/
│       │   └── page.tsx          # All bugs across runs, filter/sort/assign
│       ├── config/
│       │   ├── page.tsx          # Gate thresholds, env vars, integrations
│       │   └── models/page.tsx   # ← Per-agent model selector UI
│       └── scripts/
│           └── page.tsx          # Script analyzer: repo path or upload
└── settings/
    └── page.tsx                  # GitHub token, org config, notification rules
```

### Key UI Modules

#### 1. Run Console (`/runs/[runId]`)
- Live log streaming via WebSocket (Xterm.js terminal component)
- Stage progress bar: `GitHub Sync → Script Analysis → Playwright → k6 → ZAP → API → AI Report`
- Per-stage status badge: Running / Passed / Failed / Blocked / Skipped
- **Model activity ticker** — real-time display of which AI model is active:
  ```
  🤖 Claude Sonnet 4.6  — analyzing 14 Playwright failures...
  🤖 Claude Opus 4.6    — generating release gate decision...
  🤖 GPT-4o             — processing k6 performance baseline...
  ```
- Live gate decision panel (block/warn/observe) updating in real time

#### 2. Unified Report Viewer
- Tabs: Summary · Functional · Performance · Security · AI Analysis · Model Usage
- Each AI-generated insight carries a source model badge: `[Claude Sonnet 4.6]` / `[GPT-4o]` / `[Claude Opus 4.6]`
- Filterable test result table with severity, status, and AI explanation column
- One-click "Create Bug" from any failed test row
- Export as PDF or share link

#### 3. Bug Tracker
- Kanban view: Open → In Progress → Fixed → Verified
- Each bug card shows: failing test name, stage, severity, AI fix recommendation, inline diff (Monaco), source model, linked commit
- Filter by: stage, severity, assignee, run_id, date range
- GitHub Issue sync: push bug to repo issues with one click
- One-click "Apply Fix" → commits Claude Sonnet 4.6 generated diff to a new branch

#### 4. AI Chat Panel
- Context-aware: loaded with current run artifacts + codebase summary
- **Model selector in chat header** — switch between GPT-4o, Claude Sonnet 4.6, Claude Opus 4.6 mid-conversation
- Default routes to the model configured for the Chat Agent per project
- Shows token usage and estimated cost per message
- Persistent conversation per run, exportable

#### 5. Script Analyzer
- Point to GitHub repo path or upload scripts
- AI reviews: test coverage gaps, dead selectors, missing assertions, poor data isolation
- Output: annotated diff view (Monaco Editor) with suggested improvements
- One-click accept → commits fix to branch via GitHub API
- Entire codebase sent in one call via Claude Sonnet 4.6's 1M token context window

#### 6. Model Config UI (`/config/models`)
- Per-agent model selector dropdown: `GPT-4o` · `Claude Sonnet 4.6` · `Claude Opus 4.6` · `Claude Haiku 4.5` · `Auto`
- Extended thinking toggle per agent (Sonnet 4.6 / Opus 4.6 only)
- Effort level selector: low / medium / high / max (Opus 4.6 only)
- Shows: estimated token cost per run, context window used, recommended model for each agent
- Live "test prompt" panel — send a sample payload and see the response with latency + cost
- Saved per project, version-controlled in `qube.config.yaml`

#### 7. Dashboard
- Project-level quality score (weighted: functional 40%, security 35%, performance 25%)
- Run trend chart: pass rate over last 30 runs
- **Model usage cost breakdown** per run: total cost, cost per agent, which model was used
- Blocker heatmap: which stage produces the most blockers over time

---

## Backend Architecture

**Stack:** Python 3.12 · FastAPI · Celery · Redis · PostgreSQL · LangGraph · Anthropic SDK · OpenAI SDK · Docker

### Services

#### API Gateway (`api-gateway/`)
- FastAPI application, single entry point for all frontend calls
- JWT + GitHub OAuth session management
- Routes requests to internal services via HTTP or task queue
- WebSocket endpoint for live log streaming per run_id
- Model usage logging endpoint (records model, tokens, cost per agent call)

#### AI Model Router (`ai-model-router/`) ← Central to the dual-model design
- The single service all agents call — agents never call providers directly
- Accepts: `{ agent: str, payload: dict, project_id: str }`
- Looks up model config for that agent + project from DB
- Routes to correct provider SDK (Anthropic or OpenAI)
- Normalizes response so agents are fully provider-agnostic
- Records usage: model, input_tokens, output_tokens, latency_ms, cost_usd
- Fallback: if primary model fails or rate-limits, routes to configured fallback and flags in report

```python
# ai-model-router/router.py

class ModelRouter:
    async def call(self, agent: str, messages: list, project_id: str) -> RouterResponse:
        config = await self.get_model_config(agent, project_id)
        
        try:
            if config.provider == "anthropic":
                return await self.call_anthropic(config, messages)
            elif config.provider == "openai":
                return await self.call_openai(config, messages)
        except (RateLimitError, APIError):
            # Fallback to secondary model
            fallback = await self.get_fallback_config(config)
            result = await self.dispatch(fallback, messages)
            result.fallback_used = True
            return result

    async def call_anthropic(self, config: ModelConfig, messages: list) -> RouterResponse:
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=config.model_id,           # claude-sonnet-4-6 or claude-opus-4-6
            max_tokens=config.max_tokens,
            thinking={"type": "adaptive"} if config.extended_thinking else None,
            system=config.system_prompt,
            messages=messages,
        )
        return RouterResponse(
            text=response.content[0].text,
            model_id=config.model_id,
            provider="anthropic",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def call_openai(self, config: ModelConfig, messages: list) -> RouterResponse:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=config.model_id,           # gpt-4o
            response_format={"type": "json_object"} if config.json_mode else None,
            messages=messages,
        )
        return RouterResponse(
            text=response.choices[0].message.content,
            model_id=config.model_id,
            provider="openai",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
```

#### Orchestrator Service (`orchestrator/`)
- Celery-based task queue backed by Redis
- Manages the full run pipeline as a DAG
- Each stage emits normalized `stage_result.json`
- Handles retries, timeouts, partial failures, stale revision detection

#### GitHub Service (`github-svc/`)
- Clone / fetch / pull target repo at specified branch + commit SHA
- Read file tree for script discovery
- Push bug reports as GitHub Issues
- Post run summary as commit status check
- Webhook listener: trigger run on push or PR event
- Commit AI-generated fix diffs to a new branch

#### Test Workers (Docker containers, isolated per stage)

| Worker | Tool | Output |
|---|---|---|
| `playwright-worker` | Playwright (Node) | `playwright_result.json`, screenshots, traces |
| `k6-worker` | k6 (Go) | `k6_result.json`, thresholds, percentiles |
| `zap-worker` | OWASP ZAP (Java) | `zap_result.json`, risk-ranked alerts |
| `api-worker` | Supertest / Newman | `api_result.json`, schema violations |

All workers output to shared artifact volume: `artifacts/{run_id}/{stage}/`

---

## LangGraph AI Agent System

QUBE uses a **LangGraph StateGraph** to orchestrate specialized AI agents. Each agent is model-agnostic — it sends work to the AI Model Router which selects the right model based on project config.

### Agent Graph

```
                      ┌───────────────────────┐
                      │    Supervisor Agent    │
                      │   Routes & Coordinates │
                      │   Model: GPT-4o        │
                      └──────────┬─────────────┘
                                 │
          ┌──────────────────────┼───────────────────────────┐
          ▼                      ▼                            ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  Functional      │  │  Performance       │  │  Security Risk Agent     │
│  Triage Agent    │  │  Analyst Agent     │  │                          │
│                  │  │                    │  │  Model: Claude Sonnet    │
│  Model: Claude   │  │  Model: GPT-4o    │  │  4.6 + Adaptive Thinking │
│  Sonnet 4.6      │  │                    │  │                          │
│                  │  │  - k6 JSON parse   │  │  - ZAP alert parsing     │
│  - Deep code     │  │  - Regression vs   │  │  - CVE classification    │
│    path analysis │  │    baseline        │  │  - Exception policy      │
│  - Root cause    │  │  - Bottleneck map  │  │  - Patch guidance        │
│  - Fix diff      │  │  - Threshold eval  │  │  - Risk scoring          │
└────────┬─────────┘  └─────────┬──────────┘  └───────────┬──────────────┘
         └────────────────────┬─┘─────────────────────────┘
                              ▼
                  ┌─────────────────────────┐
                  │   Script Analyzer Agent  │
                  │                         │
                  │   Model: Claude Sonnet   │
                  │   4.6 (1M token ctx)    │
                  │                         │
                  │   - Full repo ingest     │
                  │   - Coverage gap map     │
                  │   - Fragile selector     │
                  │     detection            │
                  │   - New test case        │
                  │     suggestions          │
                  └──────────┬──────────────┘
                             ▼
                  ┌─────────────────────────┐
                  │  Release Decision Agent  │
                  │                         │
                  │  Model: Claude Opus 4.6  │
                  │  Adaptive Thinking ON   │
                  │  Effort: high / max     │
                  │                         │
                  │  - Aggregates all agent  │
                  │    outputs               │
                  │  - Multi-factor gate     │
                  │    policy reasoning      │
                  │  - Exception evaluation  │
                  │  - PASS / BLOCK / WARN   │
                  │    + full justification  │
                  └──────────┬──────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Bug Fix Agent               │
              │                              │
              │  Model: Claude Sonnet 4.6    │
              │                              │
              │  - Generates code fix diffs  │
              │  - Per blocking finding      │
              │  - Produces patch + test     │
              │    case update suggestion    │
              └──────────┬───────────────────┘
                         ▼
              ┌──────────────────────────────┐
              │  Chat Agent (On demand)       │
              │                              │
              │  Model: User-selected        │
              │  Default: Claude Sonnet 4.6  │
              │                              │
              │  - Full run context loaded   │
              │  - Codebase-aware            │
              │  - Streaming output          │
              │  - Persistent per run        │
              └──────────────────────────────┘
```

### LangGraph State Schema

```python
from typing import TypedDict
from langgraph.graph import StateGraph

class ModelAttribution(TypedDict):
    agent: str
    model_id: str
    provider: str           # "anthropic" | "openai"
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    thinking_used: bool
    fallback_used: bool

class QUBERunState(TypedDict):
    run_id: str
    repo: dict                          # branch, sha, file tree
    merged_summary: dict                # all stage results
    functional_findings: list           # Playwright triage agent output
    performance_findings: list          # k6 analyst agent output
    security_findings: list             # ZAP risk agent output
    script_analysis: dict               # Script analyzer agent output
    fix_diffs: list                     # Bug Fix agent output
    gate_policy: dict                   # configured thresholds
    blockers: list                      # HIGH+ findings
    release_decision: str               # PASS | BLOCK | WARN
    release_justification: str          # Opus 4.6 reasoning narrative
    ai_insights_markdown: str           # human-readable summary
    model_attributions: list[ModelAttribution]  # full audit trail
    chat_history: list                  # Chat Agent session
```

---

## AI Model Strategy — Dual Provider Routing

QUBE intelligently routes each agent's work to the model best suited for it. All assignments are the project-level default and are fully overridable.

### Default Model Assignments

| Agent | Default Model | Provider | Reasoning |
|---|---|---|---|
| **Supervisor** | `gpt-4o` | OpenAI | Fast routing decisions; structured JSON; low latency |
| **Functional Triage** | `claude-sonnet-4-6` | Anthropic | Deep TypeScript/JS reasoning; 1M token context for large Playwright output; best code understanding |
| **Performance Analyst** | `gpt-4o` | OpenAI | Quantitative data analysis; k6 JSON is compact and structured; reliable `json_object` output |
| **Security Risk** | `claude-sonnet-4-6` + Adaptive Thinking | Anthropic | CVE classification + exception policy reasoning; adaptive thinking for nuanced risk evaluation |
| **Script Analyzer** | `claude-sonnet-4-6` | Anthropic | 1M token context ingests entire codebase in one call; leading code quality analysis |
| **Release Decision** | `claude-opus-4-6` + Adaptive Thinking | Anthropic | Most critical reasoning task; Opus 4.6 for complex multi-factor gate logic with full justification |
| **Bug Fix** | `claude-sonnet-4-6` | Anthropic | Code generation and patch production; produces actual diffs |
| **Chat Agent** | `claude-sonnet-4-6` (user-switchable) | Anthropic | Long-context conversational reasoning; user can switch to GPT-4o or Opus 4.6 in the UI |

### Why This Split Makes Sense

**Claude Sonnet 4.6** (`claude-sonnet-4-6`) is the default for code-heavy agents because it provides a 1M token context window with adaptive thinking, making it capable of ingesting an entire test suite output alongside a large codebase in a single call. It is state-of-the-art for real-world software coding tasks and excels at long-horizon, autonomous work — exactly what deep test failure analysis requires.

**Claude Opus 4.6** (`claude-opus-4-6`) handles the Release Decision Agent exclusively. This is the most consequential output in the entire pipeline — a gate decision with multi-factor logic, exception handling, and a full written justification. Opus 4.6 supports 128k output tokens, adaptive thinking with a `max` effort level, and delivers the deepest reasoning available.

**GPT-4o** handles agents where the primary requirement is structured, predictable JSON output against compact data — the Supervisor's routing call and the Performance Analyst's quantitative baseline comparison. Both are tasks where GPT-4o's consistent `json_object` mode is the most pragmatic choice.

### Model Capability Comparison for QUBE Tasks

| Capability | GPT-4o | Claude Sonnet 4.6 | Claude Opus 4.6 | Claude Haiku 4.5 |
|---|---|---|---|---|
| Context window | 128k | **1M** | **1M** | 200k |
| Max output tokens | 16k | 64k | **128k** | 8k |
| JSON structured output | ✅ Excellent | ✅ Good | ✅ Good | ✅ Good |
| Code understanding | ✅ Strong | ✅ **Best-in-class** | ✅ Excellent | ⚠️ Basic |
| Adaptive thinking | ❌ | ✅ (effort: low–high) | ✅ **(effort: low–max)** | ❌ |
| Full repo ingest (no chunking) | ❌ Chunking required | ✅ Native 1M | ✅ Native 1M | ⚠️ Limited |
| Complex multi-step reasoning | ✅ Strong | ✅ Strong | ✅ **Frontier** | ⚠️ Basic |
| Streaming chat | ✅ | ✅ | ✅ | ✅ |
| Cost (relative) | Mid | Mid | High | **Lowest** |

### Auto Routing Mode

When an agent is set to `model: auto`, the Model Router applies these rules:

```python
AUTO_ROUTING_RULES = {
    "supervisor":             lambda ctx: "gpt-4o",
    "functional_triage":      lambda ctx: "claude-sonnet-4-6",
    "performance_analyst":    lambda ctx: "gpt-4o",
    "security_risk":          lambda ctx: "claude-sonnet-4-6",
    "script_analyzer":        lambda ctx: "claude-sonnet-4-6",
    "release_decision":       lambda ctx: (
        "claude-opus-4-6"      # Opus when blockers or exceptions are present
        if ctx["blocker_count"] > 0 or ctx["exception_count"] > 0
        else "claude-sonnet-4-6"  # Sonnet sufficient for clean runs
    ),
    "bug_fix":                lambda ctx: "claude-sonnet-4-6",
    "chat":                   lambda ctx: "claude-sonnet-4-6",  # user overrides in UI
}
```

### Fallback Chain

```
Primary model fails or rate-limits
         │
         ▼
Retry with exponential backoff (3 attempts, 2s / 4s / 8s)
         │
         ▼
Route to configured fallback model
(default: claude-sonnet-4-6 ↔ gpt-4o swap)
         │
         ▼
Mark insight with [FALLBACK MODEL USED] badge in report
         │
         ▼
Log to model_usage_log table for review
```

### SDK Setup

```python
# requirements.txt
anthropic>=0.40.0
openai>=1.50.0
langgraph>=0.2.0

# Anthropic SDK — Sonnet 4.6 and Opus 4.6
import anthropic

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

response = await client.messages.create(
    model="claude-sonnet-4-6",   # or "claude-opus-4-6"
    max_tokens=8192,
    thinking={"type": "adaptive"},   # Sonnet 4.6 + Opus 4.6 feature
    system=system_prompt,
    messages=[{"role": "user", "content": payload}],
)

# OpenAI SDK — GPT-4o
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

response = await client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload},
    ],
)
```

---

## GitHub Integration

### Connection Flow

```
User enters GitHub PAT or installs GitHub App
          │
          ▼
QUBE stores token encrypted (never in DB plaintext or logs)
          │
          ▼
User selects org → repo → branch
          │
          ▼
QUBE lists branches and recent commits via GitHub API
          │
          ▼
Run triggered (manual / scheduled / webhook)
          │
          ▼
Orchestrator → GitHub Service:
  1. git fetch origin <branch>
  2. git checkout <commit_sha>
  3. Record branch, sha, actor, timestamp in run metadata
          │
          ▼
After completion:
  - Post commit status ✅ PASS / ❌ BLOCK / ⚠️ WARN
  - Open GitHub Issues for each blocker bug
  - Post PR comment with summary table + AI insight excerpt
  - Commit AI-generated fix diffs to a new branch (optional)
```

### Webhook Trigger

```
POST /api/webhooks/github/{project_id}
```

Register in: GitHub repo → Settings → Webhooks. QUBE auto-triggers on:
- `push` to protected branch
- `pull_request` opened or synchronized

---

## Test Orchestration Engine

### Pipeline DAG

```
[1] sync_github
      │  Fetch repo at target sha. Abort on conflict.
      ▼
[2] analyze_scripts          ← Claude Sonnet 4.6 (1M ctx, full repo in one call)
      │  (runs in parallel with stage 3)
      ▼
[3] run_playwright
      │  Execute all *.spec.ts against target env
      ▼
[4] run_k6                   (parallel with [5])
      │  Load test with configured VUs and thresholds
      ▼
[5] run_zap
      │  OWASP ZAP active scan against test environment URL
      ▼
[6] run_api_tests
      │  Newman / Supertest API contract tests
      ▼
[7] merge_report
      │  Combine all stage_result.json → merged_summary.json
      ▼
[8] run_ai_agents            ← LangGraph multi-agent graph
      │  Functional:         Claude Sonnet 4.6
      │  Performance:        GPT-4o
      │  Security:           Claude Sonnet 4.6 + Adaptive Thinking
      │  Script Analyzer:    Claude Sonnet 4.6
      │  Release Decision:   Claude Opus 4.6 + Adaptive Thinking (effort: high)
      │  Bug Fix:            Claude Sonnet 4.6
      ▼
[9] finalize_gate
      │  gate_decision.json + post GitHub commit status
      ▼
[10] notify
       Slack / email based on notification rules
```

### Normalized Stage Result Contract

```json
{
  "stage": "playwright",
  "run_id": "run_20240410_abc123",
  "started_at": "2024-04-10T09:00:00Z",
  "completed_at": "2024-04-10T09:05:32Z",
  "status": "failed",
  "summary": {
    "total": 120,
    "passed": 115,
    "failed": 5,
    "skipped": 0
  },
  "gate_impact": "block",
  "findings": [
    {
      "id": "f_001",
      "title": "Login flow fails on empty password",
      "severity": "critical",
      "file": "tests/auth/login.spec.ts",
      "line": 42,
      "error_message": "Expected 'dashboard' URL, got '/'",
      "screenshot": "artifacts/run_20240410_abc123/playwright/login_fail.png"
    }
  ],
  "artifacts": [
    "artifacts/run_20240410_abc123/playwright/report.html"
  ],
  "repo_context": {
    "branch": "main",
    "sha": "a1b2c3d4",
    "actor": "jane.doe"
  }
}
```

---

## Report & Bug System

### Unified Report Structure

```
reports/
└── {run_id}/
    ├── merged_summary.json          # All stage data merged
    ├── gate_decision.json           # PASS/BLOCK/WARN with policy trace
    ├── ai_insights.json             # LangGraph outputs with model attribution
    ├── ai_insights.md               # Human-readable AI narrative
    ├── model_usage.json             # Full audit: model, tokens, cost, latency per agent
    ├── report.html                  # Full rendered HTML report
    └── stages/
        ├── playwright_result.json
        ├── k6_result.json
        ├── zap_result.json
        └── api_result.json
```

### model_usage.json

```json
{
  "run_id": "run_20240410_abc123",
  "total_cost_usd": 0.38,
  "agents": [
    {
      "agent": "functional_triage",
      "model": "claude-sonnet-4-6",
      "provider": "anthropic",
      "input_tokens": 24800,
      "output_tokens": 3200,
      "cost_usd": 0.12,
      "latency_ms": 4200,
      "thinking_used": false,
      "fallback_used": false
    },
    {
      "agent": "security_risk",
      "model": "claude-sonnet-4-6",
      "provider": "anthropic",
      "input_tokens": 8100,
      "output_tokens": 2200,
      "cost_usd": 0.08,
      "latency_ms": 6800,
      "thinking_used": true,
      "fallback_used": false
    },
    {
      "agent": "release_decision",
      "model": "claude-opus-4-6",
      "provider": "anthropic",
      "input_tokens": 12400,
      "output_tokens": 4100,
      "cost_usd": 0.14,
      "latency_ms": 9100,
      "thinking_used": true,
      "effort": "high",
      "fallback_used": false
    },
    {
      "agent": "performance_analyst",
      "model": "gpt-4o",
      "provider": "openai",
      "input_tokens": 3200,
      "output_tokens": 800,
      "cost_usd": 0.04,
      "latency_ms": 1800,
      "thinking_used": false,
      "fallback_used": false
    }
  ]
}
```

### Bug Card Schema

```json
{
  "bug_id": "bug_run_abc123_f001",
  "run_id": "run_20240410_abc123",
  "title": "Login flow fails on empty password",
  "stage": "playwright",
  "severity": "critical",
  "status": "open",
  "created_at": "2024-04-10T09:06:00Z",
  "finding_ref": "f_001",
  "ai_root_cause": "The form submit handler does not validate empty password before POST. Backend returns 401 but the frontend router does not handle the redirect, leaving the user on the login page with no error message.",
  "ai_fix_recommendation": "Add client-side validation in LoginForm.tsx before submit. Check password.trim().length > 0. Also add an E2E test for empty credential edge case.",
  "ai_fix_diff": "--- a/src/components/LoginForm.tsx\n+++ b/src/components/LoginForm.tsx\n@@ -24,6 +24,9 @@\n   const handleSubmit = async () => {\n+    if (!password.trim()) {\n+      setError('Password is required');\n+      return;\n+    }\n     await authApi.login(email, password);",
  "fix_model": "claude-sonnet-4-6",
  "affected_files": ["src/components/LoginForm.tsx", "src/api/auth.ts"],
  "assignee": null,
  "github_issue_url": null,
  "exception_approved": false,
  "exception_owner": null,
  "exception_expiry": null
}
```

---

## Data Contracts & Schemas

### Environment Variables

```env
# GitHub
GITHUB_TOKEN=ghp_...
GITHUB_ORG=your-org
GITHUB_REPO=your-repo
GITHUB_BRANCH=main

# Test Target
TARGET_BASE_URL=https://staging.yourapp.com

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Default model assignments (overridden per-project in qube.config.yaml)
DEFAULT_MODEL_SUPERVISOR=gpt-4o
DEFAULT_MODEL_FUNCTIONAL=claude-sonnet-4-6
DEFAULT_MODEL_PERFORMANCE=gpt-4o
DEFAULT_MODEL_SECURITY=claude-sonnet-4-6
DEFAULT_MODEL_SCRIPT_ANALYZER=claude-sonnet-4-6
DEFAULT_MODEL_RELEASE_DECISION=claude-opus-4-6
DEFAULT_MODEL_BUG_FIX=claude-sonnet-4-6
DEFAULT_MODEL_CHAT=claude-sonnet-4-6

# k6 Thresholds
K6_P95_WARN_MS=2000
K6_P95_BLOCK_MS=4000
K6_ERROR_RATE_BLOCK=0.01

# ZAP
ZAP_HIGH_BLOCK=true
ZAP_MEDIUM_WARN=true

# Playwright
PLAYWRIGHT_CRITICAL_PATH_BLOCK=true

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
NOTIFY_ON_BLOCK=true
NOTIFY_ON_WARN=false
```

### Database Schema (PostgreSQL)

```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  github_org TEXT,
  github_repo TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE project_model_config (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  agent TEXT NOT NULL,
  provider TEXT NOT NULL,           -- anthropic | openai
  model_id TEXT NOT NULL,           -- claude-sonnet-4-6 | claude-opus-4-6 | gpt-4o | auto
  extended_thinking BOOLEAN DEFAULT false,
  effort_level TEXT DEFAULT 'high', -- low | medium | high | max
  fallback_model_id TEXT,
  fallback_provider TEXT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(project_id, agent)
);

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  branch TEXT,
  commit_sha TEXT,
  actor TEXT,
  triggered_by TEXT,
  status TEXT,
  gate_decision TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  artifact_path TEXT,
  total_ai_cost_usd NUMERIC(10,4)
);

CREATE TABLE model_usage_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT REFERENCES runs(id),
  agent TEXT,
  provider TEXT,
  model_id TEXT,
  input_tokens INT,
  output_tokens INT,
  cost_usd NUMERIC(10,4),
  latency_ms INT,
  thinking_used BOOLEAN DEFAULT false,
  effort_level TEXT,
  fallback_used BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bugs (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(id),
  project_id UUID REFERENCES projects(id),
  stage TEXT,
  severity TEXT,
  title TEXT,
  status TEXT DEFAULT 'open',
  ai_root_cause TEXT,
  ai_fix_recommendation TEXT,
  ai_fix_diff TEXT,
  fix_model TEXT,
  affected_files JSONB,
  assignee TEXT,
  github_issue_url TEXT,
  exception_approved BOOLEAN DEFAULT false,
  exception_owner TEXT,
  exception_expiry DATE,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Configuration Reference

### `qube.config.yaml`

```yaml
version: "1"
project: my-app

github:
  org: your-org
  repo: your-app
  branch: main
  protected_branches: [main, release/*]

ai:
  agents:
    supervisor:
      model: gpt-4o
      provider: openai
      fallback: claude-sonnet-4-6

    functional_triage:
      model: claude-sonnet-4-6
      provider: anthropic
      extended_thinking: false
      fallback: gpt-4o

    performance_analyst:
      model: gpt-4o
      provider: openai
      fallback: claude-sonnet-4-6

    security_risk:
      model: claude-sonnet-4-6
      provider: anthropic
      extended_thinking: true       # adaptive thinking for CVE reasoning
      effort: high
      fallback: gpt-4o

    script_analyzer:
      model: claude-sonnet-4-6      # 1M ctx — ingest full repo in one call
      provider: anthropic
      extended_thinking: false
      fallback: claude-sonnet-4-6

    release_decision:
      model: claude-opus-4-6        # Opus for the most critical reasoning task
      provider: anthropic
      extended_thinking: true
      effort: high                  # use "max" for highest-stakes releases
      fallback: claude-sonnet-4-6

    bug_fix:
      model: claude-sonnet-4-6
      provider: anthropic
      fallback: gpt-4o

    chat:
      model: claude-sonnet-4-6      # user can override in the UI per session
      provider: anthropic
      fallback: gpt-4o

stages:
  playwright:
    enabled: true
    command: "npx playwright test"
    timeout_minutes: 15
    gate_impact: block_on_critical

  k6:
    enabled: true
    script: tests/load/main.k6.js
    vus: 50
    duration: 2m
    thresholds:
      p95_warn_ms: 2000
      p95_block_ms: 4000
      error_rate_block: 0.01
    gate_impact: block_on_severe

  zap:
    enabled: true
    target_url: ${TARGET_BASE_URL}
    scan_type: active
    gate_impact: block_on_high

  api:
    enabled: true
    collection: tests/api/postman_collection.json
    gate_impact: warn_on_failure

notifications:
  slack:
    webhook: ${SLACK_WEBHOOK_URL}
    on: [block, warn]
  github_status: true
  github_issues: true
  include_model_cost_in_report: true
```

---

## Folder Structure

```
qube/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── frontend/                           # Next.js 14
│   ├── app/
│   │   ├── dashboard/
│   │   ├── (auth)/
│   │   └── settings/
│   ├── components/
│   │   ├── run-console/                # Xterm.js + model activity ticker
│   │   ├── report-viewer/              # Tabbed report + model attribution badges
│   │   ├── bug-tracker/                # Kanban + Monaco diff viewer
│   │   ├── ai-chat/                    # Chat + per-session model switcher
│   │   ├── script-analyzer/            # Monaco diff editor
│   │   ├── model-config/               # Per-agent model selector UI
│   │   └── config-ui/                  # Gate + env config
│   └── lib/
│       ├── api.ts
│       └── store.ts
│
├── backend/
│   ├── api-gateway/                    # FastAPI — single entry point
│   │   ├── routers/
│   │   │   ├── runs.py
│   │   │   ├── bugs.py
│   │   │   ├── projects.py
│   │   │   ├── github.py
│   │   │   ├── ai.py
│   │   │   └── model_config.py
│   │   ├── websockets/
│   │   │   └── log_stream.py
│   │   └── main.py
│   │
│   ├── ai-model-router/                # Central provider dispatch
│   │   ├── router.py
│   │   ├── auto_rules.py
│   │   ├── usage_logger.py
│   │   ├── providers/
│   │   │   ├── anthropic_provider.py   # claude-sonnet-4-6 / claude-opus-4-6
│   │   │   └── openai_provider.py      # gpt-4o
│   │   └── schemas.py
│   │
│   ├── orchestrator/                   # Celery DAG
│   │   ├── pipeline/
│   │   │   ├── dag.py
│   │   │   └── tasks/
│   │   │       ├── sync_github.py
│   │   │       ├── run_playwright.py
│   │   │       ├── run_k6.py
│   │   │       ├── run_zap.py
│   │   │       ├── run_api.py
│   │   │       ├── merge_report.py
│   │   │       └── finalize_gate.py
│   │   └── celery_app.py
│   │
│   ├── github-svc/
│   │   ├── clone.py
│   │   ├── status.py
│   │   ├── issues.py
│   │   └── webhook.py
│   │
│   ├── report-svc/
│   │   ├── merger.py
│   │   ├── gate_engine.py
│   │   ├── html_renderer.py
│   │   └── templates/
│   │       └── report.html.j2
│   │
│   ├── script-analyzer/
│   │   ├── walker.py
│   │   └── analyzer.py
│   │
│   └── ai-engine/                      # LangGraph agent graph
│       ├── graph.py
│       ├── state.py
│       ├── agents/
│       │   ├── supervisor.py           # gpt-4o
│       │   ├── functional_triage.py    # claude-sonnet-4-6
│       │   ├── performance_analyst.py  # gpt-4o
│       │   ├── security_risk.py        # claude-sonnet-4-6 + thinking
│       │   ├── script_analyzer.py      # claude-sonnet-4-6
│       │   ├── release_decision.py     # claude-opus-4-6 + thinking
│       │   ├── bug_fix.py              # claude-sonnet-4-6
│       │   └── chat.py                 # user-selected
│       └── prompts/
│           ├── functional.txt
│           ├── performance.txt
│           ├── security.txt
│           ├── script_analyzer.txt
│           └── release.txt
│
├── workers/
│   ├── playwright/
│   ├── k6/
│   ├── zap/
│   └── api/
│
├── schemas/
│   ├── stage_result.schema.json
│   ├── merged_summary.schema.json
│   ├── gate_decision.schema.json
│   ├── model_usage.schema.json
│   └── bug.schema.json
│
├── infra/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── postgres/init.sql
│
└── reports/
    └── .gitkeep
```

---

## Setup & Installation

### Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.12+
- GitHub Personal Access Token (`repo`, `write:repo_hook` scopes)
- OpenAI API Key (GPT-4o access)
- Anthropic API Key (Claude Sonnet 4.6 + Opus 4.6 access)

### Quick Start

```bash
# 1. Clone QUBE
git clone https://github.com/your-org/qube.git
cd qube

# 2. Configure environment
cp .env.example .env
# Add: ANTHROPIC_API_KEY, OPENAI_API_KEY, GITHUB_TOKEN, TARGET_BASE_URL

# 3. Start all services
docker-compose up -d

# 4. Open the platform
open http://localhost:3000
```

### First Run

1. **Settings → GitHub** — connect your organization
2. **New Project** — select repo + branch
3. **Config → Models** — review default model assignments (or customize per agent)
4. Place `qube.config.yaml` in your repo root (template auto-generated)
5. **New Run → Start**
6. Watch the live console — model activity ticker shows which AI is active at each stage
7. View unified report, model usage breakdown, and AI insights when complete

---

## Roadmap

| Phase | Milestone | AI Models | Status |
|---|---|---|---|
| **v1.0** | GitHub sync, 4-stage test runners, merged report, gate decision | — | 🔵 In Design |
| **v1.1** | LangGraph agents: Functional (Sonnet 4.6), Performance (GPT-4o), Security (Sonnet 4.6), Release (Opus 4.6) | Sonnet 4.6, Opus 4.6, GPT-4o | 🔵 In Design |
| **v1.2** | AI Model Router + per-project model config UI + fallback chain | All | ⬜ Planned |
| **v1.3** | Bug tracker, GitHub Issue sync, commit status, AI fix diffs (Sonnet 4.6) | Sonnet 4.6 | ⬜ Planned |
| **v1.4** | Script Analyzer (full 1M ctx codebase ingest via Sonnet 4.6) | Sonnet 4.6 | ⬜ Planned |
| **v1.5** | AI Chat panel with per-session model switcher | All | ⬜ Planned |
| **v1.6** | Model usage cost dashboard + per-run cost breakdown + budget alerts | — | ⬜ Planned |
| **v2.0** | Claude Haiku 4.5 routing for fast lightweight triage on high-volume CI | Haiku 4.5 | ⬜ Planned |
| **v2.1** | Embeddings-based script similarity search (find duplicate/redundant tests) | `text-embedding-3-large` | ⬜ Planned |
| **v2.2** | Contract testing stage (Pact) + API fuzzing stage | — | ⬜ Planned |
| **v2.3** | On-premise Ollama support for air-gapped environments | Llama / Mistral | ⬜ Planned |

---

## Governance

| Role | Owner |
|---|---|
| Platform Lead | Quality Platform Lead |
| Policy Approvers | Engineering Manager, Security Lead, SRE Lead |
| Model Assignment Authority | Quality Platform Lead + Engineering Manager |
| Review Cadence | Monthly policy · Quarterly threshold + model calibration |
| Change Process | GitHub PR → impact note → required approvals → changelog entry |

---

## Non-Negotiables

- Every run produces a single `merged_summary.json` and `gate_decision.json`
- Every AI insight is attributed to its source model in `model_usage.json` — no anonymous AI outputs
- All artifacts stored under `reports/{run_id}/`, indexed and retrievable
- Any HIGH security finding blocks release unless a documented, expiry-dated exception exists
- Critical functional path failures always block release
- API keys for Anthropic and OpenAI are never stored in logs, reports, or committed to files
- No run proceeds if the local source revision conflicts with origin
- Model fallback events are always surfaced in the report — no silent model swaps

---

*QUBE — The right model for the right task. One platform. One signal. One decision.*
