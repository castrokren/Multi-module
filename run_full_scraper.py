#!/usr/bin/env python3
"""
Run the full scraper on all 247 suppliers and track results.
"""
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "PROJECTS" / "src" / "services" / "scraper-full"))

import pandas as pd
from scraper_engine import ScraperEngine
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
)

def main():
    project_root = Path(__file__).parent / "PROJECTS"
    supplier_excel = project_root / "data" / "masterlist" / "updated_master_list.xlsx"
    output_dir = Path("C:/Data/Crawler/output")
    db_path = output_dir / ".scraper_dedup.db"

    print("\n" + "="*80)
    print("FULL SCRAPER RUN - ALL 247 SUPPLIERS")
    print("="*80)

    # Load full supplier list
    print(f"\n[1] Loading supplier list...")
    df = pd.read_excel(supplier_excel)
    print(f"    Total suppliers: {len(df)}")

    # Ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run scraper on FULL list
    print(f"\n[2] SCRAPER RUN - ALL SUPPLIERS")
    print("-" * 80)
    start_time = time.time()

    engine = ScraperEngine(
        page_timeout=15,
        max_pdf_size_mb=100,
        verbose=False,
        skip_recent_sites=False,  # Force scrape all suppliers
    )

    try:
        result = engine.run(str(supplier_excel), str(output_dir))
        elapsed = time.time() - start_time

        print(f"\n[3] SCRAPER COMPLETE")
        print(f"    Duration: {elapsed/60:.1f} minutes")
        print(f"    Pages crawled: {result.get('pages', 0)}")
        print(f"    PDFs downloaded: {result.get('pdfs', 0)}")
        print(f"    Suppliers processed: {result.get('suppliers', 0)}")

    except Exception as e:
        print(f"[ERROR] Scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Check database
    print(f"\n[4] DATABASE STATUS")
    if db_path.exists():
        print(f"    [OK] Database exists: {db_path}")
        db_size_mb = db_path.stat().st_size / 1024 / 1024
        print(f"    Size: {db_size_mb:.2f} MB")

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
        print(f"    [ERROR] Database not created!")
        return 1

    # Count actual files
    pdf_files = list(output_dir.glob("**/*.pdf"))
    print(f"\n[5] ACTUAL FILES")
    print(f"    Total PDF files on disk: {len(pdf_files)}")

    # Calculate stats
    unique_suppliers = len(set(p.parent.name for p in pdf_files))
    print(f"    Unique suppliers with PDFs: {unique_suppliers}")

    # Sample some files
    if pdf_files:
        print(f"\n[6] SAMPLE FILES")
        for pdf in sorted(pdf_files)[:5]:
            size_kb = pdf.stat().st_size / 1024
            print(f"    - {pdf.parent.name}/{pdf.name} ({size_kb:.1f} KB)")
        if len(pdf_files) > 5:
            print(f"    ... and {len(pdf_files) - 5} more")

    print(f"\n" + "="*80)
    print("FULL SCRAPER RUN COMPLETE")
    print("="*80 + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
