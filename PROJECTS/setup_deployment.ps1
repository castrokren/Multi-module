#############################################################################
# Crawler Pipeline Deployment Setup
#############################################################################
# Purpose: Initialize deployment automation with Task Scheduler
# Usage: Run as Administrator
#
# This script:
#   1. Pushes pending commits to GitHub
#   2. Creates deployment directories
#   3. Sets up Windows Task Scheduler job for daily updates
#   4. Verifies setup
#############################################################################

param(
    [switch]$Force,
    [string]$GitHubToken,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "ERROR"   = "Red"
        "WARNING" = "Yellow"
    }[$Type]
    Write-Host "[$timestamp] [$Type] $Message" -ForegroundColor $color
}

function Test-Admin {
    $admin = [bool]([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544')
    if (-not $admin) {
        Write-Status "This script requires Administrator privileges" "ERROR"
        exit 1
    }
}

#############################################################################
# PHASE 1: Initialization
#############################################################################

Write-Status "Crawler Pipeline Deployment Setup" "INFO"
Write-Status "Starting initialization..." "INFO"

Test-Admin

$projectRoot = "C:\Projects\Crawler"
$projectsDir = "$projectRoot\PROJECTS"
$logsDir = "$projectsDir\logs"
$backupDir = "$projectsDir\backups"

# Create directories
Write-Status "Creating required directories..." "INFO"
@($logsDir, $backupDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Status "Created: $_" "SUCCESS"
    }
}

#############################################################################
# PHASE 2: Git Push (if not skipped)
#############################################################################

if (-not $SkipPush) {
    Write-Status "Checking for unpushed commits..." "INFO"

    Push-Location $projectRoot

    # Check if there are commits to push
    $unpushed = git log origin/main..HEAD --oneline 2>$null

    if ($unpushed) {
        Write-Status "Found unpushed commits:" "WARNING"
        Write-Host $unpushed

        Write-Status "Attempting to push to origin/main..." "INFO"

        # Try to push with stored credentials (if available)
        try {
            git push origin main --porcelain
            Write-Status "Push successful" "SUCCESS"
        }
        catch {
            Write-Status "Push failed: $_" "ERROR"
            Write-Status "Troubleshooting:" "WARNING"
            Write-Host @"
1. Ensure Git credentials are stored/cached:
   git config --global credential.helper wincred

2. Or set up GitHub SSH keys:
   https://docs.github.com/en/authentication/connecting-to-github-with-ssh

3. Or use GitHub personal access token:
   git config --global credential.https://github.com.username <USERNAME>
   git config --global credential.https://github.com.password <TOKEN>

4. Then re-run this script
"@
            Pop-Location
            exit 1
        }
    }
    else {
        Write-Status "All commits already pushed" "SUCCESS"
    }

    Pop-Location
}

#############################################################################
# PHASE 3: Set Up Task Scheduler
#############################################################################

Write-Status "Setting up Windows Task Scheduler..." "INFO"

$taskName = "Crawler-Pipeline-Update"
$taskPath = "Crawler"
$updateScript = "$projectsDir\update.bat"

# Verify update.bat exists
if (-not (Test-Path $updateScript)) {
    Write-Status "update.bat not found at: $updateScript" "ERROR"
    exit 1
}

Write-Status "Creating scheduled task: $taskName" "INFO"

# Remove existing task if it exists
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Status "Removing existing task..." "INFO"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null
}

# Create task action
$action = New-ScheduledTaskAction `
    -Execute "$updateScript" `
    -WorkingDirectory $projectsDir

# Create task trigger (daily at 6:00 AM)
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At 6:00AM

# Create principal (run as SYSTEM with high privileges)
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Settings: allow task to run for 30 minutes max
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Write-Status "Task created successfully" "SUCCESS"

#############################################################################
# PHASE 4: Verification
#############################################################################

Write-Status "Verifying setup..." "INFO"

$task = Get-ScheduledTask -TaskName $taskName
$taskInfo = Get-ScheduledTaskInfo -InputObject $task

Write-Host @"

TASK CONFIGURATION:
  Name:           $taskName
  Status:         $($task.State)
  Next Run Time:  $($taskInfo.NextRunTime)
  Last Run Time:  $($taskInfo.LastRunTime)

SCRIPT LOCATIONS:
  Update Script:  $updateScript
  Logs:           $logsDir
  Backups:        $backupDir

CONFIGURATION:
  Repository:     $projectRoot
  Schedule:       Daily at 6:00 AM
  Time Limit:     30 minutes per run

"@

Write-Status "Verifying critical files..." "INFO"

$criticalFiles = @(
    "$projectsDir\src\services\scraper-full\scraper_engine.py"
    "$projectsDir\src\services\pipeline.py"
    "$projectsDir\src\services\pipeline_config.json"
)

$allFound = $true
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        Write-Status "✓ $file" "SUCCESS"
    }
    else {
        Write-Status "✗ MISSING: $file" "ERROR"
        $allFound = $false
    }
}

if (-not $allFound) {
    Write-Status "Some critical files are missing!" "ERROR"
    exit 1
}

#############################################################################
# PHASE 5: Summary
#############################################################################

Write-Status "Setup completed successfully!" "SUCCESS"

Write-Host @"

NEXT STEPS:
1. The scheduled task will run daily at 6:00 AM
2. It will check GitHub for new commits
3. Updates will be automatically deployed
4. Logs are stored in: $logsDir

TO RUN MANUALLY:
  $updateScript

TO TEST (dry run):
  $updateScript (currently live - test with actual pipeline)

TO VIEW LOGS:
  Get-Content -Tail 50 -Wait "$logsDir\deployment.log"

TO MODIFY SCHEDULE:
  Open Task Scheduler (taskschd.msc)
  Find: $taskName under Task Scheduler Library

MORE INFORMATION:
  See: $projectsDir\DEPLOYMENT.md

"@

Write-Status "Deployment system is ready!" "SUCCESS"
