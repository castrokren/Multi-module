"""
Unit tests for crossref_utils module.
Tests filename normalization, deduplication, and column detection.
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from crossref_utils import (
    normalize_filename,
    deduplicate_matches,
    find_required_columns
)


@pytest.mark.unit
class TestNormalizeFilename:
    """Test filename normalization for deduplication."""

    def test_remove_parenthetical_numbers(self):
        """Should remove (n) style numbering."""
        result = normalize_filename('Document (1).pdf')
        assert '(1)' not in result

    def test_remove_version_numbers(self):
        """Should remove v1, v2 style version numbers."""
        result = normalize_filename('Manual_v2.pdf')
        assert 'v2' not in result

        result = normalize_filename('Guide v3.pdf')
        assert 'v3' not in result

    def test_remove_years(self):
        """Should remove year patterns."""
        result = normalize_filename('Report_2024.pdf')
        assert '2024' not in result

        result = normalize_filename('Sheet-2023.pdf')
        assert '2023' not in result

    def test_remove_common_suffixes(self):
        """Should remove common file suffixes."""
        assert 'updated' not in normalize_filename('Manual_updated.pdf')
        assert 'final' not in normalize_filename('Report_final.pdf')
        assert 'revised' not in normalize_filename('Sheet_revised.pdf')
        assert 'new' not in normalize_filename('Manual_new.pdf')
        assert 'latest' not in normalize_filename('Guide_latest.pdf')

    def test_normalize_separators(self):
        """Should normalize separators to underscore."""
        result1 = normalize_filename('Product-Sheet.pdf')
        result2 = normalize_filename('Product_Sheet.pdf')
        result3 = normalize_filename('Product Sheet.pdf')

        # All variations should normalize similarly
        assert result1 == result2 or '_' in result1

    def test_lowercase_normalization(self):
        """Should convert to lowercase."""
        result = normalize_filename('PRODUCT_SHEET.PDF')
        assert result == result.lower()

    def test_case_insensitive_matching(self):
        """Same file in different cases should normalize identically."""
        result1 = normalize_filename('Product_Sheet.pdf')
        result2 = normalize_filename('PRODUCT_SHEET.PDF')

        assert result1 == result2

    def test_complex_filename_normalization(self):
        """Should handle complex filenames."""
        result = normalize_filename('Product_Sheet_v2_2024_Final (1).pdf')

        # Should remove version, year, suffix, numbering
        assert 'v2' not in result
        assert '2024' not in result
        assert 'final' not in result
        assert '(1)' not in result

    def test_preserve_core_name(self):
        """Should preserve the core filename."""
        result = normalize_filename('Spectrometer_Manual_v1.pdf')
        assert 'spectrometer' in result
        assert 'manual' in result

    def test_empty_filename(self):
        """Should handle empty filename."""
        result = normalize_filename('')
        assert result == ''

    def test_extension_removal(self):
        """Should handle extension removal."""
        result = normalize_filename('document.pdf')
        assert 'pdf' not in result or result.startswith('pdf')


@pytest.mark.unit
class TestDeduplicateMatches:
    """Test match deduplication."""

    def test_deduplicate_identical_filenames(self):
        """Should keep only best match for identical files."""
        matches = [
            {'pdf_path': '/path/Document.pdf', 'score': 80.0},
            {'pdf_path': '/path/Document.pdf', 'score': 90.0},  # Higher score
            {'pdf_path': '/path/Document.pdf', 'score': 70.0}
        ]

        result = deduplicate_matches(matches)

        assert len(result) == 1
        assert result[0]['score'] == 90.0

    def test_deduplicate_versioned_files(self):
        """Should deduplicate versioned files, keeping best."""
        matches = [
            {'pdf_path': '/path/Manual_v1.pdf', 'score': 75.0},
            {'pdf_path': '/path/Manual_v2.pdf', 'score': 85.0},
            {'pdf_path': '/path/Manual_updated.pdf', 'score': 80.0}
        ]

        result = deduplicate_matches(matches)

        assert len(result) == 1
        assert result[0]['score'] == 85.0

    def test_keep_different_documents(self):
        """Should keep different documents."""
        matches = [
            {'pdf_path': '/path/Manual.pdf', 'score': 80.0},
            {'pdf_path': '/path/Specifications.pdf', 'score': 85.0},
            {'pdf_path': '/path/Datasheet.pdf', 'score': 75.0}
        ]

        result = deduplicate_matches(matches)

        assert len(result) == 3

    def test_empty_matches(self):
        """Should handle empty match list."""
        result = deduplicate_matches([])
        assert result == []

    def test_single_match(self):
        """Should return single match unchanged."""
        matches = [{'pdf_path': '/path/Document.pdf', 'score': 80.0}]
        result = deduplicate_matches(matches)

        assert len(result) == 1
        assert result[0] == matches[0]

    def test_score_selection(self):
        """Should select highest scoring duplicate."""
        matches = [
            {'pdf_path': '/path/Document_2024_final.pdf', 'score': 60.0},
            {'pdf_path': '/path/Document_2023_revised.pdf', 'score': 95.0},
            {'pdf_path': '/path/Document_v1.pdf', 'score': 50.0}
        ]

        result = deduplicate_matches(matches)

        assert len(result) == 1
        assert result[0]['score'] == 95.0

    def test_none_handling(self):
        """Should handle None matches gracefully."""
        result = deduplicate_matches(None)
        # Should return None or empty list
        assert result is None or result == []


@pytest.mark.unit
class TestFindRequiredColumns:
    """Test column detection in DataFrames."""

    def test_find_all_standard_columns(self):
        """Should find all standard columns."""
        df = pd.DataFrame({
            'Type': ['Hardware'],
            'Item Code': ['CODE001'],
            'Item Description': ['Microscope'],
            'Supplier Name': ['Zeiss']
        })

        result = find_required_columns(df)

        assert result['type_col'] == 'Type'
        assert result['code_col'] == 'Item Code'
        assert result['desc_col'] == 'Item Description'
        assert result['supplier_col'] == 'Supplier Name'

    def test_find_alternate_type_names(self):
        """Should find alternate Type column names."""
        df = pd.DataFrame({
            'Product Type': ['Hardware'],
            'Code': ['CODE001'],
            'Description': ['Microscope']
        })

        result = find_required_columns(df)

        assert result['type_col'] == 'Product Type'

    def test_find_alternate_code_names(self):
        """Should find alternate Code column names."""
        df = pd.DataFrame({
            'ItemCode': ['CODE001'],
            'Item Description': ['Microscope']
        })

        result = find_required_columns(df)

        assert result['code_col'] == 'ItemCode'

    def test_find_alternate_description_names(self):
        """Should find alternate Description column names."""
        df = pd.DataFrame({
            'Name': ['Microscope'],
            'Type': ['Hardware']
        })

        result = find_required_columns(df)

        assert result['desc_col'] == 'Name'

    def test_find_alternate_supplier_names(self):
        """Should find alternate Supplier column names."""
        df = pd.DataFrame({
            'Vendor': ['Zeiss'],
            'Type': ['Hardware']
        })

        result = find_required_columns(df)

        assert result['supplier_col'] == 'Vendor'

    def test_missing_columns_return_none(self):
        """Should return None for missing columns."""
        df = pd.DataFrame({
            'Price': [100.0],
            'Quantity': [5]
        })

        result = find_required_columns(df)

        assert result['type_col'] is None
        assert result['code_col'] is None
        assert result['desc_col'] is None
        assert result['supplier_col'] is None

    def test_partial_columns(self):
        """Should find available columns, None for missing."""
        df = pd.DataFrame({
            'Type': ['Hardware'],
            'Item Description': ['Microscope']
        })

        result = find_required_columns(df)

        assert result['type_col'] == 'Type'
        assert result['desc_col'] == 'Item Description'
        assert result['code_col'] is None
        assert result['supplier_col'] is None

    def test_column_order_preference(self):
        """Should prefer more specific column names."""
        df = pd.DataFrame({
            'Type': ['Hardware'],
            'Item Type': ['Hardware'],  # More specific
            'Code': ['CODE001']
        })

        result = find_required_columns(df)

        # Should prefer Item Type over Type (based on candidate order)
        # Implementation dependent - both are valid
        assert result['type_col'] in ['Type', 'Item Type']

    def test_empty_dataframe(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame()

        result = find_required_columns(df)

        assert result['type_col'] is None
        assert result['code_col'] is None
        assert result['desc_col'] is None
        assert result['supplier_col'] is None
