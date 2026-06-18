Set-Location $PSScriptRoot\..

$conn = netstat -ano | Select-String ":8000.*LISTENING"
if ($conn) {
    $pid = ($conn -split "\s+")[-1]
    Write-Host "Encerrando API antiga (PID $pid)..." -ForegroundColor Yellow
    taskkill /PID $pid /F | Out-Null
    Start-Sleep -Seconds 1
}

Write-Host "Iniciando API em http://127.0.0.1:8000" -ForegroundColor Cyan
python -m atlas.cli api
