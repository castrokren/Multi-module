#!/usr/bin/env python3
"""
Resume cross-reference analysis from where it got stuck
"""
import sys
import os
import pandas as pd
from datetime import datetime

def main():
    print("=== RESUMING CROSS-REFERENCE ANALYSIS ===")
    
    # Check if we have a results file to resume from
    result_files = [f for f in os.listdir('.') if f.startswith('crossref_results_') and f.endswith('.xlsx')]
    
    if result_files:
        latest_file = max(result_files, key=os.path.getctime)
        print(f"Found existing results: {latest_file}")
        
        try:
            df = pd.read_excel(latest_file)
            print(f"Loaded {len(df)} existing results")
            print(f"Unique items processed: {df['Item Code'].nunique()}")
            print(f"Last few items:")
            print(df['Item Code'].tail(5).tolist())
            
            # Check what items we still need to process
            input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
            if os.path.exists(input_file):
                input_df = pd.read_excel(input_file)
                total_items = len(input_df)
                processed_items = df['Item Code'].nunique()
                remaining = total_items - processed_items
                
                print(f"\nTotal items to process: {total_items}")
                print(f"Items already processed: {processed_items}")
                print(f"Items remaining: {remaining}")
                
                if remaining > 0:
                    print(f"Progress: {processed_items}/{total_items} ({processed_items/total_items*100:.1f}%)")
                    print("Analysis is incomplete. Need to resume from remaining items.")
                else:
                    print("✅ Analysis appears to be complete!")
                    
        except Exception as e:
            print(f"Error reading results file: {e}")
    else:
        print("No existing results file found.")
    
    print("\n=== CHECKING FILES ===")
    files_to_check = [
        "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx",
        "updated_master_list.xlsx",
        "PDFs"
    ]
    
    for file in files_to_check:
        exists = os.path.exists(file)
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        print(f"  {file}: {status}")
    
    print("\n=== CHECKING IMPORTS ===")
    try:
        from crossref_standalone_fast import CrossReferenceEngine
        print("  CrossReferenceEngine: ✅ OK")
        
        # Try to create engine instance
        engine = CrossReferenceEngine()
        print("  Engine instance: ✅ OK")
        
    except Exception as e:
        print(f"  CrossReferenceEngine: ❌ ERROR - {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== RESUME COMPLETE ===")

if __name__ == "__main__":
    main()

