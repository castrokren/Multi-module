# ARCHIVED - 2026-06-16
# This file is deprecated. Use v2_monitor/monitor.py instead.
# simple_monitor.py has been consolidated into the unified FileMonitor in v2_monitor/

"""
Simplified Windows service for monitoring Excel files.
Uses the unified AdaptiveExcelProcessor and Config system.

DEPRECATED: Use v2_monitor.monitor.FileMonitor instead.
"""

import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
            print(f"[{event_type}] Processing: {file_path}")
            success = self.processor.process_file(file_path)

            if success:
                print(f"[Success] Processed: {Path(file_path).name}")
            else:
                print(f"[Failed] Could not process: {Path(file_path).name}")

        except Exception as e:
            print(f"[Error] Processing {file_path}: {str(e)}")

if __name__ == '__main__':
    # This file is deprecated
    print("ERROR: simple_monitor.py is deprecated.")
    print("Please use: python -m v2_monitor.run_monitor_service")
    sys.exit(1)
