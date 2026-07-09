"""
Unit Tests for scraper_engine security-sensitive functions.

Covers:
- _sanitize_path path traversal protection
- _load_keywords graceful handling of missing files
- _validate_url basic checks

Run with: python -m pytest src/services/scraper-full/tests/unit/test_scraper_security.py -v -m unit
"""

import sys
import os
from pathlib import Path
import tempfile

import pytest
from unittest.mock import patch, MagicMock, mock_open


service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

from scraper_engine import (
    _sanitize_path,
    _load_keywords,
    _validate_url,
)


# ============================================================================
# _sanitize_path
# ============================================================================


class TestSanitizePath:
    @pytest.mark.unit
    def test_removes_dot_dot(self):
        assert ".." not in _sanitize_path("../outside.txt")

    @pytest.mark.unit
    def test_removes_multiple_dot_dots(self):
        assert ".." not in _sanitize_path("a/../../b")

    @pytest.mark.unit
    def test_replaces_backslash(self):
        result = _sanitize_path("folder\\malicious.exe")
        assert "\\" not in result
        assert "_" in result

    @pytest.mark.unit
    def test_replaces_forward_slash(self):
        result = _sanitize_path("folder/file.pdf")
        assert "/" not in result
        assert "_" in result

    @pytest.mark.unit
    def test_handles_dot_dot_slash_combinations(self):
        result = _sanitize_path("....//")
        for ch in [".", "/", "\\"]:
            assert ch not in result

    @pytest.mark.unit
    def test_returns_empty_for_empty_string(self):
        assert _sanitize_path("") == ""

    @pytest.mark.unit
    def test_removes_windows_special_chars(self):
        special = '<>:"|?*'
        result = _sanitize_path(f"file{special[0]}name")
        for ch in special:
            assert ch not in result

    @pytest.mark.unit
    def test_passes_through_normal_filename(self):
        normal = "product_catalog_2024.pdf"
        assert _sanitize_path(normal) == normal

    @pytest.mark.unit
    def test_passes_through_alphanumeric(self):
        normal = "Manual123.pdf"
        assert _sanitize_path(normal) == normal

    @pytest.mark.unit
    def test_handles_spaces(self):
        assert _sanitize_path("file name.pdf") == "file name.pdf"

    @pytest.mark.unit
    def test_handles_mixed_traversal(self):
        result = _sanitize_path("..\\..\\etc\\passwd")
        for bad in (".", "\\", "/"):
            assert bad not in result

    @pytest.mark.unit
    def test_unicode_normal(self):
        safe = _sanitize_path("résumé.pdf")
        assert "résumé.pdf" == safe


# ============================================================================
# _load_keywords — missing file handling
# ============================================================================


class TestLoadKeywords:
    @pytest.mark.unit
    def test_returns_empty_set_when_hardware_file_missing(self):
        with patch("scraper_engine.os.path.exists", return_value=False), \
             patch("scraper_engine.logger"):
            result = _load_keywords()
            assert result == set()

    @pytest.mark.unit
    def test_does_not_crash_when_software_file_missing(self):
        with patch("scraper_engine.os.path.exists") as mock_exists, \
             patch("scraper_engine.logger"):
            mock_exists.side_effect = [False, False]
            result = _load_keywords()
            assert result == set()

    @pytest.mark.unit
    def test_loads_keywords_from_existing_files(self):
        fake_content = "microscope\nspectrometer\n# comment\npipette\n"
        with patch("scraper_engine.os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=fake_content)), \
             patch("scraper_engine.logger"):
            result = _load_keywords()
            assert "microscope" in result
            assert "spectrometer" in result
            assert "pipette" in result
            assert "# comment" not in result
            assert "" not in result

    @pytest.mark.unit
    def test_keywords_stored_as_lowercase(self):
        fake_content = "Microscope\nSPECTROMETER\n"
        with patch("scraper_engine.os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=fake_content)), \
             patch("scraper_engine.logger"):
            result = _load_keywords()
            assert "microscope" in result
            assert "spectrometer" in result

    @pytest.mark.unit
    def test_loads_from_both_files(self):
        hw_content = "microscope\nspectrometer\n"
        sw_content = "software\nlicense\n"
        call_count = 0

        def mock_open_side(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_open(read_data=hw_content).return_value
            return mock_open(read_data=sw_content).return_value

        with patch("scraper_engine.os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=mock_open_side), \
             patch("scraper_engine.logger"):
            result = _load_keywords()
            assert result == {"microscope", "spectrometer", "software", "license"}

    @pytest.mark.unit
    def test_handles_read_error_gracefully(self):
        with patch("scraper_engine.os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=PermissionError), \
             patch("scraper_engine.logger") as mock_log:
            result = _load_keywords()
            assert result == set()
            assert mock_log.warning.called


# ============================================================================
# _validate_url — basic url validation
# ============================================================================


class TestValidateUrl:
    @pytest.mark.unit
    def test_valid_https_url(self):
        assert _validate_url("https://www.example.com") is True

    @pytest.mark.unit
    def test_valid_http_url(self):
        assert _validate_url("http://example.com/page") is True

    @pytest.mark.unit
    def test_rejects_localhost(self):
        assert _validate_url("http://localhost:8080") is False

    @pytest.mark.unit
    def test_rejects_loopback(self):
        assert _validate_url("http://127.0.0.1/admin") is False

    @pytest.mark.unit
    def test_rejects_empty_string(self):
        assert _validate_url("") is False

    @pytest.mark.unit
    def test_rejects_no_domain(self):
        assert _validate_url("http://") is False

    @pytest.mark.unit
    def test_rejects_ftp(self):
        assert _validate_url("ftp://files.example.com") is False

    @pytest.mark.unit
    def test_rejects_path_traversal(self):
        assert _validate_url("../../../etc/passwd") is False

    @pytest.mark.unit
    def test_accepts_url_with_port(self):
        assert _validate_url("https://example.com:8443/page") is True

    @pytest.mark.unit
    def test_accepts_subdomain(self):
        assert _validate_url("https://sub.domain.co.uk/path") is True
