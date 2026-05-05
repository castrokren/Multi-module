"""
Shared utilities for the Classify module.
Centralises functions that were previously duplicated across processors.
"""

import re
import pandas as pd
from pathlib import Path
import logging
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Pre-compiled regex patterns (compiled once at import time)
_RE_MODEL_NUMBERS = re.compile(r'\b[A-Z0-9\-]{6,}\b')
_RE_MEASUREMENTS = re.compile(r'\b\d+\.?\d*\s*(cu\.ft\.|volts?|v|w|a|hz|rpm|db|lux|psi|bar)\b')
_RE_NUMBER_SUFFIX = re.compile(r'^\d+[a-z]*$')
_RE_MODEL_PATTERN = re.compile(r'^[a-z0-9\-]{2,}$')

_EXCEL_EXTENSIONS = frozenset(('.xls', '.xlsx'))


def should_process(file_path):
    """Return True if the file is an Excel file that has not already been processed."""
    path = Path(file_path)
    if path.name.startswith('~$') or path.stem.endswith('_labeled'):
        return False
    return path.suffix.lower() in _EXCEL_EXTENSIONS


def read_excel_file(file_path):
    """Read an Excel file, selecting the engine from the file extension."""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext == '.xls':
        engine = 'xlrd'
    elif ext == '.xlsx':
        engine = 'openpyxl'
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    try:
        df = pd.read_excel(file_path, header=1, engine=engine)
        logging.info(f"Read {file_path.name} with {engine}")
        return df
    except Exception as e:
        logging.error(f"Error reading {file_path.name}: {e}")
        raise


def find_description_column(df):
    """Find the item-description column by name pattern."""
    cols = df.columns
    matches = [c for c in cols if 'description' in c.lower()]
    if not matches:
        patterns = ('desc', 'item', 'name', 'title', 'product', 'material')
        matches = [c for c in cols if any(p in c.lower() for p in patterns)]
    if not matches:
        available = ', '.join(str(c) for c in cols[:10])
        raise ValueError(f"No description column found. Available columns: {available}...")
    logging.info(f"Using '{matches[0]}' as description column")
    return matches[0]


def find_supplier_column(df):
    """Find the supplier/vendor column by name pattern. Returns None if absent."""
    cols = df.columns
    matches = [c for c in cols if 'supplier' in c.lower()]
    if not matches:
        patterns = ('vendor', 'company', 'manufacturer', 'distributor', 'source')
        matches = [c for c in cols if any(p in c.lower() for p in patterns)]
    if matches:
        logging.info(f"Using '{matches[0]}' as supplier column")
        return matches[0]
    logging.info("No supplier column found — vendor classification disabled")
    return None


def clean_dataframe(df):
    """Drop layout columns that carry no classification value."""
    cols = df.columns.tolist()
    drop_indices = list(range(0, 6)) + [7] + list(range(9, 13)) + list(range(15, 32))
    to_drop = [cols[i] for i in drop_indices if i < len(cols)]
    return df.drop(columns=to_drop, errors='ignore')
