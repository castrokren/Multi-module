import pandas as pd
from pathlib import Path
import sys

# Read labeled data
labeled_file = Path("C:/Data/Crawler/labeled/NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx")
df = pd.read_excel(labeled_file)

# Pick a supplier with PDFs - ILLUMINA INC (has 17 PDFs)
supplier_name = "ILLUMINA INC"
pdf_dir = Path("C:/Data/Crawler/output") / supplier_name

# Get items for this supplier
items = df[df['Supplier Name'] == supplier_name]
print(f"Supplier: {supplier_name}")
print(f"Items for this supplier: {len(items)}")
print(f"PDF files in folder: {list(pdf_dir.glob('*.pdf')).__len__()}")

if len(items) > 0:
    item = items.iloc[0]
    print(f"\n=== SAMPLE ITEM ===")
    print(f"Code: {item.iloc[0]}")
    print(f"Description: {item['Item Description'] if 'Item Description' in df.columns else item.iloc[1]}")
    print(f"Type: {item['TYPE'] if 'TYPE' in df.columns else 'N/A'}")

# List PDF files
if pdf_dir.exists():
    pdfs = list(pdf_dir.glob("*.pdf"))
    print(f"\n=== PDF FILES IN {supplier_name} ({len(pdfs)} files) ===")
    for pdf in pdfs[:10]:
        print(f"  {pdf.name}")
    if len(pdfs) > 10:
        print(f"  ... and {len(pdfs) - 10} more")

    # Try to extract text from first PDF
    print(f"\n=== TEXT EXTRACTION TEST ===")
    if pdfs:
        try:
            import PyPDF2
            with open(pdfs[0], 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page_num in range(min(3, len(reader.pages))):
                    page = reader.pages[page_num]
                    text += page.extract_text()
                print(f"PDF: {pdfs[0].name}")
                print(f"Text extracted: {len(text)} characters")
                print(f"First 200 chars: {text[:200]}")
        except Exception as e:
            print(f"Error extracting text: {e}")
