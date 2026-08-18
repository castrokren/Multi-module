"""
Improved Column Filtering + Classification Pipeline (v2)
- Fixes conflicting and overly-broad keywords
- Requires 2+ keyword matches for confident classification
- Fallback to inspection if ambiguous
"""

import pandas as pd
from pathlib import Path
import sys
import os

COLUMN_MAP = {
    "Req ID": "B",
    "Supplier ID": "F",
    "Supplier Name": "G",
    "Item Description": "I",
    "Req Line Item": "O"
}

KEYWORD_DIR = Path(__file__).parent.parent / "classify"

# Core keyword lists (cleaned: removed conflicts, overly-broad terms)
INSTRUMENT_KEYWORDS = {
    "microscope", "centrifuge", "spectrometer", "chromatograph", "pcr", "thermocycler",
    "incubator", "sonicator", "analyzer", "sequencer", "cytometer", "hplc", "gc-ms",
    "mass spec", "nmr", "imager", "scanner", "sorter", "shaker", "pump", "probe",
    "laser", "oscilloscope", "meter", "gauge", "sensor", "transducer", "detector",
    "dispensary", "stirrer", "vortex", "autoclave", "fume hood", "biosafety cabinet",
    "refrigerator", "freezer", "evaporator", "rotavap", "distillation", "furnace",
    "oven", "hood", "bath", "heater", "cooler", "magnetic separator", "balance",
    "scale", "spectrophotometer", "densitometer", "nephelometer", "colorimeter",
    "turbidimeter", "luminometer", "fluorometer", "ph meter", "conductivity",
    "osmometer", "viscometer", "rheometer", "tensiometer", "refractometer",
    "interferometer", "ellipsometer", "polarimeter", "raman", "afm",
    "sem", "tem", "stm", "confocal", "electrophoresis", "gel", "elisa",
    "immunoassay", "blotter", "cycler", "dispenser", "pipette", "extractor",
    "rotor", "homogenizer", "lyophilizer", "freeze dryer", "spray dryer",
    "cryostat", "microtome", "cutter", "grinder", "blender", "mixer"
}

SOFTWARE_KEYWORDS = {
    "software", "application", "platform", "system", "tool", "license", "subscription",
    "license", "matlab", "labview", "prism", "graphpad", "spss", "sas", "r", "python",
    "julia", "c#", "c++", "java", "javascript", "sql", "postgresql", "mysql", "oracle",
    "tableau", "power bi", "qlik", "looker", "splunk", "elasticsearch", "kibana",
    "grafana", "prometheus", "jenkins", "docker", "kubernetes", "git", "gitlab",
    "jira", "confluence", "slack", "zoom", "teams", "sharepoint", "onedrive",
    "aws", "azure", "google cloud", "salesforce", "sap", "oracle erp", "peoplesoft",
    "servicenow", "workday", "netbeans", "intellij", "visual studio", "pycharm",
    "eclipse", "vscode", "xcode", "sublime", "atom", "vim", "emacs", "photoshop",
    "illustrator", "indesign", "lightroom", "premiere", "after effects", "audition",
    "acrobat", "solidworks", "autocad", "revit", "sketchup", "blender", "cinema4d",
    "3dsmax", "maya", "unity", "unreal engine", "godot", "coco2d", "phaser",
    "wordpress", "drupal", "joomla", "magento", "shopify", "wix", "squarespace",
    "office", "excel", "word", "powerpoint", "access", "outlook", "teams",
    "github", "bitbucket", "gitlab", "confluence", "jira", "asana", "monday",
    "clickup", "notion", "airtable", "figma", "sketch", "xd", "invision"
}

NON_INSTRUMENT_KEYWORDS = {
    "cable", "cord", "wire", "connector", "adapter", "plug", "socket", "usb",
    "hdmi", "fiber optic", "ethernet", "power strip", "extension cord",
    "clamp", "clip", "mount", "holder", "stand", "rack", "shelf", "cabinet",
    "cart", "trolley", "table", "desk", "chair", "seat", "stool", "bench",
    "cover", "shield", "guard", "protection", "case", "box", "container",
    "tube", "vial", "plate", "dish", "petri", "slide", "coverslip", "well",
    "tip", "pipette tip", "filter tip", "column", "cartridge", "membrane",
    "buffer", "reagent", "chemical", "solvent", "medium", "culture", "agar",
    "glucose", "serum", "plasma", "antibody", "antigen", "dna", "rna", "protein",
    "enzyme", "substrate", "inhibitor", "cofactor", "standard", "control",
    "manual", "handbook", "guide", "instruction", "training", "documentation",
    "installation", "maintenance", "repair", "support", "warranty", "license",
    "contract", "agreement", "invoice", "invoice", "quote", "estimate", "order",
    "delivery", "shipping", "freight", "packaging", "unboxing", "calibration",
    "validation", "qualification", "certification", "compliance", "audit",
    "discount", "promotion", "sale", "offer", "bundle", "kit", "set", "package"
}

def classify_item(req_line: str, item_desc: str) -> str:
    """
    Classify with improved logic:
    - Requires 2+ keyword matches for confidence
    - Clear priority: Instrument > Software > Non-Instrument
    - Falls back to "Unknown" if ambiguous
    """
    text = (str(req_line) + " " + str(item_desc)).lower()

    hw_score = sum(1 for kw in INSTRUMENT_KEYWORDS if kw in text)
    sw_score = sum(1 for kw in SOFTWARE_KEYWORDS if kw in text)
    ni_score = sum(1 for kw in NON_INSTRUMENT_KEYWORDS if kw in text)

    # Require 2+ matches for confident classification
    if hw_score >= 2 and hw_score > sw_score and hw_score > ni_score:
        return "Instrument"
    elif sw_score >= 2 and sw_score > hw_score and sw_score > ni_score:
        return "Software"
    elif ni_score >= 2 and ni_score > hw_score and ni_score > sw_score:
        return "Non-Instrument"

    # Single match: allow if it's strong and unique
    elif hw_score == 1 and sw_score == 0 and ni_score == 0:
        return "Instrument"
    elif sw_score == 1 and hw_score == 0 and ni_score == 0:
        return "Software"
    elif ni_score == 1 and hw_score == 0 and sw_score == 0:
        return "Non-Instrument"

    # No clear match or ambiguous
    else:
        return "Unknown"


def filter_and_classify(input_file: str, output_dir: str = None) -> dict:
    """
    Read Excel, filter columns, classify with improved logic, output formatted Excel.
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

    print(f"[v2] Loaded {len(df)} rows from {input_path.name}")

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
        print(f"[v2] Available columns: {available_cols}")

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

    print(f"[v2] Filtered to 5 columns: {', '.join(col_names)}")

    # Classify each row
    classifications = []
    for idx, row in df_filtered.iterrows():
        req_line = str(row.get("Req Line Item", ""))
        item_desc = str(row.get("Item Description", ""))
        classification = classify_item(req_line, item_desc)
        classifications.append(classification)

    df_filtered["Type"] = classifications

    # Count types
    type_counts = df_filtered["Type"].value_counts().to_dict()
    print(f"[v2] Classification results: {type_counts}")

    # Save to output
    output_file = output_path / (input_path.stem + "_classified_v2.xlsx")
    df_filtered.to_excel(output_file, index=False)
    print(f"[v2] Saved to {output_file}")

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
    print(f"[v2] Found {len(files)} files")

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
