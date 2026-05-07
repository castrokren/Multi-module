@echo off
echo ============================================
echo Excel Folder Monitor Service Installer
echo ============================================
echo.
echo This script must be run as Administrator!
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

:: Remove existing service if it exists
echo Removing any existing service...
python simple_W_service.py remove >nul 2>&1
echo.

:: Install service as LocalSystem (no credentials needed)
echo Installing service as LocalSystem account...
python simple_W_service.py install
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Service installation failed!
    echo.
    pause
    exit /b 1
)

echo.
echo Setting service to Auto start...
sc config MonitorFolderSvc start= auto
echo.

echo ============================================
echo Service Installation Complete!
echo ============================================
echo.
echo Service Name: MonitorFolderSvc
echo Display Name: Excel Folder Monitor Service
echo Start Type: Automatic
echo Account: LocalSystem
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
echo 2. Check Event Viewer for service logs:
echo    eventvwr.msc
echo    Navigate to: Windows Logs ^> Application
echo    Filter by source: MonitorFolderSvc
echo.
echo 3. Monitor the output folder:
echo    D:\SOM_in_labeled
echo.

pause

