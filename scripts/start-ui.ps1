Set-Location $PSScriptRoot\..

Write-Host "Iniciando UI em http://localhost:5173 (ou 3000)" -ForegroundColor Cyan
npm.cmd run dev
