"""
GUI-specific pytest fixtures and configuration for Tkinter testing.
Provides utilities to launch, interact with, and verify GUI components.
"""

import pytest
import sys
import os
from pathlib import Path
import tkinter as tk
from unittest.mock import MagicMock, patch
import time

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "services" / "scraper-full"
sys.path.insert(0, str(SRC_PATH))


class TkinterTestHelper:
    """Helper class for Tkinter GUI testing."""

    @staticmethod
    def find_widget(root, widget_name, widget_class=None):
        """
        Find a widget by name or class in the widget tree.

        Args:
            root: The root Tk widget
            widget_name: Name of the widget or partial name
            widget_class: Optional widget class to match

        Returns:
            Widget if found, None otherwise
        """
        try:
            for child in root.winfo_children():
                if widget_name in str(child):
                    if widget_class is None or isinstance(child, widget_class):
                        return child
                # Recursive search
                result = TkinterTestHelper.find_widget(child, widget_name, widget_class)
                if result:
                    return result
        except Exception:
            pass
        return None

    @staticmethod
    def find_button(root, button_text):
        """Find a button by its text content."""
        try:
            for child in root.winfo_children():
                if isinstance(child, tk.Button):
                    if hasattr(child, 'cget'):
                        try:
                            if button_text.lower() in child.cget('text').lower():
                                return child
                        except Exception:
                            pass
                # Recursive search
                result = TkinterTestHelper.find_button(child, button_text)
                if result:
                    return result
        except Exception:
            pass
        return None

    @staticmethod
    def find_entry(root, label_text=None):
        """Find an Entry widget, optionally by nearby label text."""
        try:
            for child in root.winfo_children():
                if isinstance(child, tk.Entry):
                    return child
                # Recursive search
                result = TkinterTestHelper.find_entry(child, label_text)
                if result:
                    return result
        except Exception:
            pass
        return None

    @staticmethod
    def get_widget_text(widget):
        """Get text from a widget (Entry, Label, Button, etc.)."""
        try:
            if hasattr(widget, 'get'):  # Entry, Combobox
                return widget.get()
            elif hasattr(widget, 'cget'):  # Label, Button
                return widget.cget('text')
        except Exception:
            pass
        return None

    @staticmethod
    def set_entry_value(entry_widget, value):
        """Set value in an Entry widget safely."""
        try:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, value)
            return True
        except Exception:
            return False

    @staticmethod
    def click_button(button_widget):
        """Simulate button click."""
        try:
            button_widget.invoke()
            return True
        except Exception:
            return False

    @staticmethod
    def process_events(root, duration_ms=100):
        """
        Process pending GUI events for a short duration.
        Allows GUI to update during tests.
        """
        end_time = time.time() + (duration_ms / 1000.0)
        while time.time() < end_time:
            try:
                root.update()
            except tk.TclError:
                break
            time.sleep(0.01)


@pytest.fixture
def tk_root():
    """
    Provide a clean Tk root window for each test.
    Automatically cleans up after test.
    """
    root = tk.Tk()
    root.withdraw()  # Hide window during testing

    yield root

    # Cleanup
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def mock_filedialog():
    """Mock tkinter filedialog for testing file selection without actual dialogs."""
    with patch('tkinter.filedialog.askopenfilename') as mock_open:
        with patch('tkinter.filedialog.askdirectory') as mock_dir:
            # Default return values for mocking
            mock_open.return_value = '/test/input.xlsx'
            mock_dir.return_value = '/test/directory'

            yield {
                'askopenfilename': mock_open,
                'askdirectory': mock_dir
            }


@pytest.fixture
def mock_crawler_config():
    """Provide mock configuration for crawler."""
    mock_config = MagicMock()
    mock_config.max_concurrent = 3
    mock_config.request_delay = 1.0
    mock_config.page_timeout = 15
    mock_config.max_pages_per_site = 50
    mock_config.match_threshold = 60
    mock_config.max_retries = 3
    mock_config.max_pdf_size_mb = 100
    mock_config.min_pdf_size_bytes = 512
    mock_config.min_text_length = 10
    mock_config.strict_content_validation = False
    return mock_config


@pytest.fixture
def test_gui_helper():
    """Provide the TkinterTestHelper class for GUI interaction."""
    return TkinterTestHelper


@pytest.fixture
def cleanup_files():
    """
    Fixture to clean up any test files created during testing.
    Yields a set to track files that should be cleaned up.
    """
    files_to_cleanup = set()

    yield files_to_cleanup

    # Cleanup phase
    for file_path in files_to_cleanup:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)
        except Exception:
            pass
