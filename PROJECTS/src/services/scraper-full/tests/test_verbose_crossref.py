#!/usr/bin/env python3
"""
Test script for verbose cross-reference functionality
This will help debug where the cross-reference app gets stuck.
"""

import sys
import os
import time
import traceback

def main():
    """Test the cross-reference functionality with verbose output"""
    print("=== VERBOSE CROSS-REFERENCE TEST ===")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print()
    
    # Check if required files exist
    test_files = {
        "Input file": "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
        "Master file": "updated_master_list.xlsx", 
        "PDF directory": "D:/ScrapedPDFs"
    }
    
    print("Checking required files:")
    for name, path in test_files.items():
        exists = os.path.exists(path)
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"  {name}: {path} - {status}")
    print()
    
    # Check if crossref_standalone.py exists
    if os.path.exists("crossref_standalone.py"):
        print("✅ crossref_standalone.py found")
    else:
        print("❌ crossref_standalone.py not found")
        return
    
    # Try to import and test
    try:
        print("Importing CrossReferenceEngine...")
        from crossref_standalone import CrossReferenceEngine
        print("✅ CrossReferenceEngine imported successfully")
        
        # Create engine
        print("Creating engine instance...")
        engine = CrossReferenceEngine()
        print("✅ Engine created")
        
        # Test with minimal data
        print("\n=== TESTING WITH MINIMAL DATA ===")
        
        # Check if we have the required files
        if not all(os.path.exists(path) for path in test_files.values()):
            print("❌ Missing required files. Please ensure:")
            print("  - NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx exists")
            print("  - updated_master_list.xlsx exists") 
            print("  - D:/ScrapedPDFs directory exists")
            print("\nPlease check your file paths")
            return
        
        print("✅ All required files found")
        
        # Run cross-reference with verbose output
        print("\n=== RUNNING CROSS-REFERENCE ANALYSIS ===")
        start_time = time.time()
        
        success = engine.run_cross_reference(
            input_file="NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
            master_file="updated_master_list.xlsx", 
            pdf_dir="D:/ScrapedPDFs",
            threshold=10
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Success: {'✅ YES' if success else '❌ NO'}")
        
        if success and hasattr(engine, 'results'):
            print(f"Results found: {len(engine.results)} items")
            
            # Show some results
            if engine.results:
                print("\nSample results:")
                for i, (item_code, result) in enumerate(engine.results.items()):
                    if i >= 3:  # Show first 3 results
                        break
                    matches = len(result.get('matches', []))
                    print(f"  {item_code}: {matches} matches")
        
        # Try to export results
        if success:
            print("\n=== EXPORTING RESULTS ===")
            export_success = engine.export_results()
            if export_success:
                print("✅ Results exported successfully")
            else:
                print("❌ Export failed")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed:")
        print("  pip install pandas openpyxl PyPDF2 pdfplumber")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main() 