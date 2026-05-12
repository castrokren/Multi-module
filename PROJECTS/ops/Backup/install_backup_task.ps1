# install_backup_task.ps1
# Run this ONCE as Administrator to register the nightly backup task.
# After registration, the task runs automatically at 2:00 AM daily.

$TaskName   = "NightlyProjectsBackup"
$ScriptPath = "C:\Projects\Crawler\PROJECTS\ops\backup\backup_projects.ps1"
$RunAt      = "02:00"

# --- Self-elevate if not already running as Administrator ---
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Not elevated — relaunching as Administrator (UAC prompt will appear)..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Wait
    exit
}

# --- Remove existing task if present ---
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# --- Define the action ---
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`""

# --- Daily trigger at 2:00 AM ---
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt

# --- Run as SYSTEM so it works even when logged out ---
$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# --- Settings: run if missed, stop after 2 hours ---
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# --- Register ---
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Nightly versioned backup of C:\Projects to Z:\Backups\Projects" `
    -Force

Write-Host ""
Write-Host "Task registered: $TaskName"
Write-Host "Runs daily at:   $RunAt"
Write-Host "Script:          $ScriptPath"
Write-Host ""
Write-Host "To run immediately for a first test:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To check last run status:"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
