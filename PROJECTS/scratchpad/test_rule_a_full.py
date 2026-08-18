#!/usr/bin/env python3
"""Test Rule A on full dataset and compare to baseline."""

import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "services" / "data-cleaning"))

from column_filter_and_classify_v3 import filter_and_classify, load_and_clean_keywords, classify_item

# Run classifier with Rule A on full dataset
input_file = r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1).csv"
output_dir = r"C:\Data\Crawler\labeled"

print("=" * 60)
print("TESTING RULE A ON FULL DATASET")
print("=" * 60)

result = filter_and_classify(input_file, output_dir)
print(f"\nProcessing result:")
print(f"  Rows: {result['rows_processed']}")
print(f"  Classifications: {result['classification_counts']}")

# Load the output to analyze
output_file = Path(output_dir) / (Path(input_file).stem + "_classified_v3.xlsx")
df = pd.read_excel(output_file)

print(f"\nLoaded output: {len(df)} rows")
print(f"Classification distribution:")
for typ, count in sorted(df["Type"].value_counts().items()):
    pct = count / len(df) * 100
    print(f"  {typ}: {count} ({pct:.1f}%)")

# Now compare to baseline (without Rule A)
# Load original data
df_raw = pd.read_csv(input_file)
print(f"\nOriginal data: {len(df_raw)} rows")

# Filter to same columns
col_indices = [1, 5, 6, 8, 14]  # B, F, G, I, O
col_names = ["Req ID", "Supplier ID", "Supplier Name", "Item Description", "Req Line Item"]
if len(df_raw.columns) >= max(col_indices) + 1:
    df_filtered = df_raw.iloc[:, col_indices].copy()
    df_filtered.columns = col_names
else:
    df_filtered = df_raw

# Run baseline classification (keyword only, no Rule A)
hw_kw, sw_kw, ni_kw = load_and_clean_keywords()
print(f"\nKeywords loaded: HW={len(hw_kw)}, SW={len(sw_kw)}, NI={len(ni_kw)}")

classifications_baseline = []
for idx, row in df_filtered.iterrows():
    req_line = str(row.get("Req Line Item", ""))
    item_desc = str(row.get("Item Description", ""))
    classification = classify_item(req_line, item_desc, hw_kw, sw_kw, ni_kw)
    classifications_baseline.append(classification)

df_filtered["Type_Baseline"] = classifications_baseline

print(f"\nBaseline (keyword only) distribution:")
for typ, count in sorted(df_filtered["Type_Baseline"].value_counts().items()):
    pct = count / len(df_filtered) * 100
    print(f"  {typ}: {count} ({pct:.1f}%)")

# Apply Rule A manually to baseline
df_filtered = df_filtered.reset_index(drop=True)
rule_a_changes = 0
for req_id in df_filtered["Req ID"].unique():
    group_indices = df_filtered[df_filtered["Req ID"] == req_id].index.tolist()
    for i in range(1, len(group_indices)):
        curr_idx = group_indices[i]
        prev_idx = group_indices[i-1]
        if df_filtered.at[curr_idx, "Type_Baseline"] == "Unknown" and df_filtered.at[prev_idx, "Type_Baseline"] == "Instrument":
            df_filtered.at[curr_idx, "Type_Baseline"] = "Instrument"
            rule_a_changes += 1

print(f"\nRule A changes: {rule_a_changes} items")

print(f"\nBaseline + Rule A distribution:")
for typ, count in sorted(df_filtered["Type_Baseline"].value_counts().items()):
    pct = count / len(df_filtered) * 100
    print(f"  {typ}: {count} ({pct:.1f}%)")

# Summary
print("\n" + "=" * 60)
print("IMPACT SUMMARY")
print("=" * 60)
unknown_before = (df_filtered["Type_Baseline"] == "Unknown").sum() - rule_a_changes
unknown_after = (df_filtered["Type_Baseline"] == "Unknown").sum()
print(f"Unknown items reduced by: {rule_a_changes} ({rule_a_changes/unknown_before*100:.1f}%)" if unknown_before > 0 else "No Unknown items before Rule A")
