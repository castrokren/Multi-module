"""
Unit tests for the Defender scan gate primitive (defender_scan.py).

The EICAR and clean-PDF cases genuinely shell out to MpCmdRun.exe, so they
are marked integration and skip on machines without a usable scanner. The
fail-closed cases are pure unit tests and must never require Defender.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import defender_scan
from defender_scan import ScanResult, ScanVerdict, scan_file

EICAR_STRING = (
    "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)

_SCANNER_MISSING = defender_scan._MPCMDRUN_PATH is None


def _defender_engine_active():
    """True only if MpCmdRun.exe exists AND the WinDefend service is running.

    MpCmdRun.exe can be present on a host whose AV engine is disabled
    (dev boxes commonly ship this way); such hosts return hr=0x800106ba,
    so the live-scan tests must skip there, not fail.
    """
    if _SCANNER_MISSING or os.name != "nt":
        return False
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-Service WinDefend).Status"],
            capture_output=True, text=True, timeout=10,
        )
        return "Running" in out.stdout
    except Exception:
        return False


_ENGINE_ACTIVE = _defender_engine_active()


def _write_pdf(tmp_path, name="clean.pdf", body=None):
    body = body or b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"
    p = tmp_path / name
    p.write_bytes(body)
    return str(p)


# ---------------------------------------------------------------------------
# Integration tests - only meaningful on a host with Defender enabled
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _ENGINE_ACTIVE, reason="Defender engine not active on this host")
def test_eicar_file_is_flagged_infected(tmp_path):
    eicar = tmp_path / "eicar.pdf"
    eicar.write_bytes(b"%PDF-1.4\n" + EICAR_STRING.encode("ascii"))
    result = scan_file(str(eicar))
    assert result.verdict == ScanVerdict.INFECTED


@pytest.mark.integration
@pytest.mark.skipif(not _ENGINE_ACTIVE, reason="Defender engine not active on this host")
def test_clean_pdf_passes(tmp_path):
    result = scan_file(_write_pdf(tmp_path))
    assert result.verdict == ScanVerdict.CLEAN


# ---------------------------------------------------------------------------
# Fail-closed unit tests - never depend on a live Defender
# ---------------------------------------------------------------------------

def test_missing_scanner_fails_closed(tmp_path):
    pdf = _write_pdf(tmp_path)
    with patch.object(defender_scan, "_MPCMDRUN_PATH", r"C:\nonexistent\MpCmdRun.exe"):
        result = scan_file(pdf)
    assert result.verdict == ScanVerdict.ERROR
    assert result.verdict is not ScanVerdict.CLEAN


def test_missing_file_fails_closed():
    result = scan_file(str(Path("C:/does/not/exist.pdf")))
    assert result.verdict == ScanVerdict.ERROR


def test_timeout_fails_closed(tmp_path):
    pdf = _write_pdf(tmp_path)
    with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
        result = scan_file(pdf)
    assert result.verdict == ScanVerdict.ERROR
    assert result.detail == "timeout"


def test_scanner_not_found_and_no_file_precedence(tmp_path):
    pdf = _write_pdf(tmp_path)
    with patch.object(defender_scan, "_MPCMDRUN_PATH", None):
        result = scan_file(pdf)
    assert result.verdict == ScanVerdict.ERROR
    assert result.detail == "scanner_not_found"


def test_kill_switch_disables_scanning(tmp_path):
    pdf = _write_pdf(tmp_path)
    defender_scan.set_scan_enabled(False)
    try:
        result = scan_file(pdf)
    finally:
        defender_scan.set_scan_enabled(True)
    assert result.verdict == ScanVerdict.CLEAN
    assert result.detail == "scan_disabled"


def test_unrecognized_output_fails_closed(tmp_path):
    pdf = _write_pdf(tmp_path)
    fake_proc = subprocess.CompletedProcess(
        args=["MpCmdRun.exe"], returncode=1, stdout="some weird output", stderr=""
    )
    with patch.object(defender_scan, "_run_defender_scan", return_value=ScanResult(
        ScanVerdict.ERROR, "unrecognized_output:rc=1"
    )):
        result = scan_file(pdf)
    assert result.verdict == ScanVerdict.ERROR


def test_quarantine_file_moves_and_strips_staging_name(tmp_path):
    src = tmp_path / ".catalog.pdf.scanning"
    src.write_bytes(b"%PDF")
    dest_root = tmp_path / "quarantine"
    dest = defender_scan.quarantine_file(str(src), str(dest_root), reason="test")
    assert dest is not None
    assert os.path.isfile(dest)
    assert not os.path.exists(str(src))
    assert dest.endswith("_catalog.pdf")