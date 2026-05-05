@echo off
echo ===================================
echo Checking MonitorFolderSvc Status
echo ===================================
echo.

echo Service Details:
sc query MonitorFolderSvc
echo.

echo Service Configuration:
sc qc MonitorFolderSvc
echo.

echo Recent Event Logs (if service has run):
echo Check Event Viewer: Windows Logs ^> Application ^> Filter by "MonitorFolderSvc"
echo.

pause

