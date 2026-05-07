#!/usr/bin/env python3
"""
Test with reasonable limits - should process more items and find matches
"""

import time
import os
import sys
import threading

# Add Cross-reference directory to Python path.
# Override with CROSSREF_DIR env var if needed; otherwise resolve relative to this file.
crossref_dir = os.environ.get(
    "CROSSREF_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Cross-reference"))
)
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

def main():
    print("🔍 REASONABLE LIMITS TEST - Up to 100 items, 30 minute timeout")
    
    start_time = time.time()
    max_runtime = 1800  # 30 minutes
    
    # Create a stop flag
    stop_flag = {'value': False}
    
    def timeout_monitor():
        """Monitor timeout in separate thread"""
        time.sleep(max_runtime)
        if not stop_flag['value']:
            print("⏰ TIMEOUT: 30 minutes exceeded, forcing exit")
            os._exit(1)
    
    # Start timeout monitor thread
    timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
    timeout_thread.start()
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        print(f"✅ Engine imported in {time.time() - start_time:.1f}s")
        
        # Create engine WITHOUT test mode for full processing
        engine = CrossReferenceEngine()
        # engine.test_mode = True  # Comment out to allow processing up to 100 items
        
        print("✅ Engine created with reasonable limits (up to 100 items)")
        
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
            return
        
        print(f"🚀 Starting reasonable limits test...")
        print(f"📊 Will process up to 100 items from Excel file")
        print(f"📊 Will run for up to 30 minutes maximum")
        
        # Run the analysis with reasonable limits
        success = engine.run_cross_reference_high_performance(
            input_file,
            master_file, 
            pdf_dir,
            30,  # 30% threshold
            test_mode=False,  # Allow full processing
            low_cpu_mode=False,  # Use normal CPU mode
            clean_output=True
        )
        
        total_time = time.time() - start_time
        print(f"✅ Reasonable limits test completed in {total_time:.1f}s")
        
        if success:
            print("✅ TEST SUCCESS - Analysis completed!")
            # Check if results were generated
            result_files = [f for f in os.listdir('.') if f.startswith('crossref_results_')]
            if result_files:
                latest_result = max(result_files)
                print(f"📊 Results saved to: {latest_result}")
            else:
                print("📊 No results file found - may indicate no matches")
        else:
            print("⚠️ Test completed but analysis failed")
            
        # Set stop flag to prevent timeout
        stop_flag['value'] = True
        
    except Exception as e:
        print(f"❌ Reasonable limits test error: {e}")
        import traceback
        traceback.print_exc()
        stop_flag['value'] = True
    finally:
        stop_flag['value'] = True
        print("🔍 Reasonable limits test finished")

if __name__ == "__main__":
    main()
