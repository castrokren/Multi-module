# ==============================================================================
# Windows Task Scheduler Setup Script
# ==============================================================================
# Automatically registers the Pipeline Monitor as a Windows Task
# Run as Administrator
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
#
# ==============================================================================

param(
    [switch]$Remove = $false
)

# Require administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Host "`n[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Run: powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1`n" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$taskName = "CrawlerPipelineMonitor"
$taskPath = "\CrawlerProjects\"
$scriptPath = "C:\Projects\Crawler\PROJECTS\start.bat"
$projectRoot = "C:\Projects\Crawler\PROJECTS"

Write-Host "`n" -ForegroundColor White
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       Windows Task Scheduler - Pipeline Monitor Setup              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if script path exists
if (-NOT (Test-Path $scriptPath))
{
    Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

if ($Remove)
{
    Write-Host "[INFO] Removing existing task..." -ForegroundColor Yellow
    $existingTask = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask)
    {
        Unregister-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Confirm:$false
        Write-Host "[OK] Task removed" -ForegroundColor Green
    }
    else
    {
        Write-Host "[INFO] Task not found" -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "[INFO] Task name: $taskName" -ForegroundColor Yellow
Write-Host "[INFO] Task path: $taskPath" -ForegroundColor Yellow
Write-Host "[INFO] Script: $scriptPath" -ForegroundColor Yellow
Write-Host ""

# Check if task already exists
Write-Host "[INFO] Checking for existing task..." -ForegroundColor Yellow
$existingTask = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask)
{
    Write-Host "[WARN] Task already exists. Removing and recreating..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Confirm:$false
}

# Create task principal (run as SYSTEM account with highest privileges)
Write-Host "[INFO] Creating task principal..." -ForegroundColor Yellow
$principal = New-ScheduledTaskPrincipal `
    -UserID "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create task trigger (at system startup)
Write-Host "[INFO] Creating task trigger (at startup)..." -ForegroundColor Yellow
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create task action (run batch file)
Write-Host "[INFO] Creating task action..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$scriptPath`"" `
    -WorkingDirectory $projectRoot

# Create task settings
Write-Host "[INFO] Creating task settings..." -ForegroundColor Yellow
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -DisallowHardTerminate $false `
    -AllowStartIfOnBatteries:$false `
    -DontStopIfGoingOnBatteries:$false `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

# Register the task
Write-Host "[INFO] Registering scheduled task..." -ForegroundColor Yellow
try
{
    Register-ScheduledTask `
        -TaskName $taskName `
        -TaskPath $taskPath `
        -Principal $principal `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Monitors input folder for Excel files and automatically runs the document crawling pipeline" `
        -Force

    Write-Host "[OK] Task registered successfully" -ForegroundColor Green
}
catch
{
    Write-Host "[ERROR] Failed to register task: $_" -ForegroundColor Red
    exit 1
}

# Verify task was created
Write-Host "[INFO] Verifying task creation..." -ForegroundColor Yellow
$createdTask = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue

if ($createdTask)
{
    Write-Host "[OK] Task verified" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:       $($createdTask.TaskName)" -ForegroundColor White
    Write-Host "  Path:       $($createdTask.TaskPath)" -ForegroundColor White
    Write-Host "  State:      $($createdTask.State)" -ForegroundColor White
    Write-Host "  Triggers:   $($createdTask.Triggers.Count) trigger(s)" -ForegroundColor White
}
else
{
    Write-Host "[ERROR] Task verification failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                        SETUP COMPLETE                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Configure email in: ops\.env" -ForegroundColor White
Write-Host "  2. Reboot the server" -ForegroundColor White
Write-Host "  3. Verify task started: Get-ScheduledTask | Where Name -eq '$taskName'" -ForegroundColor White
Write-Host "  4. Check dashboard: http://localhost:5000" -ForegroundColor White
Write-Host "  5. Monitor logs: src\services\cross-reference\results\monitor_service.log" -ForegroundColor White
Write-Host ""
Write-Host "To view task in GUI:" -ForegroundColor Yellow
Write-Host "  1. Open Task Scheduler" -ForegroundColor White
Write-Host "  2. Navigate to: Task Scheduler Library > CrawlerProjects" -ForegroundColor White
Write-Host "  3. Right-click '$taskName' to run manually" -ForegroundColor White
Write-Host ""
Write-Host "To remove task later:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1 -Remove" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
