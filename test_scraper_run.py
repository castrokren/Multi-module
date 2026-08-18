#!/usr/bin/env python3
"""
Test the refactored scraper with dedup database.
Runs on a sample of suppliers to verify:
  1. Database is created
  2. Files are downloaded
  3. Second run skips already-downloaded URLs
"""
import sys
import os
import json
import logging
from pathlib import Path

# Add scraper to path
sys.path.insert(0, str(Path(__file__).parent / "PROJECTS" / "src" / "services" / "scraper-full"))

import pandas as pd
from scraper_engine import ScraperEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
)

def main():
    # Paths
    project_root = Path(__file__).parent / "PROJECTS"
    supplier_excel = project_root / "data" / "masterlist" / "updated_master_list.xlsx"
    output_dir = project_root / "data" / "scraped-pdfs"
    db_path = output_dir / ".scraper_dedup.db"

    print("\n" + "="*70)
    print("SCRAPER DEDUP TEST")
    print("="*70)

    # Load supplier list and get first N suppliers
    print(f"\n[1] Loading supplier list from: {supplier_excel}")
    df = pd.read_excel(supplier_excel)
    print(f"    Total suppliers: {len(df)}")
    print(f"    Columns: {list(df.columns)}")

    # Use first 5 suppliers for testing
    test_count = 5
    test_suppliers = df.head(test_count).copy()
    print(f"\n[2] Testing with first {test_count} suppliers:")
    for idx, row in test_suppliers.iterrows():
        print(f"    - {row.get('Supplier Name', 'N/A')}")

    # Save test list to temp file
    test_excel = project_root / "data" / "test_suppliers.xlsx"
    test_suppliers.to_excel(test_excel, index=False)
    print(f"\n[3] Test supplier list saved to: {test_excel}")

    # Ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[4] Output directory: {output_dir}")

    # Run scraper - first pass
    print(f"\n[5] FIRST SCRAPER RUN")
    print("-" * 70)
    engine = ScraperEngine(
        page_timeout=15,
        max_pdf_size_mb=100,
        verbose=False,
        skip_recent_sites=False,  # Force re-scrape for testing
    )

    try:
        result1 = engine.run(str(test_excel), str(output_dir))
        print(f"\nFirst run results:")
        print(f"  - Pages crawled: {result1.get('pages', 0)}")
        print(f"  - PDFs downloaded: {result1.get('pdfs', 0)}")
        print(f"  - Suppliers processed: {result1.get('suppliers', 0)}")
    except Exception as e:
        print(f"[ERROR] First run failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Check if database was created
    print(f"\n[6] DATABASE CHECK")
    if db_path.exists():
        print(f"    [OK] Database created: {db_path}")
        db_size_kb = db_path.stat().st_size / 1024
        print(f"    Size: {db_size_kb:.1f} KB")

        # Check database contents
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM seen_urls")
            url_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM downloaded")
            file_count = cursor.fetchone()[0]
            conn.close()
            print(f"    - Tracked URLs: {url_count}")
            print(f"    - Downloaded files: {file_count}")
        except Exception as e:
            print(f"    [WARN] Could not read database: {e}")
    else:
        print(f"    [ERROR] Database NOT created: {db_path}")
        return 1

    # Count actual files downloaded
    pdf_files = list(output_dir.glob("**/*.pdf"))
    print(f"\n[7] ACTUAL FILES ON DISK")
    print(f"    Total PDF files: {len(pdf_files)}")

    # Run scraper second time - should skip everything
    print(f"\n[8] SECOND SCRAPER RUN (should skip all)")
    print("-" * 70)
    engine2 = ScraperEngine(
        page_timeout=15,
        max_pdf_size_mb=100,
        verbose=False,
        skip_recent_sites=False,  # Force re-scrape for testing
    )

    try:
        result2 = engine2.run(str(test_excel), str(output_dir))
        print(f"\nSecond run results:")
        print(f"  - Pages crawled: {result2.get('pages', 0)}")
        print(f"  - PDFs downloaded: {result2.get('pdfs', 0)}")
        print(f"  - Suppliers processed: {result2.get('suppliers', 0)}")
    except Exception as e:
        print(f"[ERROR] Second run failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Verify dedup worked
    pdf_files_after = list(output_dir.glob("**/*.pdf"))
    print(f"\n[9] DEDUP VERIFICATION")
    print(f"    Files after first run: {len(pdf_files)}")
    print(f"    Files after second run: {len(pdf_files_after)}")
    if len(pdf_files) == len(pdf_files_after):
        print(f"    [OK] No new files downloaded (dedup works!)")
    else:
        new_count = len(pdf_files_after) - len(pdf_files)
        print(f"    [WARN] {new_count} new files downloaded (dedup might not be working)")

    print(f"\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
