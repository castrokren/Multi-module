@echo off
REM ============================================================================
REM Crawler Pipeline Auto-Updater
REM ============================================================================
REM Purpose: Check GitHub for new commits and automatically deploy updates
REM Author: Kren Castro
REM Usage: Scheduled via Windows Task Scheduler
REM
REM Features:
REM   - Checks for new commits on origin/main
REM   - Creates timestamped backup of current code
REM   - Downloads latest code from GitHub
REM   - Validates deployment
REM   - Logs all operations to file
REM ============================================================================

setlocal enabledelayedexpansion
set REPO_DIR=C:\Users\castrk05_adm\Desktop\Multi-module
set BACKUP_DIR=C:\Users\castrk05_adm\Desktop\Multi-module\backups
set LOG_DIR=C:\Users\castrk05_adm\Desktop\Multi-module\logs
set DEPLOYMENT_LOG=%LOG_DIR%\deployment.log
set STATE_FILE=%LOG_DIR%\.last_deployed_hash
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Create required directories
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM ============================================================================
REM PHASE 1: Initialize Logging
REM ============================================================================
echo. >> "%DEPLOYMENT_LOG%"
echo ============================================================================ >> "%DEPLOYMENT_LOG%"
echo [%TIMESTAMP%] Pipeline Update Check >> "%DEPLOYMENT_LOG%"
echo ============================================================================ >> "%DEPLOYMENT_LOG%"

echo [%TIMESTAMP%] Starting update check...
echo [%TIMESTAMP%] Repository: %REPO_DIR% >> "%DEPLOYMENT_LOG%"

REM ============================================================================
REM PHASE 2: Check for Updates
REM ============================================================================
pushd "%REPO_DIR%"

REM Fetch latest from origin without changing working directory
echo [%TIMESTAMP%] Fetching latest from origin/main... >> "%DEPLOYMENT_LOG%"
git fetch origin main >> "%DEPLOYMENT_LOG%" 2>&1
if errorlevel 1 (
    echo [%TIMESTAMP%] ERROR: Failed to fetch from origin >> "%DEPLOYMENT_LOG%"
    popd
    goto :ERROR_EXIT
)

REM Get current commit hash
for /f %%i in ('git rev-parse HEAD') do set CURRENT_HASH=%%i
REM Get remote commit hash
for /f %%i in ('git rev-parse origin/main') do set REMOTE_HASH=%%i

echo [%TIMESTAMP%] Current hash:  %CURRENT_HASH% >> "%DEPLOYMENT_LOG%"
echo [%TIMESTAMP%] Remote hash:   %REMOTE_HASH% >> "%DEPLOYMENT_LOG%"

REM Check if last deployed hash file exists
if not exist "%STATE_FILE%" (
    echo %CURRENT_HASH% > "%STATE_FILE%"
    echo [%TIMESTAMP%] First run - storing baseline hash >> "%DEPLOYMENT_LOG%"
)

REM Read last deployed hash
set /p LAST_DEPLOYED=< "%STATE_FILE%"

REM If we're already on the latest, exit
if "%CURRENT_HASH%"=="%REMOTE_HASH%" (
    echo [%TIMESTAMP%] Already on latest commit - no update needed >> "%DEPLOYMENT_LOG%"
    popd
    goto :SUCCESS_EXIT
)

echo [%TIMESTAMP%] New commits available - deploying update >> "%DEPLOYMENT_LOG%"

REM ============================================================================
REM PHASE 3: Backup Current Code
REM ============================================================================
echo [%TIMESTAMP%] Creating backup of current code...
set BACKUP_ARCHIVE=%BACKUP_DIR%\backup_%TIMESTAMP%.zip

REM Backup PROJECTS directory
powershell -Command "Compress-Archive -Path '%REPO_DIR%\PROJECTS' -DestinationPath '%BACKUP_ARCHIVE%' -Force" >> "%DEPLOYMENT_LOG%" 2>&1
if errorlevel 1 (
    echo [%TIMESTAMP%] WARNING: Failed to create backup >> "%DEPLOYMENT_LOG%"
) else (
    echo [%TIMESTAMP%] Backup created: %BACKUP_ARCHIVE% >> "%DEPLOYMENT_LOG%"
)

REM Keep only last 5 backups
echo [%TIMESTAMP%] Cleaning old backups (keeping last 5)... >> "%DEPLOYMENT_LOG%"
cd /d "%BACKUP_DIR%"
for /f "skip=5 delims=" %%i in ('dir /b /o-d backup_*.zip') do (
    del "%%i" >> "%DEPLOYMENT_LOG%" 2>&1
    echo [%TIMESTAMP%] Deleted old backup: %%i >> "%DEPLOYMENT_LOG%"
)

REM ============================================================================
REM PHASE 4: Pull Latest Code
REM ============================================================================
pushd "%REPO_DIR%"
echo [%TIMESTAMP%] Pulling latest from origin/main... >> "%DEPLOYMENT_LOG%"
git pull origin main >> "%DEPLOYMENT_LOG%" 2>&1
if errorlevel 1 (
    echo [%TIMESTAMP%] ERROR: Failed to pull from origin >> "%DEPLOYMENT_LOG%"
    echo [%TIMESTAMP%] ROLLBACK: Your code is still at previous version >> "%DEPLOYMENT_LOG%"
    popd
    goto :ERROR_EXIT
)

REM Get new commit hash
for /f %%i in ('git rev-parse HEAD') do set NEW_HASH=%%i
echo [%TIMESTAMP%] New commit hash: %NEW_HASH% >> "%DEPLOYMENT_LOG%"

REM ============================================================================
REM PHASE 5: Validate Deployment
REM ============================================================================
echo [%TIMESTAMP%] Validating critical files exist...

set FILES_OK=1
for %%F in (
    "PROJECTS\src\services\scraper-full\scraper_engine.py"
    "PROJECTS\src\services\pipeline.py"
    "PROJECTS\src\services\pipeline_config.json"
) do (
    if not exist "%REPO_DIR%\%%F" (
        echo [%TIMESTAMP%] ERROR: Missing file: %%F >> "%DEPLOYMENT_LOG%"
        set FILES_OK=0
    )
)

if "%FILES_OK%"=="0" (
    echo [%TIMESTAMP%] ERROR: Validation failed - critical files missing >> "%DEPLOYMENT_LOG%"
    popd
    goto :ERROR_EXIT
)

echo [%TIMESTAMP%] Validation passed - all critical files present >> "%DEPLOYMENT_LOG%"

REM ============================================================================
REM PHASE 6: Update State and Notify
REM ============================================================================
echo %NEW_HASH% > "%STATE_FILE%"
echo [%TIMESTAMP%] Update completed successfully >> "%DEPLOYMENT_LOG%"
echo [%TIMESTAMP%] Code is ready - pipeline will use new version on next run >> "%DEPLOYMENT_LOG%"

popd
goto :SUCCESS_EXIT

REM ============================================================================
REM Exit Points
REM ============================================================================
:SUCCESS_EXIT
echo [%TIMESTAMP%] ===== UPDATE SUCCESSFUL ===== >> "%DEPLOYMENT_LOG%"
echo.
echo Logfile: %DEPLOYMENT_LOG%
echo.
pause
endlocal
exit /b 0

:ERROR_EXIT
echo [%TIMESTAMP%] ===== UPDATE FAILED ===== >> "%DEPLOYMENT_LOG%"
echo.
echo Check log: %DEPLOYMENT_LOG%
echo.
pause
endlocal
exit /b 1
