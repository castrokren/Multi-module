#!/usr/bin/env python3
import pandas as pd
import os

# Force immediate output
import sys
sys.stdout.flush()

print("=== QUICK STATUS CHECK ===")

# Check existing results
try:
    df = pd.read_excel('crossref_results_20250808_235653.xlsx')
    print(f"Results file loaded: {len(df)} rows")
    print(f"Unique items: {df['Item Code'].nunique()}")
    
    # Get last few items
    last_items = df['Item Code'].tail(5).tolist()
    print(f"Last 5 items: {last_items}")
    
    # Check input file
    input_df = pd.read_excel('NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx')
    total_items = len(input_df)
    processed = df['Item Code'].nunique()
    
    print(f"Total items to process: {total_items}")
    print(f"Items processed: {processed}")
    print(f"Items remaining: {total_items - processed}")
    print(f"Progress: {processed/total_items*100:.1f}%")
    
    if processed >= total_items:
        print("✅ ANALYSIS COMPLETE!")
    else:
        print("⚠️  ANALYSIS INCOMPLETE - NEEDS TO RESUME")
        
except Exception as e:
    print(f"Error: {e}")

print("=== STATUS CHECK COMPLETE ===")
sys.stdout.flush()
