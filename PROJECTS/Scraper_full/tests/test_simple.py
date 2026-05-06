#!/usr/bin/env python3
"""
Simple test script to check basic functionality
"""
import os
import sys

# Add Cross-reference directory to Python path.
# Override with CROSSREF_DIR env var if needed; otherwise resolve relative to this file.
crossref_dir = os.environ.get(
    "CROSSREF_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Cross-reference"))
)
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

# Write to file immediately
with open('test_output.txt', 'w') as f:
    f.write("=== SIMPLE TEST STARTED ===\n")
    f.flush()

print("=== SIMPLE TEST ===")
print("Python version:", sys.version)
print("Current directory:", os.getcwd())

# Write to file
with open('test_output.txt', 'a') as f:
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Current directory: {os.getcwd()}\n")
    f.flush()

files_to_check = [
    "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
    "updated_master_list.xlsx",
    "PDFs"
]

print("\nChecking files:")
with open('test_output.txt', 'a') as f:
    f.write("\nChecking files:\n")
    f.flush()

for file in files_to_check:
    exists = os.path.exists(file)
    status = '✅ EXISTS' if exists else '❌ NOT FOUND'
    print(f"  {file}: {status}")
    with open('test_output.txt', 'a') as f:
        f.write(f"  {file}: {status}\n")
        f.flush()

print("\nChecking imports:")
with open('test_output.txt', 'a') as f:
    f.write("\nChecking imports:\n")
    f.flush()

try:
    import pandas as pd
    print("  pandas: ✅ OK")
    with open('test_output.txt', 'a') as f:
        f.write("  pandas: ✅ OK\n")
        f.flush()
except Exception as e:
    print(f"  pandas: ❌ ERROR - {e}")
    with open('test_output.txt', 'a') as f:
        f.write(f"  pandas: ❌ ERROR - {e}\n")
        f.flush()

try:
    from PyPDF2 import PdfReader
    print("  PyPDF2: ✅ OK")
    with open('test_output.txt', 'a') as f:
        f.write("  PyPDF2: ✅ OK\n")
        f.flush()
except Exception as e:
    print(f"  PyPDF2: ❌ ERROR - {e}")
    with open('test_output.txt', 'a') as f:
        f.write(f"  PyPDF2: ❌ ERROR - {e}\n")
        f.flush()

try:
    import pdfplumber
    print("  pdfplumber: ✅ OK")
    with open('test_output.txt', 'a') as f:
        f.write("  pdfplumber: ✅ OK\n")
        f.flush()
except Exception as e:
    print(f"  pdfplumber: ❌ ERROR - {e}")
    with open('test_output.txt', 'a') as f:
        f.write(f"  pdfplumber: ❌ ERROR - {e}\n")
        f.flush()

try:
    from crossref_standalone_fast import CrossReferenceEngine
    print("  CrossReferenceEngine: ✅ OK")
    with open('test_output.txt', 'a') as f:
        f.write("  CrossReferenceEngine: ✅ OK\n")
        f.flush()
except Exception as e:
    print(f"  CrossReferenceEngine: ❌ ERROR - {e}")
    with open('test_output.txt', 'a') as f:
        f.write(f"  CrossReferenceEngine: ❌ ERROR - {e}\n")
        f.flush()

print("\n=== TEST COMPLETE ===")
with open('test_output.txt', 'a') as f:
    f.write("\n=== TEST COMPLETE ===\n")
    f.flush()
