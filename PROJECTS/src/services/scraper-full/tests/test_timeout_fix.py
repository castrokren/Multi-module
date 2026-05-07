#!/usr/bin/env python3
"""
Quick test script to verify the timeout fixes work.
This will process only a few PDFs to test the new timeout mechanisms.
"""

import sys
import os

# Add Cross-reference directory to Python path.
# Override with CROSSREF_DIR env var if needed; otherwise resolve relative to this file.
crossref_dir = os.environ.get(
    "CROSSREF_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Cross-reference"))
)
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

from crossref_standalone_fast import CrossReferenceEngine

def test_timeout_fixes():
    """Test the timeout fixes with a small sample."""
    print("🧪 Testing timeout fixes...")
    
    # Create engine instance
    engine = CrossReferenceEngine()
    
    # Enable test mode to limit PDFs
    engine.test_mode = True
    
    # Set up test parameters
    input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
    master_file = "updated_master_list.xlsx"
    pdf_dir = "D:/ScrapedPDFs"  # Use the same directory as the GUI
    threshold = 30
    
    print(f"📁 Input file: {input_file}")
    print(f"📁 Master file: {master_file}")
    print(f"📁 PDF directory: {pdf_dir}")
    print(f"🎯 Threshold: {threshold}%")
    
    # Check if PDF directory exists and has content
    if not os.path.exists(pdf_dir):
        print(f"❌ PDF directory not found: {pdf_dir}")
        print("💡 Creating test PDF structure for testing...")
        
        # Create test PDFs
        try:
            from create_test_pdfs import create_test_pdf_structure
            test_pdf_dir = create_test_pdf_structure()
            pdf_dir = test_pdf_dir
            print(f"✅ Using test PDF directory: {pdf_dir}")
        except Exception as e:
            print(f"❌ Failed to create test PDFs: {e}")
            return
    
    # Check if directory has PDFs
    try:
        contents = os.listdir(pdf_dir)
        pdf_files = [f for f in contents if f.lower().endswith('.pdf')]
        supplier_dirs = [d for d in contents if os.path.isdir(os.path.join(pdf_dir, d))]
        
        if not pdf_files and not supplier_dirs:
            print(f"❌ No PDF files or supplier directories found in: {pdf_dir}")
            print("💡 Expected structure:")
            print("  D:/ScrapedPDFs/")
            print("  ├── Supplier1/")
            print("  │   ├── document1.pdf")
            print("  │   └── document2.pdf")
            print("  └── Supplier2/")
            print("      └── document3.pdf")
            return
        else:
            print(f"✅ Found {len(pdf_files)} PDF files and {len(supplier_dirs)} supplier directories")
    except Exception as e:
        print(f"❌ Error reading PDF directory: {e}")
        return
    
    try:
        # Run the analysis with timeout protection
        print("\n🚀 Starting test analysis with timeout protection...")
        success = engine.run_cross_reference_high_performance(
            input_file, master_file, pdf_dir, threshold, 
            test_mode=True, low_cpu_mode=True, clean_output=True
        )
        
        if success:
            print("✅ Test completed successfully!")
            # Export results
            export_success = engine.export_results()
            if export_success:
                print("✅ Results exported successfully!")
            else:
                print("⚠️ Analysis completed but export failed")
        else:
            print("❌ Test failed")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_timeout_fixes()
