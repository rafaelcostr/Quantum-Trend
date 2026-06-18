# Quantum-Trend — inicia API Python + UI React (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Quantum-Trend — iniciando API (porta 8000) e UI (porta 3000)..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'; python -m atlas.cli api"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'; npm.cmd run dev"

Write-Host "Dois terminais abertos. UI: http://localhost:3000" -ForegroundColor Green
