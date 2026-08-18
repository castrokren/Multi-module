"""
Column Filtering + Classification Pipeline
Step 1: Filter columns B, F, G, I, O
Step 2: Classify entries (Instrument/Software/Non-Instrument)
Step 3: Output formatted Excel sheets
"""

import pandas as pd
from pathlib import Path
import sys
import os

# Add classify service to path to import adaptive processor
sys.path.insert(0, str(Path(__file__).parent.parent / "classify"))
from adaptive_excel_processor import AdaptiveExcelProcessor

# Column mapping
COLUMN_MAP = {
    "Req ID": "B",
    "Supplier ID": "F",
    "Supplier Name": "G",
    "Item Description": "I",
    "Req Line Item": "O"
}

KEYWORD_DIR = Path(__file__).parent.parent / "classify"


def filter_and_classify(input_file: str, output_dir: str = None) -> dict:
    """
    Read Excel, filter columns, classify, output formatted Excel.

    Args:
        input_file: Path to input Excel/CSV
        output_dir: Where to save results (default: C:\\Data\\Crawler\\labeled\\)

    Returns:
        Dict with stats
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_path = Path(output_dir or "C:\\Data\\Crawler\\labeled")
    output_path.mkdir(parents=True, exist_ok=True)

    # Load file
    file_ext = input_path.suffix.lower()
    if file_ext == ".csv":
        df = pd.read_csv(input_file)
    else:
        df = pd.read_excel(input_file)

    print(f"[pipeline] Loaded {len(df)} rows from {input_path.name}")

    # Map columns by position (Excel uses 1-indexed, pandas 0-indexed)
    # A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11, M=12, N=13, O=14
    col_indices = [1, 5, 6, 8, 14]  # B, F, G, I, O
    col_names = ["Req ID", "Supplier ID", "Supplier Name", "Item Description", "Req Line Item"]

    # Select columns by position
    if len(df.columns) >= max(col_indices) + 1:
        df_filtered = df.iloc[:, col_indices].copy()
        df_filtered.columns = col_names
    else:
        # Fall back: try to match by name if columns are named
        available_cols = list(df.columns)
        print(f"[pipeline] Available columns: {available_cols}")

        # Try fuzzy column matching
        col_mapping = {}
        for target, col_pos in zip(col_names, [1, 5, 6, 8, 14]):
            # Try exact match first
            if target in df.columns:
                col_mapping[target] = target
            # Try column by position
            elif col_pos < len(df.columns):
                col_mapping[target] = df.columns[col_pos]
            else:
                raise ValueError(f"Cannot find column for {target}")

        df_filtered = df[[col_mapping[name] for name in col_names]]
        df_filtered.columns = col_names

    print(f"[pipeline] Filtered to 5 columns: {', '.join(col_names)}")

    # Initialize classifier
    hw_kw_file = KEYWORD_DIR / "research_instrument_keywords.txt"
    sw_kw_file = KEYWORD_DIR / "software_keywords.txt"
    ni_kw_file = KEYWORD_DIR / "non_instrument_keywords.txt"

    classifier = AdaptiveExcelProcessor(
        hw_keywords_file=str(hw_kw_file),
        sw_keywords_file=str(sw_kw_file),
        ni_keywords_file=str(ni_kw_file),
        output_dir=str(output_path),
        learning_mode=False
    )

    # Classify each row based on "Req Line Item" column
    classifications = []
    for idx, row in df_filtered.iterrows():
        req_line = str(row.get("Req Line Item", "")).lower()
        item_desc = str(row.get("Item Description", "")).lower()

        # Use classifier's scoring logic
        hw_score = sum(1 for kw in classifier.hw_keywords if kw in req_line or kw in item_desc)
        sw_score = sum(1 for kw in classifier.sw_keywords if kw in req_line or kw in item_desc)
        ni_score = sum(1 for kw in classifier.ni_keywords if kw in req_line or kw in item_desc)

        # Determine type
        if hw_score > 0 and hw_score >= sw_score and hw_score >= ni_score:
            classification = "Instrument"
        elif sw_score > 0 and sw_score >= ni_score:
            classification = "Software"
        elif ni_score > 0:
            classification = "Non-Instrument"
        else:
            classification = "Unknown"  # No keywords matched

        classifications.append(classification)

    df_filtered["Type"] = classifications

    # Count types
    type_counts = df_filtered["Type"].value_counts().to_dict()
    print(f"[pipeline] Classification results: {type_counts}")

    # Save to output
    output_file = output_path / (input_path.stem + "_classified.xlsx")
    df_filtered.to_excel(output_file, index=False)
    print(f"[pipeline] Saved to {output_file}")

    return {
        "input_file": str(input_path),
        "output_file": str(output_file),
        "rows_processed": len(df_filtered),
        "classification_counts": type_counts,
        "status": "success"
    }


def process_all_inputs(input_dir: str = None, output_dir: str = None) -> dict:
    """Process all Excel/CSV files in input directory."""
    input_path = Path(input_dir or "C:\\Data\\Crawler\\input")
    output_path = Path(output_dir or "C:\\Data\\Crawler\\labeled")

    if not input_path.exists():
        raise FileNotFoundError(f"Input dir not found: {input_path}")

    files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls")) + list(input_path.glob("*.csv"))
    print(f"[pipeline] Found {len(files)} files")

    results = []
    for file in files:
        try:
            result = filter_and_classify(str(file), str(output_path))
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {file.name}: {e}")
            results.append({"file": str(file), "status": "error", "error": str(e)})

    return {"files_processed": len(files), "results": results}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Process single file
        filter_and_classify(sys.argv[1])
    else:
        # Process all files in input dir
        process_all_inputs()
