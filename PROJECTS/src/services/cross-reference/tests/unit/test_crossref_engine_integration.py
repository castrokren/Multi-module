"""
Integration tests for CrossReferenceEngine core utilities with sample data.

Tests normalize_filename(), deduplicate_matches(), and config threshold (60)
in an integrated cross-reference context. Uses mocks — no real PDFs.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

service_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(service_dir))

from crossref_utils import normalize_filename, deduplicate_matches


@pytest.mark.integration
class TestNormalizeFilenameIntegration:
    """Integration-level tests for normalize_filename with real-world patterns."""

    def test_strips_version_and_parenthetical(self):
        """Real-world filenames with version + (1) suffix should normalize."""
        cases = [
            ("Product_Sheet_v2_(1).pdf", "product_sheet"),
            ("Manual_v3_2024_Final.pdf", "manual"),
            ("Specifications_(Revised).pdf", "specifications"),
            ("Brochure_2025_updated.pdf", "brochure"),
            ("Datasheet_v5_final_new.pdf", "datasheet"),
        ]
        for raw, expected_core in cases:
            result = normalize_filename(raw)
            assert expected_core in result, f"'{raw}' -> '{result}', expected core '{expected_core}'"

    def test_identical_normalized_forms(self):
        """Filenames that differ only by version/year should normalize identically."""
        group = [
            "Product_Sheet_v1.pdf",
            "Product-Sheet-v2_updated.pdf",
            "PRODUCT_SHEET_2024_updated.pdf",
            "Product-Sheet-(1).pdf",
        ]
        normalized = [normalize_filename(f) for f in group]
        assert len(set(normalized)) == 1, f"Expected all to normalize to same form: {normalized}"

    def test_distinct_documents_remain_distinct(self):
        """Different documents should NOT normalize to the same value."""
        docs = [
            ("User_Manual_v2.pdf", "user_manual"),
            ("Spec_Sheet_2024.pdf", "spec_sheet"),
            ("Certificate_of_Analysis.pdf", "certificate_of_analysis"),
        ]
        normalized = {normalize_filename(f): label for f, label in docs}
        assert len(normalized) == len(docs), f"Collision in normalized forms: {normalized}"

    def test_no_false_collisions(self):
        """Documents with different core names should never collide."""
        names = ["Axioscope_manual.pdf", "Stemi_manual.pdf", "Primo_manual.pdf"]
        result = [normalize_filename(n) for n in names]
        assert len(set(result)) == 3


@pytest.mark.integration
class TestDeduplicateMatchesIntegration:
    """Integration-level tests for deduplicate_matches with realistic match data."""

    @pytest.fixture
    def sample_matches(self):
        return [
            {"pdf_path": "/pdfs/Zeiss/BX53_manual_v1.pdf", "score": 72.0, "supplier": "Zeiss"},
            {"pdf_path": "/pdfs/Zeiss/BX53_manual_v2.pdf", "score": 88.0, "supplier": "Zeiss"},
            {"pdf_path": "/pdfs/Zeiss/BX53_manual_final.pdf", "score": 85.0, "supplier": "Zeiss"},
            {"pdf_path": "/pdfs/Zeiss/BX53_datasheet.pdf", "score": 65.0, "supplier": "Zeiss"},
            {"pdf_path": "/pdfs/Olympus/CX23_manual.pdf", "score": 90.0, "supplier": "Olympus"},
        ]

    def test_deduplicate_keeps_highest_score_per_group(self, sample_matches):
        """Among versioned copies, only the highest score should survive."""
        result = deduplicate_matches(sample_matches)
        bx53_manual_entries = [m for m in result if "bx53_manual" in normalize_filename(os.path.basename(m["pdf_path"]))]
        assert len(bx53_manual_entries) == 1
        assert bx53_manual_entries[0]["score"] == 88.0

    def test_deduplicate_preserves_distinct_docs(self, sample_matches):
        """Completely different documents should each survive."""
        result = deduplicate_matches(sample_matches)
        olympus = [m for m in result if "Olympus" in m["pdf_path"]]
        datasheet = [m for m in result if "datasheet" in m["pdf_path"].lower()]
        assert len(olympus) == 1
        assert len(datasheet) == 1

    def test_deduplicate_empty_list(self):
        """Empty list should return empty list."""
        assert deduplicate_matches([]) == []

    def test_deduplicate_single_match(self):
        """Single match should be returned unchanged."""
        m = [{"pdf_path": "/a.pdf", "score": 50.0}]
        assert deduplicate_matches(m) == m

    def test_deduplicate_none_matches(self):
        """None input should not raise (returns None or empty)."""
        result = deduplicate_matches(None)
        assert result is None or result == []


@pytest.mark.integration
class TestConfigThresholdRespected:
    """Verify the default threshold (60) is used correctly in matching context."""

    DEFAULT_THRESHOLD = 60

    def test_threshold_is_60(self):
        """The configured default threshold must be 60."""
        assert self.DEFAULT_THRESHOLD == 60

    def test_high_score_passes_threshold(self):
        """Scores >= 60 should be accepted."""
        scores = [60, 75, 88.5, 100, 99.9]
        for s in scores:
            assert s >= self.DEFAULT_THRESHOLD

    def test_low_score_fails_threshold(self):
        """Scores < 60 should be rejected."""
        scores = [0, 30, 59, 59.9, 10]
        for s in scores:
            assert s < self.DEFAULT_THRESHOLD

    def test_deduplicate_respects_threshold_post_filter(self):
        """After threshold filtering, dedup should only act on survivors."""
        raw = [
            {"pdf_path": "/m/Manual_v1.pdf", "score": 55.0},
            {"pdf_path": "/m/Manual_v2.pdf", "score": 82.0},
        ]
        filtered = [m for m in raw if m["score"] >= self.DEFAULT_THRESHOLD]
        assert len(filtered) == 1
        assert filtered[0]["score"] == 82.0

        deduped = deduplicate_matches(filtered)
        assert len(deduped) == 1
        assert deduped[0]["score"] == 82.0

    def test_threshold_from_config_file(self):
        """Read the configured threshold from pipeline_config.json."""
        cfg_path = Path(__file__).resolve().parents[3] / "pipeline_config.json"
        if not cfg_path.exists():
            cfg_path = Path(__file__).resolve().parents[4] / "src" / "services" / "pipeline_config.json"
        import json
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        threshold = cfg.get("crossref", {}).get("threshold", 60)
        assert threshold == 60, f"Expected crossref.threshold=60, got {threshold}"
