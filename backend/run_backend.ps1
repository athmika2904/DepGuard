
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"

if (!(Test-Path $ActivateScript)) {
    Write-Host "Virtual environment not found." -ForegroundColor Red
    Write-Host "From the project root, run:"
    Write-Host "python -m venv .venv"
    Write-Host ".\.venv\Scripts\Activate.ps1"
    Write-Host "pip install -r requirements.txt"
    exit 1
}

Push-Location $ProjectRoot

try {
    . $ActivateScript

    Write-Host "Starting DepGuard backend..." -ForegroundColor Cyan

    python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
}
finally {
    Pop-Location
}
