#!/usr/bin/env python3
"""
Create test PDF files for testing the timeout fixes.
This creates a simple test structure with a few sample PDFs.
"""

import os
import sys

def create_test_pdf_structure():
    """Create a test PDF directory structure with sample files."""
    
    # Create test directory structure
    test_dir = "test_pdfs"
    supplier1_dir = os.path.join(test_dir, "TestSupplier1")
    supplier2_dir = os.path.join(test_dir, "TestSupplier2")
    
    # Create directories
    os.makedirs(supplier1_dir, exist_ok=True)
    os.makedirs(supplier2_dir, exist_ok=True)
    
    # Create simple test PDF files (just text files with .pdf extension for testing)
    test_pdfs = [
        (os.path.join(supplier1_dir, "test_document1.pdf"), "This is a test PDF document for testing purposes. It contains some sample text."),
        (os.path.join(supplier1_dir, "test_document2.pdf"), "Another test PDF with different content for testing the cross-reference system."),
        (os.path.join(supplier2_dir, "test_document3.pdf"), "Third test PDF document with more sample text for testing."),
    ]
    
    for pdf_path, content in test_pdfs:
        with open(pdf_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {pdf_path}")
    
    print(f"\n✅ Test PDF structure created in: {test_dir}")
    print("📁 Structure:")
    print("  test_pdfs/")
    print("  ├── TestSupplier1/")
    print("  │   ├── test_document1.pdf")
    print("  │   └── test_document2.pdf")
    print("  └── TestSupplier2/")
    print("      └── test_document3.pdf")
    
    return test_dir

if __name__ == "__main__":
    create_test_pdf_structure()
