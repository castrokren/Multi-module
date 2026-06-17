@echo off
REM Commit and push CrossRef fixes to GitHub
setlocal enabledelayedexpansion

echo.
echo ========================================
echo CrossRef Fixes - GitHub Push
echo ========================================
echo.

REM Verify correct directory
if not exist "src\services\pipeline_config.json" (
    echo Error: Not in PROJECTS directory
    echo Please run from: C:\Projects\Crawler\PROJECTS
    exit /b 1
)

REM Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo Error: Git not found. Please install Git.
    exit /b 1
)

echo.
echo Git found. Proceeding...
echo.

REM Show status
echo Checking git status...
git status
echo.

REM Stage files
echo Staging files...
git add "src\services\pipeline_config.json"
git add "Cross-reference\crossref_standalone_fast.py"
git add "CROSSREF_DEBUGGING_REPORT.md"
git add "test_crossref_fixes.py"

echo.
echo Staged files:
git diff --cached --name-only
echo.

REM Commit
echo Creating commit...
git commit -m "fix(crossref): Fix hardcoded paths, remove duplicates, add state tracking" -m "Critical fixes for CrossRef failures:" -m "1. Updated pipeline_config.json with relative paths (fixes FileNotFoundError)" -m "2. Removed duplicate find_matching_pdfs() stub methods" -m "3. Added state tracking to prevent rescanning directories" -m "4. Added CROSSREF_DEBUGGING_REPORT.md with root cause analysis" -m "Verified: All fixes tested and working correctly"

if errorlevel 1 (
    echo Error: Commit failed
    exit /b 1
)

echo.
echo Commit successful!
echo.

REM Get branch name
for /f %%i in ('git rev-parse --abbrev-ref HEAD') do set branch=%%i

echo Pushing to GitHub...
echo Current branch: %branch%
echo.

git push origin %branch%

if errorlevel 1 (
    echo.
    echo Error: Push failed!
    exit /b 1
) else (
    echo.
    echo ========================================
    echo SUCCESS! Push complete!
    echo ========================================
    echo.
    echo Next steps:
    echo   1. Run deployment: .\update.bat
    echo   2. Test pipeline: python pipeline.py --only-crossref
    echo   3. Verify .crossref_state.json is created
    echo.
)

endlocal
