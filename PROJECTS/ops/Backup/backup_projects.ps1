#!/usr/bin/env powershell
# backup_projects.ps1
# Versioned nightly backup of C:\Projects to Z:\Backups\Projects
# Keeps last 7 daily snapshots. Run via Windows Task Scheduler.

$Source      = "C:\Projects"
$BackupRoot  = "Z:\Backups\Projects"
$LogRoot     = "Z:\Backups\logs"
$KeepDays    = 7
$Timestamp   = Get-Date -Format "yyyy-MM-dd"
$Dest        = "$BackupRoot\$Timestamp"
$LogFile     = "$LogRoot\backup_$Timestamp.log"

# Exclusions — skip Python cache, git worktree temps, OS junk
$Excludes = @(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    "*.tmp",
    "Thumbs.db",
    "desktop.ini"
)

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

# --- Setup ---
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogRoot    | Out-Null

Write-Log "===== Backup started ====="
Write-Log "Source : $Source"
Write-Log "Dest   : $Dest"

# --- Check NAS is reachable ---
if (-not (Test-Path "Z:\")) {
    Write-Log "ERROR: NAS drive Z:\ is not accessible. Aborting."
    exit 1
}

# --- Check if today's backup already exists (idempotent) ---
if (Test-Path $Dest) {
    Write-Log "Backup for $Timestamp already exists at $Dest. Skipping."
    exit 0
}

# --- Find most recent previous backup to use as base (incremental copy) ---
$Previous = Get-ChildItem -Path $BackupRoot -Directory |
            Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' } |
            Sort-Object Name -Descending |
            Select-Object -First 1

# --- Run robocopy ---
# /E     - copy all subdirectories including empty ones
# /COPYALL - copy all file info (data, attributes, timestamps, ACLs)
# /R:2   - retry 2 times on failure
# /W:5   - wait 5 seconds between retries
# /NP    - no progress percentage (cleaner logs)
# /NDL   - no directory list in log
# /XD    - exclude directories
# /XF    - exclude files

$RobocopyArgs = @(
    $Source, $Dest,
    "/E", "/COPYALL", "/R:2", "/W:5", "/NP", "/NDL",
    "/LOG+:$LogFile"
)

foreach ($xd in $Excludes | Where-Object { -not $_.Contains("*") }) {
    $RobocopyArgs += "/XD"; $RobocopyArgs += $xd
}
foreach ($xf in $Excludes | Where-Object { $_.Contains("*") }) {
    $RobocopyArgs += "/XF"; $RobocopyArgs += $xf
}

Write-Log "Running robocopy..."
$proc = Start-Process -FilePath "robocopy" -ArgumentList $RobocopyArgs `
        -Wait -PassThru -NoNewWindow

# Robocopy exit codes: 0-3 = success, 4+ = warnings/errors
if ($proc.ExitCode -le 3) {
    Write-Log "Robocopy completed successfully (exit code $($proc.ExitCode))."
} else {
    Write-Log "WARNING: Robocopy exit code $($proc.ExitCode) — check log for details."
}

# --- Prune old backups (keep last $KeepDays) ---
Write-Log "Pruning backups older than $KeepDays days..."
$AllBackups = Get-ChildItem -Path $BackupRoot -Directory |
              Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' } |
              Sort-Object Name -Descending

$ToDelete = $AllBackups | Select-Object -Skip $KeepDays

foreach ($old in $ToDelete) {
    Write-Log "Deleting old backup: $($old.FullName)"
    Remove-Item -Recurse -Force -Path $old.FullName
}

Write-Log "Kept $([Math]::Min($AllBackups.Count, $KeepDays)) backups."
Write-Log "===== Backup complete ====="
exit 0
