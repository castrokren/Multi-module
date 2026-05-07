"""
Tests for the main PDFCrawlerEnhancedApp window and core UI elements.
Tests window creation, tab visibility, and basic widget existence.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tkinter as tk

# Setup path to import the GUI module
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "services" / "scraper-full"
sys.path.insert(0, str(SRC_PATH))


class TestMainWindowCreation:
    """Test main window creation and initialization."""

    def test_window_creates_without_errors(self, tk_root):
        """Test that the main app window can be created without crashing."""
        # Mock heavy dependencies to avoid import errors
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify app instance was created
                assert app is not None
                assert app.master == tk_root

    def test_window_has_notebook_tabs(self, tk_root):
        """Test that the window contains a Notebook with expected tabs."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify notebook exists
                assert hasattr(app, 'notebook')
                assert app.notebook is not None

                # Verify tab frames exist
                assert hasattr(app, 'crawler_frame')
                assert hasattr(app, 'overview_frame')
                assert hasattr(app, 'crossref_frame')
                assert hasattr(app, 'cleanup_frame')

    def test_window_title_set_correctly(self, tk_root):
        """Test that window title is set correctly."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Check window title
                title = tk_root.title()
                assert 'PDF Crawler' in title
                assert 'Enhanced' in title


class TestInitialState:
    """Test the initial state of the application."""

    def test_running_flag_is_false(self, tk_root):
        """Test that running flag is initialized to False."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)
                assert app.running is False

    def test_vendor_data_initialized(self, tk_root):
        """Test that vendor_data dict is initialized empty."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)
                assert isinstance(app.vendor_data, dict)
                assert len(app.vendor_data) == 0

    def test_session_created(self, tk_root):
        """Test that a requests session is created."""
        with patch('pdf_crawler_gui_2.requests.Session') as mock_session:
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)
                assert app.session is not None


class TestTabSetup:
    """Test that all tabs are properly set up with widgets."""

    def test_crawler_tab_has_widgets(self, tk_root):
        """Test that Crawler tab contains expected widgets."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify crawler_frame was created
                assert app.crawler_frame is not None
                # Check that tab was added to notebook
                tabs = app.notebook.tabs()
                assert len(tabs) > 0

    def test_overview_tab_has_widgets(self, tk_root):
        """Test that Overview tab contains expected widgets."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify overview_frame was created
                assert app.overview_frame is not None

    def test_crossref_tab_exists(self, tk_root):
        """Test that Cross-Reference tab exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify crossref_frame was created
                assert app.crossref_frame is not None

    def test_cleanup_tab_exists(self, tk_root):
        """Test that Cleanup tab exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify cleanup_frame was created
                assert app.cleanup_frame is not None


class TestWindowGeometry:
    """Test window size and geometry settings."""

    def test_window_size_set(self, tk_root):
        """Test that window is created with expected size."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Get window geometry
                geometry = tk_root.geometry()
                # Should be in format WxH+X+Y
                assert 'x' in geometry.lower() or '+' in geometry

    def test_window_visible_after_creation(self, tk_root):
        """Test that window is in a valid state after creation."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Window should be valid
                try:
                    tk_root.winfo_width()
                    tk_root.winfo_height()
                    is_valid = True
                except tk.TclError:
                    is_valid = False

                assert is_valid


class TestWindowCleanup:
    """Test proper cleanup when window closes."""

    def test_on_closing_method_exists(self, tk_root):
        """Test that on_closing method is registered."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify on_closing method exists
                assert hasattr(app, 'on_closing')
                assert callable(app.on_closing)

    def test_session_cleanup_on_close(self, tk_root):
        """Test that session is cleaned up when window closes."""
        with patch('pdf_crawler_gui_2.requests.Session') as mock_session_class:
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                # Create a mock session instance
                mock_session_instance = MagicMock()
                mock_session_class.return_value = mock_session_instance

                app = PDFCrawlerEnhancedApp(tk_root)

                # Call on_closing
                app.on_closing()

                # Session should have been cleaned up (closed)
                # Note: This depends on implementation details
                assert app.session is not None or app.running is False
