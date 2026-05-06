"""
Shared utilities for the Cross-reference module.
Centralises column detection and filename normalisation that were previously
duplicated across instrument_labeler_cli.py, instrument_labeling_manager.py,
and crossref_standalone_fast.py.
"""

import re
import os

# ---------------------------------------------------------------------------
# Pre-compiled regex for filename normalisation (used by normalize_filename)
# ---------------------------------------------------------------------------
_RE_PAREN_NUM   = re.compile(r'[_\-\s]*\([0-9]+\)')
_RE_VERSION     = re.compile(r'[_\-\s]*v[0-9]+')
_RE_YEAR        = re.compile(r'[_\-\s]*20[0-9]{2}')
_RE_SUFFIX      = re.compile(r'[_\-\s]*(updated|final|revised|new|latest)$')
_RE_SEPARATORS  = re.compile(r'[_\-\s]+')


def normalize_filename(filename):
    """
    Normalise a PDF filename for deduplication by stripping version numbers,
    year patterns, and common suffixes.
    """
    if not filename:
        return ""
    base = os.path.splitext(filename.lower())[0]
    base = _RE_PAREN_NUM.sub('', base)
    base = _RE_VERSION.sub('', base)
    base = _RE_YEAR.sub('', base)
    base = _RE_SUFFIX.sub('', base)
    base = _RE_SEPARATORS.sub('_', base)
    return base.strip('_-. ')


def deduplicate_matches(matches):
    """
    Remove duplicate PDF matches by normalised filename, keeping the
    highest-scoring entry from each group.
    """
    if not matches:
        return matches

    groups = {}
    for match in matches:
        key = normalize_filename(os.path.basename(match['pdf_path']))
        groups.setdefault(key, []).append(match)

    result = []
    for key, group in groups.items():
        best = max(group, key=lambda m: m['score'])
        if len(group) > 1:
            print(f"    [dedup] {len(group)} copies of '{key}' -> kept best (score: {best['score']:.1f}%)")
        result.append(best)
    return result


# ---------------------------------------------------------------------------
# Shared column detection (identical logic duplicated in CLI and GUI tools)
# ---------------------------------------------------------------------------

# Ordered candidate names for each logical column
_TYPE_CANDIDATES        = ('TYPE', 'Type', 'Item Type', 'Product Type')
_CODE_CANDIDATES        = ('Item Code', 'ItemCode', 'Code', 'ID', 'Item ID', 'Item_ID')
_DESCRIPTION_CANDIDATES = ('Item Description', 'Description', 'ItemDescription',
                            'Name', 'Title', 'Product Name')
_SUPPLIER_CANDIDATES    = ('Supplier Name', 'Supplier', 'Vendor', 'Company')


def _first_match(columns, candidates):
    """Return the first candidate that appears in columns, or None."""
    col_set = set(columns)
    for c in candidates:
        if c in col_set:
            return c
    return None


def find_required_columns(df):
    """
    Detect the logical columns needed for instrument labelling.

    Returns a dict:
        {
            'type_col':     str | None,
            'code_col':     str | None,
            'desc_col':     str | None,
            'supplier_col': str | None,
        }
    """
    columns = df.columns.tolist()
    return {
        'type_col':     _first_match(columns, _TYPE_CANDIDATES),
        'code_col':     _first_match(columns, _CODE_CANDIDATES),
        'desc_col':     _first_match(columns, _DESCRIPTION_CANDIDATES),
        'supplier_col': _first_match(columns, _SUPPLIER_CANDIDATES),
    }
