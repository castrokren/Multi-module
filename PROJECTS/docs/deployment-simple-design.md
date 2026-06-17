# One-Click Pipeline Deployment — Design Spec

**Date:** 2026-05-12  
**Version:** 1.0  
**Status:** Design Approved

---

## Overview

Single-file, one-click deployment for the Crawler Pipeline on Windows servers with Python already installed. User double-clicks `setup.bat`, answers email questions (30 seconds), and pipeline is fully operational.

---

## Goals

- ✅ Eliminate installation complexity
- ✅ Zero config files to edit
- ✅ Works with existing Python
- ✅ Automated Windows Task Scheduler registration
- ✅ Services start automatically after setup
- ✅ Clear next steps after completion

---

## Architecture

```
setup.bat (double-click)
  ├─ Check Python installed
  ├─ Create venv
  ├─ Install dependencies (pip)
  ├─ Interactive email prompt (30 seconds)
  ├─ Create .env file (auto-generated)
  ├─ Register Windows Task Scheduler
  ├─ Start folder monitor service
  ├─ Start web dashboard
  └─ Open http://localhost:5000 in browser
  
Result: Pipeline running and ready for input files
```

---

## Components

### 1. Main Setup Script: `setup.bat`
- **Purpose:** One-click deployment orchestrator
- **Actions:**
  - Verify Python 3.8+ installed
  - Create virtual environment (`venv/`)
  - Install dependencies from `requirements.txt`
  - Display interactive email setup (SMTP_USERNAME, SMTP_PASSWORD, ALERT_RECIPIENTS)
  - Auto-generate `.env` file from responses
  - Run `setup_task_scheduler.ps1` to register Task Scheduler job
  - Start both services (`folder_monitor_service.py`, `dashboard.py`)
  - Open dashboard in default browser
- **Duration:** 2-3 minutes
- **Output:** "Setup complete! Dashboard opened."

### 2. Service Scripts (Existing)
- `folder_monitor_service.py` — Watches `data/som-in/` for new Excel files, runs pipeline
- `dashboard.py` — Web UI on HTTPS port 443 with self-signed certificate (shows current status + last 5 runs)

### 3. Utility Scripts
- `start.bat` — Start services (after setup)
- `stop.bat` — Stop services
- `setup_task_scheduler.ps1` — Register auto-start with Windows (called by setup.bat)

### 4. Configuration
- No `.env` file needed (no email alerts)
- Setup is completely automated with no user input

---

## User Experience Flow

### First Time: Setup
```
User double-clicks: setup.bat

[Screen shows]
✓ Python 3.8+ found
✓ Creating virtual environment...
✓ Installing dependencies...
✓ Generating HTTPS certificate...
✓ Registering with Windows Task Scheduler...
✓ Starting services...

Opening dashboard: https://localhost

→ [Browser opens automatically]
→ [Browser warning: "Not secure" - click "Proceed"]

Setup complete! Pipeline is running.
```

### Daily: Use Pipeline
```
1. Drop Excel file in: data/som-in/
2. Monitor detects within 10 seconds
3. Pipeline starts automatically
4. Check dashboard: https://localhost
5. View current status and last 5 runs

No further action needed.
```

### If Issues Occur
```
Check dashboard for status
Review logs in: src/services/cross-reference/results/
Restart services: stop.bat → start.bat
```

---

## Data Files Generated

| File | Purpose | Created |
|------|---------|---------|
| `venv/` | Python virtual environment | setup.bat |
| `monitor_service.log` | Activity log | folder_monitor_service.py |
| `pipeline_*.log` | Pipeline execution logs | pipeline.py |
| `crossref_results_*.xlsx` | Final output files | pipeline.py (Stage 3) |

---

## Requirements

**Pre-requisites:**
- Windows Server 2016+ or Windows 10 Pro
- Python 3.8+ installed and in PATH
- 15+ GB free disk space (for downloaded PDFs)

**Network:**
- Access to supplier websites (for PDF scraping)

---

## Error Handling

**Python not found:**
```
[ERROR] Python 3.8+ not found in PATH
Please install Python from: https://www.python.org/
Make sure to check "Add Python to PATH"
[Exit]
```

**Port 443 already in use:**
```
[ERROR] Port 443 already in use (required for HTTPS)
Check: netstat -an | findstr :443
Stop the blocking service and retry setup.bat
```

**Pipeline fails:**
```
Check dashboard for error details
Review logs in: src/services/cross-reference/results/pipeline_*.log
```

---

## Success Criteria

✅ User can deploy with single double-click  
✅ Setup completes in <2 minutes  
✅ No config files to manually edit  
✅ HTTPS certificate auto-generated during setup  
✅ Dashboard accessible at https://localhost  
✅ Dashboard shows current status + last 5 runs  
✅ Folder monitor detects new files automatically  
✅ Pipeline runs on file detection  
✅ Services auto-start on server reboot  
✅ Clear error messages if anything fails  

---

## Post-Setup Operations

### Daily
- Upload Excel files to `data/som-in/`
- Monitor auto-detects and runs pipeline
- Check email for completion/failure alerts
- Results in: `src/services/cross-reference/results/crossref_results_*.xlsx`

### If Problems
- Check dashboard: `http://localhost:5000`
- Check logs: `src/services/cross-reference/results/`
- Restart: `stop.bat` → `start.bat`

### Maintenance
- Keep `data/scraped-pdfs/` clean (archive old PDFs)
- Keep logs under 90 days (`rotate_logs.ps1`)
- Update supplier master list weekly

---

## Limitations

- No uninstall script (manual deletion of `venv/` and Windows task)
- Dashboard is read-only (monitoring only, no manual controls)

---

## Files Modified/Created

**Created:**
- `setup.bat` — Main deployment script

**Existing (unchanged):**
- `folder_monitor_service.py`
- `dashboard.py`
- `setup_task_scheduler.ps1`
- `start.bat`
- `stop.bat`

**Auto-generated during setup:**
- `venv/` — Python virtual environment
- `.env` — Configuration from user input

---

## Testing Strategy

1. **Clean test:** Run on fresh Windows server with no previous setup
2. **Python check:** Verify Python detection works
3. **Certificate generation:** Verify self-signed HTTPS certificate created
4. **Service startup:** Verify both services running after setup
5. **Dashboard access:** Verify https://localhost loads (browser warning expected)
6. **Dashboard content:** Verify current status + last 5 runs displays
7. **File detection:** Drop test Excel file, verify pipeline starts
8. **Status update:** Verify dashboard updates as pipeline progresses
9. **Results generation:** Verify crossref_results file created

---

## Implementation Approach

1. Create `setup.bat` with:
   - Python 3.8+ version check
   - Create virtual environment
   - Install dependencies (pip install from requirements.txt)
   - Register with Windows Task Scheduler (call PowerShell script)
   - Start services
   - Open dashboard in browser
   - Error handling for each step

2. Modify `dashboard.py` to:
   - Show current pipeline status (Running/Idle + current stage)
   - Display last 5 completed runs with status/duration

3. Modify `folder_monitor_service.py` to:
   - Log status to file that dashboard can read
   - Write run history to JSON file

4. Create utility scripts:
   - `start.bat` — Start services
   - `stop.bat` — Stop services

5. Result: Single `setup.bat` file + working dashboard that monitors pipeline

---

*Design Document v1.0 — Approved for Implementation*
