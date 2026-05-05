#!/usr/bin/env python3
"""
Comprehensive test to see exactly what's happening with the updated limits
"""

import time
import os
import sys
import pandas as pd

# Add Cross-reference directory to Python path
crossref_dir = r"C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Cross-reference"
if crossref_dir not in sys.path:
    sys.path.insert(0, crossref_dir)

def debug_log(message):
    """Log with timestamp"""
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def main():
    debug_log("🔍 COMPREHENSIVE TEST STARTED")
    
    try:
        debug_log("Checking input files...")
        
        input_file = "NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx"
        master_file = "updated_master_list.xlsx"
        pdf_dir = "D:/ScrapedPDFs"
        
        # Check input file
        if os.path.exists(input_file):
            try:
                df = pd.read_excel(input_file)
                debug_log(f"✅ Input file: {len(df)} rows, columns: {list(df.columns)}")
                debug_log(f"📊 First few item codes: {df['TYPE'].head(5).tolist() if 'TYPE' in df.columns else 'No TYPE column'}")
            except Exception as e:
                debug_log(f"❌ Error reading input file: {e}")
        else:
            debug_log(f"❌ Input file not found: {input_file}")
            return
        
        # Check master file
        if os.path.exists(master_file):
            try:
                master_df = pd.read_excel(master_file)
                debug_log(f"✅ Master file: {len(master_df)} rows, columns: {list(master_df.columns)}")
            except Exception as e:
                debug_log(f"❌ Error reading master file: {e}")
        else:
            debug_log(f"❌ Master file not found: {master_file}")
            return
        
        # Check PDF directory
        if os.path.exists(pdf_dir):
            try:
                contents = os.listdir(pdf_dir)
                supplier_dirs = [d for d in contents if os.path.isdir(os.path.join(pdf_dir, d))]
                pdf_files = [f for f in contents if f.lower().endswith('.pdf')]
                debug_log(f"✅ PDF directory: {len(supplier_dirs)} supplier dirs, {len(pdf_files)} direct PDFs")
                debug_log(f"📂 First few suppliers: {supplier_dirs[:5]}")
                
                # Count PDFs in supplier directories
                total_pdfs = 0
                for supplier in supplier_dirs[:5]:  # Check first 5
                    supplier_path = os.path.join(pdf_dir, supplier)
                    supplier_pdfs = [f for f in os.listdir(supplier_path) if f.lower().endswith('.pdf')]
                    total_pdfs += len(supplier_pdfs)
                    debug_log(f"  📄 {supplier}: {len(supplier_pdfs)} PDFs")
                
                debug_log(f"📊 Total PDFs in first 5 suppliers: {total_pdfs}")
                
            except Exception as e:
                debug_log(f"❌ Error reading PDF directory: {e}")
        else:
            debug_log(f"❌ PDF directory not found: {pdf_dir}")
            return
        
        debug_log("Starting analysis with updated limits...")
        
        from crossref_standalone_fast import CrossReferenceEngine
        
        engine = CrossReferenceEngine()
        # Don't set test_mode to allow processing up to 100 items
        
        start_time = time.time()
        
        success = engine.run_cross_reference_high_performance(
            input_file,
            master_file,
            pdf_dir,
            30,  # 30% threshold
            test_mode=False,  # Allow full processing up to 100 items
            low_cpu_mode=False,
            clean_output=True
        )
        
        end_time = time.time()
        runtime = end_time - start_time
        
        debug_log(f"Analysis completed in {runtime:.1f} seconds")
        
        if success:
            debug_log("✅ Analysis SUCCESS")
            
            # Check for results
            if hasattr(engine, 'results') and engine.results:
                debug_log(f"📊 Found {len(engine.results)} matches!")
                for i, result in enumerate(engine.results[:3]):  # Show first 3
                    debug_log(f"  Match {i+1}: {result.get('Item Code', 'N/A')} -> {os.path.basename(result.get('Matched PDF', 'N/A'))}")
            else:
                debug_log("📊 No matches found in results")
            
            # Check for output files
            result_files = [f for f in os.listdir('.') if f.startswith('crossref_results_')]
            if result_files:
                latest_result = max(result_files)
                debug_log(f"📁 Results file created: {latest_result}")
            else:
                debug_log("📁 No results file created")
        else:
            debug_log("❌ Analysis FAILED")
        
        debug_log("🔍 COMPREHENSIVE TEST COMPLETED")
        
    except Exception as e:
        debug_log(f"❌ Error: {e}")
        import traceback
        debug_log(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
