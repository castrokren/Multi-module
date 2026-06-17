@echo off
REM ============================================================================
REM Deploy to Remote Machine
REM ============================================================================
REM Purpose: Copy deployment system and pull latest code on remote machine
REM Author: Kren Castro
REM Usage: deploy_to_remote.bat [REMOTE_PATH]
REM
REM Example:
REM   deploy_to_remote.bat "C:\Users\castrk05_adm\Desktop\Multi-module"
REM ============================================================================

setlocal enabledelayedexpansion
set LOCAL_REPO=C:\Projects\Crawler
set REMOTE_REPO=%1

if "%REMOTE_REPO%"=="" (
    echo Usage: deploy_to_remote.bat "REMOTE_PATH"
    echo.
    echo Example:
    echo   deploy_to_remote.bat "C:\Users\castrk05_adm\Desktop\Multi-module"
    echo.
    exit /b 1
)

echo ============================================================================
echo Deploying to Remote Machine
echo ============================================================================
echo.
echo Local repo:  %LOCAL_REPO%
echo Remote repo: %REMOTE_REPO%
echo.

REM Verify remote path exists
if not exist "%REMOTE_REPO%" (
    echo ERROR: Remote path not found: %REMOTE_REPO%
    exit /b 1
)

REM Check if it's a git repo
if not exist "%REMOTE_REPO%\.git" (
    echo ERROR: Not a git repository: %REMOTE_REPO%
    exit /b 1
)

echo Step 1: Copy deployment scripts to remote...
copy "%LOCAL_REPO%\PROJECTS\update.bat" "%REMOTE_REPO%\PROJECTS\update.bat"
copy "%LOCAL_REPO%\PROJECTS\setup_deployment.ps1" "%REMOTE_REPO%\PROJECTS\setup_deployment.ps1"
copy "%LOCAL_REPO%\PROJECTS\DEPLOYMENT.md" "%REMOTE_REPO%\PROJECTS\DEPLOYMENT.md"
copy "%LOCAL_REPO%\PROJECTS\DEPLOYMENT_QUICK_START.txt" "%REMOTE_REPO%\PROJECTS\DEPLOYMENT_QUICK_START.txt"

echo Step 2: Pull latest code on remote machine...
cd /d "%REMOTE_REPO%"
git fetch origin main
git pull origin main

if errorlevel 1 (
    echo ERROR: Failed to pull on remote machine
    exit /b 1
)

echo.
echo ============================================================================
echo Deployment successful!
echo ============================================================================
echo.
echo Next steps on remote machine:
echo   1. Open PowerShell as Administrator
echo   2. Run: %REMOTE_REPO%\PROJECTS\setup_deployment.ps1
echo   3. This will set up Task Scheduler for automatic updates
echo.
