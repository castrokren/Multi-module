# Unit Test Infrastructure Setup

## Overview
This document describes the pytest-based unit testing infrastructure for the Crawler Projects application.

## Directory Structure

```
C:\Projects\Crawler\PROJECTS\
├── pytest.ini                          # Pytest configuration
├── requirements-test.txt               # Testing dependencies
├── tests/
│   ├── conftest.py                    # Shared fixtures for all services
│   │
│   └── unit/                          # (Root-level test imports, if needed)
│
├── src/services/
│   ├── scraper-full/
│   │   ├── scraper_engine.py          # Core scraper logic
│   │   └── tests/
│   │       ├── unit/
│   │       │   ├── __init__.py
│   │       │   ├── conftest.py        # Service-specific fixtures
│   │       │   ├── test_scraper_validation.py    # 7 tests
│   │       │   ├── test_scraper_initialization.py # 10 tests
│   │       │   └── test_scraper_supplier_loading.py # 8 tests
│   │       └── archive/               # Existing integration tests
│   │
│   ├── classify/
│   │   ├── adaptive_excel_processor.py # Classification logic
│   │   └── tests/
│   │       ├── unit/
│   │       │   ├── __init__.py
│   │       │   ├── conftest.py        # Service-specific fixtures
│   │       │   ├── test_adaptive_processor_keywords.py    # 16 tests
│   │       │   └── test_adaptive_processor_file_handling.py # 14 tests
│   │       └── archive/
│   │
│   └── cross-reference/
│       ├── crossref_utils.py          # Cross-reference utilities
│       └── tests/
│           ├── unit/
│           │   ├── __init__.py
│           │   ├── conftest.py        # Service-specific fixtures
│           │   ├── test_crossref_utils.py      # 18 tests
│           │   └── test_crossref_matching.py   # 15 tests
│           └── archive/
```

## Test Summary

### Total Unit Tests: 88

#### scraper-full Service: 25 tests
- **test_scraper_validation.py** (7 tests)
  - URL validation (6 tests)
  - Path sanitization (6 tests)
  - File hashing (5 tests)

- **test_scraper_initialization.py** (10 tests)
  - Engine initialization (7 tests)
  - Control methods (3 tests)
  - Session creation (1 test)
  - Parameter validation (5 tests)

- **test_scraper_supplier_loading.py** (8 tests)
  - Load supplier pairs (6 tests)
  - Supplier pair processing (2 tests)

#### classify Service: 30 tests
- **test_adaptive_processor_keywords.py** (16 tests)
  - Keyword loading (5 tests)
  - Keyword extraction (7 tests)
  - Keyword validation (6 tests)
  - Confidence calculation (4 tests)

- **test_adaptive_processor_file_handling.py** (14 tests)
  - File processing decision (6 tests)
  - Excel file reading (6 tests)
  - Description column detection (5 tests)
  - Supplier column detection (4 tests)

#### cross-reference Service: 33 tests
- **test_crossref_utils.py** (18 tests)
  - Filename normalization (10 tests)
  - Match deduplication (6 tests)
  - Column detection (9 tests)

- **test_crossref_matching.py** (15 tests)
  - String matching (5 tests)
  - Code normalization (5 tests)
  - Supplier matching (5 tests)
  - Score calculation (5 tests)
  - Match filtering (4 tests)

## Setting Up Tests

### 1. Install Dependencies

```bash
pip install -r requirements-test.txt
```

### 2. Run All Tests

```bash
# From project root
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=src/services --cov-report=html
```

### 3. Run Tests by Service

```bash
# Scraper-full tests
pytest src/services/scraper-full/tests/unit/ -v

# Classify tests
pytest src/services/classify/tests/unit/ -v

# Cross-reference tests
pytest src/services/cross-reference/tests/unit/ -v
```

### 4. Run Specific Test File

```bash
pytest src/services/scraper-full/tests/unit/test_scraper_validation.py -v
```

### 5. Run Specific Test Class or Function

```bash
# Run test class
pytest src/services/scraper-full/tests/unit/test_scraper_validation.py::TestValidateUrl -v

# Run specific test
pytest src/services/scraper-full/tests/unit/test_scraper_validation.py::TestValidateUrl::test_valid_https_url -v
```

### 6. Run with Coverage

```bash
# Coverage for all services
pytest --cov=src/services --cov-report=term-missing

# Coverage for specific service
pytest src/services/scraper-full/tests/unit/ --cov=src/services/scraper-full --cov-report=term-missing
```

### 7. Run Tests in Parallel

```bash
# Requires pytest-xdist
pytest -n auto
```

## Test Configuration

### pytest.ini
- **testpaths**: Points to `tests` directory
- **python_files**: Matches `test_*.py` files
- **python_classes**: Matches `Test*` classes
- **python_functions**: Matches `test_*` functions
- **Markers**: unit, integration, slow

### Shared Fixtures (tests/conftest.py)
- **temp_output_dir**: Temporary directory for file operations
- **temp_excel_file**: Sample Excel file with test data
- **temp_csv_file**: Sample CSV file with test data
- **hw_keywords_list**: Hardware keyword test data
- **sw_keywords_list**: Software keyword test data
- **ni_keywords_list**: Non-instrument keyword test data
- **temp_hw_keywords_file**: Temporary hardware keywords file
- **temp_sw_keywords_file**: Temporary software keywords file
- **temp_ni_keywords_file**: Temporary non-instrument keywords file
- **classification_test_data**: Classification test data
- **supplier_test_data**: Supplier test data
- **invalid_urls**: Invalid URL test cases
- **valid_urls**: Valid URL test cases
- **sample_classification_df**: Classification DataFrame fixture
- **sample_supplier_df**: Supplier DataFrame fixture

## Test Categories

### Unit Tests (✓ All tests are unit tests)
Focus on individual functions and methods without external dependencies:
- Input validation
- Data transformation
- String/filename normalization
- Configuration handling
- Column detection

### No Integration Tests Currently
- File I/O operations are mocked
- External API calls are not tested
- Database operations are not tested

### No Slow Tests Currently
All tests should run quickly (<1 second each)

## Coverage Goals

Target coverage for critical paths:
- URL validation: 100%
- Path sanitization: 100%
- File hashing: 90%
- Keyword extraction: 85%
- File format detection: 100%
- Column detection: 95%
- Filename normalization: 100%
- Match deduplication: 95%

## Best Practices

1. **Use Fixtures**: Leverage pytest fixtures for test data and setup/teardown
2. **Isolate Tests**: Each test should be independent and can run in any order
3. **Mock External Dependencies**: Don't rely on actual files or network calls
4. **Clear Assertions**: Use descriptive assertion messages
5. **Test Naming**: Test names should describe what is being tested
6. **Parameterization**: Use pytest.mark.parametrize for multiple test cases
7. **Documentation**: Add docstrings to test functions

## Troubleshooting

### Import Errors
If you get import errors, ensure:
- Service directories are in sys.path (done in conftest.py)
- All __init__.py files exist (created)
- Python path is set correctly

### Fixture Not Found
Check that:
- Fixture is defined in appropriate conftest.py
- Fixture name matches parameter name exactly
- conftest.py is in correct directory

### File Operations Fail
Ensure:
- Using temp_output_dir fixture for file creation
- Files are cleaned up properly
- Path separators are correct for Windows

## Adding New Tests

1. Create test file in appropriate service: `test_<feature>.py`
2. Import fixtures from conftest.py
3. Follow naming conventions:
   - Class: `Test<Feature>`
   - Method: `test_<scenario>`
4. Add pytest markers if needed: `@pytest.mark.unit`
5. Run tests to verify: `pytest <file> -v`

## CI/CD Integration

To integrate with CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Unit Tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=src/services --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Next Steps

1. Run tests to ensure infrastructure works
2. Add tests for critical business logic
3. Achieve target coverage for key functions
4. Set up CI/CD integration
5. Regular test maintenance and updates
