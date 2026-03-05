---
description: Run the full quality pipeline — tests, lint, typecheck
---
// turbo-all

## Steps

1. Ensure dev dependencies are installed:

```bash
pip install -e ".[dev]"
```

1. Run linter (ruff):

```bash
ruff check .
```

1. Run type checker (mypy):

```bash
mypy
```

1. Run tests with coverage:

```bash
pytest -q --cov=src/antigravity --cov=src/antigravity_orchestrator --cov-report=term-missing
```

## Success criteria

- `ruff check .` exits with code 0 (no lint errors)
- `mypy` exits with code 0 (no type errors)
- `pytest` passes all tests with ≥80% coverage
