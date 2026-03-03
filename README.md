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
| Agents take dangerous actions with no checks | **Policy engine** — approve, deny, or escalate any action before it runs |
| Conversations reset on every request | **Stateful memory** — InMemory, Redis, or Postgres, swappable at runtime |
| No idea why an agent failed or how much it cost | **Unified observability** — latency, token cost, and quality in one trace |
| Hard-coded integrations to Slack, DBs, GitHub | **Connector SDK** — plug-and-play adapters, add your own in < 50 lines |
| Starting from scratch for every new workflow | **Template gallery** — 5 battle-tested workflow templates, load & render in 2 lines |
| LLM vendor lock-in | **Provider abstraction** — swap OpenAI → Ollama → any DBAPI2 with one line |

**Antigravity is the backbone, not the brain — it makes your agents safe, observable, and composable without getting in the way.**

---

## Architecture

```mermaid
flowchart LR
    A(["Client / API Gateway"]) --> B(["Planner"])
    B --> C{"Policy Engine"}
    C -->|"approved"| D(["Executor"])
    C -->|"rejected"| E(["Audit Log"])
    D --> F(["Tool / Connector Layer"])
    F --> G[("Memory & State Store")]
    D --> H(["Observability\nlatency · cost · quality"])
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

Or copy only the modules you need directly into your project:

```bash
# Minimal: just the LLM policy engine
cp Agent-Orchestrator-driven/src/llm_policy.py your_project/

# Connectors only
cp -r Agent-Orchestrator-driven/connectors/ your_project/connectors/
```

### Step 2 — Add a Policy Gate to your existing agent

Before Antigravity, your agent probably looks like this:

```python
# your_project/agent.py  (before)
def run_action(action: str, payload: dict):
    # No checks — dangerous in production
    return execute(action, payload)
```

After adding Antigravity's policy engine:

```python
# your_project/agent.py  (after)
from antigravity.policy import PolicyEngine, Rule, Action

policy = PolicyEngine(rules=[
    Rule(pattern="delete_*",  action=Action.ESCALATE),  # flag destructive ops
    Rule(pattern="send_email", action=Action.ALLOW,
         condition=lambda ctx: ctx.get("user_verified")),
    Rule(pattern="*",          action=Action.ALLOW),     # default allow
])

def run_action(action: str, payload: dict, context: dict = {}):
    decision = policy.evaluate(action, context)
    if not decision.is_allowed:
        raise PermissionError(f"Action '{action}' blocked: {decision.reason}")
    return execute(action, payload)
```

### Step 3 — Swap in Stateful Memory

Replace your in-process dict cache with a persistent backend in one line:

```python
from antigravity.memory import create_memory_backend

# Development: in-process dict
memory = create_memory_backend("memory")

# Staging/Production: Redis (requires redis-py)
memory = create_memory_backend("redis", url="redis://localhost:6379/0")

# Anywhere your agents store/retrieve state:
memory.set("session:user_42", {"history": [...], "preferences": {...}})
state = memory.get("session:user_42")
```

### Step 4 — Use the LLM Policy Engine

Replace raw OpenAI calls with a provider-agnostic engine:

```python
from src.llm_policy import create_engine

# Works with OpenAI
engine = create_engine("openai", model="gpt-4o-mini")

# Or local Ollama — zero code change
engine = create_engine("ollama", model="llama3")

# Or the offline stub for unit tests
engine = create_engine("stub")

# Same interface regardless of provider
result = engine.decide(
    task="Classify this support ticket and suggest next action.",
    context="You are a support triage agent for a SaaS product."
)
print(result.content)   # → "Priority: HIGH. Suggested action: escalate to Tier 2."
print(result.usage)     # → {"prompt_tokens": 42, "completion_tokens": 18, ...}
```

### Step 5 — Connect to your tools via Connectors

```python
from connectors.slack_connector import SlackConnector
from connectors.sql_connector import SQLConnector

# Post a message to Slack
slack = SlackConnector(webhook_url="https://hooks.slack.com/services/...")
slack.send_alert("[P1] Database CPU > 90% — triggering incident response")

# Query your database
with SQLConnector("postgresql://user:pass@host/db") as db:
    incidents = db.query(
        "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC",
        ("open",)
    )
```

### Step 6 — Load a workflow template

Use a pre-built workflow template instead of designing from scratch:

```python
from templates.gallery import TemplateGallery

gallery = TemplateGallery.load()   # auto-discovers all .md templates

# List what's available
for t in gallery.list_all():
    print(f"{t.name:25s}  {t.description}")
# Incident Response          End-to-end agent workflow for triaging production incidents.
# Bug Triage                 Automated bug classification and routing to the responsible team.
# ...

# Load and render a template with your variables
template = gallery.get("incident-response")
workflow = template.render({
    "team": "Platform Engineering",
    "severity": "P1",
    "service": "payments-api",
})
print(workflow)  # → fully rendered incident-response runbook
```

### Minimal end-to-end example

Put it all together in ~30 lines:

```python
# examples/quickstart_integration.py
from antigravity.policy import PolicyEngine, Rule, Action
from antigravity.memory import create_memory_backend
from src.llm_policy import create_engine
from connectors.slack_connector import SlackConnector

# 1. Set up components
policy  = PolicyEngine(rules=[Rule(pattern="*", action=Action.ALLOW)])
memory  = create_memory_backend("memory")
llm     = create_engine("stub")           # swap to "openai" in prod
slack   = SlackConnector(webhook_url="...")  # optional

def handle_user_request(user_id: str, request: str) -> str:
    # 2. Policy check
    decision = policy.evaluate("llm_call", {"user_id": user_id})
    if not decision.is_allowed:
        return "Request not permitted."

    # 3. Load conversation history
    history = memory.get(f"history:{user_id}") or []

    # 4. Call LLM
    result = llm.decide(task=request)

    # 5. Persist state
    history.append({"role": "assistant", "content": result.content})
    memory.set(f"history:{user_id}", history)

    # 6. Alert if needed
    if "escalate" in result.content.lower():
        slack.send_alert(f"Escalation triggered for user {user_id}")

    return result.content

if __name__ == "__main__":
    print(handle_user_request("user_42", "My payment is stuck — help!"))
```

---

## Use Cases

> **Note:** The figures below are illustrative targets based on internal prototypes, not externally validated benchmarks. Reproducible benchmarks are in progress — see [`benchmarks/`](./benchmarks/).

### 1. Support Automation
Automatically triage, route, and resolve repetitive tickets with policy checks and escalation logic.
- Target: reduce first-response time and ticket deflection rate
- Example: [`examples/support_automation/`](./examples/)

### 2. Growth Operations
Coordinate campaign planning, copy generation, QA, and launch workflows across agents.
- Target: faster experiment velocity, reduced manual ops overhead
- Example: [`examples/growth_ops/`](./examples/)

### 3. Incident Response
Detect anomalies, fan out diagnostics, and propose remediation runbooks automatically.
- Target: lower Mean Time to Acknowledge (MTTA) and Mean Time to Resolve (MTTR)
- Example: [`examples/incident_response/`](./examples/)

---

## Quickstart (fresh project)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose v2
- An LLM API key (OpenAI, Anthropic, or compatible)

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/MinhAn15/Agent-Orchestrator-driven.git
cd Agent-Orchestrator-driven
```

**2. Configure environment**
```bash
cp .env.example .env
# Edit .env: set LLM_API_KEY and any connector credentials
```

**3. Start the orchestrator**
```bash
docker compose up -d
# Alternative: make dev
```

**4. Trigger a demo workflow**
```bash
curl -X POST http://localhost:8080/workflows/demo/run \
  -H "Content-Type: application/json" \
  -d '{"input": "run support automation sample"}'
```

**5. View dashboard & traces**
Open [http://localhost:3000](http://localhost:3000) to see the workflow execution graph, latency metrics, and policy audit trail.

---

## Project Structure

```
.
├── src/              # Core orchestration engine (planner, executor, policy, LLM)
├── runtime/          # Agentic runtime modules and semantics
├── connectors/       # Connector SDK + integrations (HTTP, GitHub, Slack, SQL, FS)
├── benchmarks/       # Reproducible benchmark suite
├── examples/         # End-to-end workflow examples
├── templates/        # Reusable workflow templates gallery
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
