# Pipeline Deployment & Operations Guide

## Overview

This folder contains everything needed to deploy the Crawler Pipeline as an automated service on a Windows server with real-time monitoring and email alerts.

---

## What You Get

### 🎯 Automated Folder Monitoring
- **Watches** `data/som-in/` for new Excel files
- **Detects** new files within 10 seconds
- **Automatically runs** the full pipeline (75-120 minutes)
- **Prevents** duplicate runs (queues if pipeline already running)

### 📊 Real-Time Dashboard
- **Web interface**: http://localhost:5000
- **Current status**: What stage is running, progress %, ETA
- **Run history**: Last 30 days of runs
- **Live logs**: Real-time log viewing
- **One-click restart**: Manually restart pipeline anytime

### 🚨 Failure Alerts
- **Email notifications** when pipeline fails
- **Instant alerting** (within seconds of failure)
- **Log excerpts** included in alert email
- **Recovery instructions** provided
- **Configurable recipients** (team distribution list)

### ⚙️ Windows Integration
- **Auto-start** on server boot via Task Scheduler
- **Auto-restart** on failure (3 retries with 5-min delays)
- **Service account** support for security
- **Logging** of all service activity

---

## Quick Start (10 minutes)

### 1. Copy Configuration Template
```powershell
copy ops\.env.example ops\.env
```

### 2. Edit Configuration
Edit `ops\.env` with your settings:
```env
SMTP_SERVER=smtp.office365.com
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENTS=ops@company.com
```

### 3. Install Dependencies
```powershell
cd C:\Projects\Crawler\PROJECTS
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install watchdog flask flask-cors python-dotenv
```

### 4. Start Services
**Option A: Double-click** (easiest)
```
Double-click: ops\start_monitor.bat
```

**Option B: PowerShell**
```powershell
python ops\folder_monitor_service.py
python ops\dashboard.py
```

### 5. Verify
- Open http://localhost:5000
- Should see "Idle - Waiting for input file..."
- Place a test Excel file in `data\som-in\`
- Pipeline should start within 10 seconds

---

## File Guide

### Configuration
| File | Purpose |
|------|---------|
| `.env.example` | Configuration template (copy and edit) |
| `.env` | Your actual configuration (edit with email settings) |

### Services
| File | Purpose | Type |
|------|---------|------|
| `folder_monitor_service.py` | Watches input folder, runs pipeline | Python |
| `dashboard.py` | Web dashboard on http://localhost:5000 | Python |
| `start_monitor.bat` | Start both services | Batch |
| `stop_monitor.bat` | Stop services | Batch |

### Utilities
| File | Purpose |
|------|---------|
| `setup_task_scheduler.ps1` | Auto-register with Windows Task Scheduler |
| `rotate_logs.ps1` | Clean up old log files (daily) |
| `test_email.py` | Test email configuration |

### Documentation
| File | Purpose |
|------|---------|
| `README.md` | This file |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step setup checklist |
| `deployment_guide.md` | Detailed technical guide |

---

## Daily Operations

### Morning Check
```
1. Open http://localhost:5000
2. Review yesterday's pipeline run
3. Check for failure emails
```

### Throughout Day
```
1. Upload new Excel files to data/som-in/
2. Monitor will detect and start pipeline within 10 seconds
3. Pipeline runs automatically (75-120 minutes)
4. Results saved to: src/services/cross-reference/results/crossref_results_*.xlsx
```

### If Pipeline Fails
```
1. Email alert received immediately
2. Check dashboard for error details
3. Review log file in alert email
4. Fix issue (check supplier connectivity, disk space, etc.)
5. Pipeline retries automatically next run or day
```

---

## Email Configuration

### Office 365 / Outlook
1. Go to https://account.activedirectory.windowsazure.com/
2. Create app-specific password
3. In `.env`:
   ```env
   SMTP_SERVER=smtp.office365.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@company.com
   SMTP_PASSWORD=<app-specific-password>
   ```

### Gmail
1. Go to https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. In `.env`:
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=<app-password>
   ```

### Test Email Configuration
```powershell
python ops\test_email.py
```

---

## Production Setup

### Step 1: Configure
```powershell
# Create .env file with email settings
copy ops\.env.example ops\.env
# Edit ops\.env with your email
```

### Step 2: Install
```powershell
cd C:\Projects\Crawler\PROJECTS
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install watchdog flask flask-cors python-dotenv
```

### Step 3: Register with Windows
```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File ops\setup_task_scheduler.ps1
```

### Step 4: Reboot & Verify
```powershell
# Reboot server
Restart-Computer -Force

# After reboot, verify services started
Get-ScheduledTask -TaskName "CrawlerPipelineMonitor"
# Should show State: Running

# Check dashboard
Start-Process http://localhost:5000
```

### Step 5: Test with Sample File
```
1. Copy sample Excel to: data\som-in\
2. Monitor should detect within 10 seconds
3. Pipeline should start automatically
4. Check dashboard for progress
5. Verify results file created after completion
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Windows Server                                  │
├─────────────────────────────────────────────────┤
│                                                   │
│  Input Folder                                   │
│  └─ data/som-in/ ← New Excel files appear      │
│     ↓ (detected within 10 seconds)              │
│                                                   │
│  Folder Monitor Service                         │
│  └─ folder_monitor_service.py                  │
│     ↓ (starts pipeline when file detected)      │
│                                                   │
│  Pipeline Orchestrator                          │
│  └─ pipeline.py (Stage 0-3)                    │
│     ├─ Stage 0: Data cleaning                   │
│     ├─ Stage 1: Scraper (PDFs)                  │
│     ├─ Stage 2: Classify items                  │
│     ├─ Stage 2b: Supplier resolution            │
│     └─ Stage 3: Cross-reference (FINAL)         │
│     ↓ (75-120 minutes)                          │
│                                                   │
│  Results                                        │
│  └─ src/services/cross-reference/results/      │
│     └─ crossref_results_[timestamp].xlsx        │
│     ↓ (email sent on completion/failure)        │
│                                                   │
│  Alert System                                   │
│  └─ Sends failure emails to ops team           │
│                                                   │
│  Dashboard                                      │
│  └─ dashboard.py                                │
│     Accessible at: http://localhost:5000        │
│                                                   │
│  Windows Task Scheduler                         │
│  └─ Auto-starts on boot                         │
│     └─ Auto-restarts on failure                 │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## Monitoring

### Dashboard (http://localhost:5000)
- Current pipeline status
- Progress bar with ETA
- Last 30 runs history
- Real-time log viewer
- One-click restart button

### Email Alerts
- Subject: ❌ PIPELINE FAILED - Run #N
- Includes: Error message, log excerpt, recovery steps
- Sent to: Recipients in `.env` → ALERT_RECIPIENTS

### Log Files
- **Monitor**: `src/services/cross-reference/results/monitor_service.log`
- **Pipeline**: `src/services/cross-reference/results/pipeline_[timestamp].log`
- **Both**: Check when troubleshooting

---

## Troubleshooting

### Monitor not detecting files
```
1. Check folder permissions: data/som-in/
2. Verify Excel file has .xlsx extension
3. Check monitor log: src/services/cross-reference/results/monitor_service.log
4. Restart monitor: stop_monitor.bat → start_monitor.bat
```

### Email not sending
```
1. Test configuration: python ops/test_email.py
2. Verify .env has correct email/password
3. Check SMTP_SERVER is correct for your provider
4. Confirm app-specific password (not regular password)
5. Check Windows Firewall allows SMTP port
```

### Dashboard not accessible
```
1. Verify dashboard is running: Get-Process python | findstr dashboard.py
2. Check port 5000 is listening: netstat -an | findstr 5000
3. Try localhost: http://127.0.0.1:5000
4. Check firewall rules for port 5000
5. Restart: stop_monitor.bat → start_monitor.bat
```

### Pipeline won't start
```
1. Check monitor log for errors
2. Verify previous run completed
3. Check disk space available (need 10+ GB)
4. Check network connectivity to supplier websites
5. Review pipeline log in src/services/cross-reference/results/
```

### Disk space running low
```
1. Archive old PDF folder: data/scraped-pdfs/
2. Clean old logs: src/services/cross-reference/results/pipeline_*.log
3. Implement log rotation: rotate_logs.ps1
4. Schedule Task Scheduler to run rotate_logs.ps1 daily
```

---

## Support

### Logs Location
- Monitor: `src/services/cross-reference/results/monitor_service.log`
- Pipeline: `src/services/cross-reference/results/pipeline_*.log`
- Always check logs first when troubleshooting

### Documents
- **Detailed Guide**: `deployment_guide.md`
- **Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **Project Info**: `../CLAUDE.md`

### Quick Commands
```powershell
# Start services
.\ops\start_monitor.bat

# Stop services
.\ops\stop_monitor.bat

# View monitor log (last 50 lines)
Get-Content src/services/cross-reference/results/monitor_service.log -Tail 50

# View latest pipeline log
Get-ChildItem src/services/cross-reference/results/pipeline_*.log -Newest 1 | Get-Content -Tail 50

# Test email
python ops/test_email.py

# Check if processes running
Get-Process python | Where-Object {$_.CommandLine -like "*monitor*" -or $_.CommandLine -like "*dashboard*"}
```

---

## What Gets Deployed

### Input
- Excel files in `data/som-in/` (SOM - Statement of Materials)
- Supplier master list in `data/masterlist/`

### Processing
- Data cleaning (removes corrupted names)
- PDF scraping from supplier websites (~4,000 files)
- Classification (Instrument/Software/Non-Instrument)
- Supplier resolution (finds websites for unknown suppliers)
- Cross-referencing (links items to PDFs)

### Output
- **Final Product**: `crossref_results_[timestamp].xlsx`
  - Items matched to supporting PDF documents
  - Confidence scores for each match
  - Supplier names and PDF file paths
  
### Duration
- **Total**: 75-120 minutes per run
- **Scraper** (largest component): 60-90 minutes
- **Classify**: 2-5 minutes
- **Cross-ref**: 5-10 minutes

---

## Performance Baseline

| Metric | Value |
|--------|-------|
| Folder detection | <10 seconds |
| Pipeline duration | 75-120 minutes |
| Match rate | 15-30% of items |
| Failure rate | <5% |
| Disk usage growth | 1-2 GB/week |
| Email latency | <1 minute on failure |
| Dashboard response | <1 second |

---

## Next Steps

1. **Read**: `DEPLOYMENT_CHECKLIST.md`
2. **Configure**: `ops\.env`
3. **Install**: Run installation commands
4. **Setup**: Run `setup_task_scheduler.ps1`
5. **Test**: Place Excel file in input folder
6. **Monitor**: Check dashboard at http://localhost:5000
7. **Go Live**: Start daily feed of Excel files

---

## Questions?

- Check `deployment_guide.md` for technical details
- Check `DEPLOYMENT_CHECKLIST.md` for step-by-step walkthrough
- Review log files for specific errors
- Test email configuration with `test_email.py`

---

*Last Updated: 2026-05-12*
*Version: 1.0*
