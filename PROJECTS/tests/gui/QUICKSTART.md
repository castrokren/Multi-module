# GUI Testing - Quick Start Guide

Get up and running with GUI tests in 5 minutes.

## 1. Install Dependencies (1 minute)

```bash
pip install pytest pytest-cov pandas openpyxl
```

## 2. Run All Tests (30 seconds)

```bash
# Using pytest directly
pytest tests/gui/ -v

# Or using Windows batch script
cd tests/gui
run_tests.bat all

# Or using PowerShell
.\run_tests.ps1 -Command all
```

Expected output:
```
tests/gui/test_main_window.py::TestMainWindowCreation::test_window_creates_without_errors PASSED
tests/gui/test_main_window.py::TestMainWindowCreation::test_window_has_notebook_tabs PASSED
... (48 tests total)
======================== 48 passed in 2.34s ========================
```

## 3. Run Specific Tests (30 seconds)

```bash
# Run only main window tests
pytest tests/gui/test_main_window.py -v

# Run only file selection tests
pytest tests/gui/test_file_selection_workflow.py -v

# Run a specific test
pytest tests/gui/test_main_window.py::TestMainWindowCreation::test_window_creates_without_errors -v
```

## 4. View Coverage Report (1 minute)

```bash
# Generate coverage report
pytest tests/gui/ --cov=src/services/scraper-full/pdf_crawler_gui_2 --cov-report=html

# Open the report in your browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

## 5. Run Tests During Development (continuous)

```bash
# Watch mode - re-run on file changes (install pytest-watch first)
pip install pytest-watch
ptw tests/gui/ -- -v

# Or run tests in parallel (install pytest-xdist first)
pip install pytest-xdist
pytest tests/gui/ -n auto -v
```

## What These Tests Do

✅ **Test Window Creation**
- Verifies the GUI window launches without errors
- Checks that all tabs (Crawler, Overview, Cross-Reference, Cleanup) exist

✅ **Test File Selection**
- Verifies browse buttons work
- Checks that selected file paths update correctly
- Tests handling of cancelled file dialogs

✅ **Test Directory Scanning**
- Verifies scan operations populate data correctly
- Tests vendor data counting
- Checks that results display in treeview

✅ **Test Cross-Reference Operations**
- Verifies cross-reference tab is initialized
- Tests run_cross_reference method existence
- Checks input validation and error handling

## What They DON'T Do

❌ **No actual GUI rendering** - Tests run headless (no windows shown)
❌ **No network calls** - Web scraping is mocked
❌ **No file operations** - File I/O is mocked
❌ **No PDF processing** - PDF parsing is mocked

## Common Commands Quick Reference

| Task | Command |
|------|---------|
| Run all GUI tests | `pytest tests/gui/ -v` |
| Run one test file | `pytest tests/gui/test_main_window.py -v` |
| Run one test method | `pytest tests/gui/test_main_window.py::TestClass::test_method -v` |
| See print output | `pytest tests/gui/ -v -s` |
| Stop on first failure | `pytest tests/gui/ -x` |
| Run last failed tests | `pytest tests/gui/ --lf` |
| Show test names only | `pytest tests/gui/ --collect-only` |
| Generate coverage | `pytest tests/gui/ --cov=src/services/scraper-full/pdf_crawler_gui_2 --cov-report=html` |
| Run specific marker | `pytest tests/gui/ -m gui -v` |
| Parallel execution | `pytest tests/gui/ -n auto -v` |
| Debug a test | `pytest tests/gui/ --pdb` |

## File Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── pytest.ini               # pytest config
└── gui/
    ├── conftest_gui.py      # GUI-specific fixtures
    ├── test_main_window.py  # 12 window tests
    ├── test_file_selection_workflow.py  # 17 file tests
    ├── test_scanning_and_display.py     # 12 scan tests
    ├── test_crossref_operations.py      # 7 crossref tests
    ├── run_tests.bat        # Windows batch runner
    ├── run_tests.ps1        # PowerShell runner
    ├── README.md            # Full documentation
    ├── TESTING_SUMMARY.md   # Implementation details
    └── QUICKSTART.md        # This file
```

## Understanding Test Output

```
tests/gui/test_main_window.py::TestMainWindowCreation::test_window_creates_without_errors PASSED [  2%]
tests/gui/test_main_window.py::TestMainWindowCreation::test_window_has_notebook_tabs PASSED [  4%]
...
======================== 48 passed in 2.34s ========================
```

- ✅ `PASSED` - Test succeeded
- ❌ `FAILED` - Test failed
- ⊘ `SKIPPED` - Test was skipped
- ✐ `XFAIL` - Test was expected to fail
- ⚠ `ERRORS` - Test had an error

## Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install pytest
```

### "No tests found"
```bash
# Make sure you're in the project root
cd C:\Projects\Crawler\PROJECTS
pytest tests/gui/ -v
```

### Tests hang or timeout
```bash
# Run with timeout (5 seconds)
pytest tests/gui/ --timeout=5
```

### "Permission denied" during cleanup
```bash
# Run with verbose output to see where it's stuck
pytest tests/gui/ -vv -s
```

## Next Steps

1. **Read Full Docs**: Open `tests/gui/README.md` for complete documentation
2. **Add Tests**: Follow patterns in existing test files to add new tests
3. **CI/CD Integration**: Add pytest step to your deployment pipeline
4. **Coverage Goals**: Aim for >80% coverage of GUI code
5. **Performance**: Monitor test duration - keep tests fast (<100ms each)

## Test Structure Example

```python
class TestMyFeature:
    """Test description of what this class tests."""
    
    def test_something_exists(self, tk_root):
        """Test that a feature exists and works."""
        with patch('pdf_crawler_gui_2.requests.Session'):
            with patch('pdf_crawler_gui_2.vv_log'):
                from pdf_crawler_gui_2 import PDFCrawlerEnhancedApp
                
                app = PDFCrawlerEnhancedApp(tk_root)
                
                # Verify the feature
                assert hasattr(app, 'some_method')
                assert callable(app.some_method)
```

## Getting Help

- **pytest help**: `pytest --help`
- **pytest fixture help**: `pytest --fixtures | grep -A 5 tk_root`
- **Check conftest.py**: Review available fixtures
- **Read test examples**: Look at test_main_window.py for patterns

---

**You're all set!** Run `pytest tests/gui/ -v` to get started. 🚀
