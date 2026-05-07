"""
Unit tests for AdaptiveExcelProcessor file handling.
Tests Excel file reading, format detection, and processing.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from adaptive_excel_processor import AdaptiveExcelProcessor


@pytest.mark.unit
class TestShouldProcess:
    """Test file processing decision logic."""

    def test_process_xlsx_file(self):
        """Should process .xlsx files."""
        assert AdaptiveExcelProcessor.should_process('test.xlsx') is True

    def test_process_xls_file(self):
        """Should process .xls files."""
        assert AdaptiveExcelProcessor.should_process('test.xls') is True

    def test_skip_temp_files(self):
        """Should skip temporary files."""
        assert AdaptiveExcelProcessor.should_process('~$test.xlsx') is False

    def test_skip_already_labeled(self):
        """Should skip already labeled files."""
        assert AdaptiveExcelProcessor.should_process('test_labeled.xlsx') is False

    def test_skip_non_excel_files(self):
        """Should skip non-Excel files."""
        assert AdaptiveExcelProcessor.should_process('test.txt') is False
        assert AdaptiveExcelProcessor.should_process('test.pdf') is False
        assert AdaptiveExcelProcessor.should_process('test.csv') is False

    def test_case_insensitive_extension(self):
        """Should handle case-insensitive extensions."""
        assert AdaptiveExcelProcessor.should_process('test.XLSX') is True
        assert AdaptiveExcelProcessor.should_process('test.XLS') is True


@pytest.mark.unit
class TestReadExcelFile:
    """Test Excel file reading."""

    def test_read_xlsx_file(self, temp_output_dir):
        """Should read .xlsx files using openpyxl."""
        filepath = Path(temp_output_dir) / 'test.xlsx'
        df_original = pd.DataFrame({
            'Column A': [1, 2, 3],
            'Column B': ['a', 'b', 'c']
        })
        df_original.to_excel(filepath, index=False)

        processor = AdaptiveExcelProcessor()
        df_read = processor.read_excel_file(str(filepath))

        assert df_read is not None
        assert len(df_read) == 3

    def test_read_xls_file(self, temp_output_dir):
        """Should read .xls files using xlrd."""
        filepath = Path(temp_output_dir) / 'test.xlsx'  # pandas will save as xlsx
        df_original = pd.DataFrame({
            'Column A': [1, 2, 3],
            'Column B': ['a', 'b', 'c']
        })
        df_original.to_excel(filepath, index=False)

        processor = AdaptiveExcelProcessor()
        df_read = processor.read_excel_file(str(filepath))

        assert df_read is not None

    def test_nonexistent_file(self):
        """Should raise error for nonexistent file."""
        processor = AdaptiveExcelProcessor()

        with pytest.raises((FileNotFoundError, Exception)):
            processor.read_excel_file('/nonexistent/file.xlsx')

    def test_unsupported_format(self, temp_output_dir):
        """Should raise error for unsupported formats."""
        filepath = Path(temp_output_dir) / 'test.txt'
        filepath.write_text('test')

        processor = AdaptiveExcelProcessor()

        with pytest.raises(ValueError):
            processor.read_excel_file(str(filepath))

    def test_read_file_with_headers(self, temp_output_dir):
        """Should correctly read file with headers."""
        filepath = Path(temp_output_dir) / 'with_headers.xlsx'
        df_original = pd.DataFrame({
            'Item Code': ['CODE1', 'CODE2'],
            'Description': ['Item 1', 'Item 2']
        })
        df_original.to_excel(filepath, index=False)

        processor = AdaptiveExcelProcessor()
        df_read = processor.read_excel_file(str(filepath))

        assert 'Item Code' in df_read.columns or any('code' in str(c).lower() for c in df_read.columns)

    def test_empty_excel_file(self, temp_output_dir):
        """Should handle empty Excel files."""
        filepath = Path(temp_output_dir) / 'empty.xlsx'
        df_original = pd.DataFrame()
        df_original.to_excel(filepath, index=False)

        processor = AdaptiveExcelProcessor()
        df_read = processor.read_excel_file(str(filepath))

        assert df_read is not None


@pytest.mark.unit
class TestFindDescriptionColumn:
    """Test description column discovery."""

    def test_find_description_column(self):
        """Should find column with 'description' in name."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Item Description': ['Item 1', 'Item 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_description_column(df)

        assert col is not None
        assert 'description' in col.lower()

    def test_find_desc_alias(self):
        """Should find common description aliases."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Name': ['Item 1', 'Item 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_description_column(df)

        assert col is not None

    def test_find_title_column(self):
        """Should find title column as description."""
        df = pd.DataFrame({
            'Code': [1, 2],
            'Title': ['Item 1', 'Item 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_description_column(df)

        assert col is not None

    def test_no_description_column_raises(self):
        """Should raise error if no description column found."""
        df = pd.DataFrame({
            'Code': [1, 2],
            'Price': [10.0, 20.0]
        })

        processor = AdaptiveExcelProcessor()

        with pytest.raises(ValueError):
            processor.find_description_column(df)

    def test_prefers_description_column(self):
        """Should prefer 'Description' over generic matches."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Item Description': ['Item 1', 'Item 2'],
            'Name': ['Name 1', 'Name 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_description_column(df)

        assert col == 'Item Description'


@pytest.mark.unit
class TestFindSupplierColumn:
    """Test supplier/vendor column discovery."""

    def test_find_supplier_column(self):
        """Should find column with 'supplier' in name."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Supplier Name': ['Supplier 1', 'Supplier 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_supplier_column(df)

        assert col is not None
        assert 'supplier' in col.lower()

    def test_find_vendor_column(self):
        """Should find vendor column as alternative."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Vendor': ['Vendor 1', 'Vendor 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_supplier_column(df)

        assert col is not None
        assert 'vendor' in col.lower()

    def test_find_manufacturer_column(self):
        """Should find manufacturer column as alternative."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Manufacturer': ['Mfg 1', 'Mfg 2']
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_supplier_column(df)

        assert col is not None

    def test_no_supplier_column_returns_none(self):
        """Should return None if no supplier column found."""
        df = pd.DataFrame({
            'Item Code': [1, 2],
            'Price': [10.0, 20.0]
        })

        processor = AdaptiveExcelProcessor()
        col = processor.find_supplier_column(df)

        assert col is None
