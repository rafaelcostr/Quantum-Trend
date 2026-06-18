@echo off
cd /d "%~dp0.."
echo Encerrando API na porta 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo Iniciando API em http://127.0.0.1:8000
python -m atlas.cli api
