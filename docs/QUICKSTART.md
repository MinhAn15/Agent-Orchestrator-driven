# Quickstart Guide

Get from zero to running orchestrated agent workflows in under 5 minutes.

---

## Installation

```bash
git clone https://github.com/MinhAn15/Agent-Orchestrator-driven.git
cd Agent-Orchestrator-driven

# Option A: Quick install
pip install -e .

# Option B: Full dev environment (recommended)
bash setup.sh          # Linux/macOS
powershell setup.ps1   # Windows
```

---

## 3 Integration Paths

### Path 1: One-call Python API

The simplest way — use `FixedOrchestrator` to run a single policy-checked action:

```python
from antigravity_orchestrator.runtime import FixedOrchestrator

def send_alert(payload):
    return {"message": "Alert sent", "service": payload.get("service")}

orchestrator = FixedOrchestrator()
orchestrator.register_action("alert", send_alert)

result = orchestrator.run("incident-response", {
    "action_type": "alert",
    "severity": "high",
    "service": "billing-api",
    "environment": "production",
})
print(result)
# ExecutionResult(run_id='...', status='completed', output={...}, error=None)
```

### Path 2: CLI with Markdown Templates

Run pre-built workflow templates from the command line:

```bash
# List available templates
python -c "from templates.gallery import get_gallery; [print(t.name, '-', t.description) for t in get_gallery().list_all()]"

# Run incident-response template
antigravity run incident-response \
  --vars '{"team":"SRE","service":"payments-api","severity":"P1"}' \
  --context '{"environment":"production","data_classification":"confidential"}'
```

**Output:**

```json
{
  "summary": {
    "workflow_slug": "incident-response",
    "total_steps": 4,
    "allowed": 2,
    "denied": 1,
    "needs_approval": 1
  },
  "steps": [
    {"step_id": "01", "title": "...", "status": "executed", "effect": "allow"},
    {"step_id": "02", "title": "...", "status": "blocked", "effect": "deny"}
  ]
}
```

### Path 3: MCP Server for AI IDEs

Expose Antigravity as an MCP tool server for VS Code, Cursor, CLine, or any MCP-compatible IDE:

```bash
python -m antigravity.cli mcp --stdio
```

**Available tools:**

| Tool | Parameters | What It Does |
|---|---|---|
| `run_workflow` | `template`, `vars`, `context` | Execute a template with policy gating |
| `inspect_state` | `namespace`, `key` | Read workflow state from memory |
| `handoff` | `from_agent`, `to_agent`, `task_id`, `reason` | Transfer context between agents |

MCP configs are pre-configured for:

- **VS Code** → `.vscode/mcp.json`
- **Cursor** → `.cursor/mcp.json`
- **CLine** → `.cline/mcp_config.json`
- **Any client** → `mcp-config.json`

---

## Configuration Reference

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `stub` | LLM backend: `openai`, `ollama`, `stub` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name for the chosen provider |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `SLACK_WEBHOOK_URL` | — | For Slack connector alerts |
| `GITHUB_TOKEN` | — | For GitHub connector (issues, PRs) |
| `DATABASE_URL` | `sqlite:///data/local.db` | For SQL connector |
| `ANTIGRAVITY_LOG_LEVEL` | `INFO` | Logging verbosity |
| `ANTIGRAVITY_CHECKPOINT_DIR` | `.checkpoints` | Checkpoint storage path |

### Policy Rules

Rules are plain dicts. Built-in defaults:

| Rule | Condition | Effect |
|---|---|---|
| `block-delete-production` | `action_type=delete` + `environment=production` | **deny** |
| `require-approval-financial` | `domain=financial` | **require_approval** |
| `block-confidential-exfil` | `action_type=send_external` + `data_classification=confidential` | **deny** |

Add custom rules:

```python
from antigravity.policy import PolicyEngine, Rule, Effect

engine = PolicyEngine()
engine.add_rule(Rule(
    id="my-rule",
    condition={"action_type": "deploy", "environment": "production"},
    effect=Effect.REQUIRE_APPROVAL,
    priority=5,
    reason="Production deploys require approval"
))
```

### Memory Backends

| Backend | Config | Use Case |
|---|---|---|
| `InMemoryBackend()` | Default, no config | Dev and testing |
| `RedisBackend(url)` | `REDIS_URL` | Single-node production |
| `PostgresBackend(dsn)` | `DATABASE_URL` | Durable, queryable state |

---

## CLI Reference

```bash
# Run a workflow template
antigravity run <template-slug> [--vars JSON] [--context JSON] [--namespace NAME]

# Start MCP stdio server
antigravity mcp --stdio
```

---

## Available Templates

| Slug | Use Case |
|---|---|
| `incident-response` | Detect → diagnose → remediate → notify |
| `bug-triage` | Classify → assign → track |
| `customer-support` | Classify intent → retrieve docs → reply or escalate |
| `content-ops` | Research → draft → review → publish |
| `lead-enrichment` | Fetch data → score → sync to CRM |

---

## Available Connectors

| Connector | Class | Key Actions |
|---|---|---|
| Slack | `SlackConnector` | Send alerts with severity levels |
| SQL | `SQLConnector` | Query any database |
| HTTP | `HTTPConnector` | Call REST APIs |
| GitHub | `GitHubConnector` | Issues, comments, PRs |
| Filesystem | `FileSystemConnector` | Read/write local files |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: antigravity` | Package not installed | Run `pip install -e .` |
| `'antigravity' is not a package` | Python stdlib name collision | Set `PYTHONPATH=src` before running |
| Tests fail with coverage < 80% | Running subset of tests | Run full suite: `pytest` |
| CLI JSON parse error on Windows | PowerShell escaping | Use double quotes: `--vars "{\"key\":\"val\"}"` |
| MCP server not discovered | Config not in right path | Check IDE-specific config file exists |
| `ImportError: templates.gallery` | Running from wrong directory | Run from repo root |
