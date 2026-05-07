# monitor_folder.py (updated to ignore already labeled files)

from pathlib import Path
import subprocess
import sys
import time
from watchdog.observers import Observer  # pyright: ignore[reportMissingImports]
from watchdog.events import FileSystemEventHandler  # pyright: ignore[reportMissingImports]

# === CONFIGURATION ===
WATCH_DIR = Path(r"Y:\SOM_in")  # Watch the specific folder
SCRIPT_PATH = Path(r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify\classify_and_clean_dynamic.py")  # Current script location

class ExcelEventHandler(FileSystemEventHandler):
    """Handles new or modified .xls and .xlsx files in the watched directory."""
    def should_process(self, path_str: str) -> bool:
        path = Path(path_str)
        # ignore temporary and already processed files
        if path.name.startswith('~$'):
            return False
        if path.stem.endswith('_labeled'):
            return False
        return path.suffix.lower() in ['.xls', '.xlsx']

    def process_file(self, file_path):
        print(f"Processing {file_path}...")
        result = subprocess.run([sys.executable, str(SCRIPT_PATH), file_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Successfully processed {file_path}")
        else:
            print(f"Error processing {file_path}:\n{result.stderr}")

    def on_created(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            print(f"[Created]  {event.src_path}")
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            print(f"[Modified] {event.src_path}")
            self.process_file(event.src_path)

if __name__ == "__main__":
    # Ensure dependencies
    try:
        import watchdog  # pyright: ignore[reportMissingImports]
    except ImportError:
        print("Please install watchdog: pip install watchdog")
        sys.exit(1)

    observer = Observer()
    observer.schedule(ExcelEventHandler(), str(WATCH_DIR), recursive=False)
    observer.start()
    print(f"Watching folder: {WATCH_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping watcher...")
        observer.stop()
    observer.join()
