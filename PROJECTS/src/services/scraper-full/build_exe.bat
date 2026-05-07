@echo off
echo ========================================
echo PDF Crawler GUI - Build Script
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing required packages...
pip install pyinstaller
pip install -r requirements.txt

echo Installing Playwright browsers...
python -m playwright install chromium

echo.
echo Building executable with PyInstaller...
pyinstaller pdf_crawler_gui_2.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo Executable location: dist\PDF_Crawler_GUI.exe
echo.
echo IMPORTANT: Make sure to install Playwright browsers on the target machine:
echo   python -m playwright install chromium
echo.
echo Or copy the browser cache from: %USERPROFILE%\.cache\ms-playwright
echo.
pause 