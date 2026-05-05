#!/usr/bin/env python3
"""
Command-line version of Cross-reference Module
"""

import sys
import os
from datetime import datetime

# Import the cross-reference engine
from crossref_standalone_fast import CrossReferenceEngine

def main():
    print("=== COMMAND-LINE CROSS-REFERENCE ANALYSIS ===")
    
    # Configuration - adjust these paths as needed
    input_file = "D:/SOM_in_labeled"
    master_file = "D:/Masterlist"
    pdf_dir = "D:/ScrapedPDFs"
    threshold = 60
    test_mode = False  # Set to True for testing with limited items
    low_cpu_mode = True  # Use single worker for stability
    
    print(f"📂 Input file: {input_file}")
    print(f"📂 Master file: {master_file}")
    print(f"📂 PDF directory: {pdf_dir}")
    print(f"🎯 Threshold: {threshold}%")
    print(f"🧪 Test mode: {test_mode}")
    print(f"🐌 Low CPU mode: {low_cpu_mode}")
    
    # Check if files exist
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return
    
    if not os.path.exists(master_file):
        print(f"❌ Master file not found: {master_file}")
        return
    
    if not os.path.exists(pdf_dir):
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    print("✅ All files found!")
    
    # Create engine and run analysis
    try:
        engine = CrossReferenceEngine()
        
        print("\n🚀 Starting cross-reference analysis...")
        print("💡 This may take a while depending on the number of PDFs")
        print("💡 Press Ctrl+C to stop if needed")
        
        # Run the analysis
        success = engine.run_cross_reference_high_performance(
            input_file=input_file,
            master_file=master_file,
            pdf_dir=pdf_dir,
            threshold=threshold,
            test_mode=test_mode,
            low_cpu_mode=low_cpu_mode,
            clean_output=True
        )
        
        if success:
            print("\n✅ Analysis completed successfully!")
            
            # Export results
            if engine.results:
                output_file = f"crossref_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                engine.export_results(output_file)
                print(f"📊 Results exported to: {output_file}")
                print(f"📈 Total matches found: {len(engine.results)}")
            else:
                print("📊 No matches found")
        else:
            print("❌ Analysis failed")
            
    except KeyboardInterrupt:
        print("\n🛑 Analysis stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
