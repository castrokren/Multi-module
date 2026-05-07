@echo off
echo ============================================
echo Excel Folder Monitor Service Installer
echo For Network Drive Access
echo ============================================
echo.
echo IMPORTANT: This service will monitor a network path.
echo You MUST use your domain credentials (not LocalSystem).
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

:: Set credentials (update these!)
echo Enter your credentials:
set /p USERNAME="Domain\Username (e.g., nyumc\castrk05_adm): "
set /p PASSWORD="Password: "
echo.

:: Show what will be installed
echo ============================================
echo Configuration:
echo ============================================
echo Service Account: %USERNAME%
echo Startup Type: Automatic
echo.
echo Watch Directory: \\research-cifs.nyumc.org\omero_dev\kren\SOM_in
echo Output Directory: D:\SOM_in_labeled
echo.

set /p CONFIRM="Continue with installation? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Installation cancelled.
    pause
    exit /b 0
)

echo.
echo Removing any existing service...
python simple_W_service.py remove >nul 2>&1
timeout /t 2 /nobreak >nul
echo.

echo Installing service with account: %USERNAME%
echo.
python simple_W_service.py --username "%USERNAME%" --password "%PASSWORD%" --startup auto install

if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo ERROR: Service installation failed!
    echo ============================================
    echo.
    echo Common issues:
    echo 1. Incorrect password
    echo 2. User doesn't have "Log on as a service" rights
    echo 3. Username format must be: domain\username
    echo.
    echo To grant "Log on as a service" rights:
    echo 1. Run: secpol.msc
    echo 2. Go to: Local Policies ^> User Rights Assignment
    echo 3. Double-click "Log on as a service"
    echo 4. Add your user account
    echo 5. Restart and try again
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Service Installation Successful!
echo ============================================
echo.

:: Show service status
echo Service Status:
sc query MonitorFolderSvc
echo.

echo ============================================
echo Starting the service...
echo ============================================
net start MonitorFolderSvc

if %errorLevel% neq 0 (
    echo.
    echo Service failed to start. Checking Event Log...
    echo.
    powershell -Command "Get-EventLog -LogName Application -Source 'MonitorFolderSvc' -Newest 1 | Format-List TimeGenerated, EntryType, Message"
    echo.
    echo Check the error above and verify:
    echo 1. Network path is accessible: \\research-cifs.nyumc.org\omero_dev\kren\SOM_in
    echo 2. Output directory is writable: D:\SOM_in_labeled
    echo 3. Keyword files exist in: %CD%
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo SUCCESS! Service is running!
echo ============================================
echo.
echo The service is now monitoring:
echo   \\research-cifs.nyumc.org\omero_dev\kren\SOM_in
echo.
echo Processed files will be saved to:
echo   D:\SOM_in_labeled
echo.
echo To view service activity:
echo 1. Open Event Viewer (eventvwr.msc)
echo 2. Navigate to: Windows Logs ^> Application
echo 3. Filter by source: MonitorFolderSvc
echo.
echo To stop the service:
echo   net stop MonitorFolderSvc
echo.
echo To restart the service:
echo   net stop MonitorFolderSvc
echo   net start MonitorFolderSvc
echo.

pause

