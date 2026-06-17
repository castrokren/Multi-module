@echo off
REM ==============================================================================
REM Stop Pipeline Monitor Services
REM ==============================================================================
REM Stops the folder monitor and dashboard services
REM ==============================================================================

echo.
echo Stopping Pipeline Monitor Services...
echo.

REM Kill all Python processes running our services
tasklist | findstr /I python >nul
if %errorlevel% equ 0 (
    taskkill /F /IM python.exe /T >nul 2>&1
    echo [OK] Python processes terminated
) else (
    echo [INFO] No Python processes found
)

echo.
echo Pipeline Monitor stopped.
echo.
pause
