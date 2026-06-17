# Crawler Pipeline Deployment Guide

**Version**: 1.0  
**Last Updated**: May 14, 2026  
**Status**: Production Ready

## Overview

This document explains how to deploy updates to the Crawler PDF processing pipeline. The system includes two critical fixes ready to ship:

1. **CrossRef Module Import Fix** - Fixes ModuleNotFoundError during Stage 3 (verified working)
2. **7-Day Smart Detection** - Skips suppliers scraped < 7 days ago, reducing runtime from ~2 hours to ~10 minutes on subsequent runs

---

## Quick Start

### Initial Setup (One-Time)

1. **Clone or pull the repository** to your local machine:
   ```bash
   git clone https://github.com/castrokren/Multi-module.git
   cd Multi-module
   ```

2. **Verify the latest code is in place**:
   ```bash
   python PROJECTS/src/services/pipeline.py --dry-run
   ```
   You should see: `Validation passed - all paths exist` (or similar success message)

### Regular Updates (Automatic)

The deployment system runs automatically via Windows Task Scheduler:

1. **Automatic check runs daily** (configured at 6:00 AM)
2. **Checks GitHub** for new commits on `origin/main`
3. **Downloads and deploys** if updates are available
4. **Creates timestamped backup** before deploying
5. **Validates critical files** after deployment
6. **Logs all activity** to `PROJECTS/logs/deployment.log`

### Manual Update (If Needed)

If you need to manually trigger an update:

```bash
cd C:\Projects\Crawler\PROJECTS
update.bat
```

This will:
- Check for new commits
- Backup current code (if updates found)
- Pull latest from GitHub
- Validate the deployment
- Log the result

---

## How It Works

### Architecture

```
┌─────────────────────────────────────┐
│   Windows Task Scheduler (Daily)    │
└─────────┬───────────────────────────┘
          │
          v
┌─────────────────────────────────────┐
│   update.bat                        │
│  (checks GitHub & deploys)          │
└─────────┬───────────────────────────┘
          │
          ├─> git fetch origin main
          ├─> Compare commit hashes
          ├─> Backup (if updates found)
          ├─> git pull origin main
          ├─> Validate files
          └─> Log results
```

### Files Involved

| File | Purpose | Type |
|------|---------|------|
| `update.bat` | Auto-updater script | Batch |
| `logs/deployment.log` | Update activity log | Log |
| `logs/.last_deployed_hash` | Tracks current version | State |
| `backups/backup_*.zip` | Timestamped backups | Archive |

### Configuration

**Quick Settings** (in `update.bat`):
```batch
set REPO_DIR=C:\Projects\Crawler
set BACKUP_DIR=C:\Projects\Crawler\backups
set LOG_DIR=C:\Projects\Crawler\logs
```

**Task Scheduler Schedule**:
- **Time**: 6:00 AM (configurable)
- **Frequency**: Daily
- **Action**: Runs `update.bat`
- **Logs**: `PROJECTS/logs/deployment.log`

---

## Deployed Features

### 1. CrossRef Module Import Fix

**Status**: Verified working on remote machine (2026-05-14)

**Problem**: `ModuleNotFoundError` when loading crossref_utils via importlib during Stage 3

**Solution**: Added sys.path setup in `crossref_standalone_fast.py` (lines 8-15)

**Result**: Stage 3 now completes successfully

**Files**:
- `PROJECTS/src/services/cross-reference/crossref_standalone_fast.py`

---

### 2. 7-Day Smart Detection for Scraper

**Status**: 16 unit tests passing, production-ready

**Feature**: Skip suppliers that were scraped less than 7 days ago

**Implementation**:
- State file: `.scraper_state.json` (stores last-scrape timestamp per supplier)
- Configuration: `pipeline_config.json`
  - `skip_recent_sites: true` (enable/disable)
  - `days_before_rescrape: 7` (configurable threshold)

**Impact**: Dramatic runtime reduction on subsequent runs
- First run: ~2 hours (full scrape)
- Subsequent runs: ~10 minutes (if skip_recent_sites enabled)

**Test Results**:
```
✓ test_scraper_smart_detection.py (16 tests passing)
  - Tests loading suppliers from Excel
  - Tests state file creation/loading
  - Tests smart detection logic
  - Tests recent site skipping
```

**Files Modified**:
- `PROJECTS/src/services/scraper-full/scraper_engine.py`
- `PROJECTS/src/services/pipeline.py`
- `PROJECTS/src/services/pipeline_config.json`

---

## Running the Pipeline After Update

Once the update is deployed, the pipeline runs automatically or can be run manually:

### Automatic (Windows Task Scheduler)

Configure a task to run daily:
```batch
python C:\Projects\Crawler\PROJECTS\src\services\pipeline.py
```

### Manual Execution

```bash
cd C:\Projects\Crawler\PROJECTS\src\services
python pipeline.py
```

With options:
```bash
python pipeline.py --skip-scraper           # Skip Stage 1 (use existing PDFs)
python pipeline.py --only-crossref          # Run Stage 3 only (test)
python pipeline.py --dry-run                # Validate without running
```

### Expected Runtime (with 7-day smart detection enabled)

| Scenario | Duration | Notes |
|----------|----------|-------|
| **First Run** | ~2 hours | Full scrape, classify, cross-ref |
| **Subsequent** (7+ days elapsed) | ~2 hours | Re-scrape all suppliers |
| **Subsequent** (< 7 days) | ~10 minutes | Skip scraper, just classify + cross-ref |

---

## Troubleshooting

### Issue: Update script fails with "git not found"

**Solution**: Ensure Git for Windows is installed and in your PATH
```bash
git --version
```

### Issue: Permission denied when creating backup

**Solution**: Check that `C:\Projects\Crawler\backups` is writable
```bash
icacls C:\Projects\Crawler\backups /grant Everyone:(F)
```

### Issue: Pipeline still runs old code after update

**Solution**: 
1. Verify update was successful:
   ```bash
   cat C:\Projects\Crawler\logs\deployment.log
   ```
2. Check that `scraper_engine.py` contains `skip_recent_sites`:
   ```bash
   findstr /C:"skip_recent_sites" C:\Projects\Crawler\PROJECTS\src\services\scraper-full\scraper_engine.py
   ```
3. Restart any running Python processes (pipeline uses new code on next invocation)

### Issue: Validation fails - critical files missing

**Solution**:
1. Check log for details:
   ```bash
   tail C:\Projects\Crawler\logs\deployment.log
   ```
2. Verify repository is in correct state:
   ```bash
   cd C:\Projects\Crawler
   git status
   git log --oneline -5
   ```
3. If corrupted, restore from backup:
   ```bash
   cd C:\Projects\Crawler\backups
   Expand-Archive backup_<timestamp>.zip -DestinationPath ..\PROJECTS -Force
   ```

---

## Backup & Recovery

### Automatic Backups

- Created before each deployment
- Stored in: `C:\Projects\Crawler\backups\backup_<timestamp>.zip`
- Retention: Last 5 backups (older ones auto-deleted)
- Size: ~50-100 MB each

### Manual Backup

```bash
powershell -Command "Compress-Archive -Path 'C:\Projects\Crawler\PROJECTS' -DestinationPath 'C:\Projects\Crawler\backups\backup_manual.zip' -Force"
```

### Restore from Backup

```bash
# Restore specific backup
Expand-Archive C:\Projects\Crawler\backups\backup_<timestamp>.zip -DestinationPath C:\Projects\Crawler\PROJECTS -Force

# OR: Restore latest
Expand-Archive (Get-ChildItem C:\Projects\Crawler\backups -Name | Select -First 1) -DestinationPath C:\Projects\Crawler\PROJECTS -Force
```

---

## Scheduling Updates with Task Scheduler

To set up automatic daily updates:

### Option 1: Via PowerShell (Recommended)

```powershell
# Run as Administrator
$taskName = "Crawler-Pipeline-Update"
$action = New-ScheduledTaskAction -Execute "C:\Projects\Crawler\PROJECTS\update.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force

# Verify
Get-ScheduledTask -TaskName $taskName | Select State, NextRunTime
```

### Option 2: Via GUI

1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task → Name: "Crawler-Pipeline-Update"
3. Trigger → Daily → Time: 6:00 AM
4. Action → Start a program → Program: `C:\Projects\Crawler\PROJECTS\update.bat`
5. Settings → Check "Run with highest privileges"
6. Finish

---

## Monitoring Deployments

### Check Latest Deployment Status

```bash
tail -f C:\Projects\Crawler\logs\deployment.log
```

### Deployment History

```bash
ls -la C:\Projects\Crawler\logs\backup_*.zip
```

### Current Version

```bash
git -C C:\Projects\Crawler log --oneline -1
```

---

## Development & Testing

### Test the Updater (Dry Run)

Modify `update.bat` to use `--dry-run` for testing:

```batch
REM In update.bat, change:
git pull origin main --dry-run
```

### Validate Critical Files

```bash
python C:\Projects\Crawler\PROJECTS\src\services\pipeline.py --dry-run
```

### Run Unit Tests

```bash
cd C:\Projects\Crawler\PROJECTS
pytest src/services/scraper-full/tests/unit/test_scraper_smart_detection.py -v
```

---

## FAQ

**Q: How often does the updater check for new commits?**  
A: Daily at 6:00 AM (configurable in Task Scheduler)

**Q: What if git credentials fail?**  
A: The script logs errors to `deployment.log`. Ensure Git credentials are cached or use SSH keys. See [GitHub SSH Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

**Q: Can I disable the 7-day smart detection?**  
A: Yes, in `pipeline_config.json`:
   ```json
   "scraper": {
     "skip_recent_sites": false,
     "days_before_rescrape": 7
   }
   ```

**Q: What's the impact of disabling smart detection?**  
A: Pipeline will take ~2 hours per run (full scrape every time) instead of ~10 minutes on subsequent runs.

**Q: How do I verify the smart detection is working?**  
A: Check for `.scraper_state.json` in your output directory after the first scraper run.

**Q: Can I rollback to a previous version?**  
A: Yes, see "Restore from Backup" section above.

---

## Support

For issues or questions:
- Check `PROJECTS/logs/deployment.log` for error details
- Review this guide's Troubleshooting section
- Contact: castrokren@gmail.com

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-14 | 1.0 | Initial deployment guide with 7-day smart detection & cross-ref fix |

