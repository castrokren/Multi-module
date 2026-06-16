# Integration Testing Guide - v2_monitor

**Date:** 2026-06-16  
**Status:** Ready for Testing  
**Components:** 5 phases complete, consolidated into 1 unified monitor

---

## Test Environment Setup

### Prerequisites
```bash
# Ensure you're in the classify directory
cd C:\Projects\Crawler\PROJECTS\src\services\classify

# Create test directories
mkdir -p C:\Data\Crawler\input
mkdir -p C:\Data\Crawler\output

# Copy a sample Excel file for testing (if available)
# cp sample.xlsx C:\Data\Crawler\input\
```

### Verify Files
```bash
# Verify v2_monitor directory structure
ls -la v2_monitor/
# Expected:
# - __init__.py
# - monitor.py
# - run_monitor_service.py
# - run_monitor_gui.py
# - Updated_Monitor_UI.py
# - tests/test_monitor.py
# - README.md
```

---

## Test Plan

### Test 1: Unit Tests (monitor.py)

**Purpose:** Verify file monitoring logic and validation

**Steps:**
```bash
# Install pytest if needed
pip install pytest

# Run unit tests
pytest v2_monitor/tests/test_monitor.py -v

# Expected: All 25 tests pass
# Output should show:
# test_process_xlsx_file PASSED
# test_process_xls_file PASSED
# test_skip_temp_excel_file PASSED
# ... (22 more tests)
# ======================== 25 passed in X.XXs ========================
```

**Success Criteria:**
- ✅ All 25 tests pass
- ✅ No import errors
- ✅ Coverage includes: validation, initialization, processing, shutdown

---

### Test 2: Direct Execution (run_monitor_service.py)

**Purpose:** Test monitor in direct mode (for development/testing)

**Steps:**
```bash
# Terminal 1: Start monitor
cd C:\Projects\Crawler\PROJECTS\src\services\classify
python -m v2_monitor.run_monitor_service

# Expected output:
# ======================================================================
# CRAWLER FOLDER MONITOR v2.0
# ======================================================================
#
# Configuration:
#   Watch directory:  C:\Data\Crawler\input
#   Output directory: C:\Data\Crawler\output
#   Learning mode:    True
#
# Starting monitor... (press Ctrl+C to stop)
# ============================================================
# Monitor started
#   Watch:  C:\Data\Crawler\input
#   Output: C:\Data\Crawler\output
# ============================================================
# ✓ Processor initialized
```

**While running:**
```bash
# Terminal 2: Add a test file
copy sample.xlsx C:\Data\Crawler\input\test_sample.xlsx

# Expected in Terminal 1:
# Processing: test_sample.xlsx
# ✓ Success: test_sample.xlsx
```

**Verify:**
- ✅ Monitor starts without errors
- ✅ Monitor detects file creation
- ✅ Processor initializes
- ✅ File is processed successfully
- ✅ Output file created in C:\Data\Crawler\output
- ✅ Logs created in C:\Data\Crawler\logs\

**Cleanup:**
```bash
# Press Ctrl+C to stop monitor
# Monitor should shut down gracefully with message:
# Monitor stopped
```

---

### Test 3: GUI Launch (run_monitor_gui.py)

**Purpose:** Verify GUI starts and configuration works

**Steps:**
```bash
# Launch GUI
python -m v2_monitor.run_monitor_gui
```

**Expected:**
- ✅ Tkinter window opens titled "Folder Monitor Service Manager"
- ✅ All UI elements visible:
  - Service Configuration section
  - Monitor Configuration section
  - Adaptive Learning Settings section
  - Test Configuration button
  - Action buttons (Install, Update, Remove, Start, Stop, Restart, Debug)
  - Config buttons (Save, Load)
  - Log display area

**Configuration Test:**
1. Set watch directory: `C:\Data\Crawler\input`
2. Set output directory: `C:\Data\Crawler\output`
3. Set keyword files (or use defaults)
4. Click "Save Config" button
5. Verify: Log shows "Configuration saved successfully"
6. Click "Load Config" button
7. Verify: Directories are restored from saved config

**Test Configuration Button:**
1. Ensure test Excel file exists in watch directory
2. Click "Test Configuration" button
3. Verify: Log shows processing output
4. Verify: Success message appears

**Verify:**
- ✅ GUI window launches
- ✅ All UI elements functional
- ✅ Config save/load works
- ✅ Test configuration processes files
- ✅ Log displays messages with timestamps

**Cleanup:**
- Close GUI window

---

### Test 4: Windows Service (run_monitor_service.py)

**Purpose:** Verify Windows Service installation and operation

**Prerequisites:**
- Run Command Prompt as Administrator
- Ensure `run_monitor_service.py` is in correct path

**Steps:**

#### 4.1 Install Service
```cmd
cd C:\Projects\Crawler\PROJECTS\src\services\classify

python -m v2_monitor.run_monitor_service install

# Expected output:
# Installing service CrawlerMonitor
# Service installed successfully
```

**Verify:**
- ✅ Service installed without errors
- ✅ Can check in Services (services.msc): "Crawler Folder Monitor"

#### 4.2 Start Service
```cmd
net start CrawlerMonitor

# Or via Services.msc: right-click → Start

# Expected:
# The Crawler Folder Monitor service is starting.
# The Crawler Folder Monitor service was started successfully.
```

**While running (File Test):**
```cmd
# In another terminal, copy test file
copy sample.xlsx C:\Data\Crawler\input\service_test.xlsx

# Wait 2-3 seconds for processing
# Check output directory
dir C:\Data\Crawler\output\

# Expected: service_test_labeled.xlsx should be present
```

**Verify:**
- ✅ Service starts without errors
- ✅ Service appears "Running" in Services
- ✅ Files are processed while service runs
- ✅ Output files created
- ✅ Logs created with service messages

#### 4.3 Stop Service
```cmd
net stop CrawlerMonitor

# Or via Services.msc: right-click → Stop

# Expected:
# The Crawler Folder Monitor service is stopping.
# The Crawler Folder Monitor service was stopped successfully.
```

**Verify:**
- ✅ Service stops gracefully
- ✅ Service appears "Stopped" in Services

#### 4.4 Restart Service
```cmd
net stop CrawlerMonitor
net start CrawlerMonitor

# Or in Services.msc: right-click → Restart
```

**Verify:**
- ✅ Service restarts successfully
- ✅ Resumes monitoring immediately

#### 4.5 Remove Service
```cmd
python -m v2_monitor.run_monitor_service remove

# Expected:
# Removing service CrawlerMonitor
# Service removed successfully
```

**Verify:**
- ✅ Service removed without errors
- ✅ Service no longer visible in Services

---

### Test 5: Environment Variables (run_monitor_service.py)

**Purpose:** Verify configuration via environment variables

**Steps:**
```bash
# Set environment variables
set WATCH_DIRECTORY=C:\Custom\Input
set OUTPUT_DIRECTORY=C:\Custom\Output
set LEARNING_MODE=false
set MIN_OCCURRENCES=10

# Run monitor with env vars
python -m v2_monitor.run_monitor_service

# Expected output should show custom paths:
# Configuration:
#   Watch directory:  C:\Custom\Input
#   Output directory: C:\Custom\Output
#   Learning mode:    False
```

**Verify:**
- ✅ Environment variables override config.py
- ✅ Custom paths used correctly

---

## Test Execution Checklist

### Phase Completion
- [ ] Test 1: Unit Tests — All 25 tests pass
- [ ] Test 2: Direct Execution — Monitor works in foreground
- [ ] Test 3: GUI Launch — UI functional and responsive
- [ ] Test 4: Windows Service — Install/Start/Stop/Restart/Remove work
- [ ] Test 5: Environment Variables — Custom paths respected

### File Operations
- [ ] Files detected in watch directory
- [ ] Files processed successfully
- [ ] Output files created in output directory
- [ ] Processed files marked with _labeled suffix
- [ ] Logs created in logs directory

### Error Handling
- [ ] Missing watch directory shows clear error
- [ ] Invalid Excel file handled gracefully
- [ ] Processor initialization errors caught
- [ ] Service shutdown is clean

---

## Logging Verification

**Check logs created:**
```bash
# After running monitor, verify logs exist
dir C:\Data\Crawler\logs\

# Expected:
# monitor_20260616.log (or current date)

# View recent logs
type C:\Data\Crawler\logs\monitor_*.log | tail -20
```

**Expected log entries:**
```
2026-06-16 10:30:45 | INFO     | ============================================================
2026-06-16 10:30:45 | INFO     | Monitor started
2026-06-16 10:30:45 | INFO     |   Watch:  C:\Data\Crawler\input
2026-06-16 10:30:45 | INFO     |   Output: C:\Data\Crawler\output
2026-06-16 10:30:47 | INFO     | ✓ Processor initialized
2026-06-16 10:31:02 | INFO     | Processing: test_file.xlsx
2026-06-16 10:31:15 | INFO     | ✓ Success: test_file.xlsx
```

---

## Success Criteria Summary

| Component | Test | Status | Notes |
|-----------|------|--------|-------|
| Unit Tests | 25 tests pass | ✅ | All validation/processing/shutdown tests |
| Direct Execution | Monitor runs, processes files | ✅ | Blocks until Ctrl+C |
| GUI | Launches, configures, tests | ✅ | All UI elements functional |
| Service | Install, start, stop, restart | ✅ | Runs as system service |
| Environment Variables | Custom paths respected | ✅ | Overrides config.py |
| File Detection | Watches directory, processes files | ✅ | Detects .xls/.xlsx only |
| Logging | Creates timestamped logs | ✅ | Logs to file + console |
| Error Handling | Graceful failures | ✅ | No crashes, clear errors |

---

## Rollback Plan

If tests fail:

1. **Unit test failure:**
   - Check imports (monitor.py depends on watchdog, adaptive_excel_processor)
   - Verify pytest installed: `pip install pytest`
   - Run individual test: `pytest v2_monitor/tests/test_monitor.py::TestFileMonitorInitialization -v`

2. **Direct execution failure:**
   - Check config.py exists and is readable
   - Verify directory paths are writable
   - Check logs directory created: `dir C:\Data\Crawler\logs\`

3. **GUI failure:**
   - Check tkinter available: `python -m tkinter` (should open window)
   - Verify Updated_Monitor_UI.py imports correctly
   - Check adaptive_excel_processor imports

4. **Service failure:**
   - Check pywin32 installed: `pip list | grep pywin32`
   - Verify service removal: `sc query CrawlerMonitor` (should fail)
   - Check Event Viewer for service errors

5. **General failures:**
   - Read logs in C:\Data\Crawler\logs\
   - Check file permissions on directories
   - Verify Python version (3.8+)

---

## Test Report Template

Once testing is complete, fill in:

```
INTEGRATION TEST REPORT - v2_monitor
====================================
Date: 2026-06-16
Tester: [Your Name]

Test 1 - Unit Tests:        [PASS / FAIL]
Test 2 - Direct Execution:  [PASS / FAIL]
Test 3 - GUI:               [PASS / FAIL]
Test 4 - Windows Service:   [PASS / FAIL]
Test 5 - Env Variables:     [PASS / FAIL]

Overall Status:             [PASS / FAIL]

Issues Found:
- [List any issues]

Notes:
- [Any additional observations]
```

---

## Next Steps After Testing

If all tests pass:
1. ✅ v2_monitor is production-ready
2. ✅ Can be deployed via GUI, service, or direct execution
3. ✅ Old monitors in archive can be removed
4. ✅ Update documentation to point to v2_monitor

If tests fail:
1. ❌ Review error logs
2. ❌ Fix issues and retest specific components
3. ❌ Use DEBUG mode for verbose output
4. ❌ Consult README.md for troubleshooting

---

**Ready to test?** Follow tests 1-5 in order. Report any failures.
