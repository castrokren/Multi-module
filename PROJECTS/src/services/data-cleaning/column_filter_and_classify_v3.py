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
import json

COLUMN_MAP = {
    "Req ID": "B",
    "Supplier ID": "F",
    "Supplier Name": "G",
    "Item Description": "I",
    "Req Line Item": "O"
}

KEYWORD_DIR = Path(__file__).parent.parent / "classify"


def load_supplier_classification():
    """Load supplier classification database for Rule B (Metadata Context)."""
    # Try multiple paths: relative to script, or from project root
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "docs" / "references" / "supplier_classification.json",
        Path(__file__).parent.parent.parent / "docs" / "references" / "supplier_classification.json",
        Path("docs/references/supplier_classification.json"),
    ]

    for db_file in possible_paths:
        if db_file.exists():
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[v3] Warning: Error loading supplier DB from {db_file}: {e}")

    return {}


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
                       sw_kw: set = None, ni_kw: set = None, supplier_db: dict = None) -> dict:
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

    # Load supplier classification DB once
    if supplier_db is None:
        supplier_db = load_supplier_classification()

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

    # PHASE 2B: Rule A - Prior Context
    # If prior item in same quote (Req ID) is Instrument + current is Unknown → reclassify as Instrument
    rule_a_count = 0
    df_filtered = df_filtered.reset_index(drop=True)
    for req_id in df_filtered["Req ID"].unique():
        group_indices = df_filtered[df_filtered["Req ID"] == req_id].index.tolist()
        for i in range(1, len(group_indices)):
            curr_idx = group_indices[i]
            prev_idx = group_indices[i-1]
            if df_filtered.at[curr_idx, "Type"] == "Unknown" and df_filtered.at[prev_idx, "Type"] == "Instrument":
                df_filtered.at[curr_idx, "Type"] = "Instrument"
                rule_a_count += 1

    # PHASE 2B: Rule C - Bundle Analysis
    # For Unknown items: extract first/dominant item from bundled descriptions
    # ponytail: simple heuristic—split on common delimiters, take first meaningful segment
    rule_c_count = 0
    for idx in df_filtered[df_filtered["Type"] == "Unknown"].index:
        desc = str(df_filtered.at[idx, "Item Description"]).strip()
        # Try to extract first item (before semicolon, comma, or slash)
        for delim in [';', ',', '/']:
            if delim in desc:
                first_part = desc.split(delim)[0].strip()
                # Only reclassify if first part is substantively different and not product ID
                if len(first_part) > 5 and not first_part[0].isdigit():
                    # Re-classify the extracted segment
                    classification = classify_item("", first_part, hw_kw, sw_kw, ni_kw)
                    if classification != "Unknown":
                        df_filtered.at[idx, "Type"] = classification
                        rule_c_count += 1
                break

    # PHASE 3: Rule B - Metadata Context (Supplier Classification)
    # For Unknown items: if supplier is classified as equipment distributor → reclassify as Instrument
    rule_b_count = 0
    unknown_before_b = len(df_filtered[df_filtered["Type"] == "Unknown"])
    if supplier_db:
        for idx in df_filtered[df_filtered["Type"] == "Unknown"].index:
            supplier = df_filtered.at[idx, "Supplier Name"]
            supplier_type = supplier_db.get(supplier, "unknown")
            # Reclassify Unknown from equipment suppliers to Instrument
            if supplier_type in ["lab_equipment", "medical_equipment", "research_equipment"]:
                df_filtered.at[idx, "Type"] = "Instrument"
                rule_b_count += 1
    unknown_after_b = len(df_filtered[df_filtered["Type"] == "Unknown"])
    if rule_b_count == 0:
        print(f"[v3] Rule B: supplier_db has {len(supplier_db)} entries, {unknown_before_b} Unknown items")

    # Count types
    type_counts = df_filtered["Type"].value_counts().to_dict()
    print(f"[v3] Results: {type_counts}")
    print(f"[v3] Rule A (Prior Context): {rule_a_count} items reclassified")
    print(f"[v3] Rule B (Supplier Metadata): {rule_b_count} items reclassified")
    print(f"[v3] Rule C (Bundle Analysis): {rule_c_count} items reclassified")

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

    # Load keywords and supplier DB once
    hw_kw, sw_kw, ni_kw = load_and_clean_keywords()
    supplier_db = load_supplier_classification()

    results = []
    for file in files:
        try:
            result = filter_and_classify(str(file), str(output_path), hw_kw, sw_kw, ni_kw, supplier_db)
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
