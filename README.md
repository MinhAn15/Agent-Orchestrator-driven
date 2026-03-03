# Antigravity

> **Open-source agent orchestration for production multi-agent systems**

[![CI](https://github.com/MinhAn15/Agent-Orchestrator-driven/actions/workflows/ci.yml/badge.svg)](https://github.com/MinhAn15/Agent-Orchestrator-driven/actions)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-v1.0.0-brightgreen)](https://github.com/MinhAn15/Agent-Orchestrator-driven/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

---

## Why Antigravity?

> **Your AI agents are only as reliable as the infrastructure beneath them.**

Most teams wire up LLM calls directly into business logic — and it works, until it doesn't.
Antigravity adds the missing production layer **without rewriting your existing code**:

| Problem you face today | What Antigravity gives you |
|---|---|
| Agents take dangerous actions with no checks | **Policy engine** — allow, deny, or require approval before any action runs |
| Conversations reset on every request | **Stateful memory** — InMemory, Redis, or Postgres, swappable at runtime |
| No idea why an agent failed or how much it cost | **Unified observability** — latency, token cost, and quality in one trace |
| Hard-coded integrations to Slack, DBs, GitHub | **Connector SDK** — plug-and-play adapters, add your own in < 50 lines |
| Starting from scratch for every new workflow | **Template gallery** — battle-tested workflow templates, load and render in 2 lines |
| LLM vendor lock-in | **Provider abstraction** — swap OpenAI → Ollama with one line |

**Antigravity is the backbone, not the brain — it makes your agents safe, observable, and composable without getting in the way.**

---

## Architecture

```mermaid
flowchart LR
    A(["Client / API Gateway"]) --> B(["Planner"])
    B --> C{"Policy Engine"}
    C -->|"allow"| D(["Executor"])
    C -->|"deny"| E(["Audit Log"])
    D --> F(["Tool / Connector Layer"])
    F --> G[("Memory & State Store")]
    D --> H(["Observability
latency · cost · quality"])
    G --> B
```

---

## Integrating into an Existing Project

Already have a Python project? Here is how to drop Antigravity in — no full rewrite required.

### Step 1 — Install

```bash
# Clone the repo and install as a local package
git clone https://github.com/MinhAn15/Agent-Orchestrator-driven.git
pip install -e ./Agent-Orchestrator-driven
```

Or copy only the modules you need:

```bash
# Minimal: just the LLM engine
cp Agent-Orchestrator-driven/src/llm_policy.py your_project/

# Connectors only
cp -r Agent-Orchestrator-driven/connectors/ your_project/connectors/
```

### Step 2 — Add a Policy Gate to your existing agent

```python
from antigravity.policy import PolicyEngine, Effect

policy = PolicyEngine()
policy.load_rules([
    {
        "id": "block-delete-in-prod",
        "priority": 1,
        "condition": {"action_type": "delete", "environment": "production"},
        "effect": "deny",
        "reason": "Destructive actions are forbidden in production.",
    },
    {
        "id": "require-approval-financial",
        "priority": 2,
        "condition": {"domain": "financial"},
        "effect": "require_approval",
        "reason": "Financial actions require human sign-off.",
    },
])

def run_action(action_type: str, context: dict):
    eval_ctx = {**context, "action_type": action_type}
    decision = policy.evaluate(eval_ctx)        # returns PolicyDecision

    if decision.is_denied:
        raise PermissionError(f"Blocked: {decision.reason}")
    if decision.requires_approval:
        request_human_approval(eval_ctx)        # your escalation hook

    return execute(action_type, context)
```

### Step 3 — Swap in Stateful Memory

The `MemoryBackend` interface uses a **namespace + key** model so different workflows never bleed state into each other.

```python
from antigravity.memory import create_memory_backend

# Local / tests
memory = create_memory_backend("memory")

# Production Redis
memory = create_memory_backend("redis", host="localhost", port=6379)

# Production Postgres
memory = create_memory_backend("postgres", dsn="postgresql://user:pass@host/db")

# Store and retrieve under (namespace, key)
memory.set("workflow_01", "session_42", {"history": [], "status": "active"})
state  = memory.get("workflow_01", "session_42")
keys   = memory.keys("workflow_01")        # list all keys in namespace
```

### Step 4 — Use the LLM Policy Engine

Replace raw LLM calls with a provider-agnostic engine that keeps your code LLM-vendor-free:

```python
from llm_policy import create_engine  # src/llm_policy.py

engine = create_engine("openai", model="gpt-4o-mini")  # production
engine = create_engine("ollama", model="llama3")         # local / private
engine = create_engine("stub")                           # unit tests, no API key

# All providers share the same interface
result = engine.decide(
    task="Classify this support ticket and suggest the next action.",
    context="You are a support triage agent for a SaaS product.",
)
print(result.content)   # LLM output
print(result.provider)  # "openai" | "ollama" | "stub"
print(result.usage)     # {"prompt_tokens": ..., "completion_tokens": ...}

# Swap provider at runtime without restarting
from llm_policy import OllamaProvider
engine.swap_provider(OllamaProvider(model="llama3"))
```

### Step 5 — Connect to your tools

```python
from connectors.slack_connector import SlackConnector
from connectors.sql_connector import SQLConnector

# Slack via Incoming Webhook
slack = SlackConnector(webhook_url="https://hooks.slack.com/services/...")
slack.send_alert(
    title="[P1] Database CPU > 90%",
    body="Incident auto-detected. Triggering remediation runbook.",
    level="error",   # 'info' | 'warning' | 'error'
)

# SQLite (default, zero deps)
with SQLConnector(dsn="app.db") as db:
    rows = db.query("SELECT * FROM incidents WHERE status = ?", ("open",))

# Postgres (set driver)
with SQLConnector(dsn="postgresql://user:pass@host/db", driver="psycopg2") as db:
    rows = db.query("SELECT * FROM incidents WHERE status = %s", ("open",))
```

### Step 6 — Load a workflow template

```python
from templates.gallery import get_gallery

gallery = get_gallery()          # auto-discovers all .md files in templates/

for t in gallery.list_all():
    print(f"{t.name:25s}  {t.description}")
# Incident Response          End-to-end agent workflow for triaging production incidents.
# Bug Triage                 Automated bug classification and routing.
# Customer Support           Multi-step support: classify, retrieve docs, escalate.

template = gallery.get("incident-response")
print(template.render({"team": "Platform", "severity": "P1", "service": "payments-api"}))
```

---

## Use Cases

> **Note:** The figures below are illustrative targets based on internal prototypes, not externally validated benchmarks. Reproducible benchmarks are in progress — see [`benchmarks/`](./benchmarks/).

### 1. Support Automation
Automatically triage, route, and resolve repetitive tickets with policy checks and escalation logic.
- Example: [`examples/support_automation/`](./examples/)

### 2. Growth Operations
Coordinate campaign planning, copy generation, QA, and launch workflows across agents.
- Example: [`examples/growth_ops/`](./examples/)

### 3. Incident Response
Detect anomalies, fan out diagnostics, and propose remediation runbooks automatically.
- Example: [`examples/incident_response/`](./examples/)

---

## Quickstart (fresh project)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose v2
- An LLM API key (OpenAI, Anthropic, or compatible)

```bash
git clone https://github.com/MinhAn15/Agent-Orchestrator-driven.git
cd Agent-Orchestrator-driven
cp .env.example .env   # set LLM_API_KEY and connector credentials
docker compose up -d
```

Then trigger a demo workflow:

```bash
curl -X POST http://localhost:8080/workflows/demo/run \
  -H "Content-Type: application/json" \
  -d '{"input": "run support automation sample"}'
```

Open [http://localhost:3000](http://localhost:3000) to see the workflow graph, latency metrics, and policy audit trail.

---

## Project Structure

```
.
├── src/              # Core engine: policy, memory, LLM provider abstraction
├── runtime/          # Agentic runtime semantics
├── connectors/       # Connector SDK: HTTP, Slack, SQL, GitHub, filesystem
├── benchmarks/       # Reproducible benchmark suite
├── examples/         # End-to-end workflow examples
├── templates/        # Reusable workflow template gallery
├── docs/             # MkDocs documentation source
└── tests/            # Unit and integration tests
```

---

## Contributing

Contributions are very welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before submitting.

- **Bug reports** → [Open an issue](https://github.com/MinhAn15/Agent-Orchestrator-driven/issues)
- **Feature requests** → [Start a discussion](https://github.com/MinhAn15/Agent-Orchestrator-driven/discussions)
- **Pull requests** → Follow the PR template in [`.github/`](./.github/)

---

## License

[Apache 2.0](./LICENSE) © 2026 MinhAn15
