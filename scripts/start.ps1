# Starts the DM Companion server. Phones on the same Wi-Fi join through the address it prints.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = "$root\server\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Not set up yet. Run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path "$root\web\dist\index.html")) {
    Push-Location "$root\web"
    try { npm run build; if ($LASTEXITCODE -ne 0) { throw "Building the web app failed." } } finally { Pop-Location }
}

Set-Location $root
& $python -m dm_companion
