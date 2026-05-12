"""
Data Cleaner — Autonomous Data Quality Module
Cleans supplier names and related fields before classification/resolution.

Handles:
- Data merge artifacts (***USE V#*** patterns)
- Whitespace normalization
- Special character cleanup
- Duplicate detection
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple


# Pattern definitions for cleanup
CLEANUP_PATTERNS = {
    "use_code_suffix": r"\*\*\*USE V#\d+\*\*\*",  # ***USE V#79***
    "use_code_parens": r"\(USE[^)]*\)",            # (USE CODE 123)
    "trailing_asterisks": r"\*+$",                 # trailing asterisks
    "leading_asterisks": r"^\*+",                  # leading asterisks
    "multiple_spaces": r"\s+",                     # multiple spaces -> single
}

# Supplier name normalization rules
SUPPLIER_SUFFIXES_TO_REMOVE = [
    " - USA", " USA", " NORTH AMERICA", " NA",
    " DIVISION", " SUBSIDIARY", " AFFILIATE",
    " CORP", " CORPORATION", " INC", " LLC", " LTD", " CO",
    " SALES", " SERVICES", " SOLUTIONS",
]


def detect_corrupted_names(df: pd.DataFrame, supplier_col: str = "Supplier Name") -> pd.DataFrame:
    """
    Detect corrupted supplier names with known patterns.
    Returns DataFrame with detected issues.
    """
    # Validate column exists
    if supplier_col not in df.columns:
        raise ValueError(f"Column '{supplier_col}' not found. Available: {list(df.columns)}")

    issues = []

    for idx, name in df[supplier_col].items():
        if pd.isna(name):
            continue

        name_str = str(name).strip()
        issue = {"index": idx, "original": name_str, "issues": []}

        # Check each pattern
        if re.search(CLEANUP_PATTERNS["use_code_suffix"], name_str, re.IGNORECASE):
            issue["issues"].append("use_code_suffix")
        if re.search(CLEANUP_PATTERNS["use_code_parens"], name_str, re.IGNORECASE):
            issue["issues"].append("use_code_parens")
        if re.search(CLEANUP_PATTERNS["leading_asterisks"], name_str):
            issue["issues"].append("leading_asterisks")
        if re.search(CLEANUP_PATTERNS["trailing_asterisks"], name_str):
            issue["issues"].append("trailing_asterisks")

        if issue["issues"]:
            issues.append(issue)

    return pd.DataFrame(issues) if issues else pd.DataFrame()


def clean_supplier_name(name: str) -> str:
    """
    Clean a single supplier name by removing data artifacts and normalizing whitespace.
    """
    if pd.isna(name):
        return name

    # Start with the input converted to string and stripped
    cleaned = str(name).strip()

    # If empty after stripping, return empty
    if not cleaned:
        return ""

    # Remove ***USE V#*** merge artifacts
    cleaned = re.sub(CLEANUP_PATTERNS["use_code_suffix"], "", cleaned, flags=re.IGNORECASE)

    # Remove (USE ...) patterns
    cleaned = re.sub(CLEANUP_PATTERNS["use_code_parens"], "", cleaned, flags=re.IGNORECASE)

    # Remove leading asterisks
    cleaned = re.sub(CLEANUP_PATTERNS["leading_asterisks"], "", cleaned)

    # Remove trailing asterisks
    cleaned = re.sub(CLEANUP_PATTERNS["trailing_asterisks"], "", cleaned)

    # Normalize whitespace to single spaces and trim
    cleaned = re.sub(CLEANUP_PATTERNS["multiple_spaces"], " ", cleaned)
    cleaned = cleaned.strip()

    return cleaned


def clean_excel_file(excel_path: str, output_path: str = None,
                     supplier_col: str = "Supplier Name",
                     dry_run: bool = False) -> Dict:
    """
    Clean an Excel file in place or to a new location.

    Args:
        excel_path: Path to Excel file to clean
        output_path: Where to save cleaned file (if None, overwrites input)
        supplier_col: Name of the supplier name column
        dry_run: If True, don't write changes, just report what would happen

    Returns:
        Dict with cleaning statistics
    """
    # Load Excel
    if not Path(excel_path).exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path)
    print(f"[data_cleaner] Loaded: {excel_path} ({len(df)} rows)")

    # Check if supplier column exists
    if supplier_col not in df.columns:
        raise ValueError(f"Column '{supplier_col}' not found. Available: {list(df.columns)}")

    # Detect issues
    issues = detect_corrupted_names(df, supplier_col)
    print(f"[data_cleaner] Found {len(issues)} rows with data quality issues")

    if len(issues) > 0:
        print("[data_cleaner] Issues detected:")
        for _, row in issues.iterrows():
            print(f"  Row {row['index']}: {row['original']}")
            print(f"    Issues: {', '.join(row['issues'])}")

    # Clean supplier names
    cleaned_count = 0
    before_values = []
    after_values = []

    for idx in df.index:
        original = df.loc[idx, supplier_col]
        cleaned = clean_supplier_name(original)

        if str(original).strip() != str(cleaned).strip():
            before_values.append((idx, original, cleaned))
            df.loc[idx, supplier_col] = cleaned
            cleaned_count += 1

    # Report changes
    print(f"\n[data_cleaner] Cleaned {cleaned_count} supplier names:")
    for idx, before, after in before_values:
        print(f"  {before} → {after}")

    # Save if not dry-run
    if dry_run:
        print(f"\n[data_cleaner] DRY RUN — no changes written")
        return {
            "input_file": excel_path,
            "rows_total": len(df),
            "rows_cleaned": cleaned_count,
            "dry_run": True,
            "status": "dry_run_complete"
        }
    else:
        save_path = output_path or excel_path
        df.to_excel(save_path, index=False)
        print(f"\n[data_cleaner] Saved cleaned file: {save_path}")
        return {
            "input_file": excel_path,
            "output_file": save_path,
            "rows_total": len(df),
            "rows_cleaned": cleaned_count,
            "dry_run": False,
            "status": "success"
        }


def clean_all_input_excels(input_dir: str, dry_run: bool = False) -> Dict:
    """
    Clean all Excel files in the input directory.

    Args:
        input_dir: Directory containing Excel files to clean
        dry_run: If True, don't write changes

    Returns:
        Summary statistics
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    excel_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls"))
    print(f"[data_cleaner] Found {len(excel_files)} Excel files in {input_dir}")

    results = []
    total_cleaned = 0
    total_rows = 0

    for excel_file in excel_files:
        print(f"\n[data_cleaner] Processing: {excel_file.name}")
        try:
            result = clean_excel_file(str(excel_file), dry_run=dry_run)
            results.append(result)
            total_cleaned += result["rows_cleaned"]
            total_rows += result["rows_total"]
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "input_file": str(excel_file),
                "status": "error",
                "error": str(e)
            })

    return {
        "input_directory": input_dir,
        "files_processed": len(excel_files),
        "total_rows": total_rows,
        "total_rows_cleaned": total_cleaned,
        "results": results,
        "dry_run": dry_run
    }


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python data_cleaner.py <input_file_or_dir> [--dry-run]")
        sys.exit(1)

    path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    # Check if it's a file or directory
    if Path(path).is_file():
        result = clean_excel_file(path, dry_run=dry_run)
        print(f"\nResult: {result['status']}")
    elif Path(path).is_dir():
        result = clean_all_input_excels(path, dry_run=dry_run)
        print(f"\nSummary:")
        print(f"  Files processed: {result['files_processed']}")
        print(f"  Total rows: {result['total_rows']}")
        print(f"  Rows cleaned: {result['total_rows_cleaned']}")
    else:
        print(f"Path not found: {path}")
        sys.exit(1)
