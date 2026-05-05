#!/usr/bin/env python3
"""
Quick info about the data files
"""

import os
import pandas as pd

def main():
    print("=== QUICK DATA INFO ===")
    
    # Check input file
    input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
    if os.path.exists(input_file):
        try:
            df = pd.read_excel(input_file)
            print(f"✅ Input file: {len(df)} total rows")
            print(f"   Columns: {list(df.columns)}")
            if 'TYPE' in df.columns:
                print(f"   First 5 item codes: {df['TYPE'].head(5).tolist()}")
        except Exception as e:
            print(f"❌ Error reading input: {e}")
    else:
        print(f"❌ Input file not found")
    
    # Check PDF directory
    pdf_dir = "D:/ScrapedPDFs"
    if os.path.exists(pdf_dir):
        try:
            contents = os.listdir(pdf_dir)
            suppliers = [d for d in contents if os.path.isdir(os.path.join(pdf_dir, d))]
            print(f"✅ PDF directory: {len(suppliers)} supplier folders")
            print(f"   First 5 suppliers: {suppliers[:5]}")
            
            # Count PDFs in first supplier
            if suppliers:
                first_supplier = suppliers[0]
                supplier_path = os.path.join(pdf_dir, first_supplier)
                pdfs = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                print(f"   {first_supplier}: {len(pdfs)} PDFs")
                
        except Exception as e:
            print(f"❌ Error reading PDFs: {e}")
    else:
        print(f"❌ PDF directory not found")
    
    print("\n=== CURRENT LIMITS ===")
    print("✅ Item limit: 100 items (was 3)")
    print("✅ Test mode: 10 items (was 2)")
    print("✅ Main loop timeout: 30 minutes (was 1 minute)")
    print("✅ Batch timeout: 30 minutes (was 5 minutes)")
    print("✅ Batch size: 50 PDFs (was 10)")

if __name__ == "__main__":
    main()
