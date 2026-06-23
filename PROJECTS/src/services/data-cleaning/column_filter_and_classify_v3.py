"""
Hybrid Column Filtering + Classification (v3)
- Uses original keyword files but REMOVES conflicting entries
- Requires 2+ matches for Instrument (original was too loose)
- Allows 1+ match for Software/Non-Instrument (rarer categories)
- Clear priority order: Instrument > Software > Non-Instrument
"""

import pandas as pd
from pathlib import Path
import sys

COLUMN_MAP = {
    "Req ID": "B",
    "Supplier ID": "F",
    "Supplier Name": "G",
    "Item Description": "I",
    "Req Line Item": "O"
}

KEYWORD_DIR = Path(__file__).parent.parent / "classify"


def load_and_clean_keywords():
    """
    Load keyword files, identify conflicts, remove them.
    Keep specialized keywords, remove generic/conflicting ones.
    """
    # Load all three files
    with open(KEYWORD_DIR / "research_instrument_keywords.txt", encoding="utf-8") as f:
        hw_kw = set(line.strip().lower() for line in f if line.strip())

    with open(KEYWORD_DIR / "software_keywords.txt", encoding="utf-8") as f:
        sw_kw = set(line.strip().lower() for line in f if line.strip())

    with open(KEYWORD_DIR / "non_instrument_keywords.txt", encoding="utf-8") as f:
        ni_kw = set(line.strip().lower() for line in f if line.strip())

    # Find conflicts
    hw_sw = hw_kw & sw_kw
    hw_ni = hw_kw & ni_kw
    sw_ni = sw_kw & ni_kw
    all_three = hw_kw & sw_kw & ni_kw

    # Remove ALL conflicting keywords (conflicts cause misclassifications)
    hw_kw_clean = hw_kw - hw_sw - hw_ni
    sw_kw_clean = sw_kw - hw_sw - sw_ni
    ni_kw_clean = ni_kw - hw_ni - sw_ni

    # Also remove overly-broad short keywords (< 4 chars, alphabetic only)
    def is_too_broad(kw):
        return len(kw) < 4 and kw.isalpha() and kw not in {"pcr", "nmr", "gc", "lc", "rna", "dna"}

    hw_kw_clean = {kw for kw in hw_kw_clean if not is_too_broad(kw)}
    sw_kw_clean = {kw for kw in sw_kw_clean if not is_too_broad(kw)}
    ni_kw_clean = {kw for kw in ni_kw_clean if not is_too_broad(kw)}

    print(f"[v3] Keyword cleanup:")
    print(f"     Instrument: {len(hw_kw)} -> {len(hw_kw_clean)} (removed {len(hw_kw) - len(hw_kw_clean)})")
    print(f"     Software: {len(sw_kw)} -> {len(sw_kw_clean)} (removed {len(sw_kw) - len(sw_kw_clean)})")
    print(f"     Non-Instrument: {len(ni_kw)} -> {len(ni_kw_clean)} (removed {len(ni_kw) - len(ni_kw_clean)})")
    print(f"     Removed conflicts: HW+SW={len(hw_sw)}, HW+NI={len(hw_ni)}, SW+NI={len(sw_ni)}, all={len(all_three)}")

    return hw_kw_clean, sw_kw_clean, ni_kw_clean


def classify_item(req_line: str, item_desc: str, hw_kw: set, sw_kw: set, ni_kw: set) -> str:
    """
    Classify with priorities:
    - Instrument: 2+ matches (high bar: it's the hardest to get right)
    - Software: 1+ matches (rarer, so lower bar)
    - Non-Instrument: 1+ matches (catch-all, lowest bar)
    - Instrument > Software > Non-Instrument (priority order for ties)
    """
    text = (str(req_line) + " " + str(item_desc)).lower()

    hw_score = sum(1 for kw in hw_kw if kw in text)
    sw_score = sum(1 for kw in sw_kw if kw in text)
    ni_score = sum(1 for kw in ni_kw if kw in text)

    # Priority order: Instrument > Software > Non-Instrument
    if hw_score >= 2:
        return "Instrument"
    elif sw_score >= 1 and sw_score > ni_score:
        return "Software"
    elif ni_score >= 1 and ni_score > sw_score:
        return "Non-Instrument"
    elif hw_score == 1:
        return "Instrument"
    else:
        return "Unknown"


def filter_and_classify(input_file: str, output_dir: str = None, hw_kw: set = None,
                       sw_kw: set = None, ni_kw: set = None) -> dict:
    """
    Read Excel, filter columns, classify with improved logic, output formatted Excel.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_path = Path(output_dir or "C:\\Data\\Crawler\\labeled")
    output_path.mkdir(parents=True, exist_ok=True)

    # Load keyword sets once
    if hw_kw is None:
        hw_kw, sw_kw, ni_kw = load_and_clean_keywords()

    # Load file
    file_ext = input_path.suffix.lower()
    if file_ext == ".csv":
        df = pd.read_csv(input_file)
    else:
        df = pd.read_excel(input_file)

    print(f"[v3] Loaded {len(df)} rows from {input_path.name}")

    # Map columns by position
    col_indices = [1, 5, 6, 8, 14]  # B, F, G, I, O
    col_names = ["Req ID", "Supplier ID", "Supplier Name", "Item Description", "Req Line Item"]

    if len(df.columns) >= max(col_indices) + 1:
        df_filtered = df.iloc[:, col_indices].copy()
        df_filtered.columns = col_names
    else:
        available_cols = list(df.columns)
        print(f"[v3] Available columns: {available_cols}")
        col_mapping = {}
        for target, col_pos in zip(col_names, [1, 5, 6, 8, 14]):
            if target in df.columns:
                col_mapping[target] = target
            elif col_pos < len(df.columns):
                col_mapping[target] = df.columns[col_pos]
            else:
                raise ValueError(f"Cannot find column for {target}")
        df_filtered = df[[col_mapping[name] for name in col_names]]
        df_filtered.columns = col_names

    print(f"[v3] Filtered to 5 columns: {', '.join(col_names)}")

    # Classify each row
    classifications = []
    for idx, row in df_filtered.iterrows():
        req_line = str(row.get("Req Line Item", ""))
        item_desc = str(row.get("Item Description", ""))
        classification = classify_item(req_line, item_desc, hw_kw, sw_kw, ni_kw)
        classifications.append(classification)

    df_filtered["Type"] = classifications

    # Count types
    type_counts = df_filtered["Type"].value_counts().to_dict()
    print(f"[v3] Results: {type_counts}")

    # Save to output
    output_file = output_path / (input_path.stem + "_classified_v3.xlsx")
    df_filtered.to_excel(output_file, index=False)
    print(f"[v3] Saved to {output_file}")

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
    print(f"[v3] Found {len(files)} files")

    # Load keywords once
    hw_kw, sw_kw, ni_kw = load_and_clean_keywords()

    results = []
    for file in files:
        try:
            result = filter_and_classify(str(file), str(output_path), hw_kw, sw_kw, ni_kw)
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {file.name}: {e}")
            results.append({"file": str(file), "status": "error", "error": str(e)})

    return {"files_processed": len(files), "results": results}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filter_and_classify(sys.argv[1])
    else:
        process_all_inputs()
