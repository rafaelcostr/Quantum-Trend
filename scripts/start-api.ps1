Set-Location $PSScriptRoot\..

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

Write-Host "Iniciando API Quantum-Trend em http://127.0.0.1:8000" -ForegroundColor Cyan
python -m atlas.cli api
