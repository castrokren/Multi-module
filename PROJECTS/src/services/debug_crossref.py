#!/usr/bin/env python3
"""
Diagnostic script for debugging zero cross-reference matches.
Runs 4 checks to identify root causes.

Usage:
    python debug_crossref.py --config pipeline_config.json
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from difflib import SequenceMatcher
import importlib.util

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent / "cross-reference"))

def load_config(config_path):
    """Load and normalize pipeline config."""
    with open(config_path) as f:
        cfg = json.load(f)

    # Normalize paths relative to PROJECT_ROOT
    project_root = Path(__file__).resolve().parents[2]
    paths = cfg.get("paths", {})
    for key in ("pdf_dir", "labeled_dir", "master_excel"):
        raw = paths.get(key, "")
        p = Path(raw)
        if not p.is_absolute():
            paths[key] = str((project_root / raw).resolve())
        else:
            paths[key] = str(p.resolve())
    cfg["paths"] = paths
    return cfg

def check_a_pdf_directory(cfg):
    """Check A: Walk pdf_dir, count .pdf files."""
    print("\n" + "="*70)
    print("CHECK A - PDF DIRECTORY CONTENTS")
    print("="*70)

    pdf_dir = cfg["paths"].get("pdf_dir", "")
    pdf_path = Path(pdf_dir)

    print(f"pdf_dir config: {pdf_dir}")
    print(f"pdf_dir exists: {pdf_path.exists()}")

    if not pdf_path.exists():
        print("[ERROR] PDF directory does not exist!")
        return

    # Count folders and PDFs
    folders = []
    pdf_count = 0

    for root, dirs, files in os.walk(pdf_path):
        # Track folders at top level (supplier folders)
        rel_root = Path(root).relative_to(pdf_path)
        if str(rel_root) != ".":
            folder_name = str(rel_root).split(os.sep)[0]
            if folder_name not in folders:
                folders.append(folder_name)

        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_count += 1

    print(f"Total supplier folders: {len(folders)}")
    print(f"Total PDFs found: {pdf_count}")

    if folders:
        print(f"First 10 folders: {folders[:10]}")

    if pdf_count == 0:
        print("[ERROR] No PDFs found in pdf_dir!")
    else:
        print(f"✅ Found {pdf_count} PDFs")

    return {
        "exists": pdf_path.exists(),
        "folder_count": len(folders),
        "pdf_count": pdf_count,
        "folders": folders
    }

def check_b_sqlite_db(cfg):
    """Check B: Try to open SQLite dedup database."""
    print("\n" + "="*70)
    print("CHECK B - SQLITE DEDUP DATABASE")
    print("="*70)

    pdf_dir = cfg["paths"].get("pdf_dir", "")
    db_path = Path(pdf_dir) / ".scraper_dedup.db"

    print(f"Looking for: {db_path}")
    print(f"DB exists: {db_path.exists()}")

    if not db_path.exists():
        print("[WARNING]️  No SQLite database found (this is OK if scraper hasn't run yet)")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Count records
        try:
            cursor.execute("SELECT COUNT(*) FROM downloaded")
            downloaded_count = cursor.fetchone()[0]
            print(f"Downloaded count: {downloaded_count}")
        except:
            downloaded_count = None
            print("[WARNING]️  Could not query 'downloaded' table")

        try:
            cursor.execute("SELECT COUNT(*) FROM seen_urls")
            seen_count = cursor.fetchone()[0]
            print(f"Seen URLs count: {seen_count}")
        except:
            seen_count = None
            print("[WARNING]️  Could not query 'seen_urls' table")

        # Show first 5 downloaded records
        try:
            cursor.execute("SELECT * FROM downloaded LIMIT 5")
            rows = cursor.fetchall()
            if rows:
                print(f"\nFirst 5 downloaded records:")
                cols = [desc[0] for desc in cursor.description]
                print(f"  Columns: {cols}")
                for row in rows:
                    print(f"    {row}")
        except Exception as e:
            print(f"[WARNING]️  Could not fetch downloaded records: {e}")

        conn.close()

        if downloaded_count == 0:
            print("\n[ERROR] Scraper downloaded zero PDFs!")
        else:
            print(f"\n✅ Scraper downloaded {downloaded_count} PDFs")

        return {
            "exists": True,
            "downloaded_count": downloaded_count,
            "seen_count": seen_count
        }

    except Exception as e:
        print(f"[ERROR] Error opening database: {e}")
        return None

def check_c_supplier_matching(cfg):
    """Check C: Fuzzy match supplier names."""
    print("\n" + "="*70)
    print("CHECK C - SUPPLIER NAME MATCHING")
    print("="*70)

    pdf_dir = cfg["paths"].get("pdf_dir", "")
    labeled_dir = cfg["paths"].get("labeled_dir", "")

    # Find most recent labeled Excel
    labeled_path = Path(labeled_dir)
    excel_files = sorted(
        list(labeled_path.glob("*_labeled.xlsx")) + list(labeled_path.glob("*.xlsx")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not excel_files:
        print(f"[ERROR] No Excel files found in {labeled_dir}")
        return

    excel_file = excel_files[0]
    print(f"Using Excel: {excel_file.name}")

    try:
        import pandas as pd
        df = pd.read_excel(str(excel_file))

        # Find supplier column
        supplier_col = None
        for col in ["Supplier Name", "Supplier", "Vendor", "Company"]:
            if col in df.columns:
                supplier_col = col
                break

        if not supplier_col:
            print(f"[WARNING]️  Could not find supplier column in Excel")
            return

        csv_suppliers = df[supplier_col].dropna().unique().tolist()
        print(f"Unique suppliers in Excel: {len(csv_suppliers)}")
        if csv_suppliers:
            print(f"  Sample: {csv_suppliers[:5]}")

    except Exception as e:
        print(f"[ERROR] Error reading Excel: {e}")
        return

    # Get folder names
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        print(f"[ERROR] PDF directory {pdf_dir} does not exist")
        return

    folder_names = [d.name for d in pdf_path.iterdir() if d.is_dir()]
    print(f"\nFolders in pdf_dir: {len(folder_names)}")
    if folder_names:
        print(f"  Sample: {folder_names[:5]}")

    # Fuzzy match
    threshold = 0.7
    hits = 0
    misses = 0
    unmatched = []

    print(f"\nFuzzy matching (threshold={threshold}):")
    for csv_name in csv_suppliers:
        best, best_score = None, 0
        for folder in folder_names:
            score = SequenceMatcher(None, csv_name.lower(), folder.lower()).ratio()
            if score > best_score:
                best, best_score = folder, score

        if best_score >= threshold:
            hits += 1
            print(f"  ✅ '{csv_name}' -> '{best}' ({best_score:.2f})")
        else:
            misses += 1
            unmatched.append((csv_name, best, best_score if best else 0))
            print(f"  [ERROR] '{csv_name}' -> no match (best: '{best}' {best_score:.2f})")

    print(f"\nResults: {hits} hits, {misses} misses")
    if misses > 0:
        print(f"Unmatched suppliers: {[name for name, _, _ in unmatched]}")

    if misses == 0:
        print("✅ All supplier names matched!")
    elif misses / len(csv_suppliers) < 0.2:
        print("✅ Hit rate > 80%")
    else:
        print("[ERROR] Hit rate < 80% - supplier name mismatch likely!")

    return {
        "csv_suppliers": len(csv_suppliers),
        "folder_names": len(folder_names),
        "hits": hits,
        "misses": misses,
        "unmatched": unmatched
    }

def check_d_pdf_smart_filter(cfg):
    """Check D: Run PDFSmartFilter classification."""
    print("\n" + "="*70)
    print("CHECK D - PDF SMART FILTER CLASSIFICATION")
    print("="*70)

    pdf_dir = cfg["paths"].get("pdf_dir", "")
    pdf_path = Path(pdf_dir)

    if not pdf_path.exists():
        print(f"[ERROR] PDF directory {pdf_dir} does not exist")
        return

    # Try to import PDFSmartFilter
    try:
        crossref_utils_path = Path(__file__).parent / "cross-reference" / "crossref_standalone_fast.py"
        spec = importlib.util.spec_from_file_location("crossref_module", crossref_utils_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        PDFSmartFilter = module.PDFSmartFilter
    except Exception as e:
        print(f"[ERROR] Could not import PDFSmartFilter: {e}")
        return

    filter_obj = PDFSmartFilter()

    # Classify all PDFs
    categories = {
        "high_priority": 0,
        "medium_priority": 0,
        "unknown": 0,
        "noise": 0
    }
    noise_files = []

    pdf_count = 0
    for root, dirs, files in os.walk(pdf_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_count += 1
                category, score = filter_obj.classify_pdf(file)
                categories[category] += 1

                if category == "noise" and len(noise_files) < 10:
                    noise_files.append(file)

    print(f"Total PDFs classified: {pdf_count}")
    print(f"  High priority: {categories['high_priority']}")
    print(f"  Medium priority: {categories['medium_priority']}")
    print(f"  Unknown: {categories['unknown']}")
    print(f"  Noise (discarded): {categories['noise']}")

    if pdf_count > 0:
        noise_pct = (categories['noise'] / pdf_count) * 100
        print(f"\nNoise percentage: {noise_pct:.1f}%")

        if noise_pct > 80:
            print("[ERROR] Over 80% of PDFs classified as noise!")
        elif noise_pct > 50:
            print("[WARNING]️  Over 50% classified as noise - may be over-filtering")
        else:
            print("✅ Reasonable noise filter rate")

    if noise_files:
        print(f"\nSample noise files (first 10):")
        for f in noise_files:
            print(f"  - {f}")

    return {
        "total_pdfs": pdf_count,
        "categories": categories,
        "noise_pct": (categories['noise'] / pdf_count * 100) if pdf_count > 0 else 0,
        "sample_noise": noise_files
    }

def main():
    parser = argparse.ArgumentParser(description="Diagnose cross-reference issues")
    parser.add_argument("--config", default="pipeline_config.json")
    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"[ERROR] Config not found: {args.config}")
        sys.exit(1)

    cfg = load_config(args.config)

    print("\n" + "="*70)
    print("CROSS-REFERENCE DIAGNOSTIC SUITE")
    print("="*70)

    results = {}
    results["check_a"] = check_a_pdf_directory(cfg)
    results["check_b"] = check_b_sqlite_db(cfg)
    results["check_c"] = check_c_supplier_matching(cfg)
    results["check_d"] = check_d_pdf_smart_filter(cfg)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if results["check_a"] and results["check_a"]["pdf_count"] == 0:
        print("\n🔴 ROOT CAUSE LIKELY: Step 1 or 2 - No PDFs in pdf_dir or scraper failed")
        print("    -> Check Step 2: Verify pdf_dir path and that scraper ran successfully")

    if results["check_b"] and results["check_b"]["downloaded_count"] == 0:
        print("\n🔴 ROOT CAUSE LIKELY: Step 2 - Scraper downloaded zero PDFs")
        print("    -> Re-run scraper stage: python pipeline.py --only-scraper")

    if results["check_c"] and results["check_c"]["misses"] / max(1, results["check_c"]["csv_suppliers"]) > 0.2:
        print("\n🟡 POSSIBLE ISSUE: Step 3 - Supplier name mismatch")
        print("    -> Check Step 3: Add logging to find_matching_pdfs() or build fuzzy mapping")

    if results["check_d"] and results["check_d"]["noise_pct"] > 80:
        print("\n🟡 POSSIBLE ISSUE: Step 4 - PDF Smart Filter over-filtering")
        print("    -> Check Step 4: Review noise_patterns in PDFSmartFilter")

    print("\n✅ Diagnostic complete. Use findings above to decide which steps to apply.")

if __name__ == "__main__":
    main()
