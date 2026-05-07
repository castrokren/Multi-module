@echo off
echo ============================================
echo Excel Folder Monitor Service Installer
echo (With Domain Credentials)
echo ============================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo.
    echo Please right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Running with Administrator privileges...
echo.

:: Prompt for credentials
set /p USERNAME="Enter domain\username (e.g., nyumc\castrk05): "
set /p PASSWORD="Enter password: "
echo.

:: Remove existing service if it exists
echo Removing any existing service...
python simple_W_service.py remove >nul 2>&1
echo.

:: Install service with credentials
echo Installing service with account: %USERNAME%
python simple_W_service.py --username "%USERNAME%" --password "%PASSWORD%" --startup auto install

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Service installation failed!
    echo.
    echo Common issues:
    echo - Incorrect password
    echo - User doesn't have "Log on as a service" rights
    echo - Username format should be: domain\username
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Service Installation Complete!
echo ============================================
echo.
echo Service Name: MonitorFolderSvc
echo Display Name: Excel Folder Monitor Service  
echo Start Type: Automatic
echo Account: %USERNAME%
echo.

:: Show service status
echo Current Status:
sc query MonitorFolderSvc
echo.

echo ============================================
echo Next Steps:
echo ============================================
echo 1. Start the service using the UI or run:
echo    net start MonitorFolderSvc
echo.
echo 2. Check Event Viewer for service logs
echo.

pause

