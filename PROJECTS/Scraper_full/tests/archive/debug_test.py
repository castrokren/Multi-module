#!/usr/bin/env python3
"""
Debug test to identify exactly where any hanging occurs
"""

import time
import os
import sys

# Add Cross-reference directory to Python path
crossref_dir = r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Cross-reference"
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

def debug_log(message):
    """Log with timestamp"""
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def main():
    debug_log("🔍 DEBUG TEST STARTED")
    
    try:
        debug_log("Importing CrossReferenceEngine...")
        from crossref_standalone_fast import CrossReferenceEngine
        debug_log("✅ Import successful")
        
        debug_log("Creating engine...")
        engine = CrossReferenceEngine()
        engine.test_mode = True
        debug_log("✅ Engine created")
        
        debug_log("Checking files...")
        input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        master_file = "updated_master_list.xlsx"
        pdf_dir = "D:/ScrapedPDFs"
        
        files_exist = all([
            os.path.exists(input_file),
            os.path.exists(master_file),
            os.path.exists(pdf_dir)
        ])
        
        if files_exist:
            debug_log("✅ All files exist")
        else:
            debug_log("❌ Some files missing, creating test structure...")
            # Create minimal test
            test_dir = "debug_test_pdfs"
            os.makedirs(os.path.join(test_dir, "TestSupplier"), exist_ok=True)
            test_file = os.path.join(test_dir, "TestSupplier", "test.pdf")
            with open(test_file, 'w') as f:
                f.write("Debug test content")
            pdf_dir = test_dir
            debug_log(f"✅ Created test directory: {test_dir}")
        
        debug_log("Starting analysis...")
        start_time = time.time()
        
        success = engine.run_cross_reference_high_performance(
            input_file,
            master_file,
            pdf_dir,
            30,
            test_mode=True,
            low_cpu_mode=True,
            clean_output=True
        )
        
        end_time = time.time()
        runtime = end_time - start_time
        
        debug_log(f"Analysis completed in {runtime:.1f} seconds")
        
        if success:
            debug_log("✅ Analysis SUCCESS")
        else:
            debug_log("⚠️ Analysis completed with no matches")
        
        debug_log("🔍 DEBUG TEST COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        debug_log(f"❌ Error: {e}")
        import traceback
        debug_log(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
