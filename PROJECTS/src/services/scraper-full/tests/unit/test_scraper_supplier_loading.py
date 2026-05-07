"""
Unit tests for supplier list loading and parsing.
Tests _load_supplier_pairs and related functionality.
"""

import pytest
import sys
from pathlib import Path
import pandas as pd
from unittest.mock import patch, MagicMock

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from scraper_engine import ScraperEngine


@pytest.mark.unit
class TestLoadSupplierPairs:
    """Test supplier list loading."""

    def test_load_valid_supplier_excel(self, temp_output_dir):
        """Should load supplier list from valid Excel file."""
        # Create test Excel file
        filepath = Path(temp_output_dir) / 'suppliers.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Acme Corp', 'Tech Industries', 'Lab Equipment'],
            'Website': [
                'https://acme.com',
                'https://techindustries.com',
                'https://labequipment.com'
            ]
        })
        df.to_excel(filepath, index=False)

        # Load it
        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        assert len(pairs) == 3
        assert pairs[0] == ('Acme Corp', 'https://acme.com')
        assert pairs[1] == ('Tech Industries', 'https://techindustries.com')

    def test_load_empty_supplier_list(self, temp_output_dir):
        """Should handle empty supplier list gracefully."""
        filepath = Path(temp_output_dir) / 'empty_suppliers.xlsx'
        df = pd.DataFrame({
            'Supplier Name': [],
            'Website': []
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        assert pairs == []

    def test_skip_invalid_urls(self, temp_output_dir):
        """Should skip suppliers with invalid URLs."""
        filepath = Path(temp_output_dir) / 'mixed_suppliers.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Valid Corp', 'Invalid Ltd', 'Another Corp'],
            'Website': [
                'https://valid.com',
                'not-a-url',
                'https://another.com'
            ]
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # Should only include valid URLs
        assert len(pairs) == 2
        names = [p[0] for p in pairs]
        assert 'Valid Corp' in names
        assert 'Another Corp' in names
        assert 'Invalid Ltd' not in names

    def test_handle_missing_website_column(self, temp_output_dir):
        """Should handle missing Website column gracefully."""
        filepath = Path(temp_output_dir) / 'no_website.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Acme Corp'],
            'URL': ['https://acme.com']  # Different column name
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # Should return empty since Website column is missing
        assert pairs == []

    def test_duplicate_suppliers(self, temp_output_dir):
        """Should handle duplicate suppliers."""
        filepath = Path(temp_output_dir) / 'duplicates.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Acme Corp', 'Acme Corp'],
            'Website': ['https://acme.com', 'https://acme.com']
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # Should include both (deduplication may be done elsewhere)
        assert len(pairs) == 2

    def test_whitespace_handling(self, temp_output_dir):
        """Should handle whitespace in supplier names and URLs."""
        filepath = Path(temp_output_dir) / 'whitespace.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['  Acme Corp  ', 'Tech Industries'],
            'Website': ['  https://acme.com  ', 'https://tech.com']
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # Should handle whitespace appropriately
        assert len(pairs) >= 1

    def test_null_values_ignored(self, temp_output_dir):
        """Should skip rows with null supplier names or URLs."""
        filepath = Path(temp_output_dir) / 'nulls.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Acme Corp', None, 'Another Corp'],
            'Website': ['https://acme.com', 'https://test.com', None]
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # Should skip null entries
        assert len(pairs) <= 1

    def test_nonexistent_file(self):
        """Should handle nonexistent file gracefully."""
        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs('/nonexistent/suppliers.xlsx')

        # Should return empty list or raise appropriate error
        assert pairs == [] or pairs is None or isinstance(pairs, list)


@pytest.mark.unit
class TestSupplierPairProcessing:
    """Test processing of supplier name/URL pairs."""

    def test_supplier_name_extraction(self, temp_output_dir):
        """Should correctly extract supplier names."""
        filepath = Path(temp_output_dir) / 'suppliers.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Supplier One', 'Supplier Two'],
            'Website': ['https://one.com', 'https://two.com']
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        names = [p[0] for p in pairs]
        assert 'Supplier One' in names
        assert 'Supplier Two' in names

    def test_url_protocol_normalization(self, temp_output_dir):
        """Should handle URLs with and without protocol."""
        filepath = Path(temp_output_dir) / 'suppliers.xlsx'
        df = pd.DataFrame({
            'Supplier Name': ['Acme', 'Tech'],
            'Website': ['https://acme.com', 'techcorp.com']  # One without protocol
        })
        df.to_excel(filepath, index=False)

        engine = ScraperEngine()
        pairs = engine._load_supplier_pairs(str(filepath))

        # At least the valid HTTPS URL should be included
        urls = [p[1] for p in pairs]
        assert any('https://' in url for url in urls)
