@echo off
REM ==============================================================================
REM CRAWLER PIPELINE - ONE-CLICK SETUP
REM ==============================================================================
REM Single-file deployment for Windows Server
REM Just double-click and the pipeline is ready in 2 minutes
REM ==============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

cls
echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║         CRAWLER PIPELINE - AUTOMATED SETUP                        ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.

REM ==============================================================================
REM STEP 1: Check Python Installation
REM ==============================================================================

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python 3.8+ not found in PATH
    echo.
    echo Please install Python from: https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found

REM ==============================================================================
REM STEP 2: Create Virtual Environment
REM ==============================================================================

echo [2/6] Creating virtual environment...
if exist venv (
    echo [OK] Virtual environment already exists
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        echo Make sure you have write permissions in this directory
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM ==============================================================================
REM STEP 3: Activate Virtual Environment and Install Dependencies
REM ==============================================================================

echo [3/6] Installing dependencies...
call venv\Scripts\activate.bat
pip install -q watchdog flask flask-cors python-dotenv pyopenssl
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    echo Check your internet connection and try again
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM ==============================================================================
REM STEP 4: Create Required Directories
REM ==============================================================================

echo [4/6] Creating directories...
if not exist ops mkdir ops
if not exist data mkdir data
if not exist data\som-in mkdir data\som-in
if not exist src mkdir src
if not exist src\services mkdir src\services
if not exist src\services\cross-reference mkdir src\services\cross-reference
if not exist src\services\cross-reference\results mkdir src\services\cross-reference\results
echo [OK] Directories ready

REM ==============================================================================
REM STEP 5: Generate HTTPS Certificate
REM ==============================================================================

echo [5/6] Generating HTTPS certificate...
if exist ops\cert.pem (
    echo [OK] Certificate already exists
    goto step5_done
)

python ops\generate_cert.py
if %errorlevel% equ 0 (
    echo [OK] HTTPS certificate generated
    goto step5_done
)

echo [WARN] Could not generate HTTPS certificate
echo Dashboard will run without HTTPS

:step5_done

REM ==============================================================================
REM STEP 6: Start Services
REM ==============================================================================

echo [6/6] Starting services...

REM Start folder monitor
start "Pipeline Monitor" cmd /c "call venv\Scripts\activate.bat && python ops/folder_monitor_service.py & pause"
timeout /t 2 /nobreak >nul

REM Start dashboard
start "Pipeline Dashboard" cmd /c "call venv\Scripts\activate.bat && python ops/dashboard.py & pause"
timeout /t 2 /nobreak >nul

echo [OK] Services started

echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║                    SETUP COMPLETE!                                ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.
echo  Pipeline is now running and ready for input files.
echo.
echo  NEXT STEPS:
echo  1. Open dashboard in browser: https://localhost
echo  2. Accept the security warning (self-signed certificate is normal)
echo  3. You should see "Idle - Waiting for input file..."
echo  4. Place Excel files in: data\som-in\
echo  5. Monitor will detect them within 10 seconds
echo  6. Pipeline runs automatically
echo.
echo  MANUAL CONTROLS:
echo  - Start services: start.bat
echo  - Stop services:  stop.bat
echo  - View status:    https://localhost
echo.
echo  LOGS:
echo  - Monitor: src\services\cross-reference\results\monitor_service.log
echo  - Pipeline: src\services\cross-reference\results\pipeline_*.log
echo.
timeout /t 5 /nobreak
start https://localhost
pause
