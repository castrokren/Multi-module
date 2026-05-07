"""
Cross-reference service specific fixtures.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pandas as pd

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))


@pytest.fixture
def crossref_config():
    """Configuration for cross-reference tests."""
    return {
        'min_score': 50.0,
        'dedup_enabled': True,
        'match_threshold': 0.6
    }


@pytest.fixture
def sample_pdf_list():
    """Sample PDF file list for matching."""
    return [
        'Product Sheet v1.pdf',
        'Product Sheet v2 (updated).pdf',
        'User Manual 2024.pdf',
        'User Manual 2023.pdf',
        'Specifications Final.pdf',
        'Specifications (Revised).pdf'
    ]


@pytest.fixture
def sample_instrument_data():
    """Sample instrument data for labeling."""
    return pd.DataFrame({
        'Item Code': ['INST001', 'INST002', 'INST003'],
        'Item Description': [
            'Zeiss Microscope Model XYZ',
            'Agilent HPLC System',
            'Waters Mass Spectrometer'
        ],
        'Type': ['Hardware', 'Hardware', 'Hardware'],
        'Supplier Name': ['Zeiss', 'Agilent', 'Waters']
    })


@pytest.fixture
def sample_item_code_variations():
    """Test data with item code variations."""
    return {
        'standard': 'INST-2024-001',
        'no_dashes': 'INST2024001',
        'spaces': 'INST 2024 001',
        'lowercase': 'inst-2024-001'
    }


@pytest.fixture
def column_detection_test_data():
    """Test data for column detection."""
    return {
        'standard_columns': {
            'Type': ['Hardware', 'Software'],
            'Item Code': ['CODE001', 'CODE002'],
            'Item Description': ['Microscope', 'License'],
            'Supplier Name': ['Zeiss', 'Microsoft']
        },
        'alternate_columns': {
            'Product Type': ['Hardware', 'Software'],
            'ItemCode': ['CODE001', 'CODE002'],
            'Description': ['Microscope', 'License'],
            'Supplier': ['Zeiss', 'Microsoft']
        },
        'mixed_columns': {
            'Type': ['Hardware', 'Software'],
            'Code': ['CODE001', 'CODE002'],
            'Item Description': ['Microscope', 'License'],
            'Vendor': ['Zeiss', 'Microsoft']
        }
    }
