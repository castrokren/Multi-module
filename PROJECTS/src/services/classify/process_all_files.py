#!/usr/bin/env python3
"""
Batch processor for Excel files in the SMB share.
This script processes all Excel files in Y:\ and saves labeled versions to D:\SOM_in_labeled
"""

import os
import sys
from pathlib import Path
import subprocess

def process_all_excel_files():
    """Process all Excel files in the watch directory."""
    
    # Configuration
    watch_dir = Path("Y:")
    output_dir = Path("D:/SOM_in_labeled")
    script_path = Path(__file__).parent / "classify_and_clean_dynamic.py"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    print(f"Scanning for Excel files in: {watch_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Classification script: {script_path}")
    print("-" * 60)
    
    # Find all Excel files (.xls and .xlsx)
    excel_files = []
    for pattern in ["*.xls", "*.xlsx"]:
        excel_files.extend(watch_dir.glob(pattern))
    
    if not excel_files:
        print("No Excel files found in the watch directory.")
        return
    
    print(f"Found {len(excel_files)} Excel file(s):")
    for file in excel_files:
        print(f"  - {file.name}")
    print("-" * 60)
    
    # Process each file
    processed_count = 0
    for excel_file in excel_files:
        # Skip already processed files
        if excel_file.stem.endswith('_labeled'):
            print(f"Skipping already processed file: {excel_file.name}")
            continue
            
        print(f"Processing: {excel_file.name}")
        
        try:
            # Run the classification script
            result = subprocess.run([
                sys.executable, 
                str(script_path), 
                str(excel_file)
            ], capture_output=True, text=True, check=True)
            
            print(f"  ✓ Success: {result.stdout.strip()}")
            processed_count += 1
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error: {e.stderr.strip()}")
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
    
    print("-" * 60)
    print(f"Processing complete! {processed_count} file(s) processed successfully.")
    
    # Show labeled files
    labeled_files = list(output_dir.glob("*_labeled.xlsx"))
    if labeled_files:
        print(f"\nLabeled files created in {output_dir}:")
        for file in labeled_files:
            print(f"  - {file.name}")

if __name__ == "__main__":
    try:
        process_all_excel_files()
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
