# 🤖 Autonomous Performance Testing Agent (APTA)
> Self-driving performance intelligence — test, analyze, diagnose, fix, and report — all without human intervention.

---

## 📌 Vision

Build a fully autonomous AI-powered agent that:
- **Runs** performance tests against any target system (API, web app, microservice, DB)
- **Analyzes** results in real time using AI inference
- **Identifies** root causes across infrastructure, code, and config layers
- **Recommends** and optionally **applies** fixes autonomously
- **Generates** structured reports with actionable insights

---

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  APTA — Orchestrator Agent                  │
│              (LLM-powered decision-making core)             │
└────────┬────────────────────────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────────────────┐
   │              Agent Tool Registry                    │
   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │
   │  │  Loader  │ │ Monitor  │ │ Analyzer │ │Fixer  │ │
   │  │  Tool    │ │  Tool    │ │  Tool    │ │ Tool  │ │
   │  └──────────┘ └──────────┘ └──────────┘ └───────┘ │
   └─────────────────────────────────────────────────────┘
         │               │               │
   ┌─────▼──────┐  ┌─────▼──────┐  ┌────▼────────┐
   │  k6 / JMeter│  │Prometheus  │  │  Claude AI  │
   │  Locust    │  │ Grafana    │  │  Root Cause │
   │  Artillery │  │ Datadog    │  │  Inference  │
   └────────────┘  └────────────┘  └─────────────┘
```

---

## 🗂️ Project Structure

```
apta/
├── agent/
│   ├── orchestrator.py        # Main LLM agent loop (Claude/GPT tool-calling)
│   ├── tools/
│   │   ├── loader_tool.py     # Triggers load tests (k6, Locust, JMeter)
│   │   ├── monitor_tool.py    # Fetches metrics (Prometheus, Datadog, CloudWatch)
│   │   ├── analyzer_tool.py   # Statistical analysis, anomaly detection
│   │   ├── rootcause_tool.py  # AI-powered root cause identification
│   │   ├── fixer_tool.py      # Applies config/code recommendations
│   │   └── reporter_tool.py   # Generates PDF/HTML/Markdown reports
│   └── memory/
│       ├── test_history.db    # SQLite store of past test runs
│       └── baseline_store.py  # Manages performance baselines
│
├── tests/
│   ├── scenarios/
│   │   ├── smoke.js           # Smoke test (k6)
│   │   ├── load.js            # Load test
│   │   ├── stress.js          # Stress test
│   │   ├── spike.js           # Spike test
│   │   └── soak.js            # Soak / endurance test
│   └── configs/
│       └── thresholds.yaml    # SLO/SLA threshold definitions
│
├── reports/
│   └── templates/
│       ├── report.html.j2     # Jinja2 HTML report template
│       └── executive_summary.md.j2
│
├── infra/
│   ├── docker-compose.yml     # k6 + Prometheus + Grafana + InfluxDB
│   └── grafana-dashboard.json
│
├── config/
│   ├── agent_config.yaml      # Agent settings, LLM model, tool toggles
│   └── targets.yaml           # Target endpoints and environments
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔄 Agent Execution Flow

```
Phase 1: PLAN
  └─► Agent reads target config + SLO thresholds
  └─► Selects appropriate test scenario (smoke → load → stress)
  └─► Confirms environment is healthy before starting

Phase 2: EXECUTE
  └─► Triggers load test (k6 / Locust) via loader_tool
  └─► Streams metrics in real time via monitor_tool
  └─► Detects anomalies mid-test (latency spikes, error rate rise)
  └─► Can abort test early if critical thresholds breached

Phase 3: ANALYZE
  └─► Collects full metrics snapshot post-test
  └─► Runs statistical analysis (P50, P90, P95, P99 latencies)
  └─► Compares against baseline and SLO thresholds
  └─► Flags regressions and improvements

Phase 4: ROOT CAUSE
  └─► AI infers root cause from metric correlations
  └─► Checks: DB slow queries, CPU/Memory saturation, GC pauses,
              thread pool exhaustion, network bottlenecks, cache misses
  └─► Cross-references APM traces (Jaeger/Zipkin) if available
  └─► Assigns confidence score to each hypothesis

Phase 5: RECOMMEND & FIX
  └─► Generates prioritized recommendations (HIGH / MEDIUM / LOW)
  └─► Optionally applies safe, reversible fixes:
        - Config tuning (connection pools, timeouts, cache TTL)
        - Auto-scaling triggers
        - Query optimization hints
  └─► Flags code-level issues for developer review

Phase 6: REPORT
  └─► Generates executive summary (1-page)
  └─► Generates detailed technical report (HTML + PDF)
  └─► Posts summary to Slack / email / Jira
  └─► Stores baseline for future regression comparison
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Agent Core** | Python 3.11+, LangGraph or custom agent loop |
| **LLM** | Anthropic Claude (claude-sonnet-4) via API |
| **Load Testing** | k6, Locust, Apache JMeter |
| **Metrics** | Prometheus + Grafana, InfluxDB |
| **APM / Tracing** | Jaeger, OpenTelemetry, Datadog (optional) |
| **Storage** | SQLite (test history), Redis (real-time cache) |
| **Reporting** | Jinja2, WeasyPrint (PDF), Markdown |
| **Notifications** | Slack Webhooks, SMTP, Jira API |
| **Infrastructure** | Docker Compose (local), Kubernetes (prod) |

---

## 📋 Phase-by-Phase Development Plan

### ✅ Phase 0 — Foundation (Week 1)
- [ ] Set up project structure and virtual environment
- [ ] Configure Docker Compose: k6 + InfluxDB + Grafana + Prometheus
- [ ] Write 3 baseline k6 test scripts (smoke, load, stress)
- [ ] Define `thresholds.yaml` with SLO values
- [ ] Test metrics pipeline end-to-end manually

### ✅ Phase 1 — Agent Shell (Week 2)
- [ ] Build orchestrator agent loop with Claude tool-calling API
- [ ] Implement `loader_tool`: trigger k6 via subprocess, capture output
- [ ] Implement `monitor_tool`: query Prometheus/InfluxDB REST API
- [ ] Wire agent to execute smoke test and return metrics JSON
- [ ] Persist test result to SQLite

### ✅ Phase 2 — Analysis Engine (Week 3)
- [ ] Implement `analyzer_tool`: compute percentiles, error rates, throughput
- [ ] Build baseline comparison logic (delta % from last run)
- [ ] Implement anomaly detection (Z-score, IQR method)
- [ ] Add mid-test monitoring loop with early abort capability
- [ ] Write unit tests for analysis functions

### ✅ Phase 3 — Root Cause Intelligence (Week 4)
- [ ] Implement `rootcause_tool` using Claude structured prompting
- [ ] Build metric correlation engine (latency vs CPU, memory vs GC, etc.)
- [ ] Add APM trace fetching (Jaeger API or OpenTelemetry collector)
- [ ] Implement hypothesis ranking with confidence scores
- [ ] Test root cause accuracy against known bottleneck scenarios

### ✅ Phase 4 — Recommendations & Auto-Fix (Week 5)
- [ ] Implement `fixer_tool` with safe-action registry
- [ ] Define fix actions: pool sizing, timeout config, cache warming
- [ ] Add dry-run mode (show what would be changed, don't apply)
- [ ] Add rollback mechanism for all applied fixes
- [ ] Build approval gate (human-in-the-loop mode toggle)

### ✅ Phase 5 — Reporting Pipeline (Week 6)
- [ ] Build Jinja2 HTML report template (executive + technical sections)
- [ ] Add chart rendering (Plotly or Chart.js embedded in HTML)
- [ ] Generate PDF via WeasyPrint
- [ ] Build Slack notification with summary embed
- [ ] Add Jira ticket creation for identified issues

### ✅ Phase 6 — Hardening & CI/CD Integration (Week 7)
- [ ] Add GitHub Actions workflow for automated perf tests on PR
- [ ] Implement agent self-evaluation (did the fix work? re-test)
- [ ] Add multi-environment support (dev, staging, prod with guardrails)
- [ ] Build dashboard for test history and trend visualization
- [ ] Write end-to-end integration tests

---

## 🧩 Agent Tool Definitions (Claude Tool Schema)

```python
tools = [
    {
        "name": "run_load_test",
        "description": "Trigger a k6 load test scenario and return raw metrics",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "enum": ["smoke", "load", "stress", "spike", "soak"]},
                "target_url": {"type": "string"},
                "duration_seconds": {"type": "integer"},
                "vus": {"type": "integer", "description": "Virtual users"}
            },
            "required": ["scenario", "target_url"]
        }
    },
    {
        "name": "get_metrics",
        "description": "Fetch performance metrics from Prometheus or InfluxDB",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_names": {"type": "array", "items": {"type": "string"}},
                "time_range_minutes": {"type": "integer"}
            }
        }
    },
    {
        "name": "analyze_results",
        "description": "Run statistical analysis on test results vs baseline",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_run_id": {"type": "string"},
                "compare_to_baseline": {"type": "boolean"}
            }
        }
    },
    {
        "name": "identify_root_cause",
        "description": "AI-powered root cause analysis from correlated metrics",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics_snapshot": {"type": "object"},
                "traces": {"type": "array"}
            }
        }
    },
    {
        "name": "apply_fix",
        "description": "Apply a safe, reversible configuration fix",
        "input_schema": {
            "type": "object",
            "properties": {
                "fix_type": {"type": "string", "enum": ["connection_pool", "timeout", "cache_ttl", "thread_pool"]},
                "target_service": {"type": "string"},
                "new_value": {},
                "dry_run": {"type": "boolean", "default": True}
            }
        }
    },
    {
        "name": "generate_report",
        "description": "Generate performance test report in specified format",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["html", "pdf", "markdown", "slack"]},
                "include_executive_summary": {"type": "boolean"}
            }
        }
    }
]
```

---

## 📊 Sample Report Output Structure

```
PERFORMANCE TEST REPORT
═══════════════════════════════════════════════════════════

Test Run ID    : APTA-2024-0312-001
Target         : https://api.example.com
Scenario       : Load Test (500 VUs, 10 min)
Status         : ⚠️  SLO BREACH DETECTED

EXECUTIVE SUMMARY
─────────────────
P95 Latency    : 2,340ms  (SLO: <500ms)  ❌ BREACH
Error Rate     : 4.2%     (SLO: <1%)     ❌ BREACH
Throughput     : 842 RPS  (Target: 1000) ⚠️  DEGRADED
Availability   : 95.8%    (SLO: 99.9%)   ❌ BREACH

ROOT CAUSE ANALYSIS
────────────────────
[HIGH CONFIDENCE - 94%] Database connection pool exhaustion
  → Pool size: 10 connections (insufficient for 500 VUs)
  → Avg wait time for connection: 1,800ms
  → Recommendation: Increase pool_size to 50, use PgBouncer

[MEDIUM CONFIDENCE - 71%] N+1 query pattern in /api/orders endpoint
  → Detected 47 sequential DB queries per request
  → Recommendation: Implement eager loading / batch queries

RECOMMENDATIONS
───────────────
1. [CRITICAL] Increase DB connection pool: 10 → 50            Auto-fixable ✓
2. [HIGH]     Add Redis cache for /api/products (TTL: 60s)    Manual review
3. [MEDIUM]   Enable HTTP/2 on load balancer                  Manual review
4. [LOW]      Add DB query result cache for user lookups       Manual review

APPLIED FIXES (dry-run)
────────────────────────
✓ connection_pool_size: 10 → 50 (pending approval)
```

---

## 🔐 Configuration (`agent_config.yaml`)

```yaml
agent:
  name: APTA
  mode: autonomous          # autonomous | supervised | dry_run
  llm_model: claude-sonnet-4
  max_iterations: 10
  human_approval_required:
    - apply_fix             # Require human sign-off before applying fixes
  auto_retest_after_fix: true

thresholds:
  p95_latency_ms: 500
  error_rate_percent: 1.0
  availability_percent: 99.9
  throughput_rps_min: 1000

notifications:
  slack_webhook: ${SLACK_WEBHOOK_URL}
  email: team@example.com
  jira_project: PERF

storage:
  history_db: ./data/test_history.db
  reports_dir: ./reports/output
```

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/your-org/apta.git
cd apta
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add: ANTHROPIC_API_KEY, PROMETHEUS_URL, SLACK_WEBHOOK_URL

# 3. Start infrastructure
docker-compose up -d

# 4. Run agent (supervised mode first!)
python -m agent.orchestrator \
  --target https://your-api.com \
  --scenario load \
  --mode supervised

# 5. View report
open reports/output/latest.html
```

---

## 📈 Roadmap

| Version | Feature |
|---|---|
| v0.1 | Basic agent loop + k6 integration |
| v0.2 | Prometheus metrics + analysis engine |
| v0.3 | Claude-powered root cause inference |
| v0.4 | Auto-fix engine (dry-run + apply) |
| v0.5 | HTML/PDF report generation |
| v1.0 | Full autonomous mode + CI/CD integration |
| v1.1 | Multi-service / distributed tracing support |
| v1.2 | Predictive degradation detection (ML model) |
| v2.0 | Self-healing infrastructure integration |

---

## ⚠️ Safety Guardrails

- **Dry-run by default**: No fixes applied without explicit `--apply` flag
- **Rollback registry**: Every fix action has a registered rollback
- **Production lock**: Agent refuses `apply_fix` in prod without human approval
- **Blast radius limit**: Agent will not modify more than 3 configs per run
- **Re-test gate**: After fix, agent automatically re-runs test to validate improvement

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feat/rootcause-tracing`
3. Commit with conventional commits: `feat:`, `fix:`, `docs:`
4. Open PR with test results attached

---

*Built with Claude AI · Powered by k6 · Monitored by Prometheus*
