"""
Windows Defender file-scan gate.

Wraps MpCmdRun.exe for a synchronous, single-file, targeted scan
(ScanType 3). Remediation is disabled on the CLI call so this module -
not Defender's default auto-quarantine - decides what happens to a
flagged file; callers move/quarantine it themselves after inspecting
the ScanResult.

Fail-closed: any condition other than a clean, understood "no threat"
result (scanner missing, timeout, unexpected output, non-zero exit
with unrecognized text) is returned as ScanVerdict.ERROR. Callers must
treat ERROR the same as INFECTED - never let an unscannable file pass.

The module carries two pieces of shared state the gates depend on:

- ``set_scan_enabled()``: hard kill-switch. When False, ``scan_file()``
  returns CLEAN("scan_disabled") so the pipeline keeps flowing. This is
  the only sanctioned way to bypass the control and flipping it requires
  the same sign-off as removing a Defender exclusion (docs/RUNBOOK.md).
- ``setup_security_logging()``: dedicated audit channel
  (``security.scan`` logger -> security_scan_<ts>.log) so every verdict
  is queryable independent of the main pipeline log.

This module has no sibling-service imports, so it is safe to load via
pipeline.py's ``_import_from_file`` dynamic-import pattern.
"""

import glob
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

_CANDIDATE_PATHS = [
    r"C:\Program Files\Windows Defender\MpCmdRun.exe",
]

_scan_enabled = True


class ScanVerdict(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


@dataclass
class ScanResult:
    verdict: ScanVerdict
    detail: str


def _discover_mpcmdrun() -> str | None:
    for p in _CANDIDATE_PATHS:
        if os.path.exists(p):
            return p
    platform_glob = (
        r"C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe"
    )
    matches = sorted(glob.glob(platform_glob))
    return matches[-1] if matches else None


_MPCMDRUN_PATH: str | None = _discover_mpcmdrun()

# ---------------------------------------------------------------------------
# Audit channel (Task 8) - one dedicated log file per run
# ---------------------------------------------------------------------------

security_logger = logging.getLogger("security.scan")
_security_handler_added = False


def setup_security_logging(log_dir: str) -> None:
    """Route the ``security.scan`` logger to security_scan_<ts>.log in log_dir.

    Idempotent: only the first call attaches the file handler, so repeated
    pipeline runs (or multiple modules calling this) never duplicate lines.
    """
    global _security_handler_added
    if _security_handler_added:
        return
    try:
        os.makedirs(log_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        handler = logging.FileHandler(
            os.path.join(log_dir, f"security_scan_{ts}.log"),
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s")
        )
        security_logger.addHandler(handler)
        security_logger.setLevel(logging.INFO)
        security_logger.propagate = False
        _security_handler_added = True
    except Exception as exc:
        logger.error("Could not set up security scan log: %s", exc)


def _log_verdict(path: str, result: ScanResult) -> None:
    line = "scan file=%s verdict=%s detail=%s" % (
        path, result.verdict.value, result.detail,
    )
    if result.verdict is ScanVerdict.CLEAN:
        security_logger.info(line)
    else:
        security_logger.error(line)


# ---------------------------------------------------------------------------
# Shared quarantine helper - one implementation for all three gates
# ---------------------------------------------------------------------------

def quarantine_file(path: str, dest_root: str, reason: str = "") -> str | None:
    """Move a flagged file into dest_root under its parent's name.

    Preserves the supplier folder (the parent directory name of ``path``)
    so a human can find the source vendor. A leading dot and a trailing
    ``.scanning`` staging suffix are stripped from the name. Returns the
    destination path, or None if the file could not be moved (it is then
    deleted rather than left in place).
    """
    if not path or not os.path.isfile(path):
        return None
    parent = os.path.basename(os.path.dirname(path)) or "unknown"
    qdir = os.path.join(dest_root, parent)
    try:
        os.makedirs(qdir, exist_ok=True)
    except Exception as exc:
        logger.error("Could not create quarantine dir %s: %s", qdir, exc)
        return None

    name = os.path.basename(path)
    while name.startswith("."):
        name = name[1:]
    if name.lower().endswith(".scanning"):
        name = name[: -len(".scanning")]

    dest = os.path.join(qdir, f"{int(time.time())}_{name}")
    try:
        os.replace(path, dest)
    except Exception as exc:
        logger.error("Quarantine move failed for %s: %s - deleting instead", path, exc)
        try:
            os.remove(path)
        except Exception:
            pass
        return None
    logger.error("Quarantined %s (%s) -> %s", path, reason, dest)
    return dest


# ---------------------------------------------------------------------------
# The scanning primitive
# ---------------------------------------------------------------------------

def _run_defender_scan(path: str, timeout: int) -> ScanResult:
    """Shell out to MpCmdRun.exe once and parse its output."""
    try:
        proc = subprocess.run(
            [
                _MPCMDRUN_PATH,
                "-Scan", "-ScanType", "3",
                "-File", path,
                "-DisableRemediation",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error("Defender scan timed out for %s", path)
        return ScanResult(ScanVerdict.ERROR, "timeout")
    except Exception as exc:
        logger.error("Defender scan failed to launch for %s: %s", path, exc)
        return ScanResult(ScanVerdict.ERROR, f"launch_failed:{exc}")

    output = f"{proc.stdout}\n{proc.stderr}".lower()

    # Text markers, not just exit code: MpCmdRun's exit-code mapping has
    # changed across platform updates, but these phrases have not. See the
    # plan's Task 1 validation step - confirm both markers against the exact
    # platform version on the target server before trusting this in prod.
    if "threat" in output and ("found" in output or "detected" in output):
        logger.warning("Defender flagged %s: %s", path, proc.stdout.strip())
        return ScanResult(ScanVerdict.INFECTED, proc.stdout.strip())

    if proc.returncode == 0 and "no threats" in output:
        return ScanResult(ScanVerdict.CLEAN, "no_threats")

    logger.error(
        "Defender scan of %s produced an unrecognized result (rc=%s) - "
        "failing closed. stdout=%r stderr=%r",
        path, proc.returncode, proc.stdout, proc.stderr,
    )
    return ScanResult(ScanVerdict.ERROR, f"unrecognized_output:rc={proc.returncode}")


def scan_file(path: str, timeout: int = 60) -> ScanResult:
    """Run a targeted Defender scan of a single file. Fail-closed."""
    if not _scan_enabled:
        result = ScanResult(ScanVerdict.CLEAN, "scan_disabled")
    elif _MPCMDRUN_PATH is None:
        logger.error("MpCmdRun.exe not found - failing closed for %s", path)
        result = ScanResult(ScanVerdict.ERROR, "scanner_not_found")
    elif not os.path.isfile(path):
        result = ScanResult(ScanVerdict.ERROR, "file_not_found")
    else:
        result = _run_defender_scan(path, timeout)

    _log_verdict(path, result)
    return result


def set_scan_enabled(enabled: bool) -> None:
    """Flip the global kill-switch (``security.malware_scan_enabled``)."""
    global _scan_enabled
    _scan_enabled = bool(enabled)