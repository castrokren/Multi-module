#!/usr/bin/env python3
"""Analyze remaining Unknown items after Rule A to see patterns for Rule C (Bundle Analysis)."""

import pandas as pd
from pathlib import Path

# Load the classified output from Rule A
classified_file = r"C:\Data\Crawler\labeled\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1)_classified_v3.xlsx"
df = pd.read_excel(classified_file)

# Filter to Unknown items
unknown = df[df["Type"] == "Unknown"].copy()
print(f"Unknown items after Rule A: {len(unknown)}")
print(f"\nSample of Unknown items (first 30):")
print("=" * 80)

for idx, (i, row) in enumerate(unknown.head(30).iterrows()):
    print(f"\n[{idx+1}] Req ID: {row['Req ID']}")
    print(f"    Supplier: {row['Supplier Name']}")
    print(f"    Item: {row['Item Description']}")

    # Check for bundle indicators
    desc = str(row['Item Description']).lower()
    has_semicolon = ';' in desc
    has_comma = ',' in desc
    has_slash = '/' in desc
    bundle_indicators = []
    if has_semicolon:
        bundle_indicators.append("semicolon")
    if has_comma:
        bundle_indicators.append("comma")
    if has_slash:
        bundle_indicators.append("slash")

    if bundle_indicators:
        print(f"    Bundle indicators: {', '.join(bundle_indicators)}")

# Statistics on bundle indicators
print("\n" + "=" * 80)
print("BUNDLE ANALYSIS STATISTICS")
print("=" * 80)

unknown["has_semicolon"] = unknown["Item Description"].astype(str).str.contains(";", na=False)
unknown["has_comma"] = unknown["Item Description"].astype(str).str.contains(",", na=False)
unknown["has_slash"] = unknown["Item Description"].astype(str).str.contains("/", na=False)
unknown["has_bundle"] = unknown["has_semicolon"] | unknown["has_comma"] | unknown["has_slash"]

print(f"Unknown items with bundle indicators:")
print(f"  Semicolon: {unknown['has_semicolon'].sum()}")
print(f"  Comma: {unknown['has_comma'].sum()}")
print(f"  Slash: {unknown['has_slash'].sum()}")
print(f"  Any bundle indicator: {unknown['has_bundle'].sum()} ({unknown['has_bundle'].sum()/len(unknown)*100:.1f}%)")

# Vague items
vague_terms = ['equipment', 'system', 'unit', 'assembly', 'component', 'kit', 'set', 'package']
def has_vague(desc):
    desc_lower = str(desc).lower()
    return any(term in desc_lower for term in vague_terms)

unknown["has_vague"] = unknown["Item Description"].apply(has_vague)
print(f"\nUnknown items with vague descriptions: {unknown['has_vague'].sum()} ({unknown['has_vague'].sum()/len(unknown)*100:.1f}%)")

# Short descriptions (likely generic)
unknown["desc_length"] = unknown["Item Description"].astype(str).str.len()
print(f"\nUnknown items by description length:")
print(f"  <20 chars: {(unknown['desc_length'] < 20).sum()}")
print(f"  20-50 chars: {((unknown['desc_length'] >= 20) & (unknown['desc_length'] < 50)).sum()}")
print(f"  50+ chars: {(unknown['desc_length'] >= 50).sum()}")

print(f"\nSample short Unknown items (<20 chars):")
short = unknown[unknown['desc_length'] < 20].head(10)
for i, (idx, row) in enumerate(short.iterrows()):
    print(f"  [{i+1}] '{row['Item Description']}' (Supplier: {row['Supplier Name']})")
