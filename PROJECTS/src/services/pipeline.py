#!/usr/bin/env python3
"""
Pipeline Orchestrator
=====================
Runs the four modules in sequence:

    Stage 0 - Data Cleaning        : fix corrupted supplier names, normalize data
    Stage 1 - Classify             : classify Excel items (Instrument / Software / Non-Instrument)
    Stage 2 - Scraper              : crawl supplier websites, download PDFs
                                     (only for rows classified Instrument/Software)
    Stage 2b - Supplier Resolution : resolve unknown suppliers via web search
    Stage 3 - Cross-ref            : link classified records to downloaded PDFs

Classify runs BEFORE the scraper: the TYPE sorting gates which requisition
rows feed the crawler, so vendors that only sold furniture, services, or
consumables are never crawled at all.

Configuration is read from ``pipeline_config.json`` in the same directory.
Individual stages can be enabled / disabled in the ``pipeline`` section of
that file.

Usage
-----
    python pipeline.py                       # run all enabled stages
    python pipeline.py --config myconf.json  # alternate config file
    python pipeline.py --skip-scraper        # override: skip Stage 1
    python pipeline.py --only-crossref       # override: run Stage 3 only
    python pipeline.py --dry-run             # validate paths, do nothing else
"""

import argparse
import importlib.util
import json
import logging
import os
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup - one timestamped log file per run, plus the console
# ---------------------------------------------------------------------------

def _setup_logging(results_dir: str) -> None:
    # Fall back to a local folder if the configured results_dir can't be created
    # (e.g. the target drive doesn't exist on this machine yet).
    try:
        os.makedirs(results_dir, exist_ok=True)
    except OSError:
        results_dir = str(Path(__file__).resolve().parents[2] / "ops" / "monitoring" / "pipeline-logs")
        os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(results_dir, f"pipeline_{ts}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Pipeline log: %s", log_file)


logger = logging.getLogger("pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    return cfg


def _resolve_path(raw_path: str | None) -> str:
    """Resolve config paths against PROJECT_ROOT when they are relative."""
    if not raw_path:
        return ""
    p = Path(raw_path)
    if p.is_absolute():
        return str(p)
    return str((PROJECT_ROOT / p).resolve())


def _normalized_config(cfg: dict) -> dict:
    """Copy config and normalize all known path fields to absolute paths."""
    normalized = dict(cfg)
    paths = dict(cfg.get("paths", {}))
    for key in ("supplier_excel", "pdf_dir", "input_excel_dir", "labeled_dir",
                "master_excel", "master_list", "results_dir"):
        paths[key] = _resolve_path(paths.get(key, ""))
    normalized["paths"] = paths

    classify = dict(cfg.get("classify", {}))
    for key in ("hw_keywords_file", "sw_keywords_file", "ni_keywords_file"):
        classify[key] = _resolve_path(classify.get(key, ""))
    normalized["classify"] = classify
    return normalized


def _import_from_file(module_name: str, file_path: Path, symbol: str):
    """Import a symbol from a specific .py file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if not spec or not spec.loader:
        raise ImportError(f"Unable to load module spec from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return getattr(module, symbol)
    except AttributeError as exc:
        raise ImportError(f"Module {module_name} does not define {symbol}") from exc


# ---- Supplier keyword loading for scraper filtering ----
_STOP_WORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'as', 'is', 'was', 'are', 'been', 'be', 'has', 'had',
    'have', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
    'might', 'shall', 'can', 'not', 'no', 'nor', 'so', 'if', 'than', 'that',
    'this', 'these', 'those', 'it', 'its', 'per', 'each', 'all', 'both',
    'from', 'via', 'into', 'more', 'some', 'any', 'such', 'only', 'own',
    'same', 'too', 'very', 'just', 'about', 'above', 'after', 'down', 'up',
    'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'which', 'who', 'whom',
    'what', 'indicated', 'listed', 'following', 'pursuant', 'pursuantto',
    'quote', 'quotes', 'number', 'numbers', 'access', 'as', 'due', 'new',
    'please', 'see', 'attached', 'including', 'include', 'includes',
    'based', 'upon', 'per', 'your', 'our', 'their', 'his', 'her', 'its',
    'according', 'also', 'well', 'other', 'another', 'various',
})


def _extract_keyword_tokens(text: str) -> set[str]:
    """Extract meaningful keyword tokens from an item description.

    Removes stop words, short tokens (under 3 chars without digits),
    and normalizes hyphens.
    """
    import re
    # Remove special chars, keep letters, digits, spaces, hyphens
    cleaned = re.sub(r'[^\w\s\-]', ' ', text)
    tokens = cleaned.split()
    result = set()
    for token in tokens:
        token = token.strip('-').strip()
        if not token:
            continue
        token_lower = token.lower()
        if token_lower in _STOP_WORDS:
            continue
        if len(token_lower) < 3:
            continue
        # ponytail: bare numbers under 4 digits ("2", "10", "100") match every
        # PDF filename as substrings; real part numbers are 4+ chars
        if token_lower.isdigit() and len(token_lower) < 4:
            continue
        result.add(token_lower)
        # Also add hyphen-stripped variant (e.g., "920-2" -> "9202")
        if '-' in token:
            result.add(token.replace('-', '').lower())
    return result


# Words that name a *document*, not a product. They are the same vocabulary the
# scraper's _PDF_ALLOWLIST uses to recognise a product doc, so as keywords they
# match every product doc a vendor publishes.
_DOC_TYPE_WORDS = frozenset({
    'catalog', 'catalogue', 'datasheet', 'sheet', 'spec', 'specs',
    'specification', 'specifications', 'product', 'products', 'manual',
    'guide', 'brochure', 'flyer', 'bulletin', 'literature', 'technical',
    'install', 'installation', 'instruction', 'instructions', 'setup',
    'configuration', 'maintenance', 'protocol', 'overview', 'reference',
    'quickstart', 'pricelist', 'resource', 'resources', 'documentation',
})

# Category nouns: what a product *is*, not *which* product. "server" matches
# every spec sheet Broadax publishes. The cross-vendor count below only catches
# these when 2+ vendors share them, so the common ones are named outright.
_CATEGORY_NOUNS = frozenset({
    'server', 'servers', 'workstation', 'workstations', 'computer',
    'computers', 'laptop', 'desktop', 'system', 'systems', 'software',
    'hardware', 'equipment', 'instrument', 'instruments', 'device',
    'devices', 'unit', 'units', 'kit', 'kits', 'accessory', 'accessories',
    'module', 'modules', 'component', 'components', 'assembly', 'adapter',
    'cable', 'cables', 'controller', 'monitor', 'printer', 'machine',
    'machines', 'tool', 'tools', 'part', 'parts', 'item', 'items',
    'model', 'series', 'replacement', 'upgrade', 'standard', 'support',
    'service', 'services', 'solution', 'solutions', 'supplies', 'supply',
})

# A token shared by this many vendors or more is a category noun the list
# above missed. Raising this loosens the filter.
_MAX_VENDORS_PER_KEYWORD = 2


def prune_generic_keywords(kw_sets: dict[str, set[str]]) -> dict[str, set[str]]:
    """Keep only tokens that can actually identify one vendor's product.

    Without this, a requisition for a single Gigabyte server yields the keyword
    "server", which matches every spec sheet on the vendor's site. Three
    passes: drop document-type words, drop category nouns, then drop tokens
    that show up across vendors - what survives is distinctive to this
    vendor's requisitions.

    A vendor left with no keywords is dropped from the map, which the scraper
    reads as "nothing relevant to look for" and skips the site entirely.
    """
    vendors_per_token = Counter()
    for tokens in kw_sets.values():
        vendors_per_token.update(set(tokens))

    pruned: dict[str, set[str]] = {}
    for supplier, tokens in kw_sets.items():
        keep = {
            t for t in tokens
            if t not in _DOC_TYPE_WORDS
            and t not in _CATEGORY_NOUNS
            and vendors_per_token[t] < _MAX_VENDORS_PER_KEYWORD
        }
        if keep:
            pruned[supplier] = keep
    return pruned


def load_supplier_keywords(labeled_dir: str) -> dict[str, list[str]]:
    """Build per-supplier keyword sets from the classified (labeled) files.

    Only rows the classify stage sorted as Instrument or Software feed the
    scraper - a requisition line for office chairs or a shredding service
    must never send the crawler to that vendor's site. Returns a dict of
    lowercase supplier name -> list of keyword tokens.
    """
    import pandas as pd
    from pathlib import Path

    labeled_path = Path(labeled_dir)
    labeled_files = sorted(labeled_path.glob("*_classified_v3.xlsx")) if labeled_path.is_dir() else []

    if not labeled_files:
        logger.warning("No classified files (*_classified_v3.xlsx) in %s - "
                       "run the classify stage first", labeled_dir)
        return {}

    logger.info("Loading supplier keywords from %d classified file(s) in %s",
                len(labeled_files), labeled_dir)

    supplier_keywords: dict[str, set[str]] = {}
    total_rows = 0
    kept_rows = 0

    for xlsx in labeled_files:
        try:
            df = pd.read_excel(xlsx)
            required = {'Supplier Name', 'Item Description', 'Type'}
            missing = required - set(df.columns)
            if missing:
                logger.warning("%s missing required column(s) %s, skipping",
                               xlsx.name, sorted(missing))
                continue

            total_rows += len(df)
            wanted = df[df['Type'].astype(str).str.strip().str.lower()
                        .isin(('instrument', 'software'))]
            kept_rows += len(wanted)

            for _, row in wanted.iterrows():
                supplier = str(row['Supplier Name']).strip()
                description = str(row['Item Description']).strip()
                if not supplier or not description or description.lower() in ("nan", "nat", ""):
                    continue
                supplier_keywords.setdefault(supplier.lower(), set()).update(
                    _extract_keyword_tokens(description))

            logger.info("  %s: %d of %d rows classified Instrument/Software",
                        xlsx.name, len(wanted), len(df))

        except Exception as exc:
            logger.error("Error reading %s: %s", xlsx.name, exc)

    raw_count = len(supplier_keywords)
    supplier_keywords = prune_generic_keywords(supplier_keywords)

    total_keywords = sum(len(v) for v in supplier_keywords.values())
    logger.info("Keyword gate: %d of %d rows are Instrument/Software -> "
                "%d supplier keyword sets (%d total tokens); "
                "%d supplier(s) dropped - no distinctive keywords",
                kept_rows, total_rows, len(supplier_keywords), total_keywords,
                raw_count - len(supplier_keywords))

    return {k: list(v) for k, v in supplier_keywords.items()}


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def _validate_paths(cfg: dict, stages: dict) -> list[str]:
    """Return a list of error strings; empty means all OK."""
    errors = []
    paths = cfg.get("paths", {})

    if stages["scraper"]:
        supplier_excel = paths.get("supplier_excel", "")
        if not os.path.exists(supplier_excel):
            errors.append(f"Stage 1 (Scraper): supplier_excel not found - {supplier_excel}")
        pdf_dir = paths.get("pdf_dir", "")
        if pdf_dir and not os.path.exists(os.path.dirname(pdf_dir) or "."):
            errors.append(f"Stage 1 (Scraper): parent directory of pdf_dir does not exist - {pdf_dir}")

    if stages["classify"]:
        input_dir = paths.get("input_excel_dir", "")
        if not os.path.exists(input_dir):
            errors.append(f"Stage 2 (Classify): input_excel_dir not found - {input_dir}")
        for key in ("hw_keywords_file", "sw_keywords_file", "ni_keywords_file"):
            kf = cfg.get("classify", {}).get(key, "")
            if kf and not Path(kf).exists():
                errors.append(f"Stage 2 (Classify): keyword file not found - {kf}")

    if stages["crossref"]:
        labeled_dir = paths.get("labeled_dir", "")
        if not os.path.exists(labeled_dir):
            errors.append(f"Stage 3 (Cross-ref): labeled_dir not found - {labeled_dir}")
        master = paths.get("master_excel", "")
        if not os.path.exists(master):
            errors.append(f"Stage 3 (Cross-ref): master_excel not found - {master}")
        pdf_dir = paths.get("pdf_dir", "")
        if not os.path.exists(pdf_dir):
            errors.append(f"Stage 3 (Cross-ref): pdf_dir not found - {pdf_dir}")

    return errors


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

def run_data_cleaner(cfg: dict) -> bool:
    """Stage 0: clean input data before classification."""
    logger.info("=" * 60)
    logger.info("STAGE 0 - DATA CLEANING")
    logger.info("=" * 60)

    paths = cfg.get("paths", {})
    input_dir = paths.get("input_excel_dir", "")

    logger.info("Input directory: %s", input_dir)

    try:
        clean_all_input_excels = _import_from_file(
            "data_cleaner",
            SERVICES_ROOT / "data-cleaning" / "data_cleaner.py",
            "clean_all_input_excels",
        )
    except ImportError as exc:
        logger.error("Cannot import data cleaner: %s", exc)
        return False

    try:
        result = clean_all_input_excels(input_dir, dry_run=False)
        logger.info(
            "Data cleaning finished - %d files processed, %d rows cleaned",
            result["files_processed"], result["total_rows_cleaned"]
        )
        return True
    except Exception as e:
        logger.error("Data cleaning failed: %s", e)
        return False


def run_scraper(cfg: dict) -> bool:
    """Stage 1: crawl supplier websites and download PDFs."""
    logger.info("=" * 60)
    logger.info("STAGE 2 - SCRAPER")
    logger.info("=" * 60)

    paths   = cfg.get("paths", {})
    scfg    = cfg.get("scraper", {})

    supplier_excel = paths["supplier_excel"]
    pdf_dir        = paths["pdf_dir"]

    logger.info("Supplier list : %s", supplier_excel)
    logger.info("PDF output    : %s", pdf_dir)

    try:
        ScraperEngine = _import_from_file(
            "scraper_engine",
            SERVICES_ROOT / "scraper-full" / "scraper_engine.py",
            "ScraperEngine",
        )
    except ImportError as exc:
        logger.error("Cannot import ScraperEngine: %s", exc)
        return False

    engine = ScraperEngine(
        page_timeout             = scfg.get("page_timeout", 15),
        max_pdf_size_mb          = scfg.get("max_pdf_size_mb", 100),
        min_pdf_size_bytes       = scfg.get("min_pdf_size_bytes", 512),
        strict_content_validation= scfg.get("strict_content_validation", False),
        verbose                  = scfg.get("verbose", False),
        skip_recent_sites        = scfg.get("skip_recent_sites", True),
        days_before_rescrape     = scfg.get("days_before_rescrape", 7),
        allowlist_only           = scfg.get("allowlist_only", False),
    )

    # Keywords come from the classified files: only rows the sorting marked
    # Instrument/Software feed the crawler. An empty engine.supplier_keywords
    # would disable the per-PDF filter entirely, so refuse to crawl instead.
    supplier_keywords = load_supplier_keywords(paths.get("labeled_dir", ""))
    if not supplier_keywords:
        logger.error("No Instrument/Software keywords from classified files - "
                     "refusing to crawl unfiltered. Run the classify stage first.")
        return False
    engine.supplier_keywords = supplier_keywords
    logger.info("Loaded %d supplier keyword mappings for targeted PDF filtering",
                len(supplier_keywords))

    t0 = time.time()
    summary = engine.run(supplier_excel, pdf_dir)
    elapsed = time.time() - t0

    logger.info(
        "Scraper finished in %.0f s - pages=%d  pdfs=%d  suppliers=%d",
        elapsed, summary["pages"], summary["pdfs"], summary["suppliers"],
    )
    return True


def run_classify(cfg: dict) -> bool:
    """Stage 2: classify every Excel file in the input directory (v3: Rules A, B, C)."""
    logger.info("=" * 60)
    logger.info("STAGE 1 - CLASSIFY (v3: Prior Context + Supplier Metadata + Bundle Analysis)")
    logger.info("=" * 60)

    paths = cfg.get("paths", {})
    input_dir   = paths["input_excel_dir"]
    labeled_dir = paths["labeled_dir"]

    logger.info("Input dir  : %s", input_dir)
    logger.info("Output dir : %s", labeled_dir)
    logger.info("Rules: A (Prior Context) + B (Supplier Metadata) + C (Bundle Analysis)")

    try:
        column_filter_and_classify = _import_from_file(
            "column_filter_and_classify_v3",
            SERVICES_ROOT / "data-cleaning" / "column_filter_and_classify_v3.py",
            "process_all_inputs",
        )
    except ImportError as exc:
        logger.error("Cannot import column_filter_and_classify_v3: %s", exc)
        return False

    t0 = time.time()
    result = column_filter_and_classify(input_dir, labeled_dir)
    elapsed = time.time() - t0
    count = len(result.get("results", []))

    logger.info("Classify finished in %.0f s - %d file(s) processed", elapsed, count)
    return count > 0 or True   # don't fail the pipeline if dir was empty


def run_supplier_resolution(cfg: dict) -> bool:
    """Stage 2b: resolve unknown suppliers via web search."""
    logger.info("=" * 60)
    logger.info("STAGE 2b - SUPPLIER RESOLUTION")
    logger.info("=" * 60)

    paths = cfg.get("paths", {})
    res_cfg = cfg.get("supplier_resolution", {})

    # Check if supplier resolution is disabled
    if not res_cfg.get("enabled", True):
        logger.info("Supplier resolution disabled in config-skipping")
        return True

    # Build the cfg dict the resolver expects
    resolver_cfg = {
        "master_list":          paths.get("master_list") or paths.get("master_excel", ""),
        "classified_excel":     paths.get("labeled_dir", ""),
        "supplier_resolution":  res_cfg,
    }

    # classified_excel should be the most-recently-labeled file, same logic as crossref
    labeled_path = Path(paths.get("labeled_dir", ""))
    if labeled_path.exists():
        excel_files = sorted(
            list(labeled_path.glob("*_labeled.xlsx")) or list(labeled_path.glob("*.xlsx")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if excel_files:
            resolver_cfg["classified_excel"] = str(excel_files[0])

    logger.info("Master list      : %s", resolver_cfg["master_list"])
    logger.info("Classified Excel : %s", resolver_cfg["classified_excel"])

    try:
        resolve_suppliers = _import_from_file(
            "supplier_resolver",
            SERVICES_ROOT / "supplier-resolution" / "supplier_resolver.py",
            "resolve_suppliers",
        )
    except ImportError as exc:
        logger.error("Cannot import resolve_suppliers: %s", exc)
        return False

    t0 = time.time()
    success = resolve_suppliers(resolver_cfg)
    elapsed = time.time() - t0
    logger.info("Supplier resolution finished in %.0f s - success=%s", elapsed, success)
    return success


def run_crossref(cfg: dict) -> bool:
    """Stage 3: link classified records to downloaded PDFs."""
    logger.info("=" * 60)
    logger.info("STAGE 3 - CROSS-REFERENCE")
    logger.info("=" * 60)

    paths  = cfg.get("paths", {})
    xcfg   = cfg.get("crossref", {})
    labeled_dir  = paths["labeled_dir"]
    master_excel = paths["master_excel"]
    pdf_dir      = paths["pdf_dir"]
    results_dir  = paths.get("results_dir", str(PROJECT_ROOT / "src" / "services" / "cross-reference" / "results"))

    logger.info("Labeled dir   : %s", labeled_dir)
    logger.info("Master Excel  : %s", master_excel)
    logger.info("PDF dir       : %s", pdf_dir)
    logger.info("Results dir   : %s", results_dir)

    try:
        CrossReferenceEngine = _import_from_file(
            "crossref_standalone_fast",
            SERVICES_ROOT / "cross-reference" / "crossref_standalone_fast.py",
            "CrossReferenceEngine",
        )
    except ImportError as exc:
        logger.error("Cannot import CrossReferenceEngine: %s", exc)
        return False

    # The engine expects a single input file; find the most recently labeled Excel
    labeled_path = Path(labeled_dir)
    excel_files = sorted(
        labeled_path.glob("*_labeled.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not excel_files:
        # Fall back: any xlsx in the labeled dir
        excel_files = sorted(
            labeled_path.glob("*.xlsx"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    if not excel_files:
        logger.error("No Excel files found in labeled_dir: %s", labeled_dir)
        return False

    input_file = str(excel_files[0])
    logger.info("Using input file: %s", input_file)
    if len(excel_files) > 1:
        logger.info("(%d other labeled files also present - using most recent)", len(excel_files) - 1)

    engine = CrossReferenceEngine()

    t0 = time.time()
    success = engine.run_cross_reference_high_performance(
        input_file   = input_file,
        master_file  = master_excel,
        pdf_dir      = pdf_dir,
        threshold    = xcfg.get("threshold", 60),
        test_mode    = xcfg.get("test_mode", False),
        low_cpu_mode = xcfg.get("low_cpu_mode", True),
        clean_output = xcfg.get("clean_output", True),
    )
    elapsed = time.time() - t0

    if success:
        os.makedirs(results_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(results_dir, f"crossref_results_{ts}.xlsx")
        engine.export_results(output_file)
        logger.info("Cross-ref finished in %.0f s - %d match(es) saved to %s",
                    elapsed, len(engine.results), output_file)

        # Copy matched PDFs to a review directory for manual inspection
        review_dir = Path(paths.get("review_dir", "C:/Data/Crawler/review")) / ts
        _collect_matched_pdfs(engine.results, review_dir)

        # Purge output PDFs older than 30 days that never matched
        matched_paths = {Path(r["Matched PDF"]).resolve()
                        for r in engine.results if r.get("Matched PDF")}
        _purge_unmatched_pdfs(Path(pdf_dir), matched_paths, days=30)
    else:
        logger.error("Cross-ref failed after %.0f s", elapsed)

    return success


def _collect_matched_pdfs(results: list, review_dir: Path) -> None:
    """Copy matched PDFs into a timestamped review folder."""
    if not results:
        return
    review_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for r in results:
        src = Path(r.get("Matched PDF", ""))
        if src.is_file():
            shutil.copy2(src, review_dir / src.name)
            copied += 1
    logger.info("Copied %d matched PDF(s) to %s", copied, review_dir)
    _purge_old_reviews(review_dir.parent, days=30)


def _purge_old_reviews(review_root: Path, days: int = 30) -> None:
    """Delete review subdirectories older than `days`."""
    if not review_root.is_dir():
        return
    cutoff = time.time() - days * 86400
    for d in review_root.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            logger.info("Purged old review folder: %s", d.name)


def _purge_unmatched_pdfs(output_dir: Path, matched: set, days: int = 30) -> None:
    """Delete PDFs in output/ older than `days` that are not in the matched set."""
    if not output_dir.is_dir():
        return
    cutoff = time.time() - days * 86400
    purged = 0
    for pdf in output_dir.rglob("*.pdf"):
        if pdf.resolve() in matched:
            continue
        if pdf.stat().st_mtime < cutoff:
            pdf.unlink(missing_ok=True)
            purged += 1
    if purged:
        logger.info("Purged %d unmatched PDF(s) older than %d days from %s",
                    purged, days, output_dir)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run the three-stage PDF pipeline.")
    parser.add_argument(
        "--config", default=str(SERVICES_ROOT / "pipeline_config.json"),
        help="Path to pipeline_config.json",
    )
    parser.add_argument("--skip-data-cleaner",         action="store_true", help="Skip Stage 0 (Data Cleaning)")
    parser.add_argument("--skip-scraper",              action="store_true", help="Skip Stage 1 (Scraper)")
    parser.add_argument("--skip-classify",             action="store_true", help="Skip Stage 2 (Classify)")
    parser.add_argument("--skip-supplier-resolution",  action="store_true", help="Skip Stage 2b (Supplier Resolution)")
    parser.add_argument("--skip-crossref",             action="store_true", help="Skip Stage 3 (Cross-ref)")
    parser.add_argument("--only-data-cleaner",         action="store_true", help="Run Stage 0 only")
    parser.add_argument("--only-scraper",              action="store_true", help="Run Stage 1 only")
    parser.add_argument("--only-classify",             action="store_true", help="Run Stage 2 only")
    parser.add_argument("--only-supplier-resolution",  action="store_true", help="Run Stage 2b only")
    parser.add_argument("--only-crossref",             action="store_true", help="Run Stage 3 only")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and paths, then exit")
    args = parser.parse_args()

    cfg = _normalized_config(_load_config(args.config))

    # Resolve which stages to run
    pipe = cfg.get("pipeline", {})
    stages = {
        "data_cleaner":         pipe.get("run_data_cleaner",         True),
        "scraper":              pipe.get("run_scraper",              True),
        "classify":             pipe.get("run_classify",             True),
        "supplier_resolution":  pipe.get("run_supplier_resolution",  True),
        "crossref":             pipe.get("run_crossref",             True),
    }

    # CLI overrides
    if args.only_data_cleaner:
        stages = {"data_cleaner": True, "scraper": False, "classify": False, "supplier_resolution": False, "crossref": False}
    elif args.only_scraper:
        stages = {"data_cleaner": False, "scraper": True,  "classify": False, "supplier_resolution": False, "crossref": False}
    elif args.only_classify:
        stages = {"data_cleaner": False, "scraper": False, "classify": True,  "supplier_resolution": False, "crossref": False}
    elif args.only_supplier_resolution:
        stages = {"data_cleaner": False, "scraper": False, "classify": False, "supplier_resolution": True,  "crossref": False}
    elif args.only_crossref:
        stages = {"data_cleaner": False, "scraper": False, "classify": False, "supplier_resolution": False, "crossref": True}
    else:
        if args.skip_data_cleaner:        stages["data_cleaner"]         = False
        if args.skip_scraper:             stages["scraper"]             = False
        if args.skip_classify:            stages["classify"]            = False
        if args.skip_supplier_resolution: stages["supplier_resolution"] = False
        if args.skip_crossref:            stages["crossref"]            = False

    # Logging starts here (needs results_dir from config)
    results_dir = cfg.get("paths", {}).get("results_dir", str(PROJECT_ROOT / "ops" / "monitoring" / "pipeline-logs"))
    _setup_logging(results_dir)

    logger.info("Pipeline starting - stages: %s", {k: v for k, v in stages.items() if v})

    # Validate paths
    errors = _validate_paths(cfg, stages)
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        if not args.dry_run:
            sys.exit(1)

    if args.dry_run:
        if errors:
            logger.error("Dry run - %d path error(s) found", len(errors))
        else:
            logger.info("Dry run - all paths OK")
        return

    stop_on_failure = pipe.get("stop_on_failure", False)
    results = {}

    if stages["data_cleaner"]:
        ok = run_data_cleaner(cfg)
        results["data_cleaner"] = ok
        if not ok and stop_on_failure:
            logger.error("Data cleaning failed - aborting pipeline (stop_on_failure=true)")
            sys.exit(1)

    # Classify BEFORE scraping: the TYPE sorting gates what the crawler
    # looks for, so it must exist first.
    if stages["classify"]:
        ok = run_classify(cfg)
        results["classify"] = ok
        if not ok and stop_on_failure:
            logger.error("Classify failed - aborting pipeline (stop_on_failure=true)")
            sys.exit(1)

    if stages["scraper"]:
        ok = run_scraper(cfg)
        results["scraper"] = ok
        if not ok and stop_on_failure:
            logger.error("Scraper failed - aborting pipeline (stop_on_failure=true)")
            sys.exit(1)

    if stages["supplier_resolution"]:
        ok = run_supplier_resolution(cfg)
        results["supplier_resolution"] = ok
        if not ok and stop_on_failure:
            logger.error("Supplier resolution failed - aborting pipeline (stop_on_failure=true)")
            sys.exit(1)

    if stages["crossref"]:
        ok = run_crossref(cfg)
        results["crossref"] = ok
        if not ok and stop_on_failure:
            logger.error("Cross-ref failed - aborting pipeline (stop_on_failure=true)")
            sys.exit(1)

    # Summary
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    for stage, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info("  %-12s %s", stage, status)
    logger.info("=" * 60)

    if any(not ok for ok in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
