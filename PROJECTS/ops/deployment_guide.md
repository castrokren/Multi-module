# Pipeline Deployment Guide — Windows Server

## Production Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Windows Server (On-Premises)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input Folder Monitor (folder_monitor_service.py)                   │
│  ├─ Watches: C:\Projects\Crawler\PROJECTS\data\som-in\             │
│  ├─ Triggers: When new .xlsx appears                                │
│  └─ Runs: Pipeline orchestrator                                     │
│                                                                       │
│  Pipeline Orchestrator (pipeline.py)                                │
│  ├─ Stage 0: Data Cleaning                                          │
│  ├─ Stage 1: Scraper (PDFs)                                         │
│  ├─ Stage 2: Classify                                               │
│  ├─ Stage 2b: Supplier Resolution                                   │
│  └─ Stage 3: Cross-Ref (FINAL OUTPUT)                               │
│                                                                       │
│  Alert System (email_alerter.py)                                    │
│  ├─ Monitors: Pipeline logs in real-time                            │
│  ├─ Triggers: On ERROR or FAILURE                                   │
│  └─ Sends: Email alerts to ops team                                 │
│                                                                       │
│  Status Dashboard (dashboard.py)                                    │
│  ├─ Web UI: http://localhost:5000                                   │
│  ├─ Shows: Current run status, logs, history                        │
│  └─ Updates: Real-time via WebSocket                                │
│                                                                       │
│  Windows Task Scheduler                                             │
│  ├─ Starts: Folder monitor at system boot                           │
│  ├─ Restarts: On failure (automatic recovery)                       │
│  └─ Logs: All service start/stop events                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Overview

### 1. Folder Monitor Service
**File**: `ops/folder_monitor_service.py`

- Watches `data/som-in` for new `.xlsx` files
- Detects new files within 10 seconds
- Prevents duplicate runs (waits for previous to complete)
- Logs all activity
- Auto-restarts on crash

**Behavior**:
```
[14:00:00] Watching folder: data/som-in
[14:05:23] ⚠️  New file detected: NQ_DG_RESEARCH_CAPITAL_V2.xlsx
[14:05:24] ✓ Pipeline not running, starting...
[14:05:25] [PIPELINE RUNNING]
[16:20:00] [PIPELINE COMPLETE] - 81 matches found
[16:20:01] ✓ Results saved to: crossref_results_20260512_162000.xlsx
[16:20:02] 📧 Email alert sent to: ops@company.com
```

### 2. Email Alert System
**File**: `ops/email_alerter.py`

- Monitors pipeline logs for ERROR/FAILURE
- Sends immediate email on failure
- Includes: Error message, log excerpt, recovery instructions
- Configurable alert recipients

**Alert Template**:
```
Subject: ⚠️ PIPELINE FAILED - NQ_DG_RESEARCH_CAPITAL_V2.xlsx

Pipeline failed at Stage 2b (Supplier Resolution)

Error: Connection timeout to DuckDuckGo API
Time: 2026-05-12 15:45:23
Duration: 1 hour 40 minutes

Recovery:
1. Check internet connectivity
2. Review: src/services/cross-reference/results/pipeline_20260512_154500.log
3. Retry: Folder monitor will auto-retry next day

Contact: DevOps team for manual restart
```

### 3. Status Dashboard
**File**: `ops/dashboard.py`

- Web interface: `http://[server]:5000`
- Real-time status updates
- Shows: Current stage, progress %, ETA, logs
- History of last 30 runs
- One-click manual restart

**Dashboard View**:
```
┌─────────────────────────────────────────────────┐
│ PIPELINE MONITOR DASHBOARD                      │
├─────────────────────────────────────────────────┤
│                                                  │
│ Current Run                                     │
│ ├─ File: NQ_DG_RESEARCH_CAPITAL_V2.xlsx        │
│ ├─ Started: 2026-05-12 14:05:24                │
│ ├─ Stage: 1 (Scraper)                          │
│ ├─ Progress: ████████░░░░░░░░░░░ 42% (1hr)    │
│ └─ ETA: 15:45 UTC                              │
│                                                  │
│ Recent Runs (Last 30 days)                      │
│ ├─ 2026-05-12 14:05 → Running (1h 40m)         │
│ ├─ 2026-05-11 17:12 → ✓ Success (2h 15m)       │
│ ├─ 2026-05-10 06:00 → ✓ Success (2h 05m)       │
│ └─ 2026-05-09 06:00 → ✗ Failed (Stage 2b)      │
│                                                  │
│ [View Full Log] [Restart] [Settings]            │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 4. Windows Task Scheduler Integration
- Starts folder monitor at boot
- Auto-restarts if service crashes
- Runs under dedicated service account
- Logs all start/stop events

---

## Deployment Steps

### Step 1: Prepare Server Environment

**Requirements**:
- Windows Server 2016+ (or Windows 10 Pro)
- Python 3.8+
- Network access to supplier websites
- SMTP access for email alerts (Office 365, Gmail, etc.)

**Create service account** (optional but recommended):
```powershell
# Run as Administrator
New-LocalUser -Name "CrawlerService" -Password (Read-Host -AsSecureString) -Description "Service account for pipeline automation"
Add-LocalGroupMember -Group "Users" -Member "CrawlerService"
```

---

### Step 2: Install Python Dependencies

```powershell
cd C:\Projects\Crawler\PROJECTS

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install watchdog  # Folder monitoring
pip install flask     # Dashboard web server
pip install flask-cors
pip install python-dotenv
```

**requirements.txt** (add if not present):
```
pandas==2.3.3
openpyxl==3.11.0
beautifulsoup4==4.12.2
requests==2.31.0
lxml==4.9.3
watchdog==3.0.0
flask==3.0.0
flask-cors==4.0.0
python-dotenv==1.0.0
```

---

### Step 3: Configure Email Alerts

**Create** `ops/.env`:
```env
# Email Configuration
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENTS=ops@company.com,devops@company.com
ALERT_SENDER=pipeline-alerts@company.com

# Server Configuration
MONITOR_INTERVAL=10
MAX_CONCURRENT_RUNS=1
LOG_RETENTION_DAYS=90

# Dashboard Configuration
DASHBOARD_PORT=5000
DASHBOARD_HOST=0.0.0.0
```

**For Office 365**:
- Use your email + app-specific password
- Enable "Allow less secure app access" or use Modern Auth

**For Gmail**:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

### Step 4: Create Batch Launcher Scripts

**File**: `ops\start_monitor.bat`
```batch
@echo off
REM Start Pipeline Monitor Service
cd /d C:\Projects\Crawler\PROJECTS

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start folder monitor and dashboard
start /B python ops/folder_monitor_service.py
start /B python ops/dashboard.py

echo.
echo Pipeline Monitor Started
echo Folder Monitor: Watching C:\Projects\Crawler\PROJECTS\data\som-in
echo Dashboard: http://localhost:5000
echo.
pause
```

**File**: `ops\stop_monitor.bat`
```batch
@echo off
REM Stop all pipeline services
taskkill /F /IM python.exe
echo Pipeline Monitor Stopped
pause
```

---

### Step 5: Configure Windows Task Scheduler

**Create Scheduled Task**:

```powershell
# Run as Administrator

$taskName = "CrawlerPipelineMonitor"
$taskDescription = "Monitors input folder and runs document crawling pipeline"
$taskPath = "\CrawlerProjects\"
$scriptPath = "C:\Projects\Crawler\PROJECTS\ops\start_monitor.bat"

$principal = New-ScheduledTaskPrincipal -UserID "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$trigger = New-ScheduledTaskTrigger -AtStartup
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$scriptPath`""

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries:$false `
    -DontStopIfGoingOnBatteries:$false

Register-ScheduledTask `
    -TaskName $taskName `
    -TaskPath $taskPath `
    -Principal $principal `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description $taskDescription
```

**Or via GUI**:
1. Open Task Scheduler
2. Create Basic Task → "Crawler Pipeline Monitor"
3. Trigger: At system startup
4. Action: Start a program
   - Program: `C:\Projects\Crawler\PROJECTS\ops\start_monitor.bat`
   - Start in: `C:\Projects\Crawler\PROJECTS`
5. Conditions:
   - ☐ Stop if computer switches to battery power
   - ☑ Start if system is on AC power
6. Settings:
   - ☑ Allow task to be run on demand
   - ☑ If task fails, restart every 5 minutes (retry 3 times)
   - ☑ Run with highest privileges

---

### Step 6: Set Up Log Rotation

**File**: `ops\rotate_logs.ps1`
```powershell
# Keep only last 90 days of logs

$logsPath = "C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results"
$retentionDays = 90

Get-ChildItem -Path $logsPath -Filter "pipeline_*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-$retentionDays)
} | Remove-Item -Force

Write-Host "Cleaned up logs older than $retentionDays days"
```

**Schedule in Task Scheduler**:
- Trigger: Daily at 2:00 AM
- Action: `powershell.exe -ExecutionPolicy Bypass -File "C:\Projects\Crawler\PROJECTS\ops\rotate_logs.ps1"`

---

### Step 7: Verify Deployment

```powershell
# Check if services are running
Get-Process python | Select-Object ProcessName, Id, StartTime

# Check recent logs
Get-ChildItem -Path "C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results\pipeline_*.log" -Newest 5

# Test email configuration
python ops/test_email.py

# Access dashboard
Start-Process "http://localhost:5000"
```

---

## Daily Operations

### Normal Flow
```
06:00 AM → New Excel file appears in data/som-in
06:05 AM → Folder monitor detects file
06:06 AM → Pipeline starts automatically
08:30 AM → Pipeline completes
08:31 AM → Success email sent to ops@company.com
         → Results file: crossref_results_20260512_083000.xlsx
08:32 AM → Dashboard updated with results
         → Ready for next input file
```

### On Failure
```
15:45 PM → Pipeline fails at Stage 2b
15:46 PM → Email alert sent immediately
15:47 PM → Alert includes: error, log excerpt, recovery steps
15:50 PM → DevOps reviews dashboard and logs
16:00 PM → Manual restart or system fix applied
16:05 PM → Pipeline reruns automatically
```

### Dashboard Monitoring
- Check dashboard daily: `http://[server-ip]:5000`
- Monitor "Recent Runs" section
- Review any failed runs
- Archive successful results

---

## Monitoring Checklist (Daily)

- ✅ Check dashboard for current status
- ✅ Review email alerts (should be 0 failures)
- ✅ Verify new results files in `crossref_results_*.xlsx`
- ✅ Confirm disk space available (PDFs can be large)
- ✅ Check network connectivity to supplier websites
- ✅ Review log file sizes (should rotate automatically)

---

## Troubleshooting

### Pipeline Starts But Gets Stuck
```powershell
# Check if previous run is still running
Get-Process python | Select-Object ProcessName, Path, StartTime

# View last log
Get-Content "C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results\pipeline_*.log" -Tail 50

# Manually kill hanging process (if needed)
Stop-Process -Name python -Force
```

### Email Alerts Not Sending
```powershell
# Test SMTP configuration
python ops/test_email.py

# Verify .env file has correct credentials
Get-Content "C:\Projects\Crawler\PROJECTS\ops\.env"

# Check Windows firewall allows SMTP port
netstat -an | Select-String "587"
```

### Dashboard Not Accessible
```powershell
# Check if Flask is running
Get-Process python | Where-Object {$_.CommandLine -like "*dashboard.py*"}

# Check if port 5000 is listening
netstat -an | Select-String "5000"

# Access locally first
Start-Process "http://localhost:5000"
```

### Disk Space Issues
```powershell
# Monitor PDF directory size
(Get-ChildItem -Path "C:\Projects\Crawler\PROJECTS\data\scraped-pdfs" -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB

# Implement cleanup (archive old PDFs)
Get-ChildItem -Path "C:\Projects\Crawler\PROJECTS\data\scraped-pdfs" -Recurse | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | Move-Item -Destination "D:\Archive\CrawlerPDFs-2026-05\"
```

---

## Production Best Practices

1. **Backup Strategy**
   - Daily backup of results files to network share
   - Weekly backup of entire `data/` directory
   - Monthly archive of old logs

2. **Monitoring**
   - Set up email alerts for failures
   - Dashboard should be checked daily
   - Consider SMS alerts for critical failures

3. **Scaling**
   - Monitor pipeline duration (should stay <3 hours)
   - If consistently over time limit, increase scraper concurrency or split supplier list
   - Monitor disk space (PDFs grow over time)

4. **Security**
   - Use dedicated service account with minimal permissions
   - Store credentials in `.env` file, not in code
   - Restrict dashboard access to internal network only
   - Review logs for any security-related errors

5. **Documentation**
   - Keep deployment guide updated
   - Document any custom configuration
   - Create runbook for common issues
   - Log all manual interventions

---

## Support & Maintenance

**Regular Tasks**:
- Weekly: Check dashboard, review failed runs
- Monthly: Validate master supplier list, archive old results
- Quarterly: Review pipeline performance metrics
- Yearly: Update dependencies, security patches

**Escalation**:
1. Check dashboard and recent logs
2. Review email alerts
3. Verify network/SMTP connectivity
4. Consult troubleshooting guide
5. Contact DevOps team

---

*Deployment Guide v1.0 — Last updated 2026-05-12*
