#!/usr/bin/env python3
"""
NUCLEAR OPTION - Maximum 2 minutes runtime, only 2 items processed
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
    print("💥 NUCLEAR TIMEOUT: 2 minutes exceeded, FORCE EXIT")
    os._exit(1)

def main():
    print("💥 NUCLEAR TEST - 2 minute MAXIMUM runtime, 2 items MAXIMUM")
    
    # Set 2-minute HARD timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)  # 2 minutes HARD LIMIT
    
    try:
        start_time = time.time()
        
        from crossref_standalone_fast import CrossReferenceEngine
        print(f"✅ Engine imported in {time.time() - start_time:.1f}s")
        
        # Create engine with test mode
        engine = CrossReferenceEngine()
        engine.test_mode = True
        
        print("✅ Engine created with NUCLEAR test mode")
        
        # Run with nuclear limits
        print("💥 Starting NUCLEAR test...")
        
        success = engine.run_cross_reference_high_performance(
            "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
            "updated_master_list.xlsx", 
            "D:/ScrapedPDFs",  # Use actual PDF directory
            30,
            test_mode=True,
            low_cpu_mode=True,
            clean_output=True
        )
        
        total_time = time.time() - start_time
        print(f"✅ NUCLEAR test completed in {total_time:.1f}s")
        
        if success:
            print("✅ NUCLEAR test SUCCESS!")
        else:
            print("⚠️ NUCLEAR test completed (no matches found)")
            
    except Exception as e:
        print(f"💥 NUCLEAR test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        signal.alarm(0)
        print("💥 NUCLEAR test finished")

if __name__ == "__main__":
    main()
