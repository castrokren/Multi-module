@echo off
REM ==============================================================================
REM Deploy Crawler Pipeline from GitHub
REM ==============================================================================
REM Copy this file to your Desktop, then double-click to deploy
REM ==============================================================================

setlocal enabledelayedexpansion
cd /d "%USERPROFILE%\Desktop"

cls
echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║         CRAWLER PIPELINE - GITHUB DEPLOYMENT                      ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.

REM Check if Git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not found in PATH
    echo.
    echo Please install Git from: https://git-scm.com/
    echo Remember to check "Add Git to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check if repo already exists
if exist Multi-module (
    echo [1/3] Repository exists, pulling latest changes...
    cd Multi-module
    git fetch origin
    git checkout claude/pedantic-hofstadter-313610
    git pull origin claude/pedantic-hofstadter-313610
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to pull latest code
        pause
        exit /b 1
    )
    echo [OK] Latest code pulled
) else (
    echo [1/3] Cloning repository from GitHub...
    git clone https://github.com/castrokren/Multi-module.git
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to clone repository
        pause
        exit /b 1
    )
    echo [OK] Repository cloned

    cd Multi-module

    echo [2/3] Checking out branch: claude/pedantic-hofstadter-313610...
    git checkout claude/pedantic-hofstadter-313610
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to checkout branch
        pause
        exit /b 1
    )
    echo [OK] Branch checked out
)

echo [3/3] Running pipeline setup...
cd PROJECTS
if not exist setup.bat (
    echo [ERROR] setup.bat not found in PROJECTS folder
    pause
    exit /b 1
)

call setup.bat
if %errorlevel% neq 0 (
    echo [ERROR] Pipeline setup failed
    pause
    exit /b 1
)

echo.
echo  ╔════════════════════════════════════════════════════════════════════╗
echo  ║                  DEPLOYMENT COMPLETE!                             ║
echo  ╚════════════════════════════════════════════════════════════════════╝
echo.
echo  Pipeline deployed to: %USERPROFILE%\Desktop\Multi-module
echo  Dashboard:           https://localhost
echo.
pause
