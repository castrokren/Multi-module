@echo off
REM Start Pipeline Services
cd /d "%~dp0"
call venv\Scripts\activate.bat
start /B "Pipeline Monitor" python ops/folder_monitor_service.py
timeout /t 1 /nobreak >nul
start /B "Pipeline Dashboard" python ops/dashboard.py
echo.
echo Pipeline services started
echo Dashboard: https://localhost
echo.
