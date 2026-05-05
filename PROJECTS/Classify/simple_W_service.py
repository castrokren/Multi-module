"""
Windows service for monitoring Excel files and classifying them automatically.
Uses AdaptiveExcelProcessor with self-learning enabled.
"""

import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import win32serviceutil
import win32service
import win32event
import servicemanager

from adaptive_excel_processor import AdaptiveExcelProcessor
from utils import should_process
from config import config

logging.basicConfig(
    level=getattr(logging, config.get('log_level', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s',
)


class ExcelFileHandler(FileSystemEventHandler):
    """Watchdog handler that classifies new/modified Excel files."""

    def __init__(self):
        self.processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(config.hardware_keywords_file),
            sw_keywords_file=str(config.software_keywords_file),
            ni_keywords_file=str(config.non_instrument_keywords_file),
            output_dir=str(config.output_directory),
            learning_mode=config.get('learning_mode', True),
            min_occurrences=config.get('min_occurrences', 5),
            confidence_threshold=config.get('confidence_threshold', 0.7),
        )

    def on_created(self, event):
        if not event.is_directory and should_process(event.src_path):
            self._handle(event.src_path, "Created")

    def on_modified(self, event):
        if not event.is_directory and should_process(event.src_path):
            self._handle(event.src_path, "Modified")

    def _handle(self, file_path, event_type):
        try:
            servicemanager.LogInfoMsg(f"[{event_type}] Processing: {file_path}")
            success = self.processor.process_file(file_path)
            if success:
                servicemanager.LogInfoMsg(f"[OK] {Path(file_path).name}")
            else:
                servicemanager.LogErrorMsg(f"[Failed] {Path(file_path).name}")
        except Exception as e:
            servicemanager.LogErrorMsg(f"[Error] {file_path}: {e}")


class FolderMonitorService(win32serviceutil.ServiceFramework):
    """Windows service wrapper for the folder monitor."""

    _svc_name_ = config.get("service_name", "MonitorFolderSvc")
    _svc_display_name_ = config.get("service_display_name", "Excel Folder Monitor Service")
    _svc_description_ = config.get(
        "service_description",
        "Monitors a folder and classifies Excel files when they are added or modified.",
    )

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.observer = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ''),
        )

        errors = config.validate()
        if errors:
            for err in errors:
                servicemanager.LogErrorMsg(f"[Config] {err}")
            return

        try:
            self.observer = Observer()
            self.observer.schedule(ExcelFileHandler(), str(config.watch_directory), recursive=False)
            self.observer.start()
            servicemanager.LogInfoMsg(f"[Started] Watching: {config.watch_directory}")

            while True:
                if win32event.WaitForSingleObject(self.stop_event, 500) == win32event.WAIT_OBJECT_0:
                    break

        except Exception as e:
            servicemanager.LogErrorMsg(f"[Service Error] {e}")

        finally:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ''),
            )


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FolderMonitorService)
