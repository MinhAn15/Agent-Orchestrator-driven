# GitHub Actions automation

This repository includes two built-in automation workflows:

- `.github/workflows/auto-triage.yml` for issue and pull request triage.
- `.github/workflows/incident-response.yml` for scheduled/manual incident processing.

## Prerequisites

1. Ensure your repository has Actions enabled.
2. Ensure the runner can execute `antigravity` (install dependencies in your workflow if your project does not bundle it in the base image).
3. Configure credentials used by workflows and connectors.

## Secrets and environment variables

Set the following repository or organization secret:

- `GITHUB_TOKEN`: token with the minimum required repo scopes for issue/PR write operations.

The GitHub connector now loads `GITHUB_TOKEN` automatically if no explicit token is passed to `GitHubConnector(...)`.

## Workflow details

### Auto triage (`auto-triage.yml`)

Triggers:

- `issues` events: `opened`, `edited`, `reopened`
- `pull_request` events: `opened`, `edited`, `reopened`, `synchronize`

Execution:

- Runs `antigravity run bug-triage` on `ubuntu-latest`.

### Incident response (`incident-response.yml`)

Triggers:

- Manual run via `workflow_dispatch`
- Scheduled run every 15 minutes (`*/15 * * * *`)

Execution:

- Runs `antigravity run incident-response` on `ubuntu-latest`.

## Trigger customization

You can tailor each workflow trigger directly in the YAML:

- Restrict by branch using `branches` / `branches-ignore`.
- Narrow event activity types.
- Adjust incident polling cadence by changing the cron expression.

Example schedule change:

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"
```

## Security guidance

- Prefer GitHub Actions OIDC and short-lived tokens where possible.
- Keep tokens scoped to least privilege.
- For read-only behavior, initialize `GitHubConnector(read_only=True)` (default).
- Enable write behavior only where required via `GitHubConnector(read_only=False)`.
