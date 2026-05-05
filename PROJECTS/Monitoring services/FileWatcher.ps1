# -------------------------------
# PowerShell File Watcher Script
# -------------------------------

# --- CONFIGURATION #IN - From my  Desktop---
$SourceFolder = "\\research-cifs.nyumc.org\Omero_dev\kren\OutPut_pdf_out\"
$TargetFolder = "\\research-cifs.nyumc.org\Omero_dev\kren\OutPut_pdf_out\"
$LogFile = "C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Monitoring services\watcher.log"  # Optional log file


# Ensure target folder exists
if (-not (Test-Path $TargetFolder)) {
    New-Item -Path $TargetFolder -ItemType Directory | Out-Null
}

# Ensure log folder exists
$logDir = Split-Path $LogFile
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory | Out-Null
}

# --- CREATE WATCHER ---
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $SourceFolder
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# --- DEFINE ACTION ---
# Action uses $Event.MessageData to get config to avoid $using:
$action = {
    $fullPath = $Event.SourceEventArgs.FullPath
    $name = $Event.SourceEventArgs.Name
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $config = $Event.MessageData
    $target = $config.TargetFolder
    $log = $config.LogFile
    try {
        # Copy file
        Copy-Item $fullPath -Destination $target -Force
        # Build log message safely
        $logMsg = "[$time] Copied $name to " + $target
        Write-Host $logMsg
        Add-Content -Path $log -Value $logMsg
        # Also write to backup log in #backup_logs under TargetFolder
        $backupLogDir = Join-Path $target '#backup_logs'
        if (-not (Test-Path $backupLogDir)) {
            New-Item -Path $backupLogDir -ItemType Directory | Out-Null
        }
        $backupLogFile = Join-Path $backupLogDir 'watcher_backup.log'
        Add-Content -Path $backupLogFile -Value $logMsg
    }
    catch {
        $errorMessage = $_.Exception.Message
        # Build log message safely using concatenation
        $logMsg = "[$time] Failed to process ${name}: " + $errorMessage
        Write-Warning $logMsg
        Add-Content -Path $log -Value $logMsg
        # Also log to backup log in #backup_logs subdirectory of TargetFolder
        $backupLogDir = Join-Path $target '#backup_logs'
        if (-not (Test-Path $backupLogDir)) {
            New-Item -Path $backupLogDir -ItemType Directory | Out-Null
        }
        $backupLogFile = Join-Path $backupLogDir 'watcher_backup.log'
        Add-Content -Path $backupLogFile -Value $logMsg
    }
}
# --- REGISTER EVENT ---
Register-ObjectEvent $watcher Created -Action $action -MessageData @{ TargetFolder = $TargetFolder; LogFile = $LogFile }

# --- KEEP SCRIPT RUNNING ---
Write-Host "Watching folder: $SourceFolder. Press Ctrl+C to stop."
while ($true) {
    Start-Sleep 1
}
