# Data Cleaning — Integration Guide

## How to Make Data Cleaning Autonomous in the Pipeline

### Option A: Pre-Classification Cleanup (Recommended)

Add to `pipeline.py` **before** the classify stage:

```python
def run_data_cleaner(cfg: dict) -> bool:
    """Stage 0: Clean input data before classification."""
    logger.info("=" * 60)
    logger.info("STAGE 0 — DATA CLEANING")
    logger.info("=" * 60)
    
    input_dir = cfg["paths"]["input_excel_dir"]
    
    try:
        DataCleaner = _import_from_file(
            "data_cleaner",
            SERVICES_ROOT / "data-cleaning" / "data_cleaner.py",
            "clean_all_input_excels",
        )
        result = DataCleaner(input_dir, dry_run=False)
        
        logger.info(
            "Data cleaning finished — %d files processed, %d rows cleaned",
            result["files_processed"], result["total_rows_cleaned"]
        )
        return True
    except Exception as e:
        logger.error("Data cleaning failed: %s", e)
        return False
```

Update the `stages` dict:
```python
stages = {
    "data_cleaner":         cfg.get("stages", {}).get("data_cleaner", True),
    "classify":             cfg.get("stages", {}).get("run_classify", True),
    "supplier_resolution":  cfg.get("stages", {}).get("run_supplier_resolution", True),
    "scraper":              cfg.get("stages", {}).get("run_scraper", True),
    "crossref":             cfg.get("stages", {}).get("run_crossref", True),
}
```

Add execution in `main()`:
```python
if stages["data_cleaner"]:
    ok = run_data_cleaner(cfg)
    results["data_cleaner"] = ok
    if not ok and stop_on_failure:
        logger.error("Data cleaning failed — aborting")
        sys.exit(1)
```

### Option B: Post-Classify Cleanup

Clean files **after** classification outputs them:
```python
if stages["classify"]:
    ok = run_classify(cfg)
    results["classify"] = ok
    
    # Clean the classified output
    if ok:
        classified_dir = cfg["paths"]["labeled_dir"]
        run_data_cleaner({"paths": {"input_excel_dir": classified_dir}})
```

### Option C: Built into Supplier-Resolution

Add cleanup as first step in `supplier_resolver.py`:
```python
def resolve_suppliers(cfg: dict) -> bool:
    # Clean first
    classified_excel = cfg["classified_excel"]
    df = pd.read_excel(classified_excel)
    
    # Apply cleaning
    for col in ["Supplier Name"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_supplier_name)
    
    # Save cleaned version
    df.to_excel(classified_excel, index=False)
    
    # Continue with resolution...
```

---

## Configuration

Add to `pipeline_config.json`:

```json
{
  "pipeline": {
    "run_data_cleaner": true,
    "run_classify": true,
    "run_supplier_resolution": true,
    "run_scraper": true,
    "run_crossref": true
  },
  
  "data_cleaning": {
    "enabled": true,
    "dry_run": false,
    "cleanup_patterns": [
      "use_code_suffix",
      "use_code_parens",
      "leading_asterisks",
      "trailing_asterisks",
      "multiple_spaces"
    ]
  }
}
```

---

## CLI Usage

Once integrated:

```powershell
# Run full pipeline (includes data cleaning)
python src/services/pipeline.py

# Skip data cleaning
python src/services/pipeline.py --skip-data-cleaner

# Only data cleaning
python src/services/pipeline.py --only-data-cleaner

# Dry run preview
python src/services/pipeline.py --data-cleaner-dry-run
```

---

## Monitoring

The data cleaner logs all changes:

```
[data_cleaner] Found 111 rows with data quality issues
[data_cleaner] Cleaned 111 supplier names:
  PHILIPS HEALTHCARE***USE V#79*** → PHILIPS HEALTHCARE
  ...
[data_cleaner] Saved cleaned file: data/...
```

Check the pipeline log for detailed cleanup reports:
```
src/services/cross-reference/results/pipeline_[timestamp].log
```

---

## Extending the Cleaner

Add new patterns to `CLEANUP_PATTERNS` in `data_cleaner.py`:

```python
CLEANUP_PATTERNS = {
    "existing_pattern": r"regex_here",
    "your_new_pattern": r"new_regex_pattern",
}
```

Add detection in `detect_corrupted_names()`:
```python
if re.search(CLEANUP_PATTERNS["your_new_pattern"], name_str):
    issue["issues"].append("your_new_pattern")
```

The cleaner will automatically detect and fix it.

---

## Recommended Implementation

**For autonomy without code changes:**

1. ✅ Use Option A (pre-classification)
2. ✅ Keep patterns in `CLEANUP_PATTERNS` (no code changes needed to add patterns)
3. ✅ Configure via `pipeline_config.json` (control cleanup with config only)
4. ✅ Log all changes (audit trail of what was cleaned)
5. ✅ Support dry-run mode (test before applying)

This way, new data quality patterns can be fixed by just updating the regex in the config, with zero code changes.
