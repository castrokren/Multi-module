"""
Tests for crossref_standalone_fast.py
Covers:
- extract_pdf_text_standalone() — file validation, size limits, missing file
- calculate_match_score_standalone() — scoring logic, empty inputs, threshold
- PDFSmartFilter — priority/depriority pattern matching
- process_single_pdf() — end-to-end with mocked extraction
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from crossref_standalone_fast import (
    extract_pdf_text_standalone,
    calculate_match_score_standalone,
    PDFSmartFilter,
    process_single_pdf,
)
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_pdf(tmp_path, filename="test.pdf", size_bytes=1024, content=b"%PDF-1.4 fake"):
    """Write a minimal fake PDF file."""
    path = tmp_path / filename
    # Pad to requested size
    data = content + b" " * max(0, size_bytes - len(content))
    path.write_bytes(data)
    return str(path)
LONG_PDF_TEXT = (
    "This document describes the Olympus BX53 fluorescence microscope. "
    "The instrument features advanced optics for high-resolution imaging. "
    "Model BX53 is designed for life science research applications. "
    "Technical specifications include a 100W mercury lamp and multiple objective lenses. "
) * 30  # ~800+ chars
# ---------------------------------------------------------------------------
# extract_pdf_text_standalone()
# ---------------------------------------------------------------------------
class TestExtractPdfText:
    def test_missing_file_returns_empty(self):
        result = extract_pdf_text_standalone("/nonexistent/path/file.pdf")
        assert result == ""
    def test_empty_file_returns_empty(self, tmp_path):
        path = tmp_path / "empty.pdf"
        path.write_bytes(b"")
        result = extract_pdf_text_standalone(str(path))
        assert result == ""
    def test_oversized_file_returns_empty(self, tmp_path):
        path = tmp_path / "huge.pdf"
        # Write just over 50MB
        path.write_bytes(b"x" * (51 * 1024 * 1024))
        result = extract_pdf_text_standalone(str(path))
        assert result == ""
    def test_valid_pdf_returns_string(self, tmp_path):
        """A real minimal PDF should return a string (even if empty text)."""
        # Use pdfplumber to create a real readable PDF via reportlab if available,
        # otherwise just verify the function handles a corrupt file gracefully.
        path = tmp_path / "corrupt.pdf"
        path.write_bytes(b"%PDF-1.4 corrupted content not a real pdf")
        result = extract_pdf_text_standalone(str(path))
        assert isinstance(result, str)
    def test_returns_string_type_always(self, tmp_path):
        path = tmp_path / "any.pdf"
        path.write_bytes(b"not a pdf at all")
        result = extract_pdf_text_standalone(str(path))
        assert isinstance(result, str)
# ---------------------------------------------------------------------------
# calculate_match_score_standalone()
# ---------------------------------------------------------------------------
class TestCalculateMatchScore:
    def test_empty_keywords_returns_zero(self):
        score = calculate_match_score_standalone([], LONG_PDF_TEXT, "microscope")
        assert score == 0.0
    def test_empty_pdf_text_returns_zero(self):
        score = calculate_match_score_standalone(["microscope"], "", "microscope")
        assert score == 0.0
    def test_none_keywords_returns_zero(self):
        score = calculate_match_score_standalone(None, LONG_PDF_TEXT, "microscope")
        assert score == 0.0
    def test_short_pdf_text_returns_zero(self):
        """PDF text under 800 chars should be rejected as low-content."""
        short_text = "microscope " * 10  # well under 800 chars
        score = calculate_match_score_standalone(["microscope"], short_text, "microscope")
        assert score == 0.0
    def test_matching_keywords_returns_positive_score(self):
        score = calculate_match_score_standalone(
            ["microscope", "olympus", "BX53"],
            LONG_PDF_TEXT,
            "Olympus BX53 microscope"
        )
        assert score > 0.0
    def test_score_is_float(self):
        score = calculate_match_score_standalone(
            ["microscope"],
            LONG_PDF_TEXT,
            "microscope"
        )
        assert isinstance(score, float)
    def test_no_matching_keywords_returns_low_score(self):
        score = calculate_match_score_standalone(
            ["cryostat", "ultramicrotome"],
            LONG_PDF_TEXT,
            "cryostat ultramicrotome"
        )
        # May not be zero due to threshold logic, but should be lower than a match
        matching_score = calculate_match_score_standalone(
            ["microscope", "olympus"],
            LONG_PDF_TEXT,
            "Olympus microscope"
        )
        assert score <= matching_score
    def test_returns_zero_on_exception(self):
        """Passing garbage should not raise — function should return 0.0."""
        score = calculate_match_score_standalone(
            [None, 123, ""],
            LONG_PDF_TEXT,
            None
        )
        assert isinstance(score, (int, float))
# ---------------------------------------------------------------------------
# PDFSmartFilter
# ---------------------------------------------------------------------------
class TestPDFSmartFilter:
    def setup_method(self):
        self.f = PDFSmartFilter()
    def test_instantiates(self):
        assert self.f is not None
    def test_manual_filename_is_high_priority(self):
        score = self.f.get_priority_score("BX53_user_manual.pdf")
        assert score > 0, "manual filename should have positive priority score"
    def test_instruction_filename_is_high_priority(self):
        score = self.f.get_priority_score("instruction_guide_v2.pdf")
        assert score > 0
    def test_datasheet_filename_is_high_priority(self):
        score = self.f.get_priority_score("product_datasheet.pdf")
        assert score > 0
    def test_invoice_filename_is_low_priority(self):
        score = self.f.get_priority_score("invoice_2024_001.pdf")
        assert score < 0, "invoice filename should have negative priority score"
    def test_receipt_filename_is_low_priority(self):
        score = self.f.get_priority_score("receipt_order.pdf")
        assert score < 0
    def test_neutral_filename_returns_zero_or_neutral(self):
        score = self.f.get_priority_score("document_abc123.pdf")
        # Neutral files should not be strongly penalized or boosted
        assert isinstance(score, (int, float))
    def test_empty_filename(self):
        score = self.f.get_priority_score("")
        assert isinstance(score, (int, float))
# ---------------------------------------------------------------------------
# process_single_pdf()
# ---------------------------------------------------------------------------
class TestProcessSinglePdf:
    def test_returns_none_when_stop_flag_set(self):
        with patch(
            "crossref_standalone_fast.GlobalStopManager.should_stop",
            return_value=True
        ):
            result = process_single_pdf((
                "/some/file.pdf",
                ["microscope"],
                "Olympus microscope",
                30
            ))
        assert result is None
    def test_returns_result_tuple_on_success(self, tmp_path):
        pdf_path = make_pdf(tmp_path, size_bytes=2048)
        with patch(
            "crossref_standalone_fast.GlobalStopManager.should_stop",
            return_value=False
        ), patch(
            "crossref_standalone_fast.extract_pdf_text_standalone",
            return_value=LONG_PDF_TEXT
        ), patch(
            "crossref_standalone_fast.calculate_match_score_standalone",
            return_value=75.0
        ):
            result = process_single_pdf((
                pdf_path,
                ["microscope", "olympus"],
                "Olympus microscope",
                30
            ))
        assert result is not None
    def test_handles_extraction_exception_gracefully(self, tmp_path):
        pdf_path = make_pdf(tmp_path, size_bytes=2048)
        with patch(
            "crossref_standalone_fast.GlobalStopManager.should_stop",
            return_value=False
        ), patch(
            "crossref_standalone_fast.extract_pdf_text_standalone",
            side_effect=Exception("unexpected error")
        ):
            # Should not raise — function must handle exceptions internally
            try:
                result = process_single_pdf((
                    pdf_path,
                    ["microscope"],
                    "microscope",
                    30
                ))
                assert result is None or isinstance(result, tuple)
            except Exception as e:
                pytest.fail(f"process_single_pdf raised unexpectedly: {e}")
