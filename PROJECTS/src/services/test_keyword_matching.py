import pandas as pd
from pathlib import Path
import PyPDF2

# Read labeled data
labeled_file = Path("C:/Data/Crawler/labeled/NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx")
df = pd.read_excel(labeled_file)

# Filter for ILLUMINA INC items
supplier_name = "ILLUMINA INC"
items = df[df['Supplier Name'] == supplier_name]

print(f"=== Testing Keyword Matching for {supplier_name} ===\n")

for idx, item in items.iterrows():
    description = item['Item Description']
    print(f"Item: {description}")

    # Extract keywords (simplified version of what cross-ref does)
    words = description.lower().split()
    keywords = [w for w in words if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'plus']]
    print(f"Keywords extracted: {keywords[:10]}")  # Show first 10

    # Get PDFs for this supplier
    pdf_dir = Path("C:/Data/Crawler/output") / supplier_name
    pdfs = list(pdf_dir.glob("*.pdf"))[:3]  # Test first 3 PDFs

    print(f"Testing against {len(pdfs)} PDFs:")
    for pdf_path in pdfs:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page_num in range(min(2, len(reader.pages))):
                    page = reader.pages[page_num]
                    text += page.extract_text().lower()

                # Check keyword matches
                found_keywords = [kw for kw in keywords if kw in text]
                match_percent = len(found_keywords) / len(keywords) * 100 if keywords else 0

                print(f"  {pdf_path.name}")
                print(f"    Text length: {len(text)} chars")
                print(f"    Keywords found: {len(found_keywords)}/{len(keywords)} ({match_percent:.1f}%)")
                print(f"    Found: {found_keywords}")
                print()
        except Exception as e:
            print(f"  {pdf_path.name}: ERROR - {e}\n")
