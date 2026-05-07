"""
Shared pytest fixtures and configuration for all services.
Provides mock data, fixtures, and test utilities.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import pandas as pd

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "services"))


# ============================================================================
# Temporary Directories & File Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir():
    """Provides a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_excel_file(temp_output_dir):
    """Create a temporary Excel file with test data."""
    file_path = Path(temp_output_dir) / "test_data.xlsx"
    df = pd.DataFrame({
        'Item Code': ['CODE001', 'CODE002', 'CODE003'],
        'Item Description': ['Microscope Model X', 'Software License Pro', 'Office Desk Chair'],
        'Supplier Name': ['Lab Equipment Inc', 'Software Corp', 'Office Furniture Ltd'],
        'Type': ['Hardware', 'Software', 'Non-Instrument']
    })
    df.to_excel(file_path, index=False)
    yield file_path
    if file_path.exists():
        file_path.unlink()


@pytest.fixture
def temp_csv_file(temp_output_dir):
    """Create a temporary CSV file with test data."""
    file_path = Path(temp_output_dir) / "test_data.csv"
    df = pd.DataFrame({
        'Supplier Name': ['Supplier A', 'Supplier B'],
        'Website': ['https://example.com', 'https://test.com']
    })
    df.to_csv(file_path, index=False)
    yield file_path
    if file_path.exists():
        file_path.unlink()


# ============================================================================
# Keyword Test Data Fixtures
# ============================================================================

@pytest.fixture
def hw_keywords_list():
    """Sample hardware/research instrument keywords."""
    return [
        'microscope',
        'spectrometer',
        'chromatograph',
        'analyzer',
        'detector',
        'centrifuge',
        'incubator',
        'fluorometer',
        'spectrophotometer',
        'pipette'
    ]


@pytest.fixture
def sw_keywords_list():
    """Sample software keywords."""
    return [
        'software',
        'application',
        'license',
        'suite',
        'platform',
        'plugin',
        'module',
        'version',
        'update',
        'subscription'
    ]


@pytest.fixture
def ni_keywords_list():
    """Sample non-instrument keywords."""
    return [
        'office',
        'furniture',
        'desk',
        'chair',
        'cabinet',
        'storage',
        'supplies',
        'stationery',
        'cleaning'
    ]


@pytest.fixture
def temp_hw_keywords_file(temp_output_dir, hw_keywords_list):
    """Create temporary hardware keywords file."""
    file_path = Path(temp_output_dir) / "hw_keywords.txt"
    file_path.write_text('\n'.join(hw_keywords_list))
    yield file_path
    if file_path.exists():
        file_path.unlink()


@pytest.fixture
def temp_sw_keywords_file(temp_output_dir, sw_keywords_list):
    """Create temporary software keywords file."""
    file_path = Path(temp_output_dir) / "sw_keywords.txt"
    file_path.write_text('\n'.join(sw_keywords_list))
    yield file_path
    if file_path.exists():
        file_path.unlink()


@pytest.fixture
def temp_ni_keywords_file(temp_output_dir, ni_keywords_list):
    """Create temporary non-instrument keywords file."""
    file_path = Path(temp_output_dir) / "ni_keywords.txt"
    file_path.write_text('\n'.join(ni_keywords_list))
    yield file_path
    if file_path.exists():
        file_path.unlink()


# ============================================================================
# Classification Test Data
# ============================================================================

@pytest.fixture
def classification_test_data():
    """Test data for classification tests."""
    return {
        'hardware': [
            'Zeiss Microscope with Advanced Optics',
            'Waters HPLC Spectrometer 2695',
            'Thermo Fisher Scientific Centrifuge 5424',
            'Agilent Technologies Analyzer GC-MS'
        ],
        'software': [
            'Microsoft Office 365 Suite License',
            'Adobe Creative Cloud Subscription',
            'Autodesk AutoCAD Pro Version 2024',
            'Graphpad Prism Statistical Software'
        ],
        'non_instrument': [
            'Empire Office Inc Desk Chair Executive',
            'Herman Miller Steelcase Storage Cabinet',
            'Staples Office Supplies Package',
            'Amazon Business Cleaning Equipment'
        ]
    }


# ============================================================================
# URL/Website Test Data
# ============================================================================

@pytest.fixture
def supplier_test_data():
    """Sample supplier data for scraper tests."""
    return [
        {'name': 'Thermo Fisher Scientific', 'url': 'https://www.thermofisher.com'},
        {'name': 'Agilent Technologies', 'url': 'https://www.agilent.com'},
        {'name': 'Waters Corporation', 'url': 'https://www.waters.com'},
        {'name': 'Zeiss', 'url': 'https://www.zeiss.com'}
    ]


@pytest.fixture
def invalid_urls():
    """Invalid URLs for validation tests."""
    return [
        'ftp://invalid.com',
        'localhost:8080',
        '127.0.0.1',
        'not-a-url',
        '../../../etc/passwd',
        'javascript:alert("xss")',
        ''
    ]


@pytest.fixture
def valid_urls():
    """Valid URLs for validation tests."""
    return [
        'https://www.example.com',
        'http://www.example.com/page',
        'https://example.com/path/to/page',
        'https://subdomain.example.co.uk:8080/resource'
    ]


# ============================================================================
# Mock Objects
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock HTTP session for scraper tests."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    return MagicMock()


# ============================================================================
# Pandas DataFrame Fixtures
# ============================================================================

@pytest.fixture
def sample_classification_df():
    """Sample DataFrame for classification testing."""
    return pd.DataFrame({
        'Item Code': ['ITEM001', 'ITEM002', 'ITEM003', 'ITEM004'],
        'Item Description': [
            'Zeiss Microscope with Advanced Optics',
            'Microsoft Office 365 License',
            'Office Desk Chair Executive',
            'Thermo Fisher Centrifuge 5424'
        ],
        'Supplier Name': [
            'Zeiss',
            'Microsoft',
            'Steelcase',
            'Thermo Fisher Scientific'
        ],
        'Category': ['Hardware', 'Software', 'Non-Instrument', 'Hardware']
    })


@pytest.fixture
def sample_supplier_df():
    """Sample supplier DataFrame for scraper testing."""
    return pd.DataFrame({
        'Supplier Name': [
            'Thermo Fisher Scientific',
            'Agilent Technologies',
            'Waters Corporation'
        ],
        'Website': [
            'https://www.thermofisher.com',
            'https://www.agilent.com',
            'https://www.waters.com'
        ]
    })


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def make_test_xlsx():
    """Factory to create test Excel files with custom content."""
    def _make_xlsx(filename, data_dict):
        filepath = Path(filename).parent / Path(filename)
        df = pd.DataFrame(data_dict)
        df.to_excel(filepath, index=False)
        return filepath
    return _make_xlsx


@pytest.fixture
def make_test_csv():
    """Factory to create test CSV files with custom content."""
    def _make_csv(filename, data_dict):
        filepath = Path(filename)
        df = pd.DataFrame(data_dict)
        df.to_csv(filepath, index=False)
        return filepath
    return _make_csv


# ============================================================================
# GUI Testing Fixtures (Tkinter)
# ============================================================================

@pytest.fixture
def tk_root():
    """
    Provide a clean Tk root window for each test.
    Automatically cleans up after test.
    """
    import tkinter as tk

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
    from unittest.mock import patch

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
