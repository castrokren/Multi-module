import sys
import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import win32serviceutil
import win32service
import win32event
import servicemanager


# ----- Configuration -----
WATCH_DIR = os.environ.get('WATCH_DIR', r"Y:")
SCRIPT_PATH = os.environ.get('SCRIPT_PATH', r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify\classify_and_clean_dynamic.py")

class ExcelEventHandler(FileSystemEventHandler):
    """Watches for new or modified .xls and .xlsx files and dispatches processing."""
    def should_process(self, path_str):
        base = os.path.basename(path_str)
        stem, ext = os.path.splitext(base)
        # Skip Excel temp files and already-processed outputs
        if stem.startswith('~$') or stem.endswith('_labeled'):
            return False
        return ext.lower() in ['.xls', '.xlsx']

    def process_file(self, file_path):
        servicemanager.LogInfoMsg(f"[MonitorService] Processing: {file_path}")
        try:
            result = subprocess.run(
                [sys.executable, SCRIPT_PATH, file_path],
                capture_output=True,
                text=True,
                check=True
            )
            servicemanager.LogInfoMsg(f"[MonitorService] Success: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            servicemanager.LogErrorMsg(f"[MonitorService] Error: {e.stderr.strip()}")

    def on_created(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            self.process_file(event.src_path)

class FolderMonitorSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "MonitorFolderSvc"
    _svc_display_name_ = "Excel Folder Monitor Service"
    _svc_description_ = "Monitors a folder and processes Excel files when added or changed."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        # Set up observer
        event_handler = ExcelEventHandler()
        observer = Observer()
        observer.schedule(event_handler, WATCH_DIR, recursive=False)
        observer.start()

        # Service loop: wait for stop signal
        while True:
            rc = win32event.WaitForSingleObject(self.stop_event, 500)
            if rc == win32event.WAIT_OBJECT_0:
                break

        # Clean up
        observer.stop()
        observer.join()
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FolderMonitorSvc)