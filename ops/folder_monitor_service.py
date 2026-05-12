#!/usr/bin/env python3
"""
Folder Monitor Service (Simplified)
====================================
Watches input folder and runs pipeline automatically.
Writes status files for dashboard to read.

Usage:
    python folder_monitor_service.py
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FOLDER = PROJECT_ROOT / "data" / "som-in"
PIPELINE_SCRIPT = PROJECT_ROOT / "src" / "services" / "pipeline.py"
LOG_FILE = PROJECT_ROOT / "src" / "services" / "cross-reference" / "results" / "monitor_service.log"
STATUS_FILE = PROJECT_ROOT / "src" / "services" / "cross-reference" / "results" / "status.json"
HISTORY_FILE = PROJECT_ROOT / "src" / "services" / "cross-reference" / "results" / "run_history.json"

# Setup logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("monitor_service")

# Global state
pipeline_running = False
last_processed_files = set()
run_count = 0


def write_status(stage: str = "", file: str = "", progress: int = 0):
    """Write current status to JSON file for dashboard."""
    try:
        status = {
            "running": pipeline_running,
            "stage": stage,
            "file": file,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f)
    except Exception as e:
        logger.error(f"Could not write status file: {e}")


def add_to_history(file: str, duration: float, success: bool):
    """Add completed run to history."""
    try:
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)

        # Keep only last 5 runs
        history.insert(0, {
            "time": datetime.now().isoformat(),
            "file": file,
            "duration": f"{int(duration/60)}m",
            "status": "success" if success else "failed"
        })
        history = history[:5]

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
    except Exception as e:
        logger.error(f"Could not write history file: {e}")


def run_pipeline(input_file: str) -> bool:
    """Execute the pipeline."""
    global pipeline_running, run_count

    run_count += 1
    pipeline_running = True
    write_status(stage="Starting", file=input_file, progress=5)

    logger.info("=" * 70)
    logger.info(f"RUN #{run_count}: PIPELINE STARTED")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        start_time = time.time()

        # Run pipeline
        result = subprocess.run(
            [sys.executable, str(PIPELINE_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            timeout=14400,  # 4 hours max
        )

        elapsed = time.time() - start_time
        success = result.returncode == 0

        if success:
            logger.info("=" * 70)
            logger.info(f"✅ PIPELINE SUCCESS (Run #{run_count})")
            logger.info(f"Completed in {elapsed/60:.1f} minutes")
            logger.info("=" * 70)
        else:
            logger.error("=" * 70)
            logger.error(f"❌ PIPELINE FAILED (Run #{run_count})")
            logger.error(f"Exit code: {result.returncode}")
            logger.error(f"Failed after {elapsed/60:.1f} minutes")
            logger.error("=" * 70)

        # Add to history
        add_to_history(input_file, elapsed, success)
        return success

    except subprocess.TimeoutExpired:
        logger.error("❌ Pipeline timeout (exceeded 4 hours)")
        add_to_history(input_file, 14400, False)
        return False

    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        add_to_history(input_file, 0, False)
        return False

    finally:
        pipeline_running = False
        write_status()


class ExcelFileHandler(FileSystemEventHandler):
    """Watch for new Excel files."""

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".xlsx"):
            return

        file_path = event.src_path
        file_name = os.path.basename(file_path)
        logger.info(f"📁 New Excel file detected: {file_name}")

        # Wait for file to be fully written
        time.sleep(2)

        # Skip if already processed
        if file_path in last_processed_files:
            logger.info(f"⏭️  File already processed, skipping: {file_name}")
            return

        # Skip if pipeline running
        if pipeline_running:
            logger.info(f"⏳ Pipeline is already running, queueing file: {file_name}")
            return

        # Run pipeline
        last_processed_files.add(file_path)
        logger.info(f"▶️  Starting pipeline for: {file_name}")

        pipeline_thread = threading.Thread(
            target=run_pipeline,
            args=(file_name,),
            daemon=True,
        )
        pipeline_thread.start()


def start_monitor():
    """Start watching input folder."""
    if not INPUT_FOLDER.exists():
        logger.error(f"Input folder not found: {INPUT_FOLDER}")
        raise FileNotFoundError(f"Input folder does not exist: {INPUT_FOLDER}")

    logger.info("=" * 70)
    logger.info("🚀 PIPELINE FOLDER MONITOR STARTED")
    logger.info("=" * 70)
    logger.info(f"Watching folder: {INPUT_FOLDER}")
    logger.info(f"Dashboard: https://localhost")
    logger.info("=" * 70)

    event_handler = ExcelFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INPUT_FOLDER), recursive=False)

    try:
        observer.start()
        logger.info("✅ Folder monitor is active")

        write_status()  # Write initial status

        # Keep running
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        logger.info("⏹️  Stopping folder monitor (Ctrl+C)")
        observer.stop()

    except Exception as e:
        logger.error(f"❌ Monitor error: {e}")
        observer.stop()
        raise

    finally:
        observer.join()
        logger.info("Folder monitor stopped")


if __name__ == "__main__":
    try:
        start_monitor()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
