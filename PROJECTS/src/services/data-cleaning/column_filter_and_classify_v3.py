"""
Hybrid Column Filtering + Classification (v3)
- Uses original keyword files but REMOVES conflicting entries
- Requires 2+ matches for Instrument (original was too loose)
- Allows 1+ match for Software/Non-Instrument (rarer categories)
- Clear priority order: Instrument > Software > Non-Instrument
"""

import pandas as pd
from pathlib import Path
import re
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


# Junk that learning_mode auto-promoted into the keyword files: word
# fragments ("multi" from MULTICLAMP, "contro" from "controlled", "ella" from
# "cancellation", "lysis" from "analysis") and generic English that names no
# product. Word-boundary matching kills the fragments; these are the ones that
# survive as whole words and still mean nothing.
# ponytail: blacklist here rather than editing the .txt files, so a future
# learning run cannot silently reintroduce them.
_JUNK_KEYWORDS = frozenset({
    # word fragments
    'multi', 'contro', 'ella', 'lysis', 'diss', 'moto', 'tera', 'diret',
    'kinas', 'aeulos', 'semg', 'nomoto',
    # generic English that names no product
    'bill', 'sale', 'other', 'real', 'load', 'port', 'cold', 'heat',
    'gene', 'pure', 'disk', 'quad', 'pico', 'trio', 'bath', 'shear',
    'buyout', 'payoff', 'total', 'known', 'whole', 'expert', 'alias',
    'legend', 'studio', 'trace', 'stress', 'pulse', 'ignite', 'encore',
    'fluent', 'atlas', 'orbit', 'nexus', 'prior', 'rebel', 'quant',
    'sonic', 'mantis', 'visor', 'flint', 'mateo', 'novac', 'miao',
    # materials and packaging, not instruments
    'glass', 'copper', 'vinyl', 'hinged', 'carboy', 'packs', 'cells',
    'scales', 'micron', 'imaging', 'optics', 'lasers', 'biosafety',
    # vendor / brand names, not products
    'fisher', 'cytiva', 'valco', 'jena', 'acuson', 'advia', 'aeolus',
    "labrepco's",
})

# Rig components and modules: parts OF an instrument, not an instrument.
# A MultiClamp amplifier or an RHD recording controller is a component of an
# electrophysiology rig - the rig is the instrument, these are not. Moved from
# the Instrument list to Non-Instrument so they classify as what they are.
_COMPONENT_KEYWORDS = frozenset({
    'controller', 'amplifier', 'microelectrode', 'headstage', 'motor',
    'pulser', 'slider', 'knobs', 'load cell', 'thermistor', 'thermocouple',
    'rotor', 'centrifuge rotor', 'w/rotor', 'strain gauge', 'accelerometer',
    'transilluminator', 'galvanometer',
})


# Part numbers and quote fragments that learning_mode harvested from past
# requisitions ("a28568", "quote#", "2x/4x/10x", "sz51;microscope"). They name
# one purchase, not a product category, and they make classification
# self-fulfilling: the item that created the keyword is the item it matches.
# Real terms with punctuation (gc-ms, icp-ms, -80, co2) are kept.
_PART_NUMBER_RE = re.compile(r"[#@;/'\"()À-￿]|^\d+\.\d+$")


# Software junk: IT/DevOps vocabulary, stopwords, fragments, and non-scientific brands.
# Phase 2 cleanup per plan + Kren's domain judgment from REVIEW-keywords.md.
_JUNK_SW = frozenset({
    # IT_JARGON (plan S1) - enterprise/devops, explicit plan list
    "docker", "kubernetes", "saas", "paas", "iaas", "gdpr", "hipaa", "itil",
    "cobit", "mtbf", "mttr", "azure", "slack", "teams", "webex", "skype",
    "redis", "mysql", "json", "yaml", "toml", "soap", "unix", "linux", "macos",
    "agile", "scrum", "jira", "jenkins", "github", "devops", "ci/cd",
    "bitbucket", "monitoring", "logging", "prometheus", "grafana", "elasticsearch",
    "splunk", "vmware",
    # STOPWORDS (plan S2) - generic English noise
    "above", "below", "list", "price",
    # FRAGMENTS (plan S2) - confirmed non-words
    "coded", "cond", "agile", "scrum", "jira", "docker", "azure",
    # Non-scientific brands / tools (Kren review S3)
    "adobe", "autocad", "prism", "visio", "revit", "salesforce", "intel",
    # Junk fragments from learning_mode
    "gmpe", "pmml",
})


# Non-Instrument junk: stopwords, fragments, and vendor names that inflate ni_score.
# Phase 3 cleanup per plan N1-N2 + Kren's domain judgment from REVIEW-keywords.md.
_JUNK_NI = frozenset({
    # STOPWORDS (plan N1) - generic English that matches half of all text
    "been", "have", "only", "once", "your", "will", "need", "next", "over",
    "four", "eight", "three", "kind", "great", "ideal", "comes", "away",
    "less", "more", "down", "back", "left", "front", "side",
    # FRAGMENTS (plan N2) - confirmed non-words
    "assy", "secu", "repl", "obser", "insta", "prev", "clin", "univ", "vert",
    "appl", "wqith",  # sic - typo in data
    # Vendor names (Kren review N3)
    "zebra", "nomad", "joel", "jess", "york", "rice",
})


def _is_scraped_part_number(kw: str) -> bool:
    """True for one-off part numbers / quote fragments, not product terms."""
    if _PART_NUMBER_RE.search(kw):
        return True
    # Alphanumeric soup like "bx43fw", "l23119", "x50i", "cm1950", "m3000":
    # has digits, is not a known chemistry/temperature term, and is not a
    # multi-word phrase.
    if any(c.isdigit() for c in kw) and " " not in kw:
        return kw not in {"co2", "pcr", "qpcr", "rtpcr", "gc-ms", "lc-ms",
                          "icp-ms", "icp-aes", "-20", "-70", "-80",
                          "real-time pcr", "spo2", "tcpco2", "pe-400"}
    return False


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
        return (len(kw) < 4 and kw.isalpha() and kw not in {"pcr", "nmr", "gc", "lc", "rna", "dna"}) \
            or kw in _JUNK_KEYWORDS \
            or _is_scraped_part_number(kw)

    def is_junk_sw(kw):
        return kw in _JUNK_SW

    def is_junk_ni(kw):
        return kw in _JUNK_NI

    hw_kw_clean = {kw for kw in hw_kw_clean if not is_too_broad(kw)}
    sw_kw_clean = {kw for kw in sw_kw_clean if not (is_too_broad(kw) or is_junk_sw(kw))}
    ni_kw_clean = {kw for kw in ni_kw_clean if not (is_too_broad(kw) or is_junk_ni(kw))}

    # Rig components are Non-Instrument, not Instrument.
    hw_kw_clean -= _COMPONENT_KEYWORDS
    ni_kw_clean |= _COMPONENT_KEYWORDS

    print(f"[v3] Keyword cleanup:")
    print(f"     Instrument: {len(hw_kw)} -> {len(hw_kw_clean)} (removed {len(hw_kw) - len(hw_kw_clean)})")
    print(f"     Software: {len(sw_kw)} -> {len(sw_kw_clean)} (removed {len(sw_kw) - len(sw_kw_clean)})")
    print(f"     Non-Instrument: {len(ni_kw)} -> {len(ni_kw_clean)} (removed {len(ni_kw) - len(ni_kw_clean)})")
    print(f"     Removed conflicts: HW+SW={len(hw_sw)}, HW+NI={len(hw_ni)}, SW+NI={len(sw_ni)}, all={len(all_three)}")

    return hw_kw_clean, sw_kw_clean, ni_kw_clean


# Instrument terms too vague to stand alone - they need a second hit to count.
# "Analyzer slider" and "balance due" are not instruments; "TOC analyzer" and
# "analytical balance" are, and those match as multi-word keywords anyway.
_WEAK_HW = frozenset({
    'meter', 'analyzer', 'balance', 'rotary', 'distillation', 'calorimetry',
    'co2', 'gc', 'lc', 'electrophoresis', 'furnace', 'glove box',
})


def _count_hits(keywords: set, text: str, words: set) -> int:
    """Count keyword hits, matching whole words - not substrings.

    Bare `kw in text` scored "lysis" against "anaLYSIS", "ella" against
    "cancELLAtion" and "contro" against "CONTROlled", which is what made the
    same product classify differently on different rows. Multi-word keywords
    ("plate reader") still need a substring test, but a single token must
    match a whole word.
    """
    hits = 0
    for kw in keywords:
        if " " in kw:
            if kw in text:
                hits += 1
        elif kw in words:
            hits += 1
    return hits


def classify_item(req_line: str, item_desc: str, hw_kw: set, sw_kw: set, ni_kw: set) -> str:
    """
    Classify with priorities:
    - Instrument: ONE unambiguous term ("centrifuge", "microscope") is enough;
      ambiguous ones (_WEAK_HW: "meter", "analyzer") need a second hit, so
      "Analyzer slider" stays out while "Eppendorf centrifuge 5810R" gets in
    - Software: 1+ matches (rarer, so lower bar)
    - Non-Instrument: 1+ matches (catch-all, lowest bar)
    - Instrument > Software > Non-Instrument (priority order for ties)
    """
    text = (str(req_line) + " " + str(item_desc)).lower()
    words = set(re.findall(r"[a-z0-9][a-z0-9\-/.]*", text))

    hw_score = _count_hits(hw_kw, text, words)
    strong_hw = _count_hits(hw_kw - _WEAK_HW, text, words)
    sw_score = _count_hits(sw_kw, text, words)
    ni_score = _count_hits(ni_kw, text, words)

    # Priority order: Instrument > Software > Non-Instrument
    if strong_hw >= 1 or hw_score >= 2:
        return "Instrument"
    elif sw_score >= 1 and sw_score > ni_score:
        return "Software"
    elif ni_score >= 1 and ni_score > sw_score:
        return "Non-Instrument"
    else:
        return "Unknown"


# Rider lines that follow an instrument in the same quote: freight, cords,
# warranties, services. Rules A and B must not promote these to Instrument.
# Word-boundary match: bare "tax"/"fee" substrings would hit Pentax,
# Stereotaxic, and feedback - all real instruments in this data.
_RIDER_RE = re.compile(
    r"\b(?:shipping|handling|freight|delivery|cords?|warr\w*|install\w*"
    r"|training|trade[- ]in|svc|services?|support|fees?|tax|surcharge"
    r"|discount|removal)\b",
    re.IGNORECASE,
)

# Rule B promotes on supplier identity alone, so demand a second signal:
# the line must cost like an instrument. Rows with no/zero price stay Unknown.
# ponytail: single global threshold; per-category thresholds if ever needed.
_RULE_B_MIN_PRICE = 1000


def _is_rider(item_desc: str) -> bool:
    """True if this line is a freight/service/accessory rider, not a product."""
    return bool(_RIDER_RE.search(str(item_desc)))


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
    col_indices = [1, 5, 6, 8, 10, 14]  # B, F, G, I, K, O
    col_names = ["Req ID", "Supplier ID", "Supplier Name", "Item Description",
                 "Unit Price", "Req Line Item"]

    if len(df.columns) >= max(col_indices) + 1:
        df_filtered = df.iloc[:, col_indices].copy()
        df_filtered.columns = col_names
    else:
        available_cols = list(df.columns)
        print(f"[v3] Available columns: {available_cols}")
        col_mapping = {}
        for target, col_pos in zip(col_names, col_indices):
            if target in df.columns:
                col_mapping[target] = target
            elif col_pos < len(df.columns):
                col_mapping[target] = df.columns[col_pos]
            else:
                raise ValueError(f"Cannot find column for {target}")
        df_filtered = df[[col_mapping[name] for name in col_names]]
        df_filtered.columns = col_names

    print(f"[v3] Filtered to {len(col_names)} columns: {', '.join(col_names)}")

    # Classify each row
    classifications = []
    for idx, row in df_filtered.iterrows():
        req_line = str(row.get("Req Line Item", ""))
        item_desc = str(row.get("Item Description", ""))
        classification = classify_item(req_line, item_desc, hw_kw, sw_kw, ni_kw)
        classifications.append(classification)

    df_filtered["Type"] = classifications

    # PHASE 2B: Rule A - Prior Context
    # If prior item in same quote (Req ID) is Instrument + current is Unknown -> reclassify as Instrument
    rule_a_count = 0
    df_filtered = df_filtered.reset_index(drop=True)
    for req_id in df_filtered["Req ID"].unique():
        group_indices = df_filtered[df_filtered["Req ID"] == req_id].index.tolist()
        for i in range(1, len(group_indices)):
            curr_idx = group_indices[i]
            prev_idx = group_indices[i-1]
            if (df_filtered.at[curr_idx, "Type"] == "Unknown"
                    and df_filtered.at[prev_idx, "Type"] == "Instrument"
                    and not _is_rider(df_filtered.at[curr_idx, "Item Description"])):
                df_filtered.at[curr_idx, "Type"] = "Instrument"
                rule_a_count += 1

    # PHASE 2B: Rule C - Bundle Analysis
    # For Unknown items: extract first/dominant item from bundled descriptions
    # ponytail: simple heuristic-split on common delimiters, take first meaningful segment
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
    # For Unknown items: if supplier is classified as equipment distributor -> reclassify as Instrument
    rule_b_count = 0
    if supplier_db:
        prices = pd.to_numeric(df_filtered["Unit Price"], errors="coerce")
        for idx in df_filtered[df_filtered["Type"] == "Unknown"].index:
            supplier = df_filtered.at[idx, "Supplier Name"]
            supplier_type = supplier_db.get(supplier, "unknown")
            # Reclassify Unknown from equipment suppliers to Instrument -
            # but only if it also costs like an instrument (NaN/0 fails).
            if (supplier_type in ["lab_equipment", "medical_equipment", "research_equipment"]
                    and not _is_rider(df_filtered.at[idx, "Item Description"])
                    and prices.at[idx] >= _RULE_B_MIN_PRICE):
                df_filtered.at[idx, "Type"] = "Instrument"
                rule_b_count += 1

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
