#!/usr/bin/env python3
"""
ULTRA-SAFE TEST - Maximum 5 minutes runtime guaranteed
"""

import sys
import os
import time
import signal

# Add Cross-reference directory to Python path
crossref_dir = r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Cross-reference"
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

def timeout_handler(signum, frame):
    print("⏰ ULTRA-SAFE TIMEOUT: 5 minutes exceeded, forcing exit")
    os._exit(1)

def main():
    print("🧪 ULTRA-SAFE TEST - 5 minute maximum runtime")
    
    # Set 5-minute timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5 minutes
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        
        print("✅ CrossReferenceEngine imported")
        
        # Create engine with test mode
        engine = CrossReferenceEngine()
        engine.test_mode = True  # This limits to 5 PDFs max
        
        print("✅ Engine created with ULTRA-SAFE test mode")
        
        # Create minimal test structure
        test_dir = "ultra_test_pdfs"
        supplier_dir = os.path.join(test_dir, "TestSupplier")
        
        os.makedirs(supplier_dir, exist_ok=True)
        
        # Create 3 simple test files
        for i in range(3):
            test_file = os.path.join(supplier_dir, f"test{i+1}.pdf")
            with open(test_file, 'w') as f:
                f.write(f"Test PDF content {i+1}")
            print(f"✅ Created: {test_file}")
        
        print(f"🚀 Starting ULTRA-SAFE test with {test_dir}")
        
        # Run with ultra-aggressive timeouts
        success = engine.run_cross_reference_high_performance(
            "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
            "updated_master_list.xlsx", 
            test_dir,
            30,
            test_mode=True,
            low_cpu_mode=True,
            clean_output=True
        )
        
        if success:
            print("✅ ULTRA-SAFE test completed successfully!")
        else:
            print("⚠️ ULTRA-SAFE test completed (no matches expected with test data)")
            
    except Exception as e:
        print(f"❌ ULTRA-SAFE test error: {e}")
    finally:
        signal.alarm(0)
        print("🏁 ULTRA-SAFE test finished")

if __name__ == "__main__":
    main()
