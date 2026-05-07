#!/usr/bin/env python3
"""
Standalone folder monitor for testing Excel file processing.
This runs in the foreground and monitors the folder for new files.
"""

import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import our unified modules
from adaptive_excel_processor import AdaptiveExcelProcessor
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ExcelFileHandler(FileSystemEventHandler):
    """File handler using unified processor."""
    
    def __init__(self):
        # Initialize processor with config
        self.processor = AdaptiveExcelProcessor(
            hw_keywords_file=config.hardware_keywords_file,
            sw_keywords_file=config.software_keywords_file,
            output_dir=config.output_directory
        )
        print(f"✓ Monitor initialized")
        print(f"  Watch directory: {config.watch_directory}")
        print(f"  Output directory: {config.output_directory}")
        print(f"  Hardware keywords: {config.hardware_keywords_file}")
        print(f"  Software keywords: {config.software_keywords_file}")
    
    def on_created(self, event):
        if not event.is_directory and AdaptiveExcelProcessor.should_process(event.src_path):
            self._process_file(event.src_path, "Created")
    
    def on_modified(self, event):
        if not event.is_directory and AdaptiveExcelProcessor.should_process(event.src_path):
            self._process_file(event.src_path, "Modified")
    
    def _process_file(self, file_path, event_type):
        """Process file and log results."""
        try:
            print(f"[{event_type}] Processing: {Path(file_path).name}")
            success = self.processor.process_file(file_path)
            
            if success:
                print(f"[SUCCESS] Processed: {Path(file_path).name}")
            else:
                print(f"[FAILED] Could not process: {Path(file_path).name}")
                
        except Exception as e:
            print(f"[ERROR] Processing {file_path}: {str(e)}")

def main():
    """Main monitoring loop."""
    print("=== Excel Folder Monitor (Standalone) ===")
    
    # Validate configuration
    config_errors = config.validate()
    if config_errors:
        print("Configuration errors:")
        for error in config_errors:
            print(f"  ✗ {error}")
        return
    
    print("✓ Configuration valid")
    
    # Start file monitoring
    try:
        observer = Observer()
        observer.schedule(
            ExcelFileHandler(), 
            str(config.watch_directory), 
            recursive=False
        )
        observer.start()
        
        print(f"✓ Monitoring started: {config.watch_directory}")
        print("Press Ctrl+C to stop monitoring...")
        
        # Main loop
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        observer.stop()
        observer.join()
        print("Monitor stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
