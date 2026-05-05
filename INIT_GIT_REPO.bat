@echo off
REM Git Repository Initialization Script for Windows
REM This script sets up the git repository for the Crawler project
REM
REM INSTRUCTIONS:
REM 1. Make sure Git is installed (https://git-scm.com/download/win)
REM 2. Run this script from the project root directory
REM 3. Right-click and select "Run as administrator" if you encounter permission issues

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Git Repository Initialization
echo ========================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Backup existing git directory if it exists
if exist .git (
    echo [WARNING] Existing .git directory found. Backing up to .git.bak
    if exist .git.bak (
        rmdir /s /q .git.bak
    )
    move .git .git.bak
)

echo [1/4] Initializing Git repository...
git init --initial-branch=main
if errorlevel 1 (
    echo ERROR: Failed to initialize git
    pause
    exit /b 1
)

echo [2/4] Configuring user...
git config user.email "castrokren@gmail.com"
git config user.name "Kren Castro"

echo [3/4] Staging files...
git add .
if errorlevel 1 (
    echo ERROR: Failed to stage files
    pause
    exit /b 1
)

echo [4/4] Creating initial commit...
git commit -m "Initial commit: Multi-module PDF Crawler System

Project Overview:
This is a production-ready system for processing and managing PDF documents
with classification and cross-referencing capabilities.

Modules:
1. CLASSIFY: Document classification with self-learning
2. CROSS-REFERENCE: PDF linking and validation
3. SCRAPER_FULL: Web scraping and PDF downloading

Documentation:
- README.md: Quick start and project overview
- MODULE_OVERVIEW.md: Detailed module documentation
- CLASSIFY_ANALYSIS.md: In-depth classification analysis
- DEVELOPMENT_PLAN.md: Improvement roadmap"

if errorlevel 1 (
    echo ERROR: Failed to create commit
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Repository initialized
echo ========================================
echo.

git log --oneline
echo.
echo Repository Status:
git status
echo.

echo Next steps:
echo 1. Update config.ini with your specific paths
echo 2. Review README.md for usage instructions
echo 3. Create branches as needed (git checkout -b feature/your-feature)
echo 4. Make your first changes and commit (git add . && git commit -m "message")
echo 5. [Optional] Add remote (git remote add origin ^<url^>)
echo.

pause
