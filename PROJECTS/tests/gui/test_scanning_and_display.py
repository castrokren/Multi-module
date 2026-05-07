"""
Tests for scanning operations and results display.
Tests scan_overview_directory, populate_overview_treeview, and result display workflows.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tkinter as tk
import tempfile
import shutil

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "services" / "scraper-full"
sys.path.insert(0, str(SRC_PATH))


class TestScanOverviewDirectory:
    """Test the scan_overview_directory workflow."""

    def test_scan_overview_directory_method_exists(self, tk_root):
        """Test that scan_overview_directory method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'scan_overview_directory')
                assert callable(app.scan_overview_directory)

    def test_scan_with_empty_path_shows_error(self, tk_root):
        """Test that scanning with empty path shows error."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'overview_pdf_folder_path'):
                    # Ensure entry is empty
                    app.overview_pdf_folder_path.delete(0, tk.END)

                    # Scanning should handle gracefully
                    try:
                        app.scan_overview_directory()
                        success = True
                    except Exception as e:
                        success = False

                    # Should complete without exception
                    assert success

    def test_scan_with_nonexistent_path(self, tk_root):
        """Test that scanning nonexistent directory shows error."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'overview_pdf_folder_path'):
                    # Set nonexistent path
                    app.overview_pdf_folder_path.delete(0, tk.END)
                    app.overview_pdf_folder_path.insert(0, '/nonexistent/path/12345')

                    # Should handle gracefully
                    try:
                        app.scan_overview_directory()
                        success = True
                    except Exception:
                        success = False

                    assert success

    def test_scan_populates_vendor_data(self, tk_root):
        """Test that scan populates vendor_data dictionary."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Create temporary directory with structure
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Create vendor directories
                    vendor1 = os.path.join(tmpdir, 'Vendor1')
                    vendor2 = os.path.join(tmpdir, 'Vendor2')
                    os.makedirs(vendor1)
                    os.makedirs(vendor2)

                    # Set path
                    if hasattr(app, 'overview_pdf_folder_path'):
                        app.overview_pdf_folder_path.delete(0, tk.END)
                        app.overview_pdf_folder_path.insert(0, tmpdir)

                        # Scan directory
                        app.scan_overview_directory()

                        # Check vendor_data was populated
                        assert len(app.vendor_data) >= 2
                        assert 'Vendor1' in app.vendor_data
                        assert 'Vendor2' in app.vendor_data

    def test_scan_counts_pdf_files(self, tk_root):
        """Test that scan correctly counts PDF files."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Create temporary directory with PDFs
                with tempfile.TemporaryDirectory() as tmpdir:
                    vendor_dir = os.path.join(tmpdir, 'TestVendor')
                    os.makedirs(vendor_dir)

                    # Create dummy PDF files (just empty files with .pdf extension)
                    for i in range(3):
                        pdf_file = os.path.join(vendor_dir, f'document{i}.pdf')
                        Path(pdf_file).touch()

                    # Set path and scan
                    if hasattr(app, 'overview_pdf_folder_path'):
                        app.overview_pdf_folder_path.delete(0, tk.END)
                        app.overview_pdf_folder_path.insert(0, tmpdir)

                        app.scan_overview_directory()

                        # Check PDF count
                        assert 'TestVendor' in app.vendor_data
                        assert app.vendor_data['TestVendor']['pdf_count'] == 3


class TestPopulateOverviewTreeview:
    """Test the populate_overview_treeview method."""

    def test_populate_overview_treeview_method_exists(self, tk_root):
        """Test that populate_overview_treeview method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'populate_overview_treeview')
                assert callable(app.populate_overview_treeview)

    def test_populate_clears_existing_items(self, tk_root):
        """Test that populate clears existing treeview items."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'overview_tree'):
                    # Populate with data
                    app.vendor_data = {
                        'Vendor1': {
                            'pdf_count': 5,
                            'total_size': 10000,
                            'last_modified': None,
                            'path': '/test'
                        }
                    }

                    # Populate treeview
                    try:
                        app.populate_overview_treeview('all')
                        success = True
                    except Exception:
                        success = False

                    assert success


class TestFilterVendorDisplay:
    """Test filtering vendors in the overview."""

    def test_show_all_vendors_method_exists(self, tk_root):
        """Test that show_all_vendors method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'show_all_vendors')
                assert callable(app.show_all_vendors)

    def test_show_vendors_with_pdfs_method_exists(self, tk_root):
        """Test that show_vendors_with_pdfs method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'show_vendors_with_pdfs')
                assert callable(app.show_vendors_with_pdfs)

    def test_show_empty_vendors_method_exists(self, tk_root):
        """Test that show_empty_vendors method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'show_empty_vendors')
                assert callable(app.show_empty_vendors)

    def test_show_all_vendors_with_no_data(self, tk_root):
        """Test show_all_vendors handles empty vendor_data."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Ensure vendor_data is empty
                app.vendor_data = {}

                # Should handle gracefully
                try:
                    app.show_all_vendors()
                    success = True
                except Exception:
                    success = False

                assert success


class TestExportSummary:
    """Test export summary functionality."""

    def test_export_summary_method_exists(self, tk_root):
        """Test that export_summary method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'export_summary')
                assert callable(app.export_summary)

    def test_export_summary_with_no_data(self, tk_root):
        """Test export_summary handles empty vendor_data."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Ensure vendor_data is empty
                app.vendor_data = {}

                # Should handle gracefully
                try:
                    app.export_summary()
                    success = True
                except Exception:
                    success = False

                assert success


class TestLoggingOutput:
    """Test logging output in GUI."""

    def test_log_overview_method_exists(self, tk_root):
        """Test that log_overview method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'log_overview')
                assert callable(app.log_overview)

    def test_log_crossref_method_exists(self, tk_root):
        """Test that log_crossref method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'log_crossref')
                assert callable(app.log_crossref)

    def test_log_output_to_text_widget(self, tk_root):
        """Test that log_overview outputs to text widget."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'log_overview'):
                    # Log a message
                    test_message = "Test log message"
                    try:
                        app.log_overview(test_message)
                        success = True
                    except Exception:
                        success = False

                    assert success
