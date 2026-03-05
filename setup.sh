#!/usr/bin/env bash
# ============================================================================
# Antigravity — One-command bootstrap
# Usage: bash setup.sh
# ============================================================================
set -euo pipefail

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

echo "══════════════════════════════════════════════════════════════"
echo "  🚀  Antigravity — Bootstrap"
echo "══════════════════════════════════════════════════════════════"

# ── 1. Check Python version ─────────────────────────────────────
PYVER=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
PYMAJOR=$(echo "$PYVER" | cut -d. -f1)
PYMINOR=$(echo "$PYVER" | cut -d. -f2)

if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; }; then
  echo "❌  Python 3.11+ required (found $PYVER)"
  exit 1
fi
echo "✅  Python $PYVER detected"

# ── 2. Create virtual environment ───────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "📦  Creating virtual environment..."
  $PYTHON -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "✅  Virtual environment activated"

# ── 3. Upgrade pip & install ────────────────────────────────────
echo "📦  Installing dependencies..."
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
echo "✅  Dependencies installed"

# ── 4. Copy .env if missing ─────────────────────────────────────
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "✅  .env created from .env.example (edit with your keys)"
fi

# ── 5. Health check ─────────────────────────────────────────────
echo ""
echo "── Health Check ──────────────────────────────────────────────"

if python -c "import antigravity; print('  ✅ antigravity package OK')" 2>/dev/null; then
  :
else
  echo "  ⚠️  antigravity import failed — check installation"
fi

if python -c "import antigravity_orchestrator; print('  ✅ antigravity_orchestrator package OK')" 2>/dev/null; then
  :
else
  echo "  ⚠️  antigravity_orchestrator import failed"
fi

if python -c "from connectors.registry import ConnectorRegistry; print('  ✅ connectors package OK')" 2>/dev/null; then
  :
else
  echo "  ⚠️  connectors import failed"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅  Setup complete!"
echo ""
echo "  Quick start:"
echo "    source $VENV_DIR/bin/activate"
echo "    python examples/quickstart.py"
echo "    antigravity run incident-response --vars '{\"team\":\"SRE\"}'"
echo "══════════════════════════════════════════════════════════════"
