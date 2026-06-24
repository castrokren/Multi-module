#!/usr/bin/env python3
"""
Phase 4 Monitoring Analysis
Analyze unknown items patterns, Rule B effectiveness, and supplier coverage.
"""

import pandas as pd
from pathlib import Path
from collections import Counter
import json

OUTPUT_DIR = Path("C:/Data/Crawler/labeled")
SUPPLIER_DB_PATH = Path("docs/references/supplier_classification.json")

def load_supplier_db():
    """Load supplier classification database."""
    if SUPPLIER_DB_PATH.exists():
        with open(SUPPLIER_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def analyze_classifications():
    """Analyze all classified files for Unknown patterns."""
    print("[Phase 4] Analyzing classification results...")

    # Only load the latest v3 files, exclude duplicates like *_v3_v3.xlsx
    all_v3_files = list(OUTPUT_DIR.glob("*_classified_v3.xlsx"))
    files = [f for f in all_v3_files if "_v3_v3" not in f.name]  # exclude duplicates

    if not files:
        print(f"  No classified files found in {OUTPUT_DIR}")
        return None

    print(f"  Found {len(files)} classified files (v3, excluding duplicates)")

    all_data = []
    for file in files:
        try:
            df = pd.read_excel(file)
            all_data.append(df)
            print(f"    Loaded {len(df)} rows from {file.name}")
        except Exception as e:
            print(f"    ERROR loading {file.name}: {e}")

    if not all_data:
        return None

    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n[Results] Total items: {len(combined)}")

    # Classification breakdown
    type_counts = combined["Type"].value_counts().to_dict()
    print(f"\n[Classification Breakdown]")
    for typ, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(combined)
        print(f"  {typ:20s}: {count:5d} ({pct:5.1f}%)")

    # Unknown analysis
    unknown = combined[combined["Type"] == "Unknown"]
    if len(unknown) > 0:
        print(f"\n[Unknown Items Analysis] ({len(unknown)} items)")

        # Top suppliers with Unknown items
        supplier_unknown = unknown["Supplier Name"].value_counts().head(20)
        print(f"\n  Top suppliers with Unknown items:")
        for supplier, count in supplier_unknown.items():
            print(f"    {supplier}: {count} items")

        # Rule B analysis: check if suppliers are in database
        supplier_db = load_supplier_db()
        in_db = 0
        not_in_db = 0
        for supplier in unknown["Supplier Name"].unique():
            if supplier in supplier_db:
                in_db += 1
            else:
                not_in_db += 1

        print(f"\n  Supplier database coverage:")
        print(f"    In database (should be reclassified): {in_db}")
        print(f"    NOT in database (needs manual review): {not_in_db}")

        # Sample Unknown items
        print(f"\n  Sample Unknown items (first 10):")
        for idx, row in unknown.head(10).iterrows():
            print(f"    {row['Supplier Name']:40s} | {row['Item Description'][:50]}")

    else:
        print("[Success] No Unknown items remaining!")

    # Rule effectiveness summary
    print(f"\n[Summary vs Phase 3 Target]")
    print(f"  Phase 3 goal: <400 Unknown items")
    print(f"  Achieved: {type_counts.get('Unknown', 0)} Unknown items")
    if type_counts.get('Unknown', 0) < 400:
        print(f"  Status: TARGET MET")
    else:
        print(f"  Status: Above target")

    return combined

if __name__ == "__main__":
    analyze_classifications()
