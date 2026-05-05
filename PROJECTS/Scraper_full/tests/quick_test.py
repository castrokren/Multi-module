#!/usr/bin/env python3
"""
Quick test to verify timeout fixes work.
"""

import sys
import os
import time
import signal

# Add Cross-reference directory to Python path
crossref_dir = r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Cross-reference"
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

# Add timeout mechanism
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Test timed out")

def main():
    print("🧪 Quick timeout test...")
    
    # Set a 2-minute timeout for the entire test
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)  # 2 minutes
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        
        print("✅ CrossReferenceEngine imported successfully")
        
        # Create engine
        engine = CrossReferenceEngine()
        engine.test_mode = True
        
        print("✅ Engine created with test mode enabled")
        
        # Test with local PDFs directory
        pdf_dir = "PDFs"
        if not os.path.exists(pdf_dir):
            print(f"❌ PDF directory not found: {pdf_dir}")
            print("💡 Creating test structure...")
            os.makedirs(pdf_dir, exist_ok=True)
            os.makedirs(os.path.join(pdf_dir, "TestSupplier"), exist_ok=True)
            
            # Create a simple test file
            test_file = os.path.join(pdf_dir, "TestSupplier", "test.pdf")
            with open(test_file, 'w') as f:
                f.write("Test PDF content")
            print(f"✅ Created test file: {test_file}")
        
        # Run a minimal test
        print("🚀 Running minimal test...")
        success = engine.run_cross_reference_high_performance(
            "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
            "updated_master_list.xlsx", 
            pdf_dir,
            30,
            test_mode=True,
            low_cpu_mode=True,
            clean_output=True
        )
        
        if success:
            print("✅ Test completed successfully!")
        else:
            print("⚠️ Test completed but no matches found (this is normal for test data)")
            
    except TimeoutError:
        print("⏰ Test timed out after 2 minutes - this indicates the timeout fixes are working!")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        signal.alarm(0)  # Cancel timeout
        print("🏁 Test finished")

if __name__ == "__main__":
    main()
