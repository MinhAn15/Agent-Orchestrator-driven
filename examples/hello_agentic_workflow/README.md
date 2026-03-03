# Hello Agentic Workflow

A minimal end-to-end sample that calls the scaffold orchestrator CLI.

## Run

```bash
PYTHONPATH=src python -m antigravity_orchestrator.cli run-workflow hello-agent --payload '{"user":"world"}'
```

Expected output contains:
- `status: "completed"`
- `output.workflow: "hello-agent"`
- `output.inputs.user: "world"`
