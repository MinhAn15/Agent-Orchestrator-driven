#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH="$(cd "$(dirname "$0")/../.." && pwd)/src" \
python -m antigravity_orchestrator.cli run-workflow hello-agent --payload '{"user":"world"}'
