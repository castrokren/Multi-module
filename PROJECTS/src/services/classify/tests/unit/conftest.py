"""
Classify service specific fixtures.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pandas as pd

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))


@pytest.fixture
def classify_config():
    """Configuration for classification tests."""
    return {
        'learning_mode': True,
        'min_occurrences': 3,
        'confidence_threshold': 0.6,
        'output_dir': None
    }


@pytest.fixture
def test_excel_with_descriptions(temp_output_dir):
    """Create a test Excel file with item descriptions."""
    filepath = Path(temp_output_dir) / 'items.xlsx'
    df = pd.DataFrame({
        'Item Code': ['ITEM001', 'ITEM002', 'ITEM003', 'ITEM004'],
        'Item Description': [
            'Zeiss Microscope Model XYZ with optical parts',
            'Microsoft Office 365 Professional License',
            'Office Desk Chair Model EC-2000',
            'Thermo Fisher Centrifuge with rotor attachment'
        ],
        'Supplier Name': [
            'Zeiss',
            'Microsoft',
            'Herman Miller',
            'Thermo Fisher Scientific'
        ]
    })
    df.to_excel(filepath, index=False)
    yield filepath


@pytest.fixture
def vendor_classification_data():
    """Test data for vendor-based classification."""
    return {
        'hw_vendors': [
            'Thermo Fisher Scientific',
            'Agilent Technologies',
            'Waters Corporation',
            'Zeiss',
            'Leica Microsystems'
        ],
        'sw_vendors': [
            'Microsoft',
            'Adobe',
            'Autodesk',
            'Mathworks'
        ],
        'ni_vendors': [
            'Empire Office Inc',
            'Staples',
            'Herman Miller'
        ]
    }


@pytest.fixture
def technical_descriptions():
    """Test data with technical keywords."""
    return [
        'Spectrometer with laser detection system',
        'Chromatograph GC-MS analysis instrument',
        'Flow Cytometer for cell analysis',
        'Microplate Reader with temperature control',
        'Centrifuge 5424 refrigerated unit'
    ]


@pytest.fixture
def office_descriptions():
    """Test data with office/non-instrument keywords."""
    return [
        'Office chair ergonomic adjustable',
        'File cabinet storage system',
        'Desk lamp LED lighting',
        'Staples office supplies bulk',
        'Storage shelving unit metal'
    ]
