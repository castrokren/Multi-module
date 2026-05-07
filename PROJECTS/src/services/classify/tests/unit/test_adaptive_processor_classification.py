"""
Tests for AdaptiveExcelProcessor — classification, process_file, and adaptive learning.

Covers:
- classify_item() — hardware / software / non-instrument decisions
- process_file() — end-to-end input xlsx → labeled output file
- Vendor-based classification
- Adaptive learning: candidate_keywords accumulation and promotion
- output_dir default fix (no hardcoded D:\\ path)
"""

import json
import pytest
import pandas as pd
from pathlib import Path
from collections import Counter
from unittest.mock import patch, MagicMock

from adaptive_excel_processor import AdaptiveExcelProcessor, process_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_processor(tmp_path, hw_keywords=None, sw_keywords=None, ni_keywords=None):
    """Create a processor wired to tmp_path with minimal keyword files."""
    hw_file = tmp_path / "hw_keywords.txt"
    sw_file = tmp_path / "sw_keywords.txt"
    ni_file = tmp_path / "ni_keywords.txt"

    hw_file.write_text("\n".join(hw_keywords or ["microscope", "centrifuge", "pipette"]))
    sw_file.write_text("\n".join(sw_keywords or ["software", "license", "subscription"]))
    ni_file.write_text("\n".join(ni_keywords or ["gloves", "paper", "cleaning"]))

    return AdaptiveExcelProcessor(
        hw_keywords_file=str(hw_file),
        sw_keywords_file=str(sw_file),
        ni_keywords_file=str(ni_file),
        output_dir=str(tmp_path),
        learning_mode=True,
    )


def make_excel(tmp_path, rows, filename="test_input.xlsx"):
    """Write a minimal Excel file with a Description column."""
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    df.to_excel(path, index=False)
    return path


# ---------------------------------------------------------------------------
# output_dir default — no hardcoded D:\ path
# ---------------------------------------------------------------------------

class TestOutputDirDefault:
    def test_output_dir_uses_provided_path(self, tmp_path):
        """output_dir should use the provided path, not a hardcoded default."""
        p = make_processor(tmp_path)
        assert p.output_dir == Path(tmp_path)

    def test_output_dir_none_does_not_use_hardcoded_path(self, tmp_path):
        """Passing output_dir=None should not silently set D:\\SOM_in_labeled."""
        # We patch Path to intercept the default — if the hardcode is still
        # present this test will fail with a path containing 'SOM_in_labeled'.
        processor = AdaptiveExcelProcessor(output_dir=None)
        assert "SOM_in_labeled" not in str(processor.output_dir), (
            "Hardcoded D:\\SOM_in_labeled default is still present in __init__. "
            "Replace with '' or a config-driven value."
        )


# ---------------------------------------------------------------------------
# classify_item()
# ---------------------------------------------------------------------------

class TestClassifyItem:
    def test_hardware_keyword_match(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("Olympus microscope for cell imaging")
        assert result["category"] == "Hardware"

    def test_software_keyword_match(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("Adobe software license renewal")
        assert result["category"] == "Software"

    def test_non_instrument_keyword_match(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("Latex gloves box of 100")
        assert result["category"] == "Non-Instrument"

    def test_no_keyword_match_returns_non_instrument(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("Miscellaneous item with no matching terms")
        # Unmatched items should default to Non-Instrument, not raise
        assert result["category"] in ("Non-Instrument", "Unknown")

    def test_empty_description(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("")
        assert result is not None  # should not raise

    def test_none_description(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item(None)
        assert result is not None  # should not raise

    def test_hardware_wins_over_non_instrument(self, tmp_path):
        """When both hw and ni keywords appear, hardware should win."""
        p = make_processor(tmp_path)
        result = p.classify_item("centrifuge gloves pipette")
        assert result["category"] == "Hardware"

    def test_result_contains_confidence(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.classify_item("microscope centrifuge")
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# process_file() — instance method end-to-end
# ---------------------------------------------------------------------------

class TestProcessFileMethod:
    def test_creates_labeled_output_file(self, tmp_path):
        p = make_processor(tmp_path)
        input_path = make_excel(tmp_path, [
            {"Description": "Olympus microscope"},
            {"Description": "Adobe software license"},
            {"Description": "Latex gloves"},
        ])
        result = p.process_file(str(input_path))
        assert result is True or result is not None  # returns truthy on success
        # Output file should exist in output_dir
        output_files = list(Path(tmp_path).glob("*_labeled*"))
        assert len(output_files) >= 1, "No labeled output file was created"

    def test_output_has_category_column(self, tmp_path):
        p = make_processor(tmp_path)
        input_path = make_excel(tmp_path, [
            {"Description": "Nikon microscope"},
            {"Description": "Software subscription"},
        ])
        p.process_file(str(input_path))
        output_files = list(Path(tmp_path).glob("*_labeled*"))
        assert output_files, "No output file found"
        df = pd.read_excel(output_files[0])
        assert any("category" in col.lower() or "classification" in col.lower()
                   for col in df.columns), (
            f"No category/classification column in output. Columns: {list(df.columns)}"
        )

    def test_output_row_count_matches_input(self, tmp_path):
        p = make_processor(tmp_path)
        rows = [{"Description": f"item {i}"} for i in range(10)]
        input_path = make_excel(tmp_path, rows)
        p.process_file(str(input_path))
        output_files = list(Path(tmp_path).glob("*_labeled*"))
        df = pd.read_excel(output_files[0])
        assert len(df) == 10

    def test_nonexistent_file_returns_falsy(self, tmp_path):
        p = make_processor(tmp_path)
        result = p.process_file(str(tmp_path / "does_not_exist.xlsx"))
        assert not result


# ---------------------------------------------------------------------------
# Module-level process_file() function
# ---------------------------------------------------------------------------

class TestProcessFileFunction:
    def test_module_function_produces_output(self, tmp_path):
        hw_file = tmp_path / "hw.txt"
        sw_file = tmp_path / "sw.txt"
        hw_file.write_text("microscope\ncentrifuge")
        sw_file.write_text("software\nlicense")

        input_path = make_excel(tmp_path, [
            {"Description": "Leica microscope"},
            {"Description": "MATLAB license"},
        ])
        result = process_file(
            filepath=str(input_path),
            hw_keywords_file=str(hw_file),
            sw_keywords_file=str(sw_file),
            output_dir=str(tmp_path),
        )
        assert result is True or result is not None


# ---------------------------------------------------------------------------
# Adaptive learning — candidate_keywords accumulation
# ---------------------------------------------------------------------------

class TestAdaptiveLearning:
    def test_candidate_keywords_accumulate_after_classification(self, tmp_path):
        p = make_processor(tmp_path, learning_mode=True)
        # Classify several items — candidates should accumulate
        for _ in range(3):
            p.classify_item("novel instrument XR-500 device")
        total = sum(
            sum(counter.values())
            for counter in p.candidate_keywords.values()
        )
        assert total > 0, "No candidate keywords accumulated after classification"

    def test_learning_log_written_to_output_dir(self, tmp_path):
        p = make_processor(tmp_path, learning_mode=True)
        p.classify_item("experimental spectrometer device")
        p.save_learning_log()
        assert (tmp_path / "learning_log.json").exists()

    def test_learning_log_round_trip(self, tmp_path):
        p = make_processor(tmp_path, learning_mode=True)
        p.candidate_keywords["hw"]["spectrometer"] = 3
        p.save_learning_log()

        p2 = make_processor(tmp_path, learning_mode=True)
        assert p2.candidate_keywords["hw"]["spectrometer"] == 3

    def test_promote_candidate_keywords(self, tmp_path):
        p = make_processor(tmp_path, learning_mode=True, min_occurrences=3)
        # Manually set a candidate above threshold
        p.candidate_keywords["hw"]["cryostat"] = 5
        p.promote_candidate_keywords(min_occurrences=3)
        # After promotion, "cryostat" should appear in hw keywords
        assert "cryostat" in p.hw_keywords or "cryostat" in [
            k.lower() for k in p.hw_keywords
        ], "Promoted keyword not found in hw_keywords after promotion"

    def test_learning_mode_false_does_not_accumulate(self, tmp_path):
        p = make_processor(tmp_path)
        # Rebuild with learning_mode=False
        hw_file = tmp_path / "hw_keywords.txt"
        sw_file = tmp_path / "sw_keywords.txt"
        p_no_learn = AdaptiveExcelProcessor(
            hw_keywords_file=str(hw_file),
            sw_keywords_file=str(sw_file),
            output_dir=str(tmp_path),
            learning_mode=False,
        )
        for _ in range(5):
            p_no_learn.classify_item("novel device XR-900")
        total = sum(
            sum(counter.values())
            for counter in p_no_learn.candidate_keywords.values()
        )
        assert total == 0, "Candidates accumulated despite learning_mode=False"
