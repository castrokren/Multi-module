import pandas as pd
from pathlib import Path
from difflib import SequenceMatcher

# Read the labeled Excel file
labeled_file = Path("C:/Data/Crawler/labeled/NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx")
df = pd.read_excel(labeled_file)

# Get unique suppliers from CSV
suppliers_csv = list(df['Supplier Name'].unique())
print(f"Total unique CSV suppliers: {len(suppliers_csv)}")
print("\nSample CSV suppliers (first 10):")
for s in suppliers_csv[:10]:
    print(f"  {s}")

# Get supplier folder names from PDF directory
pdf_dir = Path("C:/Data/Crawler/output")
suppliers_folders = sorted([d.name for d in pdf_dir.iterdir() if d.is_dir() and d.name != "#backup_logs"])
print(f"\nTotal PDF supplier folders: {len(suppliers_folders)}")
print("\nSample PDF folders (first 10):")
for s in suppliers_folders[:10]:
    print(f"  {s}")

# Check for exact matches
csv_set = set(suppliers_csv)
folder_set = set(suppliers_folders)
exact_matches = csv_set & folder_set

print(f"\n=== MATCHING ANALYSIS ===")
print(f"Exact matches: {len(exact_matches)}")
print(f"CSV suppliers not in folders: {len(csv_set - folder_set)}")

# Find best fuzzy matches for mismatches
print(f"\n=== FUZZY MATCHING (threshold 0.8) ===")
fuzzy_matches = 0
for csv_supplier in sorted(csv_set - folder_set)[:10]:
    best_match = None
    best_score = 0
    for folder in suppliers_folders:
        score = SequenceMatcher(None, csv_supplier.lower(), folder.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = folder
    if best_score >= 0.8:
        print(f"  CSV: {csv_supplier}")
        print(f"  Folder: {best_match} (score: {best_score:.2f})")
        fuzzy_matches += 1

print(f"\nFuzzy matches found: {fuzzy_matches}")

# Check PDF counts per supplier
pdfs_with_files = sum(1 for d in suppliers_folders if len(list(d.glob("*.pdf"))) > 0 for d in [Path("C:/Data/Crawler/output") / d])
print(f"\n=== PDF DISTRIBUTION ===")
total_pdfs = sum(len(list((Path("C:/Data/Crawler/output") / d).glob("*.pdf"))) for d in suppliers_folders)
print(f"Total PDFs: {total_pdfs}")
print(f"Suppliers with PDFs: {sum(1 for d in suppliers_folders if len(list((Path('C:/Data/Crawler/output') / d).glob('*.pdf'))) > 0)}")
