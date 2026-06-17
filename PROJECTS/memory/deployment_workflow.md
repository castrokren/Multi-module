---
name: One-Click Deployment Workflow
description: Complete setup for Crawler Pipeline deployment on Windows servers with GitHub integration
type: project
---

## Architecture

The deployment consists of three main scripts that work together:

### 1. **setup.bat** (Main installation script)
Located in: `PROJECTS/setup.bat`

Runs 6 sequential steps:
1. Check Python 3.8+ installed
2. Create Python virtual environment
3. Install dependencies (calls `ops/check_dependencies.py`)
4. Create required directories + copy source files
5. Generate HTTPS certificate (self-signed)
6. Start services (monitor + dashboard)

**Key behaviors:**
- Creates venv in `PROJECTS/` directory
- Copies src/ files from PROJECTS to parent for deployment compatibility
- Shows service windows (not backgrounded) so errors are visible
- Automatically opens dashboard at https://localhost on completion

### 2. **deploy-from-github.bat** (GitHub deployment wrapper)
Located in: `PROJECTS/deploy-from-github.bat`

Runs on user's Desktop, clones repo and runs setup:
1. Clone Multi-module from GitHub to Desktop
2. Checkout `claude/pedantic-hofstadter-313610` branch
3. CD into PROJECTS folder
4. Run setup.bat

**Critical fix (2026-05-12):** Must `cd PROJECTS` before running setup.bat because repo has structure:
```
Multi-module/
  ├── PROJECTS/
  │   ├── setup.bat
  │   ├── ops/
  │   ├── src/
  │   └── data/
  └── <other repo files>
```

### 3. **start.bat** (Service restart)
Located in: `PROJECTS/start.bat`

Restarts monitor and dashboard services manually. Opens windows (not backgrounded) so errors are visible.

## Key Learnings

### Batch File Syntax Issues
- `else` statements in multi-line blocks with parentheses cause "else was unexpected at this time" error
- Solution: Use `goto` labels instead of nested if/else with parentheses
- Parentheses in echo statements must be escaped: `echo ^(text^)`

### Path Resolution in Python
When deploying from GitHub:
- Repository structure has PROJECTS as subfolder: `Multi-module/PROJECTS/src/...`
- setup.bat copies src/ from PROJECTS to parent so monitor finds pipeline at `../src/services/pipeline.py`
- folder_monitor_service.py has fallback logic to detect PROJECTS subfolder structure

### Virtual Environment Isolation
- venv is completely isolated from system Python
- Must activate venv before running Python scripts
- All pip packages must be installed into venv, not global Python
- Deploy scripts must account for this isolation

### Windows PowerShell vs Command Prompt
- PowerShell requires `.\script.bat` to run scripts in current directory
- Command Prompt allows just `script.bat`
- Users on remote PC typically using PowerShell, so documentation should reflect this

### GitHub Branch Strategy
- Single deployment branch: `claude/pedantic-hofstadter-313610`
- All deployment files must be committed and pushed (setup.bat, ops/, src/, start.bat, stop.bat)
- Use force push when needed: `git push -f origin HEAD:branch-name`

## Deployment Checklist

Before pushing to GitHub:
- [ ] All .bat files committed
- [ ] ops/check_dependencies.py committed
- [ ] ops/generate_cert.py committed
- [ ] ops/folder_monitor_service.py committed
- [ ] All src/ files committed
- [ ] Tested locally with setup.bat
- [ ] Tested GitHub deployment with deploy-from-github.bat
- [ ] Verified monitor detects files
- [ ] Verified dashboard accessible at https://localhost

## File Detection and Pipeline Execution

**Monitor Service (folder_monitor_service.py):**
- Polls `data/som-in/` every 5 seconds for new .xlsx files
- Uses polling instead of watchdog (more reliable on Windows)
- Triggers `src/services/pipeline.py` when new file detected
- Writes status to `src/services/cross-reference/results/status.json`
- Maintains last 5 runs in `run_history.json`

**Expected Pipeline Failures:**
- Missing `data/masterlist/updated_master_list.xlsx` (supplier master list)
- Missing `data/som-in-labeled/` (labeled classification data)
- Missing `data/scraped-pdfs/` (PDF directory from scraper)

These are normal on fresh deployment — user must provide input data files.

## Dashboard

**URL:** https://localhost (self-signed certificate)

**Features:**
- Real-time status (Idle / Running)
- Current stage and progress
- Last 5 completed runs with file names, duration, status
- Auto-refreshes every 5 seconds

**Implementation:**
- Flask app at `ops/dashboard.py`
- Reads from status.json and run_history.json
- Port 443 for corporate network compatibility

---

**Last Updated:** 2026-05-12  
**Status:** Production-ready, tested end-to-end
