@echo off
REM ==============================================================================
REM Crawler Pipeline Monitor Launcher
REM ==============================================================================
REM Starts the folder monitor service and web dashboard
REM Usage: Double-click this file or run from command prompt
REM ==============================================================================

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Colors (if supported)
for /F %%A in ('copy /Z "%~f0" nul') do set "BS=%%A"

cls
echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║         CRAWLER PIPELINE MONITOR - Folder Watch Service           ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/
    echo Remember to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version

REM Check if venv exists
if not exist "%PROJECT_ROOT%\venv" (
    echo.
    echo [INFO] Virtual environment not found, creating one...
    cd /d "%PROJECT_ROOT%"
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo [INFO] Activating virtual environment...
call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Check required packages
echo.
echo [INFO] Checking required packages...
python -c "import watchdog, flask, flask_cors" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Installing required packages...
    pip install watchdog flask flask-cors python-dotenv -q
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install packages
        pause
        exit /b 1
    )
)
echo [OK] Required packages available

REM Check .env file
if not exist "%SCRIPT_DIR%.env" (
    echo.
    echo [WARN] Configuration file not found: %SCRIPT_DIR%.env
    echo [INFO] Creating template from example...
    (
        echo # Email Configuration
        echo SMTP_SERVER=smtp.office365.com
        echo SMTP_PORT=587
        echo SMTP_USERNAME=your-email@company.com
        echo SMTP_PASSWORD=your-app-password
        echo ALERT_RECIPIENTS=ops@company.com
        echo ALERT_SENDER=pipeline-alerts@company.com
        echo.
        echo # Server Configuration
        echo MONITOR_INTERVAL=10
        echo MAX_CONCURRENT_RUNS=1
        echo.
        echo # Dashboard Configuration
        echo DASHBOARD_PORT=5000
        echo DASHBOARD_HOST=0.0.0.0
    ) > "%SCRIPT_DIR%.env"
    echo [OK] Created template at: %SCRIPT_DIR%.env
    echo [WARN] Please edit .env with your email configuration before running
    pause
)

REM Create output directories
if not exist "%PROJECT_ROOT%\data\som-in" mkdir "%PROJECT_ROOT%\data\som-in"
if not exist "%PROJECT_ROOT%\src\services\cross-reference\results" mkdir "%PROJECT_ROOT%\src\services\cross-reference\results"

echo.
echo [INFO] Starting services...
echo.

REM Start folder monitor in a new window
start /B "Pipeline Monitor Service" ^
    python "%SCRIPT_DIR%folder_monitor_service.py"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start monitor service
    pause
    exit /b 1
)
echo [OK] Monitor service started (PID: !errorlevel!)

REM Start dashboard in a new window
timeout /t 2 /nobreak
start /B "Pipeline Monitor Dashboard" ^
    python "%SCRIPT_DIR%dashboard.py"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start dashboard
)
echo [OK] Dashboard started

echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║                      SERVICES STARTED                              ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.
echo  Folder Monitor:     Watching C:\Projects\Crawler\PROJECTS\data\som-in
echo  Dashboard:          http://localhost:5000
echo.
echo  Log Files:
echo  - Monitor:  %PROJECT_ROOT%\src\services\cross-reference\results\monitor_service.log
echo  - Pipeline: %PROJECT_ROOT%\src\services\cross-reference\results\pipeline_*.log
echo.
echo  Status:
echo  - Place new Excel files in: data/som-in
echo  - Monitor will detect them within 10 seconds
echo  - Pipeline will run automatically
echo  - Open dashboard to watch progress: http://localhost:5000
echo.
echo  To stop:
echo  - Close this window and run: stop_monitor.bat
echo  - Or press Ctrl+C (may not stop immediately)
echo.
echo  Notes:
echo  - Make sure email is configured in: ops\.env
echo  - Check dashboard for any errors
echo  - Review logs if pipeline doesn't start
echo.
pause
