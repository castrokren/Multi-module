#!/usr/bin/env python3
"""
Final diagnostic to determine if zero matches is a data quality issue
or a code/algorithm issue.
"""
import pandas as pd
from pathlib import Path
import PyPDF2
import re
from difflib import SequenceMatcher

print("="*80)
print("FINAL DIAGNOSTIC: Why are we getting 0 matches?")
print("="*80)

# Read the labeled data
labeled_file = Path("C:/Data/Crawler/labeled/NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx")
df = pd.read_excel(labeled_file)

# Get suppliers with PDFs
pdf_dir = Path("C:/Data/Crawler/output")
suppliers_with_pdfs = [d.name for d in pdf_dir.iterdir()
                      if d.is_dir() and len(list(d.glob("*.pdf"))) > 0]

print(f"\nSuppliers in CSV: {len(df['Supplier Name'].unique())}")
print(f"Suppliers with PDFs: {len(suppliers_with_pdfs)}")

# Pick a supplier with PDFs and items
for supplier in suppliers_with_pdfs[:5]:
    supplier_items = df[df['Supplier Name'] == supplier]
    if len(supplier_items) == 0:
        continue

    print(f"\n{'='*80}")
    print(f"Testing Supplier: {supplier} ({len(supplier_items)} items, {len(list((pdf_dir/supplier).glob('*.pdf')))} PDFs)")
    print(f"{'='*80}")

    # Test first item
    item = supplier_items.iloc[0]
    description = item['Item Description']
    print(f"\nItem Description: {description}")

    # Extract keywords like the cross-ref code does
    common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = re.findall(r'\b\w+\b', description.lower())
    keywords = [w for w in words if w not in common_words and len(w) > 1]
    print(f"Keywords: {keywords[:15]}")

    # Test against first PDF
    pdfs = list((pdf_dir / supplier).glob("*.pdf"))[:3]
    for pdf_path in pdfs:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page_num in range(min(5, len(reader.pages))):
                    try:
                        text += reader.pages[page_num].extract_text() or ""
                    except:
                        continue

            if len(text) < 200:
                print(f"\n  {pdf_path.name}: REJECTED (text < 200 chars: {len(text)})")
                continue

            text_lower = text.lower()

            # Calculate score like standalone function does
            matched = [kw for kw in keywords if kw in text_lower]
            keyword_score = (len(matched) / len(keywords) * 60) if keywords else 0

            # Similarity
            desc_lower = description.lower()
            similarity = SequenceMatcher(None, desc_lower, text_lower[:2000]).ratio()
            similarity_score = similarity * 25

            total = min(100, keyword_score + similarity_score)

            print(f"\n  {pdf_path.name}:")
            print(f"    Text length: {len(text)} chars")
            print(f"    Keywords matched: {len(matched)}/{len(keywords)}")
            print(f"    Keyword score: {keyword_score:.1f}")
            print(f"    Similarity: {similarity:.2f} -> {similarity_score:.1f}")
            print(f"    TOTAL SCORE: {total:.1f} (threshold: 30)")
            print(f"    RESULT: {'✅ MATCH' if total >= 30 else '[ERROR] NO MATCH'}")

        except Exception as e:
            print(f"  {pdf_path.name}: ERROR - {e}")
