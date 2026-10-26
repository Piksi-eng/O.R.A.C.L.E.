# One-time setup on the DM's Windows PC: Python environment + built web app.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Checked([string]$what, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)." }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python not found. Install Python 3.11+ from python.org and tick 'Add python.exe to PATH'."
}
Invoke-Checked "Python 3.11+ check" { py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" }

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js not found. Install the LTS version from nodejs.org."
}

Push-Location "$root\server"
try {
    if (-not (Test-Path ".venv")) { Invoke-Checked "Creating the Python environment" { py -3 -m venv .venv } }
    Invoke-Checked "Installing Python packages" { .\.venv\Scripts\python.exe -m pip install --upgrade pip }
    Invoke-Checked "Installing Python packages" { .\.venv\Scripts\python.exe -m pip install -e ".[dev]" }
} finally { Pop-Location }

Push-Location "$root\web"
try {
    Invoke-Checked "npm install" { npm install --no-audit --no-fund }
    Invoke-Checked "Building the web app" { npm run build }
} finally { Pop-Location }

Write-Host ""
Write-Host "Setup done. Start the server with:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1" -ForegroundColor Green
