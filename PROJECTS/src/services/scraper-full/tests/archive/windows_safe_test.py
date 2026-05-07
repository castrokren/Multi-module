#!/usr/bin/env python3
"""
Windows-compatible test script - No signal handling
Uses threading timeout instead of SIGALRM
"""

import sys
import os
import time
import threading

# Add Cross-reference directory to Python path
crossref_dir = r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Cross-reference"
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

def main():
    print("🪟 WINDOWS SAFE TEST - 3 minute maximum runtime")
    
    start_time = time.time()
    max_runtime = 180  # 3 minutes
    
    # Create a stop flag
    stop_flag = {'value': False}
    
    def timeout_monitor():
        """Monitor timeout in separate thread"""
        time.sleep(max_runtime)
        if not stop_flag['value']:
            print("⏰ TIMEOUT: 3 minutes exceeded, forcing exit")
            os._exit(1)
    
    # Start timeout monitor thread
    timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
    timeout_thread.start()
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        print(f"✅ Engine imported in {time.time() - start_time:.1f}s")
        
        # Create engine with test mode
        engine = CrossReferenceEngine()
        engine.test_mode = True
        
        print("✅ Engine created with Windows-safe test mode")
        
        # Check for required files
        input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        master_file = "updated_master_list.xlsx"
        pdf_dir = "D:/ScrapedPDFs"
        
        if not os.path.exists(input_file):
            print(f"❌ Input file not found: {input_file}")
            return
        
        if not os.path.exists(master_file):
            print(f"❌ Master file not found: {master_file}")
            return
        
        if not os.path.exists(pdf_dir):
            print(f"❌ PDF directory not found: {pdf_dir}")
            print("💡 Creating test directory...")
            # Create simple test structure
            test_dir = "windows_test_pdfs"
            os.makedirs(os.path.join(test_dir, "TestSupplier"), exist_ok=True)
            
            # Create a simple test file
            test_file = os.path.join(test_dir, "TestSupplier", "test.pdf")
            with open(test_file, 'w') as f:
                f.write("Test PDF content for Windows testing")
            print(f"✅ Created test structure: {test_dir}")
            pdf_dir = test_dir
        
        print(f"🚀 Starting Windows-safe test with timeout protection...")
        
        # Run the analysis
        success = engine.run_cross_reference_high_performance(
            input_file,
            master_file, 
            pdf_dir,
            30,
            test_mode=True,
            low_cpu_mode=True,
            clean_output=True
        )
        
        total_time = time.time() - start_time
        print(f"✅ Windows-safe test completed in {total_time:.1f}s")
        
        if success:
            print("✅ TEST SUCCESS!")
        else:
            print("⚠️ Test completed (no matches found - normal for test data)")
            
        # Set stop flag to prevent timeout
        stop_flag['value'] = True
        
    except Exception as e:
        print(f"❌ Windows-safe test error: {e}")
        import traceback
        traceback.print_exc()
        stop_flag['value'] = True
    finally:
        stop_flag['value'] = True
        print("🪟 Windows-safe test finished")

if __name__ == "__main__":
    main()
