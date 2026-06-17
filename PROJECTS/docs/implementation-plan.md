# Implementation Plan: One-Click Pipeline Deployment

**Based on:** `docs/deployment-simple-design.md`  
**Created:** 2026-05-12  
**Status:** Ready for Implementation

---

## Overview

Create a one-click Windows setup that deploys the entire pipeline with HTTPS dashboard on port 443. Users double-click `setup.bat` and 2 minutes later the pipeline is running.

---

## Tasks

### Task 1: Create setup.bat (Main Deployment Script)
**Purpose:** Single entry point for entire deployment

**Steps:**
1. Create `setup.bat` in project root
2. Implement Python version check (3.8+)
3. Implement virtual environment creation
4. Implement pip dependency installation
5. Implement self-signed HTTPS certificate generation
6. Implement Windows Task Scheduler registration (call setup_task_scheduler.ps1)
7. Implement service startup (both folder_monitor_service.py and dashboard.py)
8. Implement browser launch (https://localhost)
9. Add error handling for each step
10. Add success/completion message

**Verification:**
- [ ] Script runs without errors on clean system
- [ ] Python check works (catches missing Python)
- [ ] Venv created successfully
- [ ] Dependencies installed (pip list shows required packages)
- [ ] HTTPS certificate generated (cert files exist)
- [ ] Task Scheduler task registered
- [ ] Services start without errors
- [ ] Browser opens to https://localhost
- [ ] User sees "Setup complete" message

**Output:** `setup.bat` ready to execute

---

### Task 2: Modify dashboard.py for HTTPS & Real Data
**Purpose:** Dashboard shows current status + last 5 runs with HTTPS

**Steps:**
1. Add SSL certificate support (pyopenssl)
2. Change port from 5000 to 443
3. Load self-signed certificate and key files
4. Modify /api/status endpoint to:
   - Return current pipeline status (Running/Idle)
   - Return current stage if running
   - Return last 5 runs from log analysis
5. Modify /api/runs endpoint to return only last 5 runs
6. Add run history persistence (JSON file)
7. Update HTML to show:
   - Current status + stage
   - Last 5 runs (timestamp, file, duration, status)
8. Test dashboard loads on https://localhost
9. Test data refreshes in real-time

**Verification:**
- [ ] Dashboard accessible at https://localhost
- [ ] Browser warning shown (expected for self-signed cert)
- [ ] Current status shows correctly
- [ ] Last 5 runs display
- [ ] Data updates every 5 seconds
- [ ] No errors in console

**Output:** `dashboard.py` with HTTPS + real monitoring

---

### Task 3: Modify folder_monitor_service.py for Status Tracking
**Purpose:** Service writes status/history for dashboard to read

**Steps:**
1. Add status file writing (JSON):
   - Current run status
   - Current stage
   - Start time
   - Duration so far
2. Add run history file (JSON):
   - Last 5 completed runs
   - Timestamp, file, duration, status
3. Update monitor when pipeline starts (write status)
4. Update monitor when pipeline completes (append to history)
5. Write current stage during execution
6. Clean up old run history (keep last 5 only)

**Verification:**
- [ ] Status file created during run
- [ ] Status file updated during pipeline execution
- [ ] Run history file created after completion
- [ ] History contains last 5 runs
- [ ] Dashboard reads files correctly

**Output:** `folder_monitor_service.py` with status tracking

---

### Task 4: Create start.bat & stop.bat
**Purpose:** Simple utility scripts for manual service control

**Steps for start.bat:**
1. Activate virtual environment
2. Start folder_monitor_service.py
3. Start dashboard.py
4. Print success message
5. Print dashboard URL (https://localhost)

**Steps for stop.bat:**
1. Kill Python processes
2. Print stopped message

**Verification:**
- [ ] start.bat starts services without errors
- [ ] stop.bat stops services cleanly
- [ ] Services can be restarted

**Output:** `start.bat` and `stop.bat` working

---

### Task 5: Create HTTPS Certificate Generation Script
**Purpose:** Auto-create self-signed certificate during setup

**Steps:**
1. Add certificate generation to setup.bat
2. Use Python/OpenSSL to generate self-signed cert
3. Create certificate files:
   - `ops/cert.pem` (certificate)
   - `ops/key.pem` (private key)
4. Valid for 365 days
5. Handle case where cert already exists (skip regeneration)

**Verification:**
- [ ] Cert files created in ops/ directory
- [ ] Certificate is valid
- [ ] Dashboard can load with cert
- [ ] Browser shows security warning (expected)

**Output:** Auto-generated HTTPS certificates

---

### Task 6: Update setup_task_scheduler.ps1
**Purpose:** Register with Windows to auto-start on boot

**Steps:**
1. Verify script exists (no changes needed if already working)
2. Test registration via setup.bat
3. Verify task shows in Task Scheduler
4. Verify task starts on system reboot

**Verification:**
- [ ] Task registers without errors
- [ ] Task appears in Task Scheduler
- [ ] Task runs at startup (test with scheduled time)
- [ ] Services start after boot

**Output:** Verified Task Scheduler registration

---

### Task 7: Test Complete Setup Flow
**Purpose:** End-to-end validation

**Steps:**
1. Clean test environment (remove venv, .env, certs)
2. Run setup.bat from scratch
3. Verify each step completes
4. Verify Python check works
5. Verify dependencies installed
6. Verify certificate created
7. Verify services start
8. Verify dashboard accessible
9. Place test Excel file in data/som-in/
10. Verify pipeline starts automatically
11. Verify dashboard shows status updates
12. Monitor until completion
13. Verify results file created

**Verification:**
- [ ] setup.bat completes without errors (<2 min)
- [ ] No manual prompts (fully automated)
- [ ] Dashboard shows current status
- [ ] Folder monitor detects new file (<10 sec)
- [ ] Pipeline runs automatically
- [ ] Dashboard updates in real-time
- [ ] Results file created
- [ ] Error handling works (test with intentional error)

**Output:** Fully tested, working one-click deployment

---

### Task 8: Create Quick Start Documentation
**Purpose:** Users know what to do

**Steps:**
1. Create `QUICKSTART.md` with:
   - "Double-click setup.bat"
   - "Wait 2 minutes"
   - "Open https://localhost (accept security warning)"
   - "Drop Excel files in data/som-in/"
   - "Check dashboard for status"
2. Create `TROUBLESHOOTING.md` with:
   - Common issues
   - How to check logs
   - How to restart services
   - Contact info

**Verification:**
- [ ] Documentation is clear and concise
- [ ] New users can follow it without help
- [ ] All major scenarios covered

**Output:** User documentation

---

## Implementation Order

1. ✓ Task 1: Create setup.bat
2. ✓ Task 2: Modify dashboard.py
3. ✓ Task 3: Modify folder_monitor_service.py
4. ✓ Task 4: Create start.bat & stop.bat
5. ✓ Task 5: HTTPS certificate generation
6. ✓ Task 6: Verify setup_task_scheduler.ps1
7. ✓ Task 7: Complete end-to-end test
8. ✓ Task 8: Documentation

---

## Success Criteria (Complete when ALL are met)

- ✅ User can deploy by double-clicking setup.bat
- ✅ Setup completes in <2 minutes
- ✅ No prompts during setup (fully automated)
- ✅ No config files to edit (automatic)
- ✅ Dashboard accessible at https://localhost
- ✅ Dashboard shows current status + last 5 runs
- ✅ Folder monitor auto-detects new Excel files
- ✅ Pipeline runs automatically on file detection
- ✅ Services auto-start on server reboot
- ✅ All error cases handled gracefully
- ✅ Documentation clear and complete

---

## Dependencies

**Python Packages (must be in requirements.txt):**
- watchdog (folder monitoring)
- flask (dashboard)
- flask-cors (CORS support)
- pyopenssl (HTTPS support)

**Windows:**
- Python 3.8+ (pre-installed, verified by setup.bat)
- PowerShell (built-in)
- Task Scheduler (built-in)

---

## Known Constraints

- Port 443 must be available (will fail with error if not)
- Requires elevated privileges to bind port 443 (will prompt)
- Certificate is self-signed (browser warning expected)
- Python must be in PATH

---

## Risk Assessment

**Low Risk:**
- setup.bat script (simple batch commands)
- Dashboard modifications (isolated changes)
- Cert generation (Python OpenSSL standard)

**Medium Risk:**
- Task Scheduler registration (admin privileges required)
- Port 443 binding (requires elevation)
- Service startup timing (may need delays)

**Mitigation:**
- Test each step individually
- Clear error messages for each failure point
- Detailed logs for troubleshooting

---

*Implementation Plan v1.0 — Ready for execution*
