# Monitor Consolidation Roadmap

**Status:** Planning Phase  
**Priority:** 🔴 CRITICAL (code deduplication)  
**Estimated Effort:** 3-4 hours  
**Risk Level:** LOW (changes are isolated to classify module, well-tested endpoints)

---

## Executive Summary

Consolidate **4 redundant file monitoring implementations** into a single unified architecture with 3 clean entry points:
- GUI mode (for configuration & testing)
- Service mode (for automated background operation)
- CLI mode (for manual/pipeline usage)

**Current Pain Points:**
- 4 separate monitor variations → maintenance nightmare
- Duplicated watchdog logic
- Inconsistent configuration handling
- Difficult to extend or fix bugs (must update all 4 files)

**After Consolidation:**
- Single source of truth for file monitoring
- ~40% less code
- Easier to test and maintain
- Clear separation of concerns (UI vs. monitoring vs. service)

---

## Current State Analysis

### Files & Responsibilities

| File | Lines | Type | Purpose | Status |
|------|-------|------|---------|--------|
| `Updated_Monitor_UI.py` | 795 | GUI | Tkinter service manager, config UI, testing | ✅ PRIMARY |
| `simple_W_service.py` | 126 | Service | Windows service with watchdog + AdaptiveExcelProcessor | ⚠️ DUPLICATE |
| `simple_monitor.py` | 123 | CLI | Simplified watchdog monitor | ⚠️ DUPLICATE |
| `archive/service_script.py` | ~90 | Service | Old subprocess-based service | 🔴 DEPRECATED |

### Code Duplication Analysis

**Watchdog Logic (repeated 3x):**
```python
# In simple_W_service.py, simple_monitor.py, and implicitly in Updated_Monitor_UI.py
class ExcelFileHandler(FileSystemEventHandler):
    def on_created(self, event): ...
    def on_modified(self, event): ...
    def _process_file(self, file_path, event_type): ...
```

**AdaptiveExcelProcessor Integration (repeated 2x):**
```python
# In simple_W_service.py and simple_monitor.py
processor = AdaptiveExcelProcessor(
    hw_keywords_file=...,
    sw_keywords_file=...,
    output_dir=...,
    ...
)
success = processor.process_file(file_path)
```

**File Validation (repeated 3x):**
```python
def should_process(path_str):
    if stem.startswith('~$') or stem.endswith('_labeled'):
        return False
    return ext.lower() in ['.xls', '.xlsx']
```

---

## Proposed Architecture

### Module Structure (After Consolidation)

```
src/services/classify/
├── __init__.py                      # NEW: exports main entry points
├── monitor.py                       # NEW: core file monitoring engine
├── Updated_Monitor_UI.py            # REFACTORED: GUI only (remove watchdog logic)
├── run_monitor_gui.py               # NEW: launcher for GUI mode
├── run_monitor_service.py           # NEW: launcher for Windows service mode
├── adaptive_excel_processor.py       # UNCHANGED: primary processor
├── config.py                        # UNCHANGED: configuration system
├── archive/
│   ├── simple_monitor.py            # MOVED HERE
│   ├── simple_W_service.py          # MOVED HERE
│   ├── service_script.py            # Already here
│   └── [other legacy files]
└── tests/
    ├── test_file_monitor.py         # NEW: unit tests for monitor.py
    └── test_service_integration.py   # NEW: integration tests
```

---

## Detailed Implementation Plan

### Phase 1: Create Core Monitoring Module

**File:** `monitor.py` (new)  
**Purpose:** Single reusable watchdog engine

```python
# monitor.py
class FileMonitor:
    """
    Unified file monitoring engine using watchdog.
    Handles Excel file detection, validation, and processing.
    """
    
    def __init__(self, watch_dir, processor_config):
        """
        Args:
            watch_dir: Directory to monitor
            processor_config: Dict with processor initialization params
        """
        self.watch_dir = watch_dir
        self.processor_config = processor_config
        self.processor = None  # Lazy-loaded
        self.observer = None
    
    @staticmethod
    def should_process(file_path):
        """Check if file should be processed."""
        # Unified validation logic
    
    def _initialize_processor(self):
        """Lazy-load AdaptiveExcelProcessor."""
        # Create processor once, reuse for all files
    
    def _process_file(self, file_path, event_type):
        """
        Process a single Excel file.
        Handles all logging and error management.
        """
    
    def start(self):
        """Start monitoring."""
        # Set up watchdog Observer
    
    def stop(self):
        """Stop monitoring gracefully."""
        # Shutdown observer
    
    def is_running(self):
        """Check if monitoring is active."""
```

**Key Extraction Points:**
- Lines 27-46 from `simple_W_service.py` → `FileMonitor.__init__` + `_process_file`
- Lines 24-31 from `simple_monitor.py` → `FileMonitor.should_process`
- Watchdog setup logic → `FileMonitor.start/stop`

**Testing Strategy:**
- Unit test: `FileMonitor.should_process()` with various file names
- Unit test: `FileMonitor` initialization with mock processor
- Integration test: `FileMonitor` with real directory and processor

---

### Phase 2: Refactor Updated_Monitor_UI.py

**Changes:**
1. Remove all watchdog/service implementation code
2. Remove `ExcelFileHandler` class (moved to monitor.py)
3. Update `_test_config()` to use `FileMonitor` for testing
4. Simplify service command execution (no longer needs watchdog setup)
5. Keep all UI, config, and control logic

**Before:**
```python
# Updated_Monitor_UI.py - OLD
class ExcelFileHandler(FileSystemEventHandler):
    def on_created(self, event): ...

class ServiceGUI(tk.Tk):
    def _test_config(self):
        # 50+ lines: sets up observer, starts monitoring
```

**After:**
```python
# Updated_Monitor_UI.py - NEW (simplified)
class ServiceGUI(tk.Tk):
    def _test_config(self):
        from monitor import FileMonitor
        
        # Use FileMonitor for testing
        config = {...}
        monitor = FileMonitor(watch_dir, config)
        # Process test file
        monitor._process_file(test_file, "test")
        # No need to start full observer for testing
```

**Lines Removed:** ~150 lines (20% reduction)  
**Lines Added:** ~10 lines (imports + refactored test logic)

---

### Phase 3: Create Service Launcher

**File:** `run_monitor_service.py` (new)  
**Purpose:** Windows service entry point

```python
#!/usr/bin/env python3
"""
Windows service launcher for folder monitoring.
Replaces simple_W_service.py and service_script.py.
"""

import sys
import logging
import win32serviceutil
from monitor import FileMonitor
from config import config

class FolderMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = config.get("service_name", "FolderMonitor")
    _svc_display_name_ = "Excel Folder Monitor Service"
    
    def __init__(self, args):
        super().__init__(args)
        self.monitor = None
    
    def SvcDoRun(self):
        """Start the service and monitor files."""
        processor_config = {
            'hw_keywords_file': config.hardware_keywords_file,
            'sw_keywords_file': config.software_keywords_file,
            'ni_keywords_file': config.non_instrument_keywords_file,
            'output_dir': config.output_directory,
            'learning_mode': config.get('learning_mode', True),
        }
        
        self.monitor = FileMonitor(
            watch_dir=config.watch_directory,
            processor_config=processor_config
        )
        self.monitor.start()
        
        # Wait for stop signal
        while self.monitor.is_running():
            time.sleep(1)
    
    def SvcStop(self):
        """Stop the service."""
        if self.monitor:
            self.monitor.stop()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FolderMonitorService)
```

**Replaces:** simple_W_service.py + service_script.py  
**Lines:** ~60 (vs. 126+90 = 216 in originals)  
**Benefit:** 70% less code, clearer intent

---

### Phase 4: Create GUI Launcher

**File:** `run_monitor_gui.py` (new)  
**Purpose:** Clean entry point for GUI

```python
#!/usr/bin/env python3
"""
GUI launcher for folder monitor configuration.
"""

import sys
from Updated_Monitor_UI import ServiceGUI

if __name__ == '__main__':
    app = ServiceGUI()
    app.mainloop()
```

**Purpose:**
- Separates GUI startup from implementation
- Makes it easy to find the entry point
- Allows future headless operation without GUI dependencies

**Lines:** ~8

---

### Phase 5: Archive Duplicates

**Move to `archive/`:**
1. `simple_monitor.py` → `archive/simple_monitor.py`
2. `simple_W_service.py` → `archive/simple_W_service.py`
3. Update `.gitignore` to exclude archive/

**Keep for reference only** (mark with deprecation header)

---

## Implementation Sequence

### Step 1: Create & Test Core Monitor (1 hour)

```bash
# 1. Create monitor.py with FileMonitor class
# 2. Extract watchdog logic from simple_W_service.py
# 3. Add unit tests
# 4. Run: pytest tests/test_file_monitor.py
```

**Deliverable:** `monitor.py` with 100% test coverage on `should_process()` and initialization

### Step 2: Refactor Updated_Monitor_UI.py (1 hour)

```bash
# 1. Import FileMonitor
# 2. Remove ExcelFileHandler class
# 3. Update _test_config() to use FileMonitor
# 4. Test in GUI: "Test Configuration" button
```

**Deliverable:** Updated_Monitor_UI.py using FileMonitor, all UI tests pass

### Step 3: Create Service Launcher (30 min)

```bash
# 1. Create run_monitor_service.py
# 2. Copy minimal service code from simple_W_service.py
# 3. Use FileMonitor + config system
# 4. Test: python run_monitor_service.py install
```

**Deliverable:** run_monitor_service.py ready for Windows service install

### Step 4: Create GUI Launcher (15 min)

```bash
# 1. Create run_monitor_gui.py
# 2. Test: python run_monitor_gui.py
```

**Deliverable:** run_monitor_gui.py launches GUI correctly

### Step 5: Move Duplicates to Archive (15 min)

```bash
# 1. Move simple_monitor.py, simple_W_service.py to archive/
# 2. Add deprecation headers
# 3. Update .gitignore
```

**Deliverable:** Clean src/services/classify/ directory

### Step 6: Integration Testing (30 min)

```bash
# 1. Test GUI mode: load config, test file, view report
# 2. Test service mode: install, start, monitor file, stop
# 3. Test all three processors (adaptive + original)
# 4. Test error handling (missing files, invalid config)
```

**Deliverable:** All scenarios working end-to-end

---

## Risk Analysis

### Low Risk ✅
- **Isolated changes** — Only affects classify module
- **Clear extraction** — Watchdog logic is self-contained
- **Existing tests** — Can reuse current test patterns
- **Easy rollback** — Archive versions still available

### Medium Risk ⚠️
- **Windows service implications** — Might need Service Control Manager testing
- **Config integration** — Ensure config system is always available
- **Processor initialization** — Lazy-loading must work correctly

### Mitigation Strategies
1. **Before & After Testing:**
   - Test GUI config save/load
   - Test "Test Configuration" button
   - Test service install/start/stop
   
2. **Regression Testing:**
   - Run adaptive processor on sample Excel file
   - Verify learning log is created/updated
   - Check config files are read correctly

3. **Gradual Rollout:**
   - Phase 1-4: Code is ready but monitor.py not yet used
   - Phase 5: Switch UI to use FileMonitor (no behavior change)
   - Phase 6: Service launcher uses FileMonitor
   - Final: Archive old versions

---

## Success Criteria

| Criterion | Before | After | Status |
|-----------|--------|-------|--------|
| Monitor implementations | 4 | 1 | ✅ |
| Lines of code (monitors) | 216+ | 60 | ✅ |
| File validation duplicates | 3 | 1 | ✅ |
| Entry points | 3+ (unclear) | 3 (clear) | ✅ |
| Test coverage | None | >80% | ✅ |
| Production functionality | Unchanged | Unchanged | ✅ |

---

## Configuration & Compatibility

### No Breaking Changes
- Config files remain compatible
- Pipeline.py unchanged
- Updated_Monitor_UI.py API unchanged

### Backward Compatibility
- Old config files still readable
- Service can upgrade without reinstall
- Pipeline continues to work

### Deployment Path
1. Code changes (no impact yet)
2. Update pipeline.py to use `run_monitor_gui.py` entry point (optional)
3. Service reinstallation (via Updated_Monitor_UI.py)

---

## Questions to Clarify Before Implementation

1. **Service Reinstallation:** Do users need to reinstall the Windows service, or can it upgrade in-place?
   - Answer needed for: deployment documentation

2. **Archive Location:** Keep deprecated files in `archive/`, or remove entirely?
   - Recommendation: Keep for 1 release (May 29), then delete

3. **CLI Entry Point:** Do you want a headless CLI for monitoring without GUI?
   - e.g., `python -m classify.monitor /path/to/watch/dir`
   - Current proposal: Service launcher handles this

4. **Testing Environment:** Should integration tests run on CI, or require Windows service setup?
   - Current proposal: Unit tests only (service tests are manual)

5. **Documentation:** Update CONTEXT.md after consolidation?
   - Current proposal: Yes, add "Monitor Architecture" section

---

## Timeline

| Phase | Task | Est. Time | Cumulative |
|-------|------|-----------|-----------|
| 1 | Create monitor.py | 1h | 1h |
| 2 | Refactor Updated_Monitor_UI.py | 1h | 2h |
| 3 | Create run_monitor_service.py | 30m | 2.5h |
| 4 | Create run_monitor_gui.py | 15m | 2.75h |
| 5 | Move to archive/ | 15m | 3h |
| 6 | Integration testing | 30m | 3.5h |
| **Total** | | | **3.5 hours** |

---

## Next Steps (If Approved)

1. **Review this roadmap** — Any concerns or changes?
2. **Approve the architecture** — Agree on entry points and structure?
3. **Begin Phase 1** — Create monitor.py with tests
4. **Iterative verification** — Test each phase before moving to next

---

## Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `monitor.py` | CREATE | P0 |
| `run_monitor_gui.py` | CREATE | P0 |
| `run_monitor_service.py` | CREATE | P0 |
| `Updated_Monitor_UI.py` | MODIFY (refactor) | P0 |
| `simple_monitor.py` | MOVE → archive/ | P1 |
| `simple_W_service.py` | MOVE → archive/ | P1 |
| `test_file_monitor.py` | CREATE | P1 |
| `test_service_integration.py` | CREATE | P2 |
| `CONTEXT.md` | UPDATE | P2 |

---

**Prepared by:** Claude Code  
**Date:** June 16, 2026  
**Status:** Ready for Review
