---
description: One-command project bootstrap — create venv, install deps, verify health
---
// turbo-all

## Steps

1. Create virtual environment if `.venv/` does not exist:

```bash
python -m venv .venv
```

1. Activate the virtual environment:

- **Windows**: `.\.venv\Scripts\Activate.ps1`
- **Linux/macOS**: `source .venv/bin/activate`

1. Upgrade pip:

```bash
pip install --upgrade pip
```

1. Install the package in editable mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

1. Copy `.env.example` to `.env` if `.env` does not exist:

```bash
cp .env.example .env
```

1. Verify installation by running the health check:

```bash
python -c "import antigravity; import antigravity_orchestrator; print('✅ All packages imported successfully')"
```

1. Run the quickstart demo to confirm everything works:

```bash
python examples/quickstart.py
```

## Success criteria

- `.venv/` directory exists
- `pip install -e ".[dev]"` completes without errors
- Health check imports succeed
- `quickstart.py` produces JSON output with `run_id` and `status`
