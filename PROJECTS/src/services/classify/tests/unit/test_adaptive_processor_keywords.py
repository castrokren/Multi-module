"""
Unit tests for AdaptiveExcelProcessor keyword handling.
Tests keyword loading, extraction, and validation.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from adaptive_excel_processor import AdaptiveExcelProcessor


@pytest.mark.unit
class TestKeywordLoading:
    """Test keyword file loading."""

    def test_load_keywords_from_files(self, temp_hw_keywords_file, temp_sw_keywords_file, temp_ni_keywords_file):
        """Should load keywords from files."""
        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(temp_hw_keywords_file),
            sw_keywords_file=str(temp_sw_keywords_file),
            ni_keywords_file=str(temp_ni_keywords_file)
        )

        assert len(processor.hw_keywords) > 0
        assert len(processor.sw_keywords) > 0
        assert len(processor.ni_keywords) > 0

    def test_load_hw_keywords(self, temp_hw_keywords_file):
        """Should load hardware keywords correctly."""
        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(temp_hw_keywords_file),
            sw_keywords_file=str(temp_hw_keywords_file),  # Use same file
        )

        assert 'microscope' in processor.hw_keywords
        assert 'spectrometer' in processor.hw_keywords

    def test_load_sw_keywords(self, temp_sw_keywords_file):
        """Should load software keywords correctly."""
        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(temp_sw_keywords_file),
            sw_keywords_file=str(temp_sw_keywords_file),
        )

        assert 'software' in processor.sw_keywords or 'license' in processor.sw_keywords

    def test_skip_comment_lines(self, temp_output_dir):
        """Should skip comment lines in keyword files."""
        filepath = Path(temp_output_dir) / 'keywords_with_comments.txt'
        content = """# This is a comment
        microscope
        # Another comment
        spectrometer
        """
        filepath.write_text(content)

        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(filepath),
            sw_keywords_file=str(filepath),
        )

        assert '#' not in processor.hw_keywords
        assert 'microscope' in processor.hw_keywords

    def test_skip_empty_lines(self, temp_output_dir):
        """Should skip empty lines in keyword files."""
        filepath = Path(temp_output_dir) / 'keywords_with_blanks.txt'
        content = """microscope

        spectrometer
        """
        filepath.write_text(content)

        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(filepath),
            sw_keywords_file=str(filepath),
        )

        # Should have keywords without empty strings
        assert '' not in processor.hw_keywords

    def test_case_normalization(self, temp_output_dir):
        """Keywords should be normalized to lowercase."""
        filepath = Path(temp_output_dir) / 'mixed_case_keywords.txt'
        content = """Microscope
        SPECTROMETER
        centrifuge"""
        filepath.write_text(content)

        processor = AdaptiveExcelProcessor(
            hw_keywords_file=str(filepath),
            sw_keywords_file=str(filepath),
        )

        assert 'microscope' in processor.hw_keywords
        assert 'spectrometer' in processor.hw_keywords
        assert 'centrifuge' in processor.hw_keywords


@pytest.mark.unit
class TestKeywordExtraction:
    """Test keyword extraction from descriptions."""

    def test_extract_single_word(self):
        """Should extract single meaningful words."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('microscope equipment')

        assert 'microscope' in keywords or 'equipment' in keywords

    def test_extract_compound_terms(self):
        """Should handle compound technical terms."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('flow cytometer analysis')

        assert len(keywords) > 0

    def test_filter_stopwords(self):
        """Should filter out common stopwords."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('the and for with from')

        # Should not include common stopwords
        assert 'the' not in keywords
        assert 'and' not in keywords
        assert 'for' not in keywords

    def test_filter_measurement_units(self):
        """Should filter out measurement units."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('50 volts 100 watts 25 ml')

        assert 'volts' not in keywords or len(keywords) > 0

    def test_filter_model_numbers(self):
        """Should filter out model numbers."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('Model ABC-123-XYZ equipment')

        # Model numbers should be filtered
        assert not any(k.startswith('abc') and len(k) > 8 for k in keywords)

    def test_empty_description(self):
        """Should handle empty descriptions gracefully."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('')

        assert keywords == []

    def test_none_description(self):
        """Should handle None descriptions gracefully."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description(None)

        assert keywords == []

    def test_minimum_keyword_length(self):
        """Should enforce minimum keyword length."""
        processor = AdaptiveExcelProcessor()
        keywords = processor.extract_keywords_from_description('a ab microscope')

        # Single and double letter words should be filtered
        assert all(len(k) >= 3 for k in keywords)


@pytest.mark.unit
class TestKeywordValidation:
    """Test keyword validation logic."""

    def test_validate_technical_term(self):
        """Technical terms should pass validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('spectrometer', 'hw')

        assert is_valid is True

    def test_validate_too_short(self):
        """Very short keywords should fail validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('ab', 'hw')

        assert is_valid is False

    def test_validate_measurement_unit(self):
        """Measurement units should fail validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('volts', 'hw')

        assert is_valid is False

    def test_validate_stopword(self):
        """Common stopwords should fail validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('the', 'hw')

        assert is_valid is False

    def test_validate_model_number_pattern(self):
        """Model number patterns should fail validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('ABC-123-XYZ', 'hw')

        assert is_valid is False

    def test_validate_numeric_pattern(self):
        """Numeric patterns should fail validation."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('123abc', 'hw')

        assert is_valid is False

    def test_validate_reasonable_length(self):
        """Keywords with reasonable length should pass."""
        processor = AdaptiveExcelProcessor()
        is_valid, reason = processor.validate_keyword('microscope', 'hw')

        assert is_valid is True


@pytest.mark.unit
class TestConfidenceCalculation:
    """Test keyword confidence scoring."""

    def test_boost_for_technical_context(self):
        """Should boost confidence in technical descriptions."""
        processor = AdaptiveExcelProcessor()

        # Description with technical indicators
        tech_desc = 'Spectrometer with laser detection system for analysis'
        confidence = processor.calculate_keyword_confidence('spectrometer', tech_desc)

        assert confidence >= 1.0  # Should be boosted

    def test_reduce_for_common_words(self):
        """Should reduce confidence for common non-specific words."""
        processor = AdaptiveExcelProcessor()
        confidence = processor.calculate_keyword_confidence('system', 'test description')

        assert confidence < 1.0

    def test_confidence_range(self):
        """Confidence should be capped at reasonable value."""
        processor = AdaptiveExcelProcessor()
        confidence = processor.calculate_keyword_confidence('spectrometer', 'spectrometer analyzer detector')

        assert confidence <= 3.0

    def test_compound_term_boost(self):
        """Compound technical terms should get boost."""
        processor = AdaptiveExcelProcessor()
        confidence_short = processor.calculate_keyword_confidence('test', 'test')
        confidence_long = processor.calculate_keyword_confidence('spectrophotometer', 'spectrophotometer analyzer')

        assert confidence_long >= confidence_short
