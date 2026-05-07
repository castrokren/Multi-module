#!/usr/bin/env python3
"""
Test the new supplier-by-supplier approach
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
    print("🎯 SUPPLIER-BY-SUPPLIER TEST")
    print("📋 This approach processes one supplier directory at a time")
    print("🏁 Will naturally complete when all supplier directories are processed")
    
    start_time = time.time()
    max_runtime = 3600  # 1 hour max
    
    # Create a stop flag
    stop_flag = {'value': False}
    
    def timeout_monitor():
        """Monitor timeout in separate thread"""
        time.sleep(max_runtime)
        if not stop_flag['value']:
            print("⏰ TIMEOUT: 1 hour exceeded, forcing exit")
            os._exit(1)
    
    # Start timeout monitor thread
    timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
    timeout_thread.start()
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine  # pyright: ignore[reportMissingImports]
        print(f"✅ Engine imported in {time.time() - start_time:.1f}s")
        
        # Create engine
        engine = CrossReferenceEngine()
        engine.test_mode = True  # Enable test mode for limited suppliers
        
        print("✅ Engine created with supplier-by-supplier approach")
        
        # Check for required files
        input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        master_file = "updated_master_list.xlsx"
        pdf_dir = "D:/ScrapedPDFs"
        
        files_exist = all([
            os.path.exists(input_file),
            os.path.exists(master_file),
            os.path.exists(pdf_dir)
        ])
        
        if not files_exist:
            print("❌ Some required files missing")
            return
        
        print(f"🚀 Starting supplier-by-supplier test...")
        print(f"📂 Will process suppliers in alphabetical order")
        print(f"🧪 Test mode: Processing first 5 suppliers only")
        
        # Run the new supplier-by-supplier analysis
        success = engine.run_cross_reference_by_supplier(
            input_file,
            master_file, 
            pdf_dir,
            30,  # 30% threshold
            test_mode=True,  # Process limited suppliers
            low_cpu_mode=False,
            clean_output=True
        )
        
        total_time = time.time() - start_time
        print(f"✅ Supplier-by-supplier test completed in {total_time:.1f}s")
        
        if success:
            print("✅ TEST SUCCESS!")
            
            # Check for results
            if hasattr(engine, 'results') and engine.results:
                print(f"📊 Found {len(engine.results)} total matches!")
                
                # Group by supplier
                suppliers_with_matches = {}
                for result in engine.results:
                    supplier = result.get('Supplier', 'Unknown')
                    if supplier not in suppliers_with_matches:
                        suppliers_with_matches[supplier] = 0
                    suppliers_with_matches[supplier] += 1
                
                print(f"📊 Matches by supplier:")
                for supplier, count in suppliers_with_matches.items():
                    print(f"  • {supplier}: {count} matches")
            else:
                print("📊 No matches found")
            
            # Check for output files
            result_files = [f for f in os.listdir('.') if f.startswith('crossref_results_')]
            if result_files:
                latest_result = max(result_files)
                print(f"📁 Results file created: {latest_result}")
        else:
            print("❌ Test failed")
            
        # Set stop flag to prevent timeout
        stop_flag['value'] = True
        
    except Exception as e:
        print(f"❌ Supplier-by-supplier test error: {e}")
        import traceback
        traceback.print_exc()
        stop_flag['value'] = True
    finally:
        stop_flag['value'] = True
        print("🎯 Supplier-by-supplier test finished")

if __name__ == "__main__":
    main()
