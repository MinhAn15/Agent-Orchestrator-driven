# MCP stdio integration

Antigravity includes a stdio JSON-RPC 2.0 endpoint that exposes three tools:

- `run_workflow(template, vars, context)`
- `inspect_state(namespace, key)`
- `handoff(from_agent, to_agent, task_id, reason)`

## Enable in VSCode

1. Ensure your environment can run `python -m antigravity.cli`.
2. Copy `.vscode/mcp.json` into your workspace (already included in this repo).
3. Start or reload your MCP-enabled extension.
4. Confirm the `antigravity` server appears and `tools/list` returns tools.

## Enable in Antigravity IDE

1. Configure an MCP server with stdio transport.
2. Use command: `python -m antigravity.cli mcp --stdio`
3. Restart the IDE MCP runtime.
4. Verify tool discovery and invoke one sample call.

## JSON-RPC examples

### 1) Run workflow

```json
{"jsonrpc":"2.0","id":1,"method":"run_workflow","params":{"template":"incident-response","vars":{"team":"SRE","service":"billing"},"context":{"environment":"production","namespace":"demo-incident"}}}
```

### 2) Inspect state

```json
{"jsonrpc":"2.0","id":2,"method":"inspect_state","params":{"namespace":"demo-incident","key":"summary"}}
```

### 3) Handoff

```json
{"jsonrpc":"2.0","id":3,"method":"handoff","params":{"from_agent":"triage","to_agent":"incident-commander","task_id":"INC-42","reason":"Escalate due to customer impact"}}
```

### MCP list/call form

List tools:

```json
{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}
```

Call tool:

```json
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"inspect_state","arguments":{"namespace":"demo-incident","key":"summary"}}}
```
