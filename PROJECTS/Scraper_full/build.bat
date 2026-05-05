@echo off
echo PDF Crawler GUI - Build Script
echo ================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install required packages
echo Installing required packages...
pip install pyinstaller
pip install -r requirements.txt

REM Install Playwright browsers
echo Installing Playwright browsers...
python -m playwright install chromium

REM Build with PyInstaller
echo Building executable...
pyinstaller pdf_crawler_gui_2.spec

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable location: dist\PDF_Crawler_GUI.exe
echo.
pause 