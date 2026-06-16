#!/usr/bin/env python3
"""
Production-ready monitor service launcher.

Works in two modes:
1. Direct execution (python run_monitor_service.py) — for testing/Docker
2. Windows Service (python run_monitor_service.py install/start/stop) — for production

Configuration is loaded from config.py with environment variable overrides.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to sys.path for imports (when run as script)
script_dir = Path(__file__).parent
if str(script_dir.parent) not in sys.path:
    sys.path.insert(0, str(script_dir.parent))

# Try relative import first (when run as module), fall back to absolute
try:
    from .monitor import FileMonitor
except ImportError:
    from monitor import FileMonitor

logger = logging.getLogger(__name__)


def load_config():
    """
    Load configuration from config.py with environment variable overrides.

    Environment variables take precedence over config.py defaults.

    Returns:
        tuple: (watch_dir, output_dir, processor_config)
    """
    try:
        from config import config
    except ImportError:
        logger.error("Cannot import config module from parent directory")
        config = {}

    # Load from config.py with defaults
    watch_dir = config.get('watch_directory', r'C:\Data\Crawler\input')
    output_dir = config.get('output_directory', r'C:\Data\Crawler\output')

    # Environment variable overrides
    watch_dir = os.getenv('WATCH_DIRECTORY', watch_dir)
    output_dir = os.getenv('OUTPUT_DIRECTORY', output_dir)

    # Processor configuration
    processor_config = {
        'hw_keywords_file': os.getenv(
            'HW_KEYWORDS_FILE',
            str(config.get('hardware_keywords_file', 'research_instrument_keywords.txt'))
        ),
        'sw_keywords_file': os.getenv(
            'SW_KEYWORDS_FILE',
            str(config.get('software_keywords_file', 'software_keywords.txt'))
        ),
        'ni_keywords_file': os.getenv(
            'NI_KEYWORDS_FILE',
            str(config.get('non_instrument_keywords_file', 'non_instrument_keywords.txt'))
        ),
        'output_dir': output_dir,
        'learning_mode': os.getenv('LEARNING_MODE', 'true').lower() == 'true',
        'min_occurrences': int(os.getenv('MIN_OCCURRENCES', config.get('min_occurrences', 5))),
        'confidence_threshold': float(os.getenv('CONFIDENCE_THRESHOLD', config.get('confidence_threshold', 0.7))),
    }

    return watch_dir, output_dir, processor_config


def main():
    """
    Main entry point for direct execution.
    Blocks until interrupted (Ctrl+C).
    """
    print("=" * 70)
    print("CRAWLER FOLDER MONITOR v2.0")
    print("=" * 70)
    print()

    try:
        watch_dir, output_dir, processor_config = load_config()

        print(f"Configuration:")
        print(f"  Watch directory:  {watch_dir}")
        print(f"  Output directory: {output_dir}")
        print(f"  Learning mode:    {processor_config['learning_mode']}")
        print()

        # Create and start monitor
        monitor = FileMonitor(
            watch_dir=watch_dir,
            output_dir=output_dir,
            processor_config=processor_config
        )

        print("Starting monitor... (press Ctrl+C to stop)")
        print()

        try:
            monitor.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            monitor.stop()

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please ensure watch directory exists or set WATCH_DIRECTORY environment variable")
        sys.exit(1)

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# Windows Service support
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class CrawlerMonitorService(win32serviceutil.ServiceFramework):
        """
        Windows Service wrapper for FileMonitor.

        Service name: CrawlerMonitor
        Display name: Crawler Folder Monitor
        Description: Monitors local folder and processes Excel files

        Commands:
            python run_monitor_service.py install   # Install service
            python run_monitor_service.py start      # Start service
            python run_monitor_service.py stop       # Stop service
            python run_monitor_service.py remove     # Remove service

        Or use Windows Service Manager (services.msc)
        """

        _svc_name_ = "CrawlerMonitor"
        _svc_display_name_ = "Crawler Folder Monitor"
        _svc_description_ = (
            "Monitors local folder for Excel files and processes them "
            "with classification and cross-reference engines"
        )

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.monitor = None
            self.is_running = False

        def SvcStop(self):
            """Handle service stop request."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            self.is_running = False

            if self.monitor:
                self.monitor.stop()

        def SvcDoRun(self):
            """Run the service main loop."""
            # Log service start
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )

            self.is_running = True

            try:
                # Load configuration
                watch_dir, output_dir, processor_config = load_config()

                servicemanager.LogInfoMsg(
                    f"Monitor configuration: watch={watch_dir}, output={output_dir}"
                )

                # Create monitor
                self.monitor = FileMonitor(
                    watch_dir=watch_dir,
                    output_dir=output_dir,
                    processor_config=processor_config
                )

                # Start monitoring (non-blocking version for service)
                self._run_service_mode()

            except Exception as e:
                servicemanager.LogErrorMsg(f"Service error: {e}")
                raise

            finally:
                # Log service stop
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, '')
                )

        def _run_service_mode(self):
            """
            Run monitor in service mode (non-blocking).
            Checks stop_event periodically instead of blocking forever.
            """
            import time
            from watchdog.observers import Observer
            from monitor import ExcelFileHandler

            try:
                # Validate directories
                watch_path = Path(self.monitor.watch_dir)
                if not watch_path.exists():
                    raise FileNotFoundError(f"Watch directory not found: {watch_path}")

                output_path = Path(self.monitor.output_dir)
                if not output_path.exists():
                    output_path.mkdir(parents=True, exist_ok=True)

                # Initialize processor
                self.monitor._initialize_processor()

                # Start observer
                observer = Observer()
                handler = ExcelFileHandler(
                    self.monitor._process_file,
                    self.monitor.should_process,
                    self.monitor.logger
                )
                observer.schedule(handler, str(watch_path), recursive=False)
                observer.start()

                servicemanager.LogInfoMsg(
                    f"Monitor started: watching {watch_path}"
                )

                # Service loop: check stop event every second
                while self.is_running:
                    rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                    if rc == win32event.WAIT_OBJECT_0:
                        break

                # Shutdown
                observer.stop()
                observer.join(timeout=5)
                servicemanager.LogInfoMsg("Monitor stopped")

            except Exception as e:
                servicemanager.LogErrorMsg(f"Service monitor error: {e}")
                raise


    def run_windows_service():
        """Handle Windows Service commands."""
        win32serviceutil.HandleCommandLine(CrawlerMonitorService)

    HAS_WINDOWS_SERVICE = True

except ImportError:
    HAS_WINDOWS_SERVICE = False

    def run_windows_service():
        """Fallback if pywin32 not installed."""
        print("ERROR: Windows Service support requires pywin32")
        print("Install with: pip install pywin32")
        print("Then run: python -m pip install pywin32 (for proper installation)")
        sys.exit(1)


if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        # Windows Service commands
        if cmd in ('install', 'remove', 'start', 'stop', 'restart', 'debug'):
            if not HAS_WINDOWS_SERVICE:
                run_windows_service()
            else:
                try:
                    run_windows_service()
                except Exception as e:
                    print(f"Service command failed: {e}")
                    sys.exit(1)

        # Help
        elif cmd in ('--help', '-h', 'help'):
            print("""
Crawler Folder Monitor v2.0

Usage:
    python run_monitor_service.py              # Run directly (for testing)
    python run_monitor_service.py install      # Install as Windows Service
    python run_monitor_service.py start        # Start Windows Service
    python run_monitor_service.py stop         # Stop Windows Service
    python run_monitor_service.py restart      # Restart Windows Service
    python run_monitor_service.py remove       # Remove Windows Service
    python run_monitor_service.py debug        # Run in debug mode
    python run_monitor_service.py --help       # Show this help

Environment Variables (override config.py):
    WATCH_DIRECTORY        # Directory to monitor
    OUTPUT_DIRECTORY       # Directory for results
    LEARNING_MODE         # true/false (default: true)
    MIN_OCCURRENCES       # Min keyword occurrences (default: 5)
    CONFIDENCE_THRESHOLD  # Confidence threshold (default: 0.7)

Examples:
    # Monitor custom directory
    set WATCH_DIRECTORY=D:\\input
    python run_monitor_service.py

    # Install service with custom paths
    set WATCH_DIRECTORY=D:\\input
    python run_monitor_service.py install
            """.strip())

        else:
            print(f"Unknown command: {cmd}")
            print("Run with --help for usage information")
            sys.exit(1)

    else:
        # No arguments — run directly
        main()
