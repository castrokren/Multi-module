# Updated script with dynamic detection of the "Item Description" column
# Save as classify_and_clean_dynamic.py

import pandas as pd
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

def load_keywords(path: Path):
    return [l.strip().lower() for l in path.read_text().splitlines() if l.strip()]

def classify(desc: str, hw_kw, sw_kw):
    txt = (desc or "").lower()
    if any(kw in txt for kw in hw_kw):
        return "Instrument"
    if any(kw in txt for kw in sw_kw):
        return "Software"
    return "Non-Instrument"

def process_file(excel_path: Path, hw_file: Path, sw_file: Path):
    # Load keywords
    hw_kw = load_keywords(hw_file)
    sw_kw = load_keywords(sw_file)

    # Determine the appropriate engine based on file extension
    file_ext = excel_path.suffix.lower()
    if file_ext == '.xls':
        engine = 'xlrd'
    elif file_ext == '.xlsx':
        engine = 'openpyxl'
    else:
        print(f"Error: Unsupported file format {file_ext} for {excel_path.name}")
        return

    try:
        # Read the sheet (header row at index=1)
        df = pd.read_excel(excel_path, header=1, engine=engine)
    except Exception as e:
        print(f"Error reading {excel_path.name}: {e}")
        return

    # Identify the description column dynamically
    print(f"Available columns: {list(df.columns)}")
    desc_cols = [c for c in df.columns if 'description' in c.lower()]
    if not desc_cols:
        # Try other common column names
        desc_cols = [c for c in df.columns if any(word in c.lower() for word in ['desc', 'item', 'name', 'title', 'product', 'material'])]
        if not desc_cols:
            print(f"Error: No suitable description column found in {excel_path.name}")
            print(f"Available columns: {list(df.columns)}")
            return
    desc_col = desc_cols[0]
    print(f"Using '{desc_col}' as the description column.")

    # Drop unwanted columns by position: A-F (0-5), H (7), J-M (9-12), P-AF (15-31)
    cols = df.columns.tolist()
    drop_indices = list(range(0, 6)) + [7] + list(range(9, 13)) + list(range(15, 32))
    to_drop = [cols[i] for i in drop_indices if i < len(cols)]
    df.drop(columns=to_drop, inplace=True, errors='ignore')

    # Classify each row without removing any
    df.insert(0, 'TYPE', df[desc_col].apply(lambda d: classify(d, hw_kw, sw_kw)))

    # Save labeled file to D:\SOM_in_labeled
    output_dir = Path(r"D:\SOM_in_labeled")
    output_dir.mkdir(exist_ok=True)  # Create directory if it doesn't exist
    out = output_dir / (excel_path.stem + '_labeled.xlsx')
    df.to_excel(out, index=False, engine='openpyxl')
    print(f"-> Saved labeled file: {out.name}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python classify_and_clean_dynamic.py <file_or_directory>")
        sys.exit(1)

    base = Path(sys.argv[1])
    # Use absolute paths for keyword files
    script_dir = Path(__file__).parent
    hw_file = script_dir / 'hardware_keywords.txt'
    sw_file = script_dir / 'software_keywords.txt'

    if not hw_file.exists() or not sw_file.exists():
        print("Error: Missing hardware_keywords.txt or software_keywords.txt")
        sys.exit(1)

    if base.is_dir():
        # Process both .xls and .xlsx files
        for pattern in ['*.xls', '*.xlsx']:
            for f in base.glob(pattern):
                process_file(f, hw_file, sw_file)
    else:
        process_file(base, hw_file, sw_file)
