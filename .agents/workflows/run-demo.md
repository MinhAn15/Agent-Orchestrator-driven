---
description: Run the quickstart demo and ad-hoc CLI to verify orchestration works
---
// turbo-all

## Steps

1. Run the Python quickstart demo:

```bash
python examples/quickstart.py
```

Expected: JSON output with `run_id` and `status: completed`.

1. Run the CLI with the incident-response template:

```bash
python -m antigravity.cli run incident-response --vars '{"team":"SRE","service":"payments-api","severity":"P1"}' --context '{"environment":"production","data_classification":"confidential"}'
```

Expected: JSON output showing steps with policy decisions (some allowed, some blocked/needs_approval).

1. (Optional) Test MCP stdio server:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m antigravity.cli mcp --stdio
```

Expected: JSON response listing available tools (`run_workflow`, `inspect_state`, `handoff`).

## Success criteria

- `quickstart.py` exits successfully with JSON output
- CLI produces valid JSON with `summary` and `steps` arrays
- At least one step is `"blocked"` (delete in production) demonstrating the policy engine
