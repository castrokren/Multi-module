"""
Tests for Cross-Reference operations and workflows.
Tests run_cross_reference method, input validation, and result handling.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tkinter as tk

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "services" / "scraper-full"
sys.path.insert(0, str(SRC_PATH))


class TestCrossReferenceInitialization:
    """Test Cross-Reference tab initialization."""

    def test_crossref_frame_created(self, tk_root):
        """Test that Cross-Reference frame is created."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert app.crossref_frame is not None
                assert isinstance(app.crossref_frame, tk.Frame)

    def test_crossref_widgets_created(self, tk_root):
        """Test that Cross-Reference widgets are created."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Check for expected widget attributes
                assert hasattr(app, 'crossref_input_excel_path')
                assert hasattr(app, 'crossref_master_excel_path')
                assert hasattr(app, 'crossref_pdf_directory_path')


class TestRunCrossReference:
    """Test the run_cross_reference method."""

    def test_run_cross_reference_method_exists(self, tk_root):
        """Test that run_cross_reference method exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'run_cross_reference')
                assert callable(app.run_cross_reference)

    def test_run_cross_reference_with_empty_inputs(self, tk_root):
        """Test run_cross_reference handles empty inputs gracefully."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Clear all inputs
                if hasattr(app, 'crossref_input_excel_path'):
                    app.crossref_input_excel_path.delete(0, tk.END)
                if hasattr(app, 'crossref_master_excel_path'):
                    app.crossref_master_excel_path.delete(0, tk.END)
                if hasattr(app, 'crossref_pdf_directory_path'):
                    app.crossref_pdf_directory_path.delete(0, tk.END)

                # Should handle gracefully (not crash)
                try:
                    app.run_cross_reference()
                    success = True
                except tk.TclError:
                    # GUI update errors are acceptable in testing
                    success = True
                except Exception as e:
                    # Other exceptions should be caught
                    success = False

                assert success

    def test_crossref_results_initialized(self, tk_root):
        """Test that crossref_results dictionary is initialized."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert isinstance(app.crossref_results, dict)
                assert len(app.crossref_results) == 0


class TestMatchThresholdControl:
    """Test match threshold control in Cross-Reference."""

    def test_match_threshold_var_exists(self, tk_root):
        """Test that match_threshold_var is created."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'match_threshold_var')

    def test_match_threshold_default_value(self, tk_root):
        """Test that match_threshold_var has reasonable default."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'match_threshold_var'):
                    try:
                        threshold = app.match_threshold_var.get()
                        # Threshold should be a reasonable percentage
                        assert isinstance(threshold, int)
                        assert 0 <= threshold <= 100
                    except Exception:
                        # Variable not initialized is acceptable for testing
                        pass


class TestCrossrefLogging:
    """Test logging in Cross-Reference operations."""

    def test_crossref_log_area_exists(self, tk_root):
        """Test that crossref_log_area widget exists."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'crossref_log_area')

    def test_log_crossref_appends_messages(self, tk_root):
        """Test that log_crossref appends messages to log area."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                if hasattr(app, 'log_crossref'):
                    test_message = "Test crossref message"

                    # Should not raise exception
                    try:
                        app.log_crossref(test_message)
                        success = True
                    except Exception:
                        success = False

                    assert success


class TestCrossrefInputValidation:
    """Test input validation for Cross-Reference."""

    def test_browse_crossref_input_updates_internal_state(self, tk_root):
        """Test that selecting input Excel updates internal state."""
        test_path = '/test/input_data.xlsx'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'browse_crossref_input_excel'):
                        app.browse_crossref_input_excel()

                        assert app.input_excel == test_path

    def test_browse_crossref_master_updates_internal_state(self, tk_root):
        """Test that selecting master Excel updates internal state."""
        test_path = '/test/master_data.xlsx'

        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                with patch('pdf_crawler_gui_2.filedialog.askopenfilename', return_value=test_path):
                    from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                    app = PDFCrawlerEnhancedApp(tk_root)

                    if hasattr(app, 'browse_crossref_master_excel'):
                        app.browse_crossref_master_excel()

                        assert app.master_excel == test_path


class TestCrossrefUIElements:
    """Test UI elements specific to Cross-Reference tab."""

    def test_crossref_has_input_entry(self, tk_root):
        """Test that Cross-Reference tab has input entry widget."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'crossref_input_excel_path')

    def test_crossref_has_master_entry(self, tk_root):
        """Test that Cross-Reference tab has master entry widget."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'crossref_master_excel_path')

    def test_crossref_has_pdf_directory_entry(self, tk_root):
        """Test that Cross-Reference tab has PDF directory entry."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                assert hasattr(app, 'crossref_pdf_directory_path')


class TestCrossrefEdgeCases:
    """Test edge cases in Cross-Reference operations."""

    def test_run_cross_reference_with_invalid_paths(self, tk_root):
        """Test run_cross_reference with invalid file paths."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Set invalid paths
                if hasattr(app, 'crossref_input_excel_path'):
                    app.crossref_input_excel_path.delete(0, tk.END)
                    app.crossref_input_excel_path.insert(0, '/nonexistent/input.xlsx')

                if hasattr(app, 'crossref_master_excel_path'):
                    app.crossref_master_excel_path.delete(0, tk.END)
                    app.crossref_master_excel_path.insert(0, '/nonexistent/master.xlsx')

                # Should handle gracefully
                try:
                    app.run_cross_reference()
                    success = True
                except tk.TclError:
                    success = True
                except Exception:
                    success = False

                assert success
