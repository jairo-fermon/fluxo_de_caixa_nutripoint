@echo off
setlocal

cd /d "%~dp0"

start "" cmd /k "cd /d %~dp0 && python run.py"

timeout /t 2 /nobreak >nul

start "" http://127.0.0.1:8000

endlocal
