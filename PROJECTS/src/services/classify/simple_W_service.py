"""
Simplified Windows service for monitoring Excel files.
Uses AdaptiveExcelProcessor and Config system.
"""

import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import win32serviceutil
import win32service
import win32event
import servicemanager

from adaptive_excel_processor import AdaptiveExcelProcessor
from config import config

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.get('log_level', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ExcelFileHandler(FileSystemEventHandler):
    """Simplified file handler using unified processor."""
    
    def __init__(self):
        servicemanager.LogInfoMsg("[Init] Using Adaptive Processor with learning enabled")
        self.processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(config.hardware_keywords_file),
            sw_keywords_file=str(config.software_keywords_file),
            output_dir=str(config.output_directory),
            learning_mode=config.get('learning_mode', True),
            min_occurrences=config.get('min_occurrences', 5),
            confidence_threshold=config.get('confidence_threshold', 0.7)
        )
    
    def on_created(self, event):
        if not event.is_directory and AdaptiveExcelProcessor.should_process(event.src_path):
            self._process_file(event.src_path, "Created")
    
    def on_modified(self, event):
        if not event.is_directory and AdaptiveExcelProcessor.should_process(event.src_path):
            self._process_file(event.src_path, "Modified")
    
    def _process_file(self, file_path, event_type):
        """Process file and log results."""
        try:
            servicemanager.LogInfoMsg(f"[{event_type}] Processing: {file_path}")
            success = self.processor.process_file(file_path)
            
            if success:
                servicemanager.LogInfoMsg(f"[Success] Processed: {Path(file_path).name}")
            else:
                servicemanager.LogErrorMsg(f"[Failed] Could not process: {Path(file_path).name}")
                
        except Exception as e:
            servicemanager.LogErrorMsg(f"[Error] Processing {file_path}: {str(e)}")

class FolderMonitorService(win32serviceutil.ServiceFramework):
    """Simplified Windows service."""
    
    _svc_name_ = config.get("service_name")
    _svc_display_name_ = config.get("service_display_name")
    _svc_description_ = config.get("service_description")
    
    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.observer = None
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
    
    def SvcDoRun(self):
        # Log service start
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            for error in config_errors:
                servicemanager.LogErrorMsg(f"[Config Error] {error}")
            return
        
        # Start file monitoring
        try:
            self.observer = Observer()
            self.observer.schedule(
                ExcelFileHandler(), 
                str(config.watch_directory), 
                recursive=False
            )
            self.observer.start()
            
            servicemanager.LogInfoMsg(f"[Started] Monitoring: {config.watch_directory}")
            
            # Service main loop
            while True:
                if win32event.WaitForSingleObject(self.stop_event, 500) == win32event.WAIT_OBJECT_0:
                    break
                    
        except Exception as e:
            servicemanager.LogErrorMsg(f"[Service Error] {str(e)}")
        
        finally:
            # Cleanup
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FolderMonitorService)