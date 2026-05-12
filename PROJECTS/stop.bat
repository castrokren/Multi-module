@echo off
REM Stop Pipeline Services
taskkill /F /IM python.exe /T >nul 2>&1
echo Pipeline services stopped
pause
