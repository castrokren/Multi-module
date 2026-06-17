# Monitor Consolidation Roadmap v2
## For Automated SharePoint Pipeline

**Context:** Monitor is the **critical entry point** in a fully automated pipeline:  
`SharePoint (source) → Monitor Service → Classification → Cross-ref → SharePoint (output) → Power Automate`

**Implication:** Reliability, resilience, and observability are **primary concerns**, not just code deduplication.

---

## Revised Priority Framework

### Production-Critical (P0)
1. ✅ **Single, reliable monitor** — One implementation to maintain and trust
2. ✅ **Error resilience** — Handle Sharepoint downtime, network interruptions, malformed files
3. ✅ **Detailed logging** — Troubleshoot issues in 24/7 operation
4. ✅ **Sharepoint integration** — Support both local filesystem AND Sharepoint
5. ✅ **No GUI dependencies** — Service runs headless in production

### Important (P1)
6. GUI for configuration (initial setup only)
7. Test configuration button
8. Config persistence

### Nice-to-Have (P2)
9. Code deduplication (secondary benefit)
10. Reduced lines of code

---

## Revised Architecture

### Core Design: Multi-Source File Monitor

```
FileMonitor (core engine)
├── Abstracted source layer (pluggable)
│   ├── LocalFilesystemSource (watchdog)
│   ├── SharepointSource (Microsoft Graph SDK)
│   └── Future: S3, Azure Blob, etc.
├── Error recovery & retry logic
├── Detailed logging
└── State tracking (what's been processed)

run_monitor_service.py (production entry point)
├── Runs headless 24/7
├── Restarts on failure
├── Logs to file + optional Azure/CloudWatch
└── Integrates with System scheduler or Kubernetes

Updated_Monitor_UI.py (optional, for initial setup)
├── Configure monitor settings
├── Test with sample file
├── View logging

archive/
├── simple_monitor.py (deprecated)
├── simple_W_service.py (deprecated)
└── service_script.py (deprecated)
```

### Key Differences from v1

| Aspect | v1 (Naive) | v2 (Pipeline-Ready) |
|--------|-----------|-------------------|
| **File Source** | Local filesystem only | Local FS + Sharepoint + pluggable |
| **Error Handling** | Basic try/except | Retry logic, graceful degradation |
| **Logging** | In-memory text widget | File + structured logging |
| **State Tracking** | None | Track processed files, resume capability |
| **Resilience** | Service restarts on crash | Automatic recovery, health checks |
| **Config Format** | JSON files | Environment variables + JSON (12-factor) |
| **Monitoring** | Manual checks | Health endpoint, metrics export |

---

## Updated Module Design

### 1. monitor.py (NEW - Core Engine)

```python
"""
Unified file monitoring engine with multi-source support.
Handles local filesystem, Sharepoint, error recovery, and logging.
"""

import logging
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from queue import Queue

# --- Source abstraction layer ---

class FileSource(ABC):
    """Abstract base for file sources."""
    
    @abstractmethod
    def connect(self):
        """Establish connection to source."""
    
    @abstractmethod
    def list_files(self, filter_pattern='*.xlsx'):
        """List available files matching pattern."""
    
    @abstractmethod
    def download_file(self, remote_path, local_path):
        """Download file from source."""
    
    @abstractmethod
    def mark_processed(self, remote_path):
        """Mark file as processed (move, flag, etc)."""
    
    @abstractmethod
    def is_connected(self):
        """Check if source is reachable."""


class LocalFilesystemSource(FileSource):
    """Watch local directory via watchdog."""
    
    def __init__(self, watch_dir):
        self.watch_dir = Path(watch_dir)
        self.observer = None
    
    def connect(self):
        """Start watchdog observer."""
    
    def list_files(self, filter_pattern='*.xlsx'):
        """List Excel files in watch dir."""
    
    def is_connected(self):
        """Check if directory exists and is accessible."""


class SharepointSource(FileSource):
    """Connect to Sharepoint via Microsoft Graph API."""
    
    def __init__(self, site_url, folder_path, client_id, client_secret):
        self.site_url = site_url
        self.folder_path = folder_path
        # Auth setup...
    
    def connect(self):
        """Authenticate and test connection."""
    
    def list_files(self, filter_pattern='*.xlsx'):
        """Query Sharepoint for Excel files."""
    
    def download_file(self, remote_path, local_path):
        """Download from Sharepoint with retry."""
    
    def mark_processed(self, remote_path):
        """Move file to 'Processed' folder in Sharepoint."""
    
    def is_connected(self):
        """Test Graph API connectivity."""


# --- Core monitoring engine ---

class FileMonitor:
    """
    Unified file monitor with error resilience and logging.
    Works with any FileSource (local, Sharepoint, etc).
    """
    
    def __init__(self, source: FileSource, processor_config, logger=None):
        self.source = source
        self.processor_config = processor_config
        self.logger = logger or self._setup_logging()
        self.processor = None
        self.running = False
        self._processed_files = self._load_state()  # Resume-able state
    
    def _setup_logging(self):
        """Configure structured logging."""
        # File logging: logs/monitor_YYYYMMDD.log
        # Format: timestamp | level | message | context
    
    def _load_state(self):
        """Load state file to resume from last checkpoint."""
        # .monitor_state.json tracks processed files
    
    def _save_state(self):
        """Save state for recovery."""
    
    def _initialize_processor(self):
        """Lazy-load AdaptiveExcelProcessor."""
    
    def _process_file(self, file_path, source_path):
        """
        Process a single file with full error handling.
        
        Args:
            file_path: Local path to downloaded file
            source_path: Original path in source (Sharepoint/local)
        """
        try:
            # Validate file
            if not self.should_process(file_path):
                self.logger.debug(f"Skipping: {file_path}")
                return False
            
            # Process
            self.logger.info(f"Processing: {source_path}")
            success = self.processor.process_file(file_path)
            
            if success:
                self.logger.info(f"✓ Processed: {source_path}")
                # Mark as processed in source
                self.source.mark_processed(source_path)
                self._processed_files.add(source_path)
                self._save_state()
                return True
            else:
                self.logger.error(f"✗ Failed: {source_path}")
                return False
        
        except Exception as e:
            self.logger.error(f"Exception processing {source_path}: {e}", 
                            exc_info=True)
            return False
    
    def _fetch_and_process(self):
        """
        Fetch files from source with retry logic.
        Called every N seconds.
        """
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if not self.source.is_connected():
                    self.logger.warning(
                        f"Source unavailable (attempt {attempt+1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.logger.error("Source unavailable, will retry later")
                        return
                
                # Connected — fetch and process
                files = self.source.list_files()
                
                for remote_path, file_info in files:
                    if remote_path in self._processed_files:
                        continue  # Already processed
                    
                    # Download to temp location
                    temp_path = f"/tmp/{Path(remote_path).name}"
                    self.source.download_file(remote_path, temp_path)
                    
                    # Process
                    self._process_file(temp_path, remote_path)
                
                break  # Success, don't retry
            
            except Exception as e:
                self.logger.error(
                    f"Error fetching from source (attempt {attempt+1}): {e}",
                    exc_info=True
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
    
    def start(self, poll_interval=60):
        """
        Start monitoring.
        
        Args:
            poll_interval: Check source every N seconds
        """
        self.running = True
        self.logger.info(f"Monitor started (poll_interval={poll_interval}s)")
        
        try:
            self.source.connect()
            self._initialize_processor()
            
            while self.running:
                try:
                    self._fetch_and_process()
                    time.sleep(poll_interval)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Monitor loop error: {e}", exc_info=True)
                    time.sleep(poll_interval)  # Retry after delay
        
        except Exception as e:
            self.logger.critical(f"Failed to start monitor: {e}", exc_info=True)
            raise
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring gracefully."""
        self.running = False
        self._save_state()
        self.source.disconnect() if hasattr(self.source, 'disconnect') else None
        self.logger.info("Monitor stopped")
    
    def health_check(self) -> dict:
        """Return health status for monitoring systems."""
        return {
            'running': self.running,
            'source_connected': self.source.is_connected(),
            'last_check': datetime.utcnow().isoformat(),
            'files_processed': len(self._processed_files),
        }
    
    @staticmethod
    def should_process(file_path):
        """Check if file should be processed."""
        # Unified validation
```

---

### 2. run_monitor_service.py (PRODUCTION ENTRY POINT)

```python
#!/usr/bin/env python3
"""
Production-ready monitor service for automated pipeline.
Supports both Windows Service and systemd/Docker.
"""

import os
import sys
import logging
import json
from pathlib import Path

# Import source types
from monitor import FileMonitor, LocalFilesystemSource, SharepointSource
from adaptive_excel_processor import AdaptiveExcelProcessor
from config import config

def get_source_from_config(cfg) -> FileSource:
    """
    Factory: Create appropriate FileSource based on config.
    
    Config structure:
    {
        "source_type": "sharepoint" | "local",
        "sharepoint": {
            "site_url": "...",
            "folder_path": "...",
            "client_id": "...",
            "client_secret": "..."  # Load from env
        },
        "local": {
            "watch_directory": "..."
        }
    }
    """
    source_type = cfg.get('source_type', 'local')
    
    if source_type == 'sharepoint':
        sp_cfg = cfg['sharepoint']
        return SharepointSource(
            site_url=sp_cfg['site_url'],
            folder_path=sp_cfg['folder_path'],
            client_id=sp_cfg['client_id'],
            client_secret=os.getenv('SHAREPOINT_SECRET'),  # From env
        )
    else:
        return LocalFilesystemSource(
            watch_dir=cfg['local']['watch_directory']
        )

class MonitorService:
    """Service wrapper for both Windows Service and direct execution."""
    
    def __init__(self):
        self.monitor = None
        self.config = self._load_config()
    
    def _load_config(self):
        """Load config from JSON + environment overrides."""
        # 12-factor: environment > config file
        cfg = config.to_dict()
        
        # Env overrides (for Docker/Kubernetes)
        if os.getenv('WATCH_DIRECTORY'):
            cfg['local']['watch_directory'] = os.getenv('WATCH_DIRECTORY')
        if os.getenv('SHAREPOINT_SITE_URL'):
            cfg['source_type'] = 'sharepoint'
            cfg['sharepoint']['site_url'] = os.getenv('SHAREPOINT_SITE_URL')
        
        return cfg
    
    def run(self):
        """Main entry point."""
        source = get_source_from_config(self.config)
        
        processor_cfg = {
            'hw_keywords_file': str(config.hardware_keywords_file),
            'sw_keywords_file': str(config.software_keywords_file),
            'ni_keywords_file': str(config.non_instrument_keywords_file),
            'output_dir': str(config.output_directory),
            'learning_mode': config.get('learning_mode', True),
        }
        
        self.monitor = FileMonitor(source, processor_cfg)
        self.monitor.start(poll_interval=self.config.get('poll_interval', 60))

# Windows Service support
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    
    class FolderMonitorWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = "CrawlerFolderMonitor"
        _svc_display_name_ = "Crawler Folder Monitor (Pipeline)"
        
        def __init__(self, args):
            super().__init__(args)
            self.service = None
        
        def SvcDoRun(self):
            self.service = MonitorService()
            try:
                self.service.run()
            except Exception as e:
                servicemanager.LogErrorMsg(f"Service failed: {e}")
                raise
        
        def SvcStop(self):
            if self.service and self.service.monitor:
                self.service.monitor.stop()
    
    def run_windows_service():
        win32serviceutil.HandleCommandLine(FolderMonitorWindowsService)

except ImportError:
    def run_windows_service():
        raise RuntimeError("pywin32 not installed; Windows Service not available")

# Main entry point
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('install', 'remove', 'start', 'stop'):
        # Windows Service commands
        run_windows_service()
    else:
        # Direct execution (for Docker, systemd, manual testing)
        service = MonitorService()
        service.run()
```

---

### 3. Updated_Monitor_UI.py (CONFIGURATION ONLY)

**Changes from v1:**
1. Remove watchdog/service code entirely
2. Remove service control buttons (start/stop) — service runs separately
3. Keep: configuration UI, test button, learning report
4. Add: "Sharepoint Configuration" tab

```python
def _build_ui(self):
    # ... existing service config frame (service_path, etc.)
    
    # NEW: Source Configuration
    source_frame = tk.LabelFrame(self, text="File Source Configuration")
    source_frame.grid(...)
    
    source_var = tk.StringVar(value='local')
    tk.Radiobutton(source_frame, text="Local Filesystem", 
                   variable=source_var, value='local').pack()
    tk.Radiobutton(source_frame, text="Sharepoint", 
                   variable=source_var, value='sharepoint').pack()
    
    # LOCAL: watch_directory (existing)
    # SHAREPOINT: site_url, folder_path, client_id, client_secret
    
    # ... rest of config
```

---

## Implementation Plan (Revised)

### Phase 0: Sharepoint SDK & Error Handling (1.5 hours)
**NEW** — Add production requirements

- [ ] Install Microsoft Graph SDK: `pip install msgraph-core`
- [ ] Implement `SharepointSource` class with retry logic
- [ ] Add structured logging (file + console)
- [ ] Add state tracking `.monitor_state.json`

### Phase 1: Core Monitor Engine (1.5 hours)
- [ ] Create `monitor.py` with `FileSource` abstraction
- [ ] Implement `LocalFilesystemSource` (refactor from simple_W_service.py)
- [ ] Implement retry logic, error handling, logging
- [ ] Add unit tests for file validation + state tracking

### Phase 2: Production Service (1 hour)
- [ ] Create `run_monitor_service.py`
- [ ] Windows Service wrapper + direct execution
- [ ] Config from JSON + environment variables (12-factor)
- [ ] Health check endpoint (for monitoring)

### Phase 3: Configuration UI (1 hour)
- [ ] Refactor `Updated_Monitor_UI.py` to use FileMonitor
- [ ] Add Sharepoint configuration tab
- [ ] Test with both local and Sharepoint sources

### Phase 4: Integration Testing (1 hour)
- [ ] Test local filesystem monitoring
- [ ] Test Sharepoint integration (with test tenant)
- [ ] Test error recovery (simulated Sharepoint downtime)
- [ ] Test state recovery (resume after restart)

### Phase 5: Archive & Documentation (30 min)
- [ ] Move old monitors to archive/
- [ ] Update CONTEXT.md with new architecture
- [ ] Add runbook for deployment

**Total: 5.5 hours**

---

## Configuration Examples

### Local Filesystem (Testing)
```json
{
  "source_type": "local",
  "local": {
    "watch_directory": "/data/sharepoint-input"
  },
  "poll_interval": 60
}
```

### Sharepoint (Production)
```json
{
  "source_type": "sharepoint",
  "sharepoint": {
    "site_url": "https://company.sharepoint.com/sites/Crawler",
    "folder_path": "/Shared Documents/Input/Reports",
    "client_id": "abc123...",
    "client_secret": "***"
  },
  "poll_interval": 300
}
```

### Docker/Kubernetes (Environment)
```bash
# .env or deployment config
SOURCE_TYPE=sharepoint
SHAREPOINT_SITE_URL=https://company.sharepoint.com/sites/Crawler
SHAREPOINT_FOLDER_PATH=/Shared Documents/Input
SHAREPOINT_CLIENT_ID=abc123
SHAREPOINT_SECRET=*** (from Kubernetes Secret)
POLL_INTERVAL=300
```

---

## Logging Strategy (Production-Critical)

### Log Format: Structured JSON
```json
{
  "timestamp": "2026-06-16T10:30:45.123Z",
  "level": "INFO",
  "module": "monitor",
  "function": "_process_file",
  "message": "Processing: Reports/Q2_Summary.xlsx",
  "source": "sharepoint",
  "file_path": "Reports/Q2_Summary.xlsx",
  "duration_ms": 1250,
  "status": "success"
}
```

### Log Destinations
- **File:** `logs/monitor_YYYYMMDD.log` (for local debugging)
- **Optional:** Azure Monitor / CloudWatch (for production dashboard)
- **Optional:** Power Automate integration (alert on errors)

---

## Success Criteria (Pipeline-Ready)

| Criterion | Before | After |
|-----------|--------|-------|
| **Reliability** | Single point of failure | Retries, error recovery, state tracking |
| **Observability** | Manual checks | Structured logging, health endpoint |
| **Source Support** | Local only | Local + Sharepoint (pluggable) |
| **Configuration** | File-based | File + environment (12-factor) |
| **Code Duplication** | 4 implementations | 1 |
| **Production-Ready** | No | Yes |

---

## Risk Mitigation for Pipeline

### Scenario 1: Sharepoint Temporarily Down
- Monitor: Retries every 5 seconds, max 3 attempts, then backs off
- Recovery: Automatically resumes when Sharepoint is back
- Logging: Clear error message in logs

### Scenario 2: Malformed Excel File
- Monitor: Catches exception, logs error, moves to next file
- Pipeline: No interruption, bad files logged for manual review
- Recovery: Admin can re-process via UI

### Scenario 3: Monitor Crashes
- Service: Windows Service auto-restart (via system config)
- Docker: Container restart policy (always)
- State: Resumes from last checkpoint via `.monitor_state.json`

### Scenario 4: Processing Backlog
- Monitor: Pulls all unprocessed files on startup
- Config: `poll_interval` can be tuned (60s default, 300s for Sharepoint)
- Logging: Reports backlog size

---

## Deployment Strategy

### Initial Setup
1. Configure source (local or Sharepoint) in UI
2. Test with sample file
3. Save configuration

### Dev Environment
```bash
python run_monitor_service.py  # Direct execution, logs to console
```

### Production (Windows Service)
```bash
python run_monitor_service.py install  # Install as Windows Service
# Or: net start CrawlerFolderMonitor
```

### Production (Docker/Kubernetes)
```dockerfile
FROM python:3.9
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "run_monitor_service.py"]
```

---

## Questions for You

1. **Sharepoint Tenant Details:**
   - Do you have Graph API credentials ready?
   - What's the folder structure? (e.g., `/Shared Documents/Crawler Input`)

2. **Error Handling:**
   - If a file fails processing, should it stay in Sharepoint for retry, or move to an error folder?
   - Alert to Power Automate on failure?

3. **Monitoring & Alerting:**
   - Should monitor export health metrics (Prometheus/CloudWatch)?
   - Slack/email alerts on errors?

4. **Performance:**
   - Expected file volume per day? (affects poll interval tuning)
   - File size range? (affects download parallelization)

5. **State Recovery:**
   - Keep `.monitor_state.json` locally, or in Sharepoint?
   - How far back to resume? (last hour, last day, all time?)

---

## Next Steps

1. **Review this revised roadmap** — Does it address the pipeline requirements?
2. **Clarify Sharepoint details** — Tenant URL, folder structure, API credentials?
3. **Approve architecture** — Multi-source abstraction, retry logic, logging?
4. **Begin Phase 0** — Set up Sharepoint SDK + structured logging

---

**Status:** Ready for approval  
**Scope Change:** v1 → v2 adds Sharepoint, error resilience, logging  
**Estimated Effort:** 5.5 hours (vs. 3.5 in v1)  
**ROI:** Production-ready monitor for critical pipeline

