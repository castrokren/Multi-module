#!/usr/bin/env python3
"""
Folder Monitor Service (Polling-based)
====================================
Watches input folder and runs pipeline automatically.
Uses polling instead of watchdog for better Windows compatibility.

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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FOLDER = PROJECT_ROOT / "data" / "som-in"
PIPELINE_SCRIPT = PROJECT_ROOT / "src" / "services" / "pipeline.py"

# If pipeline.py doesn't exist at PROJECT_ROOT, check if we're in a repo clone where PROJECTS is a subfolder
if not PIPELINE_SCRIPT.exists():
    repo_root = PROJECT_ROOT.parents[0]
    alt_pipeline = repo_root / "PROJECTS" / "src" / "services" / "pipeline.py"
    if alt_pipeline.exists():
        PROJECT_ROOT = repo_root / "PROJECTS"
        INPUT_FOLDER = PROJECT_ROOT / "data" / "som-in"
        PIPELINE_SCRIPT = alt_pipeline
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


def check_for_new_files():
    """Poll folder for new Excel files."""
    if not INPUT_FOLDER.exists():
        logger.error(f"Input folder not found: {INPUT_FOLDER}")
        return

    try:
        # Get all .xlsx files in the folder
        xlsx_files = list(INPUT_FOLDER.glob("*.xlsx"))

        for file_path in xlsx_files:
            file_path_str = str(file_path)
            file_name = file_path.name

            # Skip if already processed
            if file_path_str in last_processed_files:
                continue

            # Skip if pipeline is already running
            if pipeline_running:
                logger.info(f"⏳ Pipeline is already running, queueing file: {file_name}")
                continue

            # Wait a moment to ensure file is fully written
            time.sleep(2)

            # Process this file
            logger.info(f"📁 New Excel file detected: {file_name}")
            last_processed_files.add(file_path_str)
            logger.info(f"▶️  Starting pipeline for: {file_name}")

            pipeline_thread = threading.Thread(
                target=run_pipeline,
                args=(file_name,),
                daemon=True,
            )
            pipeline_thread.start()

    except Exception as e:
        logger.error(f"Error checking folder: {e}")


def start_monitor():
    """Start monitoring folder with polling."""
    if not INPUT_FOLDER.exists():
        logger.error(f"Input folder not found: {INPUT_FOLDER}")
        raise FileNotFoundError(f"Input folder does not exist: {INPUT_FOLDER}")

    logger.info("=" * 70)
    logger.info("🚀 PIPELINE FOLDER MONITOR STARTED (Polling Mode)")
    logger.info("=" * 70)
    logger.info(f"Watching folder: {INPUT_FOLDER}")
    logger.info(f"Poll interval: 5 seconds")
    logger.info(f"Dashboard: https://localhost")
    logger.info("=" * 70)

    try:
        logger.info("✅ Folder monitor is active")
        write_status()  # Write initial status

        # Keep polling
        while True:
            check_for_new_files()
            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        logger.info("⏹️  Stopping folder monitor (Ctrl+C)")

    except Exception as e:
        logger.error(f"❌ Monitor error: {e}")
        raise

    finally:
        logger.info("Folder monitor stopped")


if __name__ == "__main__":
    try:
        start_monitor()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
