"""
Tests for file selection workflows in the GUI.
Tests browse buttons, file path input, and directory selection.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import tkinter as tk
import tempfile

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "services" / "scraper-full"
sys.path.insert(0, str(SRC_PATH))


class TestBrowseInputWorkflow:
    """Test the browse input file workflow."""

    def test_browse_input_button_exists(self, tk_root):
        """Test that browse input button is present in Crawler tab."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # browse_input method should exist
                assert hasattr(app, 'browse_input')
                assert callable(app.browse_input)

    def test_browse_input_updates_entry_widget(self, tk_root):
        """Test that browse_input updates the entry widget with selected path."""
        test_path = '/test/input.xlsx'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    # Store initial value
                    if hasattr(app, 'input_entry'):
                        initial_value = app.input_entry.get()

                        # Call browse_input
                        app.browse_input()

                        # Check that value was updated
                        new_value = app.input_entry.get()
                        assert new_value == test_path

    def test_browse_input_handles_no_selection(self, tk_root):
        """Test that browse_input gracefully handles when user cancels dialog."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=''):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    # Should not raise exception
                    try:
                        app.browse_input()
                        success = True
                    except Exception:
                        success = False

                    assert success


class TestBrowseMasterWorkflow:
    """Test the browse master file workflow."""

    def test_browse_master_button_exists(self, tk_root):
        """Test that browse master button is present."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # browse_master method should exist
                assert hasattr(app, 'browse_master')
                assert callable(app.browse_master)

    def test_browse_master_updates_entry_widget(self, tk_root):
        """Test that browse_master updates the entry widget."""
        test_path = '/test/master.xlsx'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'master_entry'):
                        # Call browse_master
                        app.browse_master()

                        # Check that value was updated
                        new_value = app.master_entry.get()
                        assert new_value == test_path


class TestBrowsePdfFolderWorkflow:
    """Test PDF folder selection workflow."""

    def test_browse_pdf_folder_button_exists(self, tk_root):
        """Test that browse PDF folder button exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # browse_pdf_folder method should exist
                assert hasattr(app, 'browse_pdf_folder')
                assert callable(app.browse_pdf_folder)

    def test_browse_pdf_folder_updates_path(self, tk_root):
        """Test that browse_pdf_folder updates the path entry."""
        test_path = '/test/pdfs'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askdirectory', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'pdf_folder_path'):
                        # Call browse_pdf_folder
                        app.browse_pdf_folder()

                        # Check that value was updated
                        new_value = app.pdf_folder_path.get()
                        assert new_value == test_path


class TestBrowseOverviewPdfFolder:
    """Test Overview tab PDF folder selection."""

    def test_browse_overview_pdf_folder_button_exists(self, tk_root):
        """Test that browse_overview_pdf_folder method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # browse_overview_pdf_folder method should exist
                assert hasattr(app, 'browse_overview_pdf_folder')
                assert callable(app.browse_overview_pdf_folder)

    def test_browse_overview_pdf_folder_updates_path(self, tk_root):
        """Test that browse_overview_pdf_folder updates the path."""
        test_path = '/test/overview_pdfs'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askdirectory', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'overview_pdf_folder_path'):
                        # Call browse_overview_pdf_folder
                        app.browse_overview_pdf_folder()

                        # Check path was updated
                        new_value = app.overview_pdf_folder_path.get()
                        assert new_value == test_path
                        # Check internal state was updated
                        assert app.pdf_directory == test_path


class TestCreateDefaultPdfFolder:
    """Test creating default PDF folder."""

    def test_create_default_pdf_folder_exists(self, tk_root):
        """Test that create_default_pdf_folder method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'create_default_pdf_folder')
                assert callable(app.create_default_pdf_folder)

    def test_create_default_pdf_folder_sets_path(self, tk_root):
        """Test that create_default_pdf_folder sets a default path."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'pdf_folder_path'):
                    # Call create_default_pdf_folder
                    app.create_default_pdf_folder()

                    # Check that a path was set
                    path = app.pdf_folder_path.get()
                    assert path is not None
                    assert len(path) > 0
                    assert 'downloaded_pdfs' in path.lower()


class TestCrossrefFileSelection:
    """Test Cross-Reference tab file selection."""

    def test_browse_crossref_input_excel_exists(self, tk_root):
        """Test that browse_crossref_input_excel method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'browse_crossref_input_excel')
                assert callable(app.browse_crossref_input_excel)

    def test_browse_crossref_master_excel_exists(self, tk_root):
        """Test that browse_crossref_master_excel method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'browse_crossref_master_excel')
                assert callable(app.browse_crossref_master_excel)

    def test_browse_crossref_pdf_directory_exists(self, tk_root):
        """Test that browse_crossref_pdf_directory method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'browse_crossref_pdf_directory')
                assert callable(app.browse_crossref_pdf_directory)

    def test_crossref_input_excel_updates_state(self, tk_root):
        """Test that selecting input Excel updates internal state."""
        test_path = '/test/crossref_input.xlsx'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'crossref_input_excel_path'):
                        # Call browse method
                        app.browse_crossref_input_excel()

                        # Check internal state
                        assert app.input_excel == test_path


class TestCleanupFolderSelection:
    """Test Cleanup tab folder selection."""

    def test_browse_cleanup_pdf_folder_exists(self, tk_root):
        """Test that browse_cleanup_pdf_folder method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'browse_cleanup_pdf_folder')
                assert callable(app.browse_cleanup_pdf_folder)
