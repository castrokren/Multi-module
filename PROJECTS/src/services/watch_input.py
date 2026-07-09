#!/usr/bin/env python3
"""
Input Directory Watcher
=======================
Watches the pipeline input directory (paths.input_excel_dir in
pipeline_config.json) and runs the full pipeline whenever new input
files arrive.

New events during a pipeline run are queued: the pipeline runs again
once, after the current run finishes. Rapid multi-file drops are
coalesced by a debounce window so one drop of N files = one run.

Usage
-----
    python watch_input.py               # watch + run pipeline on changes
    python watch_input.py --once        # process pending changes and exit

Run automatically at boot (Task Scheduler, run as your user):
    schtasks /create /tn "CrawlerInputWatcher" /sc onlogon ^
        /tr "\"<python.exe>\" \"<this file>\""
"""

import argparse
import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ROOT = Path(__file__).resolve().parent
INPUT_SUFFIXES = (".csv", ".xlsx", ".xls")
# ponytail: fixed 30s debounce covers slow copies of typical input files;
# make it a config knob if drops ever exceed that
DEBOUNCE_SECONDS = 30


def _load_input_dir() -> Path:
    cfg = json.loads((ROOT / "pipeline_config.json").read_text(encoding="utf-8"))
    return Path(cfg["paths"]["input_excel_dir"])


class _InputHandler(FileSystemEventHandler):
    """Sets a flag on any relevant file event; the main loop does the rest."""

    def __init__(self):
        self.trigger = threading.Event()

    def on_any_event(self, event):
        path = str(getattr(event, "dest_path", "") or getattr(event, "src_path", ""))
        if event.is_directory or not path.lower().endswith(INPUT_SUFFIXES):
            return
        if Path(path).name.startswith("~$"):  # Excel lock files
            return
        logging.info("Input change detected: %s", path)
        self.trigger.set()


def run_pipeline() -> int:
    """Run the pipeline as a subprocess so a crash never kills the watcher."""
    logging.info("Starting pipeline run...")
    t0 = time.time()
    result = subprocess.run([sys.executable, str(ROOT / "pipeline.py")], cwd=str(ROOT))
    logging.info("Pipeline finished in %.0f s (exit code %d)",
                 time.time() - t0, result.returncode)
    return result.returncode


def watch(input_dir: Path, once: bool = False):
    handler = _InputHandler()
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=False)
    observer.start()
    logging.info("Watching %s (debounce %ds)", input_dir, DEBOUNCE_SECONDS)

    try:
        while True:
            if not handler.trigger.wait(timeout=60):
                if once:
                    logging.info("No pending changes - exiting (--once)")
                    return
                continue
            # Debounce: wait until the directory has been quiet for a while,
            # so one drop of many files (or a slow copy) becomes one run.
            while True:
                handler.trigger.clear()
                time.sleep(DEBOUNCE_SECONDS)
                if not handler.trigger.is_set():
                    break
            run_pipeline()
            # Events that arrived during the run left trigger set - the
            # loop naturally runs again for them.
            if once:
                return
    except KeyboardInterrupt:
        logging.info("Stopping watcher")
    finally:
        observer.stop()
        observer.join()


def main():
    parser = argparse.ArgumentParser(description="Watch input dir, run pipeline on changes")
    parser.add_argument("--once", action="store_true",
                        help="process pending changes then exit (for scheduled runs)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.FileHandler(ROOT / "watch_input.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    input_dir = _load_input_dir()
    if not input_dir.is_dir():
        logging.error("Input directory not found: %s", input_dir)
        sys.exit(1)
    watch(input_dir, once=args.once)


if __name__ == "__main__":
    main()
