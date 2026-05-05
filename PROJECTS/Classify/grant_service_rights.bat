@echo off
echo ============================================
echo Grant "Log on as a service" Rights
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

echo This will grant "Log on as a service" rights to your account.
echo.
set /p USERNAME="Enter your account (e.g., nyumc\castrk05_adm): "
echo.

echo Granting rights to: %USERNAME%
echo.

:: Use PowerShell to grant the right
powershell -Command "& {$username = '%USERNAME%'; $tmp = New-TemporaryFile; secedit /export /cfg $tmp.FullName | Out-Null; $content = Get-Content $tmp.FullName; $newContent = $content -replace '(SeServiceLogonRight = .*)', \"`$1,$username\"; $newContent | Set-Content $tmp.FullName; secedit /configure /db secedit.sdb /cfg $tmp.FullName /areas USER_RIGHTS | Out-Null; Remove-Item $tmp.FullName -Force; Write-Host 'Rights granted successfully!' -ForegroundColor Green}"

if %errorLevel% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS!
    echo ============================================
    echo.
    echo The account %USERNAME% now has "Log on as a service" rights.
    echo.
    echo IMPORTANT: You may need to log out and log back in for changes to take effect.
    echo.
) else (
    echo.
    echo ============================================
    echo FAILED!
    echo ============================================
    echo.
    echo Manual method:
    echo 1. Press Win + R
    echo 2. Type: secpol.msc
    echo 3. Navigate to: Local Policies ^> User Rights Assignment
    echo 4. Double-click: "Log on as a service"
    echo 5. Click "Add User or Group"
    echo 6. Enter: %USERNAME%
    echo 7. Click OK
    echo.
)

pause

