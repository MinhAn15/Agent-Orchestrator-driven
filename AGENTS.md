# AGENTS.md — AI Coding Assistant Guide

> This file helps AI coding assistants (Antigravity, Codex, Copilot, CLine, Kilo, Windsurf)
> understand and work with this codebase effectively.

## Project Purpose

**Antigravity** is a production-ready agent orchestration framework. It provides:

- **Policy engine** — rule-based gating for every agent action
- **Connectors** — pluggable skills (Slack, SQL, HTTP, GitHub, filesystem)
- **Templates** — markdown workflow definitions with variable substitution
- **Runtime** — deterministic execution with checkpoint, handoff, retry, and audit

## Architecture

```
Your Agent → Planner → Policy Check → Execute Skill → Connector/Tool → Memory → loop
```

## Directory Map

| Path | Purpose |
|---|---|
| `src/antigravity/` | Core engine: policy, memory, CLI, DAG engine, MCP stdio, ad-hoc orchestrator |
| `src/antigravity_orchestrator/` | Runtime: FixedOrchestrator, models, core workflow, observability |
| `src/llm_policy.py` | LLM provider abstraction (OpenAI, Ollama, stub) |
| `connectors/` | Pluggable skills: Slack, SQL, HTTP, GitHub, filesystem. All extend `BaseConnector` |
| `templates/` | Markdown workflow templates + `gallery.py` registry |
| `runtime/` | Agent registry, checkpoint, handoff, policy, retry |
| `tests/` | pytest test suite (80%+ coverage target) |
| `examples/` | Runnable demos (`quickstart.py`, incident_triage, hello_agentic_workflow) |
| `benchmarks/` | Performance baselines |
| `docs/` | Architecture, getting-started, MCP integration, connector SDK |
| `.agents/workflows/` | AI-assistant discoverable workflow instructions |

## Key Commands

```bash
# Bootstrap
bash setup.sh          # Linux/macOS
powershell setup.ps1   # Windows

# Quality
make test              # or: pytest
make lint              # or: ruff check .
make typecheck         # or: mypy

# Demo
python examples/quickstart.py
python -m antigravity.cli run incident-response --vars '{"team":"SRE"}'

# MCP server
python -m antigravity.cli mcp --stdio
```

## Coding Conventions

- **Python 3.11+**, strict mypy, ruff linter
- **Naming**: `snake_case` for files / functions, `PascalCase` for classes
- **Connectors**: extend `connectors.base.BaseConnector`, implement `execute(action, params)`
- **Templates**: markdown with `## Workflow` section containing checklist items (`- [ ]`)
- **Policy rules**: plain dicts with `id`, `condition`, `effect`, `priority`, `reason`
- **Tests**: mirror source structure in `tests/`, prefix with `test_`
- **No runtime dependencies** — core package has zero pip dependencies

## MCP Tools Available

| Tool | Description |
|---|---|
| `run_workflow` | Execute a template with variables and policy context |
| `inspect_state` | Read memory state by namespace + key |
| `handoff` | Transfer context between agents with audit trail |

## When Adding Features

1. **New connector** → follow `.agents/workflows/add-connector.md`
2. **New template** → follow `.agents/workflows/add-template.md`
3. **New policy rule** → add dict to `src/antigravity/policy.py` `create_default_engine()`
4. **New runtime capability** → add to `runtime/` or `src/antigravity_orchestrator/`

## Environment Variables

See `.env.example` for all configurable settings. Key ones:

- `LLM_PROVIDER` — `openai` | `ollama` | `stub`
- `OPENAI_API_KEY` — required for OpenAI provider
- `SLACK_WEBHOOK_URL` — for Slack connector
- `DATABASE_URL` — for SQL connector
