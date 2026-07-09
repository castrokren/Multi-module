"""
Unified File Monitor Engine
Watches a directory for Excel files and processes them with AdaptiveExcelProcessor.
"""

import os
import logging
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from adaptive_excel_processor import AdaptiveExcelProcessor
except ImportError:
    AdaptiveExcelProcessor = None


class FileMonitor:
    """
    Watches a directory for Excel files and processes them.

    Features:
    - Monitors local directory via watchdog
    - Validates and filters Excel files
    - Processes files with AdaptiveExcelProcessor
    - Logs to file + console
    - Graceful shutdown

    Usage:
        config = {
            'hw_keywords_file': 'keywords_hw.txt',
            'sw_keywords_file': 'keywords_sw.txt',
            'ni_keywords_file': 'keywords_ni.txt',
            'output_dir': 'output',
            'learning_mode': True,
        }
        monitor = FileMonitor(
            watch_dir='input',
            output_dir='output',
            processor_config=config
        )
        monitor.start()
    """

    def __init__(self, watch_dir, output_dir, processor_config, logger=None):
        """
        Initialize the FileMonitor.

        Args:
            watch_dir: Directory to monitor for Excel files
            output_dir: Directory to write processed files
            processor_config: Dict with AdaptiveExcelProcessor settings
            logger: Optional logger instance (creates one if not provided)
        """
        self.watch_dir = Path(watch_dir)
        self.output_dir = Path(output_dir)
        self.processor_config = processor_config
        self.logger = logger or self._setup_logging()

        self.processor = None
        self.observer = None
        self.running = False

    def _setup_logging(self):
        """
        Configure logging to file + console.
        Creates logs directory in parent of watch_dir.
        """
        log_dir = self.watch_dir.parent / "logs"
        log_dir.mkdir(exist_ok=True, parents=True)

        log_file = log_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"

        # Remove existing handlers to avoid duplicates
        logger = logging.getLogger(__name__)
        logger.handlers.clear()

        # Set up new handlers
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.setLevel(logging.INFO)
        return logger

    def _initialize_processor(self):
        """
        Lazy-load AdaptiveExcelProcessor.
        Initializes processor only on first use.
        """
        if self.processor is None:
            if AdaptiveExcelProcessor is None:
                raise ImportError("AdaptiveExcelProcessor not available")
            try:
                self.processor = AdaptiveExcelProcessor(**self.processor_config)
                self.logger.info("[OK] Processor initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize processor: {e}", exc_info=True)
                raise

    @staticmethod
    def should_process(file_path):
        """
        Check if file should be processed.

        Filters:
        - Skip Excel temp files (start with ~$)
        - Skip already-processed files (end with _labeled)
        - Only process .xls and .xlsx files

        Args:
            file_path: Path to file to check

        Returns:
            bool: True if file should be processed, False otherwise
        """
        path = Path(file_path)

        # Skip Excel temp files
        if path.name.startswith('~$'):
            return False

        # Skip already-processed files
        if path.stem.endswith('_labeled'):
            return False

        # Only process Excel files
        return path.suffix.lower() in ['.xls', '.xlsx']

    def _process_file(self, file_path):
        """
        Process a single Excel file.

        Handles:
        - Lazy processor initialization
        - File validation
        - Processor execution
        - Error logging

        Args:
            file_path: Path to file to process

        Returns:
            bool: True if successful, False otherwise
        """
        path = Path(file_path)

        try:
            # Ensure processor is initialized
            if self.processor is None:
                self._initialize_processor()

            self.logger.info(f"Processing: {path.name}")

            # Process the file
            success = self.processor.process_file(file_path)

            if success:
                self.logger.info(f"[OK] Success: {path.name}")
                return True
            else:
                self.logger.warning(f"✗ Failed: {path.name}")
                return False

        except Exception as e:
            self.logger.error(f"Exception processing {path.name}: {e}", exc_info=True)
            return False

    def start(self):
        """
        Start monitoring the directory.

        Validates directories, initializes watchdog observer,
        and blocks until interrupted or stopped.

        Raises:
            FileNotFoundError: If watch_dir doesn't exist
            Exception: If observer fails to start
        """
        # Validate watch directory
        if not self.watch_dir.exists():
            self.logger.error(f"Watch directory not found: {self.watch_dir}")
            raise FileNotFoundError(f"Watch directory: {self.watch_dir}")

        # Create output directory if needed
        if not self.output_dir.exists():
            self.logger.info(f"Creating output directory: {self.output_dir}")
            self.output_dir.mkdir(parents=True, exist_ok=True)

        self.running = True
        self.logger.info("=" * 60)
        self.logger.info("Monitor started")
        self.logger.info(f"  Watch:  {self.watch_dir.resolve()}")
        self.logger.info(f"  Output: {self.output_dir.resolve()}")
        self.logger.info("=" * 60)

        try:
            # Create and start observer
            self.observer = Observer()
            handler = ExcelFileHandler(self._process_file, self.should_process, self.logger)
            self.observer.schedule(handler, str(self.watch_dir), recursive=False)
            self.observer.start()

            # Keep running until interrupted
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Monitor interrupted by user")

        except Exception as e:
            self.logger.error(f"Monitor error: {e}", exc_info=True)
            raise

        finally:
            self.stop()

    def stop(self):
        """
        Stop monitoring gracefully.

        Stops watchdog observer and cleans up resources.
        Safe to call multiple times.
        """
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)

        self.logger.info("=" * 60)
        self.logger.info("Monitor stopped")
        self.logger.info("=" * 60)


class ExcelFileHandler(FileSystemEventHandler):
    """
    Handles file system events in watched directory.

    Listens for file creation and modification events,
    validates files, and delegates to process callback.
    """

    def __init__(self, process_callback, validation_callback, logger=None):
        """
        Initialize file handler.

        Args:
            process_callback: Function(file_path) to process a file
            validation_callback: Function(file_path) -> bool to validate file
            logger: Optional logger instance
        """
        self.process_callback = process_callback
        self.should_process = validation_callback
        self.logger = logger or logging.getLogger(__name__)

    def on_created(self, event):
        """
        Handle file creation event.

        Waits briefly for file to be fully written,
        validates file, then processes if needed.
        """
        if event.is_directory:
            return

        if not self.should_process(event.src_path):
            return

        # Wait for file to be fully written
        time.sleep(0.5)

        self.logger.debug(f"File created: {Path(event.src_path).name}")
        self.process_callback(event.src_path)

    def on_modified(self, event):
        """
        Handle file modification event.

        Waits briefly to avoid processing incomplete writes,
        validates file, then processes if needed.
        """
        if event.is_directory:
            return

        if not self.should_process(event.src_path):
            return

        # Wait for file to be fully written
        time.sleep(0.5)

        self.logger.debug(f"File modified: {Path(event.src_path).name}")
        self.process_callback(event.src_path)
