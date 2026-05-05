#!/usr/bin/env python3
"""
Simple check to see if the script runs without infinite loops
"""

import time

def main():
    print("=== SIMPLE CHECK ===")
    start_time = time.time()
    
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        print(f"✅ Import successful in {time.time() - start_time:.1f}s")
        
        engine = CrossReferenceEngine()
        print("✅ Engine created")
        
        # Check if input file exists
        import os
        input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        if os.path.exists(input_file):
            print(f"✅ Input file found: {input_file}")
            
            # Read first few rows to see what we're working with
            import pandas as pd
            try:
                df = pd.read_excel(input_file)
                print(f"✅ Input file has {len(df)} rows")
                print(f"✅ Columns: {list(df.columns)}")
                
                # Show first 2 rows
                print("📊 First 2 rows:")
                for idx, row in df.head(2).iterrows():
                    print(f"  Row {idx}: {dict(row)}")
                    
            except Exception as e:
                print(f"❌ Error reading input file: {e}")
        else:
            print(f"❌ Input file not found: {input_file}")
        
        total_time = time.time() - start_time
        print(f"✅ Check completed in {total_time:.1f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
