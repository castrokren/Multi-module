#!/usr/bin/env python3
"""
Command-line entry point for the Cross-reference module.

Paths are read from environment variables so the script works across machines
without editing source code.  Set the variables before running, e.g.:

    set CROSSREF_INPUT=D:/SOM_in_labeled
    set CROSSREF_MASTER=D:/Masterlist
    set CROSSREF_PDF_DIR=D:/ScrapedPDFs
    python run_crossref_cli.py
"""

import sys
import os
from datetime import datetime

from crossref_standalone_fast import CrossReferenceEngine


def main():
    print("=== COMMAND-LINE CROSS-REFERENCE ANALYSIS ===")

    # Read paths from environment variables; fall back to previous defaults
    input_file = os.environ.get("CROSSREF_INPUT",  "D:/SOM_in_labeled")
    master_file = os.environ.get("CROSSREF_MASTER", "D:/Masterlist")
    pdf_dir     = os.environ.get("CROSSREF_PDF_DIR", "D:/ScrapedPDFs")

    # Optional tuning via env vars
    threshold    = int(os.environ.get("CROSSREF_THRESHOLD", "60"))
    test_mode    = os.environ.get("CROSSREF_TEST_MODE", "false").lower() == "true"
    low_cpu_mode = os.environ.get("CROSSREF_LOW_CPU", "true").lower() == "true"

    print(f"📂 Input file  : {input_file}")
    print(f"📂 Master file : {master_file}")
    print(f"📂 PDF dir     : {pdf_dir}")
    print(f"🎯 Threshold   : {threshold}%")
    print(f"🧪 Test mode   : {test_mode}")
    print(f"🐌 Low CPU     : {low_cpu_mode}")
    print()
    print("💡 Override any path with env vars: CROSSREF_INPUT, CROSSREF_MASTER, CROSSREF_PDF_DIR")
    print("💡 Other options: CROSSREF_THRESHOLD, CROSSREF_TEST_MODE, CROSSREF_LOW_CPU")
    print()

    # Validate paths before starting
    for label, path in (("Input file", input_file), ("Master file", master_file), ("PDF dir", pdf_dir)):
        if not os.path.exists(path):
            print(f"❌ {label} not found: {path}")
            sys.exit(1)

    print("✅ All paths verified")

    try:
        engine = CrossReferenceEngine()

        print("\n🚀 Starting cross-reference analysis …")
        print("💡 Press Ctrl+C to stop")

        success = engine.run_cross_reference_high_performance(
            input_file=input_file,
            master_file=master_file,
            pdf_dir=pdf_dir,
            threshold=threshold,
            test_mode=test_mode,
            low_cpu_mode=low_cpu_mode,
            clean_output=True,
        )

        if success:
            print("\n✅ Analysis completed successfully!")
            if engine.results:
                output_file = f"crossref_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                engine.export_results(output_file)
                print(f"📊 Results saved to: {output_file}")
                print(f"📈 Total matches: {len(engine.results)}")
            else:
                print("📊 No matches found")
        else:
            print("❌ Analysis failed")

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
