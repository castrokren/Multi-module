#!/usr/bin/env python3
"""Test Rule A (Prior Context) impact on Phase 2 sample data."""

import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "services" / "data-cleaning"))

from column_filter_and_classify_v3 import classify_item, load_and_clean_keywords

# Load the phase2a test data
test_data_path = Path(__file__).parent / "phase2a_sample_test_results.csv"
print(f"Loading test data from {test_data_path}")
df = pd.read_csv(test_data_path)

print(f"\nTest dataset: {len(df)} rows")
print(f"Columns: {list(df.columns)}")

# Load keywords
hw_kw, sw_kw, ni_kw = load_and_clean_keywords()

# Run classification WITHOUT Rule A
print("\n--- PHASE 1: Baseline (keyword classification only) ---")
classifications_baseline = []
for idx, row in df.iterrows():
    req_line = str(row.get("Req Line Item", ""))
    item_desc = str(row.get("Item Description", ""))
    classification = classify_item(req_line, item_desc, hw_kw, sw_kw, ni_kw)
    classifications_baseline.append(classification)

df["Baseline_Classification"] = classifications_baseline
baseline_counts = df["Baseline_Classification"].value_counts().to_dict()
print(f"Baseline results: {baseline_counts}")

# Apply Rule A (Prior Context)
print("\n--- PHASE 2B: Rule A (Prior Context) ---")
rule_a_count = 0
df = df.reset_index(drop=True)
for req_id in df["Req ID"].unique():
    group_indices = df[df["Req ID"] == req_id].index.tolist()
    for i in range(1, len(group_indices)):
        curr_idx = group_indices[i]
        prev_idx = group_indices[i-1]
        if df.at[curr_idx, "Baseline_Classification"] == "Unknown" and df.at[prev_idx, "Baseline_Classification"] == "Instrument":
            df.at[curr_idx, "Baseline_Classification"] = "Instrument"
            rule_a_count += 1
            print(f"  Req {req_id}: Item {i} Unknown -> Instrument (prior Instrument)")

print(f"\nRule A reclassified: {rule_a_count} items")

# Compare results
print("\n--- IMPACT ANALYSIS ---")
rule_a_counts = df["Baseline_Classification"].value_counts().to_dict()
print(f"After Rule A: {rule_a_counts}")

# Calculate Unknown reduction
unknown_before = baseline_counts.get("Unknown", 0)
unknown_after = rule_a_counts.get("Unknown", 0)
unknown_reduction = unknown_before - unknown_after
unknown_reduction_pct = (unknown_reduction / unknown_before * 100) if unknown_before > 0 else 0

print(f"\nUnknown reduction:")
print(f"  Before: {unknown_before} items")
print(f"  After:  {unknown_after} items")
print(f"  Reduction: {unknown_reduction} items ({unknown_reduction_pct:.1f}%)")

# Instrument increase
instrument_before = baseline_counts.get("Instrument", 0)
instrument_after = rule_a_counts.get("Instrument", 0)
instrument_increase = instrument_after - instrument_before

print(f"\nInstrument increase:")
print(f"  Before: {instrument_before} items")
print(f"  After:  {instrument_after} items")
print(f"  Increase: {instrument_increase} items")

# Save detailed results
output_path = Path(__file__).parent / "rule_a_test_results.csv"
df.to_csv(output_path, index=False)
print(f"\nDetailed results saved to {output_path}")
