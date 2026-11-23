
$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot

try {
    if (!(Test-Path "package.json")) {
        throw "package.json not found in the frontend directory."
    }

    if (!(Test-Path "node_modules")) {
        Write-Host "Installing frontend packages..." -ForegroundColor Cyan
        npm install

        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed."
        }
    }

    Write-Host "Starting DepGuard frontend..." -ForegroundColor Cyan
    npm run dev
}
finally {
    Pop-Location
}
