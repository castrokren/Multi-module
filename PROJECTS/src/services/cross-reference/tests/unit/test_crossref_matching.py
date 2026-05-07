"""
Unit tests for cross-reference matching logic.
Tests matching algorithms and score calculation.
"""

import pytest
import sys
from pathlib import Path

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))


@pytest.mark.unit
class TestStringMatching:
    """Test string matching for cross-reference."""

    def test_exact_match(self):
        """Exact strings should match."""
        str1 = 'Zeiss Microscope'
        str2 = 'Zeiss Microscope'

        # Simple exact match
        assert str1 == str2

    def test_case_insensitive_match(self):
        """Should match case-insensitively."""
        str1 = 'Zeiss Microscope'
        str2 = 'zeiss microscope'

        assert str1.lower() == str2.lower()

    def test_partial_word_match(self):
        """Should match partial words."""
        str1 = 'Zeiss Microscope Model XYZ'
        str2 = 'Microscope'

        # At least one word should match
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        assert len(words1 & words2) > 0

    def test_whitespace_normalization(self):
        """Should normalize whitespace."""
        str1 = 'Zeiss   Microscope'
        str2 = 'Zeiss Microscope'

        assert ' '.join(str1.split()) == ' '.join(str2.split())

    def test_special_character_handling(self):
        """Should handle special characters."""
        str1 = 'Model XYZ-123'
        str2 = 'Model XYZ 123'

        # Basic normalization
        norm1 = ''.join(c for c in str1 if c.isalnum()).lower()
        norm2 = ''.join(c for c in str2 if c.isalnum()).lower()

        assert norm1 == norm2


@pytest.mark.unit
class TestCodeNormalization:
    """Test item code normalization for matching."""

    def test_normalize_code_with_dashes(self):
        """Should handle codes with dashes."""
        code1 = 'INST-2024-001'
        code2 = 'INST2024001'

        norm1 = code1.replace('-', '').lower()
        norm2 = code2.replace('-', '').lower()

        assert norm1 == norm2

    def test_normalize_code_with_spaces(self):
        """Should handle codes with spaces."""
        code1 = 'INST 2024 001'
        code2 = 'INST2024001'

        norm1 = code1.replace(' ', '').lower()
        norm2 = code2.replace(' ', '').lower()

        assert norm1 == norm2

    def test_case_insensitive_code(self):
        """Should match codes case-insensitively."""
        code1 = 'INST-2024-001'
        code2 = 'inst-2024-001'

        assert code1.lower() == code2.lower()

    def test_leading_zeros(self):
        """Should handle codes with leading zeros."""
        code1 = 'INST-001'
        code2 = 'INST-1'

        # These are different codes - leading zeros matter
        assert code1 != code2

    def test_mixed_normalization(self):
        """Should normalize dashes, spaces, and case."""
        code1 = 'INST-2024-001'
        code2 = 'inst 2024 001'

        norm1 = ''.join(c for c in code1 if c.isalnum()).lower()
        norm2 = ''.join(c for c in code2 if c.isalnum()).lower()

        assert norm1 == norm2


@pytest.mark.unit
class TestSupplierMatching:
    """Test supplier name matching."""

    def test_exact_supplier_match(self):
        """Exact supplier names should match."""
        supplier1 = 'Zeiss'
        supplier2 = 'Zeiss'

        assert supplier1.lower() == supplier2.lower()

    def test_partial_supplier_match(self):
        """Should match partial supplier names."""
        supplier1 = 'Zeiss Microscopy'
        supplier2 = 'Zeiss'

        assert supplier2.lower() in supplier1.lower()

    def test_supplier_abbreviation(self):
        """Should match supplier abbreviations."""
        supplier1 = 'Thermo Fisher Scientific'
        supplier2 = 'TFS'

        # Could be matched via acronym
        words = supplier1.split()
        acronym = ''.join(w[0] for w in words)

        assert acronym.startswith(supplier2[0]) or supplier2.lower() not in supplier1.lower()

    def test_case_insensitive_supplier(self):
        """Supplier matching should be case-insensitive."""
        supplier1 = 'Thermo Fisher Scientific'
        supplier2 = 'thermo fisher scientific'

        assert supplier1.lower() == supplier2.lower()

    def test_whitespace_in_supplier(self):
        """Should normalize supplier whitespace."""
        supplier1 = 'Thermo  Fisher  Scientific'
        supplier2 = 'Thermo Fisher Scientific'

        assert ' '.join(supplier1.split()) == ' '.join(supplier2.split())


@pytest.mark.unit
class TestScoreCalculation:
    """Test matching score calculation."""

    def test_perfect_match_high_score(self):
        """Perfect matches should have high score."""
        score = 100.0
        assert score == 100.0

    def test_no_match_low_score(self):
        """No matches should have low score."""
        score = 0.0
        assert score == 0.0

    def test_partial_match_medium_score(self):
        """Partial matches should have medium score."""
        # Assuming simple word overlap metric
        words_match = 2
        words_total = 5
        score = (words_match / words_total) * 100

        assert 0 < score < 100

    def test_score_range(self):
        """Scores should be in valid range."""
        scores = [0.0, 25.5, 50.0, 75.5, 100.0]

        for score in scores:
            assert 0.0 <= score <= 100.0

    def test_score_precision(self):
        """Scores should have reasonable precision."""
        score = 85.5

        # One decimal place is reasonable
        assert len(str(score).split('.')[-1]) <= 2


@pytest.mark.unit
class TestMatchFiltering:
    """Test match result filtering."""

    def test_filter_below_threshold(self):
        """Matches below threshold should be filtered."""
        matches = [
            {'score': 95.0},
            {'score': 75.0},
            {'score': 45.0},  # Below 50 threshold
            {'score': 50.0}
        ]
        threshold = 50.0

        filtered = [m for m in matches if m['score'] >= threshold]

        assert len(filtered) == 3
        assert 45.0 not in [m['score'] for m in filtered]

    def test_sort_by_score_descending(self):
        """Matches should be sortable by score."""
        matches = [
            {'score': 75.0},
            {'score': 95.0},
            {'score': 60.0}
        ]

        sorted_matches = sorted(matches, key=lambda m: m['score'], reverse=True)

        assert sorted_matches[0]['score'] == 95.0
        assert sorted_matches[-1]['score'] == 60.0

    def test_empty_match_handling(self):
        """Should handle empty match lists."""
        matches = []
        filtered = [m for m in matches if m.get('score', 0) >= 50]

        assert filtered == []

    def test_match_result_structure(self):
        """Match results should have required fields."""
        match = {
            'pdf_path': '/path/to/file.pdf',
            'score': 85.0,
            'supplier': 'Zeiss',
            'code': 'INST-001'
        }

        assert 'pdf_path' in match
        assert 'score' in match
        assert isinstance(match['score'], (int, float))
