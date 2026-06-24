#!/usr/bin/env python3
"""Test combined Rules A + C on actual classifier."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "services" / "data-cleaning"))

from column_filter_and_classify_v3 import filter_and_classify

input_file = r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1).csv"
output_dir = r"C:\Data\Crawler\labeled"

print("=" * 60)
print("TESTING RULES A + C ON FULL DATASET")
print("=" * 60)

result = filter_and_classify(input_file, output_dir)
print(f"\nResults:")
for typ, count in sorted(result['classification_counts'].items()):
    pct = count / result['rows_processed'] * 100
    print(f"  {typ}: {count} ({pct:.1f}%)")

# Compare to baseline
baseline_unknown = 1134
baseline_instrument = 840
current_unknown = result['classification_counts'].get('Unknown', 0)
current_instrument = result['classification_counts'].get('Instrument', 0)

print(f"\nImpact:")
print(f"  Unknown: {baseline_unknown} → {current_unknown} ({baseline_unknown - current_unknown} items, {(baseline_unknown - current_unknown) / baseline_unknown * 100:.1f}% reduction)")
print(f"  Instrument: {baseline_instrument} → {current_instrument} ({current_instrument - baseline_instrument} items)")
