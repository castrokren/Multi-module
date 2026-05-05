@echo off
echo ============================================
echo Test Network Path Access
echo ============================================
echo.

set NETWORK_PATH=\\research-cifs.nyumc.org\omero_dev\kren\SOM_in

echo Testing access to: %NETWORK_PATH%
echo.

echo Current user:
whoami
echo.

echo Attempting to access network path...
dir "%NETWORK_PATH%" >nul 2>&1

if %errorLevel% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS! Network path is accessible.
    echo ============================================
    echo.
    echo Listing first 10 files:
    dir /b "%NETWORK_PATH%" | findstr /i ".xls" | more
    echo.
    echo You have access to the network drive.
    echo The service should be able to access it with proper credentials.
    echo.
) else (
    echo.
    echo ============================================
    echo FAILED! Cannot access network path.
    echo ============================================
    echo.
    echo Error: Access denied to %NETWORK_PATH%
    echo.
    echo Possible issues:
    echo 1. You don't have permission to access this network share
    echo 2. The network path doesn't exist
    echo 3. You need to map the network drive first
    echo.
    echo Try mapping the drive manually:
    echo   net use Z: %NETWORK_PATH% /user:nyumc\castrk05_adm YourPassword
    echo.
)

echo.
echo Testing output directory access...
set OUTPUT_DIR=D:\SOM_in_labeled

if exist "%OUTPUT_DIR%" (
    echo ✓ Output directory exists: %OUTPUT_DIR%
    
    :: Test write access
    echo test > "%OUTPUT_DIR%\test_write.tmp" 2>nul
    if exist "%OUTPUT_DIR%\test_write.tmp" (
        del "%OUTPUT_DIR%\test_write.tmp"
        echo ✓ Output directory is writable
    ) else (
        echo ✗ Output directory is NOT writable
    )
) else (
    echo ✗ Output directory does NOT exist: %OUTPUT_DIR%
    echo   Creating it...
    mkdir "%OUTPUT_DIR%" 2>nul
    if exist "%OUTPUT_DIR%" (
        echo ✓ Output directory created successfully
    ) else (
        echo ✗ Failed to create output directory
    )
)

echo.
pause

