"""Self-check for watch_input: N file drops -> one debounced pipeline run,
irrelevant files ignored. Run: python test_watch_input.py"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import watch_input


def demo():
    watch_input.DEBOUNCE_SECONDS = 1  # fast debounce for the test
    runs = []

    with tempfile.TemporaryDirectory() as d:
        watched = Path(d)

        with patch.object(watch_input, "run_pipeline", lambda: runs.append(time.time()) or 0):
            t = threading.Thread(
                target=watch_input.watch, args=(watched,), kwargs={"once": True}, daemon=True)
            t.start()
            time.sleep(1.0)  # let the observer start

            (watched / "notes.txt").write_text("ignore me")   # wrong suffix
            (watched / "~$lock.xlsx").write_text("ignore me")  # Excel lock file
            for i in range(3):                                 # burst of real inputs
                (watched / f"req_{i}.csv").write_text("Supplier Name,Item Description\n")
                time.sleep(0.2)

            t.join(timeout=10)
            assert not t.is_alive(), "watcher did not exit in --once mode"

    assert len(runs) == 1, f"expected exactly 1 coalesced run, got {len(runs)}"
    print("OK: 3 CSV drops + 2 irrelevant files -> 1 pipeline run")


if __name__ == "__main__":
    demo()
