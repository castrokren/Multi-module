#!/usr/bin/env python3
"""
Test script to verify XLS file support
"""

import pandas as pd
import sys
from pathlib import Path

def test_xls_reading(file_path):
    """Test reading both .xls and .xlsx files"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return False
    
    file_ext = path.suffix.lower()
    print(f"Testing file: {path.name} (extension: {file_ext})")
    
    # Determine the appropriate engine
    if file_ext == '.xls':
        engine = 'xlrd'
        print("Using xlrd engine for .xls file")
    elif file_ext == '.xlsx':
        engine = 'openpyxl'
        print("Using openpyxl engine for .xlsx file")
    else:
        print(f"Unsupported file format: {file_ext}")
        return False
    
    try:
        # Try reading with header=1 (second row as header)
        df = pd.read_excel(path, header=1, engine=engine)
        print(f"✓ Successfully read file with header=1")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        # Look for description columns
        desc_cols = [c for c in df.columns if 'description' in c.lower()]
        if desc_cols:
            print(f"  Found description column: {desc_cols[0]}")
        else:
            # Try other common names
            desc_cols = [c for c in df.columns if any(word in c.lower() for word in ['desc', 'item', 'name', 'title', 'product', 'material'])]
            if desc_cols:
                print(f"  Found potential description column: {desc_cols[0]}")
            else:
                print(f"  No description column found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_xls_reading(sys.argv[1])
    else:
        print("Usage: python test_xls_support.py <file_path>")
        print("This script tests reading both .xls and .xlsx files")
