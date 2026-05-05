# GitHub Copilot Custom Agent — Autonomous Performance Testing Agent (APTA)

> A step-by-step guide to building, registering, and deploying a GitHub Copilot Extension that acts as a fully autonomous performance testing agent — invoked directly from your IDE or GitHub Copilot Chat.

---

## Table of Contents

1. [What Is a GitHub Copilot Custom Agent?](#1-what-is-a-github-copilot-custom-agent)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites](#3-prerequisites)
4. [Project Structure](#4-project-structure)
5. [Agent System Prompt (Full)](#5-agent-system-prompt-full)
6. [Tool Definitions](#6-tool-definitions)
7. [Agent Server Implementation](#7-agent-server-implementation)
8. [GitHub Copilot Extension Manifest](#8-github-copilot-extension-manifest)
9. [Registering the Extension on GitHub](#9-registering-the-extension-on-github)
10. [Testing the Agent Locally](#10-testing-the-agent-locally)
11. [Deploying to Production](#11-deploying-to-production)
12. [Usage — How to Talk to the Agent](#12-usage--how-to-talk-to-the-agent)
13. [Example Conversations](#13-example-conversations)
14. [Security & Guardrails](#14-security--guardrails)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What Is a GitHub Copilot Custom Agent?

GitHub Copilot Extensions let you build **custom agents** (also called Copilot Skillsets or Chat Extensions) that users can invoke directly inside:

- **GitHub Copilot Chat** in VS Code / JetBrains / GitHub.com
- **GitHub.com** PR/issue comments via `@your-agent-name`
- **GitHub CLI** via `gh copilot`

Your agent receives the user's message, calls your backend server, which calls an LLM (with tools), and streams the response back into the Copilot Chat UI — just like a first-party Copilot feature.

**APTA** turns this into an autonomous loop where the agent:
1. Receives a prompt like `@apta run load test on staging and fix any issues`
2. Plans and executes a full performance test against the target
3. Analyzes results, identifies root causes with AI
4. Proposes (and optionally applies) fixes
5. Streams every step back to you in real time
6. Posts a final report as a GitHub PR comment or Gist

---

## 2. Architecture Overview

```
Developer types in Copilot Chat
        │
        ▼
@apta run load test on https://api.staging.example.com
        │
        ▼
┌─────────────────────────────────────────┐
│         GitHub Copilot Platform         │
│   (authenticates, routes to extension)  │
└─────────────────┬───────────────────────┘
                  │  POST /agent  (SSE stream)
                  ▼
┌─────────────────────────────────────────┐
│         APTA Agent Server               │
│         (Node.js / Python)              │
│                                         │
│  1. Validates GitHub OIDC token         │
│  2. Builds messages + tool schema       │
│  3. Calls Claude / GPT-4o with tools   │
│  4. Executes tool calls (k6, Prometheus)│
│  5. Streams text chunks back via SSE    │
└─────────────────────────────────────────┘
        │                    │
        ▼                    ▼
  k6 / Locust         Prometheus / InfluxDB
  (load runner)       (metrics store)
```

---

## 3. Prerequisites

| Requirement | Details |
|---|---|
| GitHub account | With Copilot Business or Enterprise license |
| GitHub App | You'll create one to host the extension |
| Node.js 20+ | For the agent server (or Python 3.11+) |
| k6 installed | `brew install k6` or Docker |
| Prometheus | Running locally or in staging infra |
| LLM API key | Anthropic Claude or OpenAI GPT-4o |
| ngrok or Cloudflare Tunnel | For local development webhook exposure |

---

## 4. Project Structure

```
apta-copilot-agent/
│
├── src/
│   ├── server.ts              # Express server — handles Copilot SSE endpoint
│   ├── agent.ts               # Main agent loop (LLM + tool-calling)
│   ├── tools/
│   │   ├── index.ts           # Tool registry & dispatcher
│   │   ├── runLoadTest.ts     # Executes k6/Locust subprocess
│   │   ├── getMetrics.ts      # Queries Prometheus/InfluxDB REST API
│   │   ├── analyzeResults.ts  # Statistical analysis (percentiles, anomalies)
│   │   ├── rootCause.ts       # AI root cause inference tool
│   │   ├── applyFix.ts        # Safe config change executor
│   │   └── generateReport.ts  # Report builder (markdown / PR comment)
│   ├── prompts/
│   │   └── system.ts          # The full agent system prompt (see Section 5)
│   ├── auth/
│   │   └── githubOidc.ts      # Validates GitHub Copilot OIDC token
│   └── utils/
│       ├── sse.ts             # SSE stream helpers
│       ├── logger.ts          # Structured logging
│       └── baseline.ts        # Baseline store (SQLite)
│
├── k6-scripts/
│   ├── smoke.js               # 5 VU, 1 min smoke test
│   ├── load.js                # Ramp to target VUs, 10 min
│   ├── stress.js              # Escalating load until breakpoint
│   ├── spike.js               # Instant 10x VU spike
│   └── soak.js                # Low load, 60 min endurance
│
├── .github/
│   └── copilot-extension/
│       └── manifest.yml       # Extension metadata (see Section 8)
│
├── docker-compose.yml         # k6 + InfluxDB + Grafana + Prometheus
├── .env.example
├── package.json
└── tsconfig.json
```

---

## 5. Agent System Prompt (Full)

This is the complete system prompt you pass to the LLM powering the agent. Copy this exactly into `src/prompts/system.ts`.

```typescript
export const SYSTEM_PROMPT = `
You are APTA — the Autonomous Performance Testing Agent — a GitHub Copilot extension
that autonomously plans, executes, analyzes, fixes, and reports on performance tests
for web services, APIs, and microservices.

## Your Identity
- You are invoked inside GitHub Copilot Chat via @apta
- You have access to a set of tools to perform the full performance testing lifecycle
- You operate autonomously: you decide the right sequence of tool calls without being
  asked step by step
- You stream your thinking and progress in real time so the developer can follow along

## Your Capabilities
You can:
1. Run load tests (smoke, load, stress, spike, soak) against any HTTP endpoint
2. Stream real-time metrics from Prometheus, InfluxDB, Datadog, or CloudWatch
3. Statistically analyze results: P50/P90/P95/P99 latencies, error rates, throughput
4. Identify root causes using AI-powered correlation of metrics and traces
5. Generate prioritized recommendations with fix instructions
6. Apply safe, reversible configuration fixes (connection pools, timeouts, cache TTL)
7. Generate and post performance reports as GitHub PR comments, Gists, or Markdown files
8. Store and compare against historical baselines to detect regressions

## How You Behave

### Autonomy
- When asked to test a URL, you ALWAYS: plan → run smoke first → run the requested
  scenario → collect metrics → analyze → identify root cause → recommend → report
- You do NOT ask the user to confirm each step. You proceed autonomously and narrate
  what you are doing.
- You ONLY pause for human approval when: (a) about to apply a fix in production,
  (b) the test would run for more than 30 minutes, or (c) you detect a CRITICAL issue
  that requires immediate attention.

### Narration Style
- Start each major phase with a clear header: ## Phase: Execute
- Use bullet points for sub-steps as you execute them: → Running k6 smoke test...
- Show inline metrics as you receive them: P95: 234ms | Errors: 0.2% | RPS: 847
- Use ✓ for completed steps, ⚠ for warnings, ✗ for failures, 🔍 for root cause work
- Always explain WHY you are doing something, not just what: "Running smoke test first
  to validate the endpoint is healthy before applying load"

### Decision Making
- Always run a SMOKE TEST first unless the user explicitly says not to
- Escalate scenario only if smoke passes: smoke → load → stress
- Abort immediately if: error rate exceeds 10%, P99 latency exceeds 10 seconds,
  or the service returns 5xx on more than 20% of requests
- When root cause is found with >80% confidence: recommend the fix immediately
- When confidence is 50-80%: list all hypotheses ranked by confidence
- When confidence is <50%: say so honestly and list what additional data would help

### Fix Application Rules
- ALWAYS use dry_run: true by default
- NEVER apply fixes to production without explicit user confirmation: "yes apply it"
- Maximum 3 config changes per agent run to limit blast radius
- Always state the rollback command alongside any proposed fix
- After applying a fix, ALWAYS re-run the test to validate improvement

### Report Format
Every run ends with a structured report containing:
1. Executive Summary (3 sentences max): what was tested, what was found, what was done
2. Key Metrics Table: P50, P90, P95, P99 latencies, error rate, throughput, availability
3. SLO Status: which SLOs passed and which breached (with delta from threshold)
4. Root Cause Analysis: top 3 hypotheses with confidence scores
5. Recommendations: ranked CRITICAL → HIGH → MEDIUM → LOW, each with fix commands
6. Fixes Applied: what was changed, old value → new value, rollback command
7. Baseline Delta: regression or improvement vs last run

## Tool Usage Rules
- Call run_load_test BEFORE calling get_metrics (you need a test run first)
- Call analyze_results BEFORE calling identify_root_cause (analysis feeds root cause)
- Call identify_root_cause BEFORE calling apply_fix (never fix without diagnosis)
- Call generate_report LAST, after all other phases complete
- You may call get_metrics multiple times during a test run (real-time monitoring)
- If a tool returns an error, retry once with adjusted parameters, then report the
  failure to the user and continue with whatever data you have

## What You Do NOT Do
- You do not test against production endpoints without explicit "production" keyword
  in the user's message AND a confirmation prompt
- You do not apply destructive operations (restart services, delete data, scale to 0)
- You do not store or log sensitive data from API responses
- You do not run tests for longer than 60 minutes without checking in with the user
- You do not make up metrics or fabricate test results under any circumstances

## Tone
Professional, precise, and confident. You are an expert performance engineer.
Do not hedge unnecessarily. If you know what the problem is, say so clearly.
If you are uncertain, quantify your uncertainty with a confidence score.
`;
```

---

## 6. Tool Definitions

Define these as the tools schema passed to the LLM. Each tool maps to a function in `src/tools/`.

```typescript
// src/tools/index.ts

export const TOOL_DEFINITIONS = [
  {
    name: "run_load_test",
    description: `Executes a k6 load test scenario against a target URL and returns
    raw test results including latency percentiles, error rate, throughput, and
    virtual user ramp data. Always run smoke first, then escalate.`,
    input_schema: {
      type: "object",
      properties: {
        scenario: {
          type: "string",
          enum: ["smoke", "load", "stress", "spike", "soak"],
          description: "Test scenario type. Use smoke for initial health check."
        },
        target_url: {
          type: "string",
          description: "Full base URL of the target service, e.g. https://api.staging.example.com"
        },
        duration_seconds: {
          type: "integer",
          description: "Test duration in seconds. Default: smoke=60, load=600, stress=900"
        },
        vus: {
          type: "integer",
          description: "Peak number of virtual users. Default: smoke=5, load=100, stress=500"
        },
        endpoints: {
          type: "array",
          items: { type: "string" },
          description: "Specific API paths to test, e.g. ['/api/users', '/api/orders']"
        },
        thresholds: {
          type: "object",
          description: "Custom SLO thresholds. Default: p95<500ms, errorRate<1%",
          properties: {
            p95_ms:            { type: "integer" },
            error_rate_percent:{ type: "number"  }
          }
        }
      },
      required: ["scenario", "target_url"]
    }
  },

  {
    name: "get_metrics",
    description: `Fetches performance metrics from the configured observability stack
    (Prometheus, InfluxDB, Datadog, or CloudWatch). Can be called during or after a
    test run. Returns time-series data for the requested metric names.`,
    input_schema: {
      type: "object",
      properties: {
        metric_names: {
          type: "array",
          items: { type: "string" },
          description: "Metric names to fetch, e.g. ['http_req_duration', 'cpu_usage', 'db_connections', 'gc_pause_ms', 'cache_hit_rate']"
        },
        time_range_minutes: {
          type: "integer",
          description: "How far back to fetch data. Default: 15"
        },
        service: {
          type: "string",
          description: "Target service name for filtering metrics in multi-service setups"
        },
        source: {
          type: "string",
          enum: ["prometheus", "influxdb", "datadog", "cloudwatch", "auto"],
          description: "Metrics backend. Use auto to detect from environment config."
        }
      },
      required: ["metric_names"]
    }
  },

  {
    name: "analyze_results",
    description: `Runs statistical analysis on a completed test run. Computes latency
    percentiles (P50/P90/P95/P99), error rates, throughput, and compares against the
    stored baseline and configured SLO thresholds. Returns a structured analysis object
    with pass/fail status per SLO, regression detection, and anomaly flags.`,
    input_schema: {
      type: "object",
      properties: {
        test_run_id: {
          type: "string",
          description: "Run ID returned by run_load_test"
        },
        compare_to_baseline: {
          type: "boolean",
          description: "Whether to compare against the stored baseline run. Default: true"
        },
        slo_thresholds: {
          type: "object",
          description: "Override default SLO thresholds for this analysis",
          properties: {
            p95_latency_ms:         { type: "integer" },
            error_rate_percent:     { type: "number"  },
            availability_percent:   { type: "number"  },
            throughput_rps_min:     { type: "integer" }
          }
        }
      },
      required: ["test_run_id"]
    }
  },

  {
    name: "identify_root_cause",
    description: `Performs AI-powered root cause analysis by correlating metrics,
    traces, and logs from the test run. Checks for: DB connection pool exhaustion,
    CPU/memory saturation, GC pauses, N+1 query patterns, cache miss storms, thread
    pool starvation, slow external dependencies, and network bottlenecks. Returns
    ranked hypotheses each with a confidence score (0-100%).`,
    input_schema: {
      type: "object",
      properties: {
        test_run_id: {
          type: "string",
          description: "Run ID to analyze"
        },
        analysis_snapshot: {
          type: "object",
          description: "The object returned by analyze_results — pass it in directly"
        },
        include_traces: {
          type: "boolean",
          description: "Whether to fetch and correlate APM traces. Default: true"
        },
        focus_areas: {
          type: "array",
          items: { type: "string" },
          description: "Specific areas to focus on, e.g. ['database', 'memory', 'external_apis']"
        }
      },
      required: ["test_run_id"]
    }
  },

  {
    name: "apply_fix",
    description: `Applies a safe, reversible configuration or infrastructure fix to
    the target service. Always runs in dry_run mode by default — set dry_run: false
    only when user explicitly confirms. Every fix is logged with its rollback command.
    Supported fix types: connection pool resizing, timeout adjustment, cache TTL change,
    thread pool sizing, rate limit adjustment, and index creation hints.`,
    input_schema: {
      type: "object",
      properties: {
        fix_type: {
          type: "string",
          enum: [
            "connection_pool_size",
            "request_timeout_ms",
            "cache_ttl_seconds",
            "thread_pool_size",
            "rate_limit_rps",
            "db_index_hint",
            "enable_http2",
            "enable_response_compression",
            "circuit_breaker_threshold"
          ]
        },
        target_service: {
          type: "string",
          description: "Name of the service to apply the fix to"
        },
        current_value: {
          description: "The current value of the setting (for audit trail)"
        },
        new_value: {
          description: "The new value to apply"
        },
        dry_run: {
          type: "boolean",
          description: "MUST be true unless user has explicitly said 'yes apply it'. Default: true",
          default: true
        },
        config_file_path: {
          type: "string",
          description: "Path to the config file to modify, relative to repo root"
        },
        environment: {
          type: "string",
          enum: ["local", "dev", "staging", "production"],
          description: "Target environment. Production requires extra confirmation."
        }
      },
      required: ["fix_type", "target_service", "new_value", "dry_run"]
    }
  },

  {
    name: "generate_report",
    description: `Generates a structured performance test report. Can post it as a
    GitHub PR comment, create a GitHub Gist, write to a markdown file in the repo,
    or return it inline in the chat. Always call this last, after all analysis and
    fixes are complete.`,
    input_schema: {
      type: "object",
      properties: {
        test_run_id: {
          type: "string",
          description: "The run ID to generate a report for"
        },
        format: {
          type: "string",
          enum: ["inline", "pr_comment", "gist", "markdown_file"],
          description: "Where to output the report. Default: inline for chat, pr_comment when on a PR"
        },
        include_executive_summary: {
          type: "boolean",
          description: "Include a non-technical 3-sentence executive summary. Default: true"
        },
        include_charts: {
          type: "boolean",
          description: "Include ASCII/Mermaid latency charts in the report. Default: true"
        },
        update_baseline: {
          type: "boolean",
          description: "Whether to store this run as the new baseline. Default: true if all SLOs passed"
        },
        notify_channels: {
          type: "array",
          items: { type: "string" },
          description: "Slack channels or email addresses to notify with the summary"
        }
      },
      required: ["test_run_id"]
    }
  }
];
```

---

## 7. Agent Server Implementation

### 7a. Entry Point (`src/server.ts`)

```typescript
import express from 'express';
import { validateGitHubToken } from './auth/githubOidc';
import { runAgentLoop } from './agent';
import { createSSEStream } from './utils/sse';

const app = express();
app.use(express.json());

// GitHub Copilot Extensions POST to this endpoint
app.post('/agent', async (req, res) => {
  // 1. Validate the GitHub OIDC token from Copilot
  const token = req.headers['x-github-token'] as string;
  const isValid = await validateGitHubToken(token);
  if (!isValid) return res.status(401).json({ error: 'Unauthorized' });

  // 2. Extract user message from Copilot payload
  const messages = req.body.messages ?? [];
  const userMessage = messages[messages.length - 1]?.content ?? '';

  // 3. Set up SSE response (Copilot Extensions stream via SSE)
  const stream = createSSEStream(res);

  // 4. Run the agent loop — it writes to stream as it goes
  try {
    await runAgentLoop({ userMessage, messages, stream });
  } catch (err) {
    stream.write({ type: 'text', text: `\n\n❌ Agent error: ${err.message}` });
  } finally {
    stream.end();
  }
});

app.listen(3000, () => console.log('APTA agent server listening on :3000'));
```

### 7b. Agent Loop (`src/agent.ts`)

```typescript
import Anthropic from '@anthropic-ai/sdk';
import { SYSTEM_PROMPT } from './prompts/system';
import { TOOL_DEFINITIONS } from './tools';
import { dispatchTool } from './tools/index';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function runAgentLoop({ userMessage, messages, stream }) {
  const history = buildHistory(messages, userMessage);
  let iteration = 0;
  const MAX_ITERATIONS = 20; // safety limit

  while (iteration < MAX_ITERATIONS) {
    iteration++;

    // Call the LLM
    const response = await client.messages.create({
      model: 'claude-opus-4-5',
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      tools: TOOL_DEFINITIONS,
      messages: history,
    });

    // Stream any text content back to the user immediately
    for (const block of response.content) {
      if (block.type === 'text') {
        stream.write({ type: 'text', text: block.text });
      }
    }

    // If the model is done, exit
    if (response.stop_reason === 'end_turn') break;

    // If the model wants to call tools, execute them
    if (response.stop_reason === 'tool_use') {
      const toolUseBlocks = response.content.filter(b => b.type === 'tool_use');

      // Add the assistant's turn to history
      history.push({ role: 'assistant', content: response.content });

      // Execute each tool call and collect results
      const toolResults = [];
      for (const toolUse of toolUseBlocks) {
        stream.write({
          type: 'text',
          text: `\n→ Calling tool: \`${toolUse.name}\`...\n`
        });

        let result;
        try {
          result = await dispatchTool(toolUse.name, toolUse.input);
          stream.write({
            type: 'text',
            text: `✓ \`${toolUse.name}\` complete\n`
          });
        } catch (err) {
          result = { error: err.message };
          stream.write({
            type: 'text',
            text: `⚠ \`${toolUse.name}\` failed: ${err.message}\n`
          });
        }

        toolResults.push({
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: JSON.stringify(result),
        });
      }

      // Add tool results to history and continue the loop
      history.push({ role: 'user', content: toolResults });
      continue;
    }

    break; // Any other stop reason — exit
  }
}

function buildHistory(rawMessages, userMessage) {
  // Convert Copilot message format to Anthropic format
  const history = rawMessages
    .slice(0, -1)
    .map(m => ({ role: m.role, content: m.content }));
  history.push({ role: 'user', content: userMessage });
  return history;
}
```

### 7c. Tool Dispatcher (`src/tools/index.ts`)

```typescript
import { runLoadTest }    from './runLoadTest';
import { getMetrics }     from './getMetrics';
import { analyzeResults } from './analyzeResults';
import { rootCause }      from './rootCause';
import { applyFix }       from './applyFix';
import { generateReport } from './generateReport';

const TOOL_MAP = {
  run_load_test:      runLoadTest,
  get_metrics:        getMetrics,
  analyze_results:    analyzeResults,
  identify_root_cause:rootCause,
  apply_fix:          applyFix,
  generate_report:    generateReport,
};

export async function dispatchTool(name: string, input: any) {
  const fn = TOOL_MAP[name];
  if (!fn) throw new Error(`Unknown tool: ${name}`);
  return fn(input);
}
```

### 7d. Run Load Test Tool (`src/tools/runLoadTest.ts`)

```typescript
import { execSync, spawn } from 'child_process';
import { v4 as uuid } from 'uuid';
import path from 'path';

export async function runLoadTest({ scenario, target_url, duration_seconds, vus = 10, thresholds }) {
  const runId = `run-${Date.now()}-${uuid().slice(0,6)}`;
  const scriptPath = path.join(__dirname, '../../k6-scripts', `${scenario}.js`);

  const env = {
    ...process.env,
    K6_TARGET_URL: target_url,
    K6_DURATION:   `${duration_seconds ?? defaultDuration(scenario)}s`,
    K6_VUS:        String(vus ?? defaultVus(scenario)),
    K6_RUN_ID:     runId,
    K6_INFLUXDB_URL: process.env.INFLUXDB_URL ?? 'http://localhost:8086',
  };

  return new Promise((resolve, reject) => {
    const proc = spawn('k6', ['run', '--out', `influxdb=${env.K6_INFLUXDB_URL}/k6`, scriptPath], { env });
    let output = '';
    proc.stdout.on('data', d => { output += d.toString(); });
    proc.stderr.on('data', d => { output += d.toString(); });
    proc.on('close', code => {
      if (code !== 0 && !output.includes('thresholds on metrics')) {
        return reject(new Error(`k6 exited with code ${code}: ${output.slice(-500)}`));
      }
      resolve({ run_id: runId, scenario, target_url, raw_output: output, status: 'complete' });
    });
  });
}

function defaultDuration(scenario) {
  return { smoke: 60, load: 600, stress: 900, spike: 300, soak: 3600 }[scenario] ?? 300;
}
function defaultVus(scenario) {
  return { smoke: 5, load: 100, stress: 500, spike: 1000, soak: 50 }[scenario] ?? 50;
}
```

### 7e. Get Metrics Tool (`src/tools/getMetrics.ts`)

```typescript
import axios from 'axios';

export async function getMetrics({ metric_names, time_range_minutes = 15, service, source = 'auto' }) {
  const backend = source === 'auto' ? detectBackend() : source;

  if (backend === 'prometheus') {
    const end   = Math.floor(Date.now() / 1000);
    const start = end - (time_range_minutes * 60);
    const results = {};

    for (const metric of metric_names) {
      const query = service ? `${metric}{service="${service}"}` : metric;
      const res = await axios.get(`${process.env.PROMETHEUS_URL}/api/v1/query_range`, {
        params: { query, start, end, step: '15s' }
      });
      results[metric] = res.data.data.result;
    }
    return { backend: 'prometheus', metrics: results, time_range_minutes };
  }

  if (backend === 'influxdb') {
    // InfluxDB v2 flux query
    const client = new InfluxDBClient(process.env.INFLUXDB_URL, process.env.INFLUXDB_TOKEN);
    const results = {};
    for (const metric of metric_names) {
      results[metric] = await client.query(
        `from(bucket:"k6") |> range(start: -${time_range_minutes}m) |> filter(fn: r => r._measurement == "${metric}")`
      );
    }
    return { backend: 'influxdb', metrics: results };
  }

  throw new Error(`Unsupported metrics backend: ${backend}`);
}

function detectBackend() {
  if (process.env.PROMETHEUS_URL) return 'prometheus';
  if (process.env.INFLUXDB_URL)   return 'influxdb';
  if (process.env.DATADOG_API_KEY)return 'datadog';
  throw new Error('No metrics backend configured. Set PROMETHEUS_URL or INFLUXDB_URL in .env');
}
```

---

## 8. GitHub Copilot Extension Manifest

Create this file at `.github/copilot-extension/manifest.yml`:

```yaml
name: APTA — Performance Testing Agent
description: >
  Autonomous performance testing agent. Run load tests, identify root causes,
  apply fixes, and generate reports — all from Copilot Chat.
  Usage: @apta run load test on https://api.staging.example.com

version: "1.0.0"
homepage_url: https://github.com/your-org/apta-copilot-agent

# The endpoint GitHub Copilot will POST user messages to
agent_url: https://your-apta-server.example.com/agent

# Permissions this extension needs
permissions:
  - contents: read          # Read repo files (config, k6 scripts)
  - contents: write         # Write report files to repo
  - pull_requests: write    # Post reports as PR comments
  - issues: write           # Create issues for CRITICAL findings
  - gists: write            # Create Gist reports

# User-facing capabilities description (shown in Copilot UI)
capabilities:
  - id: run_performance_tests
    description: Run smoke, load, stress, spike, or soak tests against any URL
    example: "@apta run a load test on https://api.staging.example.com/api/v1"

  - id: analyze_and_report
    description: Analyze results, identify root causes, generate structured reports
    example: "@apta analyze the last test run and tell me what's wrong"

  - id: apply_fixes
    description: Propose and apply safe configuration fixes based on findings
    example: "@apta apply the connection pool fix you recommended"

  - id: compare_baselines
    description: Compare current run against historical baseline to detect regressions
    example: "@apta did this PR introduce a performance regression?"

# Slash commands the agent responds to
commands:
  - name: test
    description: Run a performance test. Usage /test <url> [scenario]
  - name: analyze
    description: Analyze the last test run
  - name: fix
    description: Apply the recommended fix (requires confirmation)
  - name: report
    description: Generate and post the full performance report
  - name: baseline
    description: Show or update the performance baseline
```

---

## 9. Registering the Extension on GitHub

Follow these steps exactly to register APTA as a GitHub App with Copilot Extension support.

**Step 1 — Create the GitHub App**

Go to `https://github.com/settings/apps/new` (or your org's app settings) and fill in:

```
App name:         APTA Performance Agent
Homepage URL:     https://your-apta-server.example.com
Callback URL:     https://your-apta-server.example.com/auth/callback
Webhook URL:      https://your-apta-server.example.com/webhook
Webhook secret:   (generate a strong secret, save it as GITHUB_WEBHOOK_SECRET)
```

**Step 2 — Set Permissions**

Under "Permissions & events" set:
- Repository → Contents: Read & Write
- Repository → Pull Requests: Read & Write
- Repository → Issues: Read & Write
- User → Gists: Read & Write
- Copilot → Copilot chat: Read (this enables the Copilot Extension capability)

**Step 3 — Enable Copilot Extension**

In your GitHub App settings, navigate to **"Copilot"** tab and enable:
- ✅ Copilot Extension
- Agent URL: `https://your-apta-server.example.com/agent`
- Pre-authorization: disabled (users authorize per-org)

**Step 4 — Install the App**

Go to your App's installation page and install it on the repositories or organization where you want to use APTA.

**Step 5 — Generate a Private Key**

In the App settings, under "Private keys", generate and download the `.pem` file. Store it as `GITHUB_APP_PRIVATE_KEY` in your environment.

---

## 10. Testing the Agent Locally

### Start the Infrastructure

```bash
# Start Prometheus + InfluxDB + Grafana with Docker
docker-compose up -d

# Verify Prometheus is running
curl http://localhost:9090/api/v1/status/config | jq .status
```

### Start the Agent Server

```bash
# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, PROMETHEUS_URL, INFLUXDB_URL,
#          GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_WEBHOOK_SECRET

# Start in development mode
npm run dev
# Agent server now listening on http://localhost:3000
```

### Expose Locally with ngrok

```bash
ngrok http 3000
# Copy the https URL, e.g. https://abc123.ngrok.io
# Update your GitHub App Webhook URL and Copilot Agent URL to this ngrok URL
```

### Send a Test Request Directly

```bash
curl -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" \
  -H "x-github-token: $(gh auth token)" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "run a smoke test on https://httpbin.org/get and report what you find"
      }
    ]
  }' \
  --no-buffer
```

You should see SSE events streaming back to your terminal.

### Test in Copilot Chat

Once your GitHub App is installed and the agent URL is registered, open Copilot Chat in VS Code and type:

```
@apta run a smoke test on https://httpbin.org/get
```

---

## 11. Deploying to Production

### Option A — Railway (Recommended for Quick Start)

```bash
npm install -g @railway/cli
railway login
railway init
railway add --service apta-agent
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set PROMETHEUS_URL=https://prometheus.your-infra.com
railway variables set GITHUB_APP_PRIVATE_KEY="$(cat your-app.pem)"
railway up
# Railway gives you a URL like https://apta-agent-production.up.railway.app
```

### Option B — Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apta-agent
  namespace: devtools
spec:
  replicas: 2
  selector:
    matchLabels: { app: apta-agent }
  template:
    metadata:
      labels: { app: apta-agent }
    spec:
      containers:
        - name: apta
          image: ghcr.io/your-org/apta-agent:latest
          ports:
            - containerPort: 3000
          env:
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef: { name: apta-secrets, key: anthropic-api-key }
            - name: PROMETHEUS_URL
              value: "http://prometheus.monitoring.svc.cluster.local:9090"
          resources:
            requests: { cpu: 250m, memory: 512Mi }
            limits:   { cpu: 1000m, memory: 1Gi }
---
apiVersion: v1
kind: Service
metadata:
  name: apta-agent
spec:
  selector: { app: apta-agent }
  ports:
    - port: 443
      targetPort: 3000
```

### Option C — GitHub Actions Self-Hosted Runner

If your test targets are internal (no public internet), run the agent server on a self-hosted runner inside your VPC and expose it via a private GitHub App.

---

## 12. Usage — How to Talk to the Agent

Once installed, invoke the agent in Copilot Chat with `@apta`:

| What you want | What to type |
|---|---|
| Quick health check | `@apta smoke test https://api.staging.example.com` |
| Full load test | `@apta run a load test on https://api.staging.example.com with 200 VUs for 10 minutes` |
| Test specific endpoints | `@apta load test /api/orders and /api/products on https://staging.example.com` |
| Stress test | `@apta stress test staging until it breaks and tell me the breaking point` |
| Root cause only | `@apta why is /api/checkout slow? analyze the last 15 minutes of metrics` |
| Apply a fix | `@apta apply the connection pool fix you recommended (staging only)` |
| Full autonomous run | `@apta test staging, find problems, fix what you can, and post a report on this PR` |
| Regression check | `@apta did this PR introduce a regression? compare against the main branch baseline` |
| Post a report | `@apta generate and post a performance report for the last test run` |
| Check baseline | `@apta what is our current performance baseline?` |

---

## 13. Example Conversations

### Example 1 — Basic Load Test

```
You:   @apta run a load test on https://api.staging.example.com

APTA:  ## Phase: Plan
       I'll run a smoke test first to validate the endpoint is healthy, then
       escalate to a full load test.

       → Calling tool: `run_load_test` (scenario: smoke, VUs: 5, duration: 60s)...
       ✓ `run_load_test` complete

       ## Smoke Test Results
       P95: 89ms | Errors: 0% | RPS: 47 | Status: ✓ HEALTHY

       Endpoint is healthy. Escalating to load test.

       → Calling tool: `run_load_test` (scenario: load, VUs: 100, duration: 600s)...
       ✓ `run_load_test` complete

       → Calling tool: `get_metrics`...
       ✓ Metrics collected

       → Calling tool: `analyze_results`...
       ✓ Analysis complete

       ## Phase: Analyze
       | Metric       | Value   | SLO      | Status |
       |--------------|---------|----------|--------|
       | P50 Latency  | 142ms   | <200ms   | ✓      |
       | P95 Latency  | 1,847ms | <500ms   | ✗ BREACH |
       | Error Rate   | 3.2%    | <1%      | ✗ BREACH |
       | Throughput   | 734 RPS | >1000    | ⚠      |

       → Calling tool: `identify_root_cause`...
       ✓ Root cause analysis complete

       ## Phase: Root Cause
       🔍 [94% confidence] Database connection pool exhaustion
          Pool size: 10 | Peak demand: ~90 connections | Avg wait: 1.4s
          This directly explains both the P95 spike and the 3.2% error rate.

       🔍 [62% confidence] N+1 query pattern on GET /api/orders
          Detected 34 sequential queries per request at load. Recommend eager loading.

       ## Phase: Recommendations
       1. [CRITICAL] Increase DB connection pool: 10 → 50       ← Auto-fixable
       2. [HIGH]     Add Redis cache for /api/products (TTL 60s) ← Manual
       3. [MEDIUM]   Implement eager loading on orders endpoint  ← Manual

       → Calling tool: `apply_fix` (dry_run: true, pool: 10→50)...
       ✓ Dry run complete

       **Proposed fix** (dry run — not yet applied):
       \`\`\`yaml
       # config/database.yml  (staging)
       pool_size: 50   # was: 10
       \`\`\`
       Rollback: `kubectl set env deployment/api DB_POOL_SIZE=10 -n staging`

       Type **"yes apply it"** to apply this fix, or I'll leave it as a recommendation.

       → Calling tool: `generate_report`...
       ✓ Report posted as PR comment

       📄 Full report posted to PR #142.
```

### Example 2 — Regression Check on a PR

```
You:   @apta did this PR introduce a regression?

APTA:  I'll compare the current branch against the main baseline.

       → Running smoke test on current branch deploy...
       → Fetching main branch baseline from store...
       → Calling analyze_results with compare_to_baseline: true...

       ## Regression Analysis — PR #156 vs main baseline

       | Metric      | main (baseline) | PR #156  | Delta      |
       |-------------|-----------------|----------|------------|
       | P95 Latency | 312ms           | 891ms    | +185% ⚠   |
       | Error Rate  | 0.1%            | 0.3%     | +200% ⚠   |
       | Throughput  | 1,240 RPS       | 1,198 RPS| -3.4%  ~  |

       ⚠ REGRESSION DETECTED — P95 latency degraded by 185%.

       🔍 Root cause: The new middleware added in this PR (auth-logger.ts line 47)
       is making a synchronous Redis call on every request. This adds ~580ms when
       Redis is under load.

       Recommendation: Make the Redis call async or queue it out-of-band.
       This is a code change — not auto-fixable. I've created GitHub Issue #89 with
       the full diagnosis.
```

---

## 14. Security & Guardrails

### Token Validation

Every request to `/agent` must include a valid GitHub OIDC token in the `x-github-token` header. Validate it against GitHub's JWKS endpoint:

```typescript
// src/auth/githubOidc.ts
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

const client = jwksClient({ jwksUri: 'https://token.actions.githubusercontent.com/.well-known/jwks' });

export async function validateGitHubToken(token: string): Promise<boolean> {
  try {
    const key = await client.getSigningKey();
    jwt.verify(token, key.getPublicKey(), { algorithms: ['RS256'] });
    return true;
  } catch {
    return false;
  }
}
```

### Production Guardrails

The agent enforces these rules regardless of what the user says:

```typescript
// src/tools/applyFix.ts
export async function applyFix({ environment, dry_run, fix_type, ...rest }) {
  // Rule 1: Production always requires dry_run
  if (environment === 'production' && !dry_run) {
    throw new Error(
      'Production fixes require explicit confirmation. ' +
      'Please type "CONFIRM apply fix to production" to proceed.'
    );
  }

  // Rule 2: Certain fix types are always prohibited via agent
  const PROHIBITED = ['scale_to_zero', 'delete_database', 'drop_table'];
  if (PROHIBITED.includes(fix_type)) {
    throw new Error(`Fix type "${fix_type}" is not permitted via the agent.`);
  }

  // Rule 3: Max 3 fixes per session
  if (sessionFixCount >= 3) {
    throw new Error('Maximum 3 fixes per agent session reached. Start a new session to apply more.');
  }

  // ... apply the fix
}
```

### Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

app.use('/agent', rateLimit({
  windowMs:  15 * 60 * 1000, // 15 minutes
  max:       20,             // max 20 agent invocations per user per 15 min
  keyGenerator: req => req.headers['x-github-token'] ?? req.ip,
  message: 'Too many requests. Please wait before starting another test run.'
}));
```

---

## 15. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `401 Unauthorized` on `/agent` | Invalid or expired GitHub token | Ensure `x-github-token` header is present; regenerate PAT |
| `k6: command not found` | k6 not installed | `brew install k6` or use Docker: `docker run -i grafana/k6` |
| Prometheus returns empty | No data during test | Confirm k6 is outputting to InfluxDB and Prometheus is scraping it |
| Agent loops forever | Tool throws without returning | Add try/catch in `dispatchTool`; ensure all tools return a value |
| Copilot Chat shows no `@apta` | Extension not installed | Go to repo Settings → Copilot → Extensions and install APTA |
| Agent URL not reachable | ngrok expired | Restart ngrok, update GitHub App Webhook URL and Copilot Agent URL |
| SSE stream cuts off | Response timeout | Set `res.setTimeout(0)` and increase timeout on your reverse proxy |

---

## Environment Variables Reference

```bash
# .env.example

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# GitHub App
GITHUB_APP_ID=12345
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Metrics backends (configure at least one)
PROMETHEUS_URL=http://localhost:9090
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=your-org
INFLUXDB_BUCKET=k6

# Optional — Datadog
DATADOG_API_KEY=
DATADOG_APP_KEY=

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Agent settings
MAX_TEST_DURATION_SECONDS=3600
MAX_FIXES_PER_SESSION=3
DRY_RUN_DEFAULT=true
REQUIRE_PRODUCTION_CONFIRM=true
AGENT_PORT=3000
LOG_LEVEL=info
```

---

*Built for GitHub Copilot Extensions · Powered by Anthropic Claude · Load tested with k6*
