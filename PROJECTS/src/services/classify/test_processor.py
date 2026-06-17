#!/usr/bin/env python3
from adaptive_excel_processor import AdaptiveExcelProcessor
from pathlib import Path
import time

files = [
    r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1).xlsx",
    r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43854371(sheet1).xlsx",
    r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1).xlsx",
]

config = {
    'hw_keywords_file': 'research_instrument_keywords.txt',
    'sw_keywords_file': 'software_keywords.txt',
    'ni_keywords_file': 'non_instrument_keywords.txt',
    'output_dir': r'C:\Data\Crawler\output',
    'learning_mode': True,
    'min_occurrences': 5,
    'confidence_threshold': 0.7
}

print("Processing all 3 research capital files...\n")

processor = AdaptiveExcelProcessor(**config)
total_start = time.time()

for excel_file in files:
    start = time.time()
    fname = Path(excel_file).name
    result = processor.process_file(excel_file, auto_promote=False)
    elapsed = time.time() - start
    status = "OK" if result else "FAILED"
    print(f"  {fname}: {elapsed:.1f}s - {status}")

total_time = time.time() - total_start
print(f"\nTotal: {total_time:.1f}s")

print("\nOutput files:")
output_dir = Path(r"C:\Data\Crawler\output")
for f in sorted(output_dir.glob("*_labeled.xlsx")):
    size_mb = f.stat().st_size / (1024*1024)
    print(f"  {f.name} ({size_mb:.1f} MB)")
