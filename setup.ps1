# ============================================================================
# Antigravity — One-command bootstrap (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File setup.ps1
# ============================================================================
$ErrorActionPreference = "Stop"

$VenvDir = ".venv"
$Python  = if ($env:PYTHON) { $env:PYTHON } else { "python" }

Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🚀  Antigravity — Bootstrap" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

# ── 1. Check Python version ─────────────────────────────────────
$PyVer = & $Python --version 2>&1
if ($PyVer -match "(\d+)\.(\d+)") {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "❌  Python 3.11+ required (found $major.$minor)" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅  Python $major.$minor detected" -ForegroundColor Green
} else {
    Write-Host "❌  Cannot determine Python version" -ForegroundColor Red
    exit 1
}

# ── 2. Create virtual environment ───────────────────────────────
if (-not (Test-Path $VenvDir)) {
    Write-Host "📦  Creating virtual environment..." -ForegroundColor Yellow
    & $Python -m venv $VenvDir
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    Write-Host "⚠️  Could not find activation script at $ActivateScript" -ForegroundColor Yellow
}
Write-Host "✅  Virtual environment activated" -ForegroundColor Green

# ── 3. Upgrade pip & install ────────────────────────────────────
Write-Host "📦  Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
Write-Host "✅  Dependencies installed" -ForegroundColor Green

# ── 4. Copy .env if missing ─────────────────────────────────────
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅  .env created from .env.example (edit with your keys)" -ForegroundColor Green
}

# ── 5. Health check ─────────────────────────────────────────────
Write-Host ""
Write-Host "── Health Check ──────────────────────────────────────────────" -ForegroundColor Cyan

try {
    python -c "import antigravity; print('  ✅ antigravity package OK')"
} catch {
    Write-Host "  ⚠️  antigravity import failed — check installation" -ForegroundColor Yellow
}

try {
    python -c "import antigravity_orchestrator; print('  ✅ antigravity_orchestrator package OK')"
} catch {
    Write-Host "  ⚠️  antigravity_orchestrator import failed" -ForegroundColor Yellow
}

try {
    python -c "from connectors.registry import ConnectorRegistry; print('  ✅ connectors package OK')"
} catch {
    Write-Host "  ⚠️  connectors import failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick start:" -ForegroundColor White
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    python examples\quickstart.py" -ForegroundColor White
Write-Host "    antigravity run incident-response --vars '{`"team`":`"SRE`"}'" -ForegroundColor White
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
