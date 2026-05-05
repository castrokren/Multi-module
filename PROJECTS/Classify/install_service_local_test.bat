@echo off
echo ============================================
echo Install Service for LOCAL TESTING
echo ============================================
echo.
echo This will install the service to monitor a LOCAL folder
echo instead of the network drive, for testing purposes.
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Create local test directories
set TEST_WATCH=C:\Temp\Excel_Watch
set TEST_OUTPUT=C:\Temp\Excel_Output

echo Creating test directories...
if not exist "%TEST_WATCH%" mkdir "%TEST_WATCH%"
if not exist "%TEST_OUTPUT%" mkdir "%TEST_OUTPUT%"
echo.

:: Update monitor_config.json for local testing
echo Creating test configuration...
(
echo {
echo   "watch_directory": "C:\\Temp\\Excel_Watch",
echo   "output_directory": "C:\\Temp\\Excel_Output",
echo   "hardware_keywords_file": "hardware_keywords.txt",
echo   "software_keywords_file": "software_keywords.txt",
echo   "use_adaptive_processor": true,
echo   "learning_mode": true,
echo   "min_occurrences": 5,
echo   "confidence_threshold": 0.7
echo }
) > monitor_config.json

echo Configuration updated for local testing.
echo.

:: Get credentials
set /p USERNAME="Enter domain\username (e.g., nyumc\castrk05_adm): "
set /p PASSWORD="Enter password: "
echo.

:: Remove old service
echo Removing any existing service...
python simple_W_service.py remove >nul 2>&1
timeout /t 2 /nobreak >nul
echo.

:: Install service
echo Installing service with account: %USERNAME%
python simple_W_service.py --username "%USERNAME%" --password "%PASSWORD%" --startup auto install

if %errorLevel% neq 0 (
    echo.
    echo Installation FAILED!
    echo.
    echo Make sure you have "Log on as a service" rights.
    echo Run: grant_service_rights.bat
    echo.
    pause
    exit /b 1
)

echo.
echo Service installed successfully!
echo.

:: Start service
echo Starting service...
net start MonitorFolderSvc

if %errorLevel% neq 0 (
    echo.
    echo Service failed to start!
    echo Checking Event Log...
    powershell -Command "Get-EventLog -LogName Application -Source 'MonitorFolderSvc' -Newest 1 | Format-List Message"
    pause
    exit /b 1
)

echo.
echo ============================================
echo SUCCESS! Service is running!
echo ============================================
echo.
echo Test setup:
echo   Watch folder:  %TEST_WATCH%
echo   Output folder: %TEST_OUTPUT%
echo.
echo To test:
echo 1. Copy an Excel file to: %TEST_WATCH%
echo 2. Check for processed file in: %TEST_OUTPUT%
echo 3. View logs in Event Viewer
echo.
echo Once confirmed working, update monitor_config.json
echo to use your network path and restart the service.
echo.

pause

