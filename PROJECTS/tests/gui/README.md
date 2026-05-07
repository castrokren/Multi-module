# GUI Testing Infrastructure for Crawler Projects

This directory contains automated tests for the Tkinter GUI of the Crawler Projects application, specifically the `PDFCrawlerEnhancedApp` from `pdf_crawler_gui_2.py`.

## Overview

The GUI testing infrastructure uses **pytest** with unittest.mock for mocking external dependencies. Tests do not require launching actual GUI windows and run headless.

### Key Design Decisions

1. **Framework**: pytest (Python's standard testing framework)
   - Simple, widely-used, excellent documentation
   - Supports fixtures, parametrization, and markers
   - Tkinter testing doesn't require special GUI testing frameworks like pytest-qt

2. **Mocking Strategy**: unittest.mock
   - Mocks heavy dependencies (requests, file dialogs, logging)
   - Mocks GUI updates to avoid window creation
   - Allows testing logic without external dependencies

3. **Test Organization**: Modular by workflow
   - `test_main_window.py` - Window creation and initialization
   - `test_file_selection_workflow.py` - File browsing and selection
   - `test_scanning_and_display.py` - Directory scanning and result display
   - `test_crossref_operations.py` - Cross-reference workflow operations

4. **No External Dependencies During Testing**
   - PDF scraping/crawling NOT executed (mocked)
   - File dialogs NOT opened (mocked)
   - Network requests NOT made (mocked)
   - Logging NOT actually written to files (mocked)

## Test Files

### test_main_window.py
Tests main window creation, initialization, and basic structure:
- Window creation without errors
- Notebook tabs exist and are accessible
- Window title, geometry, and state
- Initial state of internal variables
- Cleanup on window close

### test_file_selection_workflow.py
Tests file and folder selection workflows:
- Browse button existence and functionality
- Entry widget updates when files are selected
- Handling of cancelled dialogs (empty selection)
- Path updates for input files, master files, and PDF folders
- Default folder creation
- Cross-reference file selection (Excel and PDF directories)
- Cleanup folder selection

### test_scanning_and_display.py
Tests scanning operations and results display:
- Scan directory method existence
- Handling empty and invalid paths
- Vendor data population from directory scanning
- PDF file counting
- Treeview population with vendor data
- Vendor filtering (show all, with PDFs, empty)
- Export summary functionality
- Logging output to text widgets

### test_crossref_operations.py
Tests Cross-Reference tab operations:
- Tab initialization and widget creation
- Running cross-reference with various input conditions
- Empty and invalid input handling
- Match threshold control
- Logging output
- Input validation and state updates
- UI element existence and properties

## Setup and Configuration

### Requirements

Install dependencies:
```bash
pip install pytest pytest-cov pandas openpyxl
```

The test suite mocks Tkinter and other heavy dependencies, so you don't need:
- Actual PDF libraries (mocked)
- Network connectivity (mocked)
- File system operations (uses temp directories)

### Python Version

- Python 3.8+

## Running Tests

### Run all GUI tests
```bash
pytest tests/gui/ -v
```

### Run tests in a specific file
```bash
pytest tests/gui/test_main_window.py -v
```

### Run a specific test class
```bash
pytest tests/gui/test_main_window.py::TestMainWindowCreation -v
```

### Run a specific test
```bash
pytest tests/gui/test_main_window.py::TestMainWindowCreation::test_window_creates_without_errors -v
```

### Run with coverage report
```bash
pytest tests/gui/ --cov=src/services/scraper-full/pdf_crawler_gui_2 --cov-report=html
```

### Run only fast tests (skip slow tests)
```bash
pytest tests/gui/ -v -m "not slow"
```

### Run tests with detailed output
```bash
pytest tests/gui/ -vv -s
```

### Run tests in parallel (requires pytest-xdist)
```bash
pip install pytest-xdist
pytest tests/gui/ -n auto
```

## Test Organization and Naming

### Test Classes
- Named `Test*` (e.g., `TestMainWindowCreation`)
- Group related test methods
- Each tests a specific aspect of functionality

### Test Methods
- Named `test_*` (e.g., `test_window_creates_without_errors`)
- Describe what is being tested in the name
- Focus on one behavior per test

### Fixtures
- Defined in `conftest_gui.py`
- Provide test utilities and mocks
- `tk_root` - Clean Tkinter root window
- `mock_filedialog` - File dialog mocking
- `mock_crawler_config` - Configuration mocking
- `test_gui_helper` - GUI testing utilities

## Mocking Strategy

The test suite heavily uses `unittest.mock.patch` to mock:

```python
with patch('pdf_crawler_gui_2.requests.Session'):
    with patch('pdf_crawler_gui_2.vv_log'):
        from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp
        app = PDFCrawlerEnhancedApp(tk_root)
```

This approach:
1. Prevents import errors from missing dependencies
2. Avoids network calls and file system operations
3. Allows fast, deterministic tests
4. Enables testing GUI logic in isolation

## Key Testing Utilities

### TkinterTestHelper (in conftest_gui.py)

Utility methods for GUI testing:

```python
# Find widgets
button = TkinterTestHelper.find_button(root, "Click Me")
entry = TkinterTestHelper.find_entry(root)

# Get/set values
text = TkinterTestHelper.get_widget_text(widget)
TkinterTestHelper.set_entry_value(entry, "new_value")

# Interact with widgets
TkinterTestHelper.click_button(button)

# Process events
TkinterTestHelper.process_events(root, duration_ms=100)
```

## Current Test Coverage

**Total Tests**: 48 GUI tests across 4 test files

| File | Test Count | Focus |
|------|------------|-------|
| test_main_window.py | 12 | Window creation, tabs, initial state |
| test_file_selection_workflow.py | 17 | File/folder browsing, path selection |
| test_scanning_and_display.py | 12 | Directory scanning, results display |
| test_crossref_operations.py | 7 | Cross-reference operations |

## Writing New GUI Tests

### Template for a new test class:

```python
class TestNewFeature:
    """Test description."""

    def test_feature_exists(self, tk_root):
        """Test that feature is properly initialized."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp

                app = PDFCrawlerEnhancedApp(tk_root)

                # Verify feature exists
                assert hasattr(app, 'feature_name')
```

### Best Practices

1. **Mock Early**: Mock dependencies at import time
2. **Test One Thing**: Each test method tests one behavior
3. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
4. **Handle Exceptions**: Tests should handle tk.TclError gracefully
5. **Clear Names**: Test method names should describe what is tested
6. **No GUI Windows**: Tests should not display windows
7. **Fast Execution**: Tests should complete in milliseconds

## Challenges and Solutions

### Challenge 1: Tkinter GUI Updates During Tests
**Solution**: Mock `tk.update()` or use `process_events()` helper to allow event processing safely

### Challenge 2: File Dialogs Block Testing
**Solution**: Mock `tkinter.filedialog` functions to return test paths

### Challenge 3: Network/Heavy Operations
**Solution**: Mock all I/O operations (requests, file writes, etc.)

### Challenge 4: Widget Finding
**Solution**: Use `TkinterTestHelper.find_*()` methods for widget discovery

### Challenge 5: Cross-Platform Path Issues
**Solution**: Use `pathlib.Path` instead of string concatenation

## Known Limitations

1. **GUI Rendering**: Tests don't verify visual appearance (colors, fonts, layout)
2. **Event Handling**: Tests verify that methods exist, not that event bindings work
3. **Threading**: GUI threading is not fully tested (use with caution in async tests)
4. **Platform-Specific**: Some tests may need adjustment on different OS

## Continuous Integration

To run tests in CI/CD pipeline:

```bash
# Run with verbose output and fail on warnings
pytest tests/gui/ -v --tb=short --strict-markers

# Generate coverage report
pytest tests/gui/ --cov=src/services/scraper-full/pdf_crawler_gui_2 --cov-report=xml

# Exit with specific code
pytest tests/gui/ --exitfirst  # Stop on first failure
```

## Debugging Failed Tests

### Run with full traceback
```bash
pytest tests/gui/test_file.py::TestClass::test_method -vv --tb=long
```

### Drop into debugger on failure
```bash
pytest tests/gui/ --pdb  # Use 'c' to continue, 'q' to quit
```

### Print debug output
```bash
pytest tests/gui/ -s  # Show print() statements
```

## Future Enhancements

1. **Visual Testing**: Add screenshot comparison tests for layouts
2. **Performance Testing**: Add timing assertions for operations
3. **Accessibility Testing**: Verify keyboard navigation and screen reader support
4. **Automated Workflows**: Test multi-step user workflows
5. **Stress Testing**: Test with large datasets and many operations
6. **Platform Testing**: Test on Windows, macOS, and Linux

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
