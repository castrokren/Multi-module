@echo off
REM Start Pipeline Services
cd /d "%~dp0"
call venv\Scripts\activate.bat
start "Pipeline Monitor" cmd /c "python ops/folder_monitor_service.py & pause"
timeout /t 1 /nobreak >nul
start "Pipeline Dashboard" cmd /c "python ops/dashboard.py & pause"
echo.
echo Pipeline services started
echo Dashboard: https://localhost
echo.
pause
