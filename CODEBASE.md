# Crawler Project — Codebase Documentation

**Location:** `C:\Projects\Crawler\PROJECTS\`  
**Type:** Python-based data pipeline  
**Status:** Multi-module production system

---

## Project Overview

Five-stage automated data pipeline that processes supplier data, crawls websites, classifies Excel items, resolves unknown suppliers, and cross-references classified records with downloaded PDFs.

**Entry Point:** `src/services/pipeline.py` — orchestrates all stages in sequence

---

## Architecture: Five-Stage Pipeline

### Stage 0: Data Cleaning
**Module:** `src/services/data-cleaning/`  
**Class:** `DataCleaner`  
**Function:** `clean_all_input_excels(input_dir, dry_run=False)`

Cleans supplier names and related fields before classification:
- Removes data merge artifacts (`***USE V#***` patterns)
- Normalizes whitespace and special characters
- Detects duplicates
- Handles supplier suffix normalization (CORP, INC, LLC, USA suffixes)

**Input:** Raw Excel files in `input_excel_dir`  
**Output:** Cleaned data ready for classification

---

### Stage 1: Scraper (Web Crawler)
**Module:** `src/services/scraper-full/`  
**Class:** `ScraperEngine` (in `scraper_engine.py`)

Crawls supplier websites and downloads PDFs:
- Reads supplier list from Excel
- HTTP requests with rate limiting (configurable delay)
- BeautifulSoup-based HTML parsing
- Same-domain enforcement on every download (`_same_site()`): candidate PDF
  URLs must resolve to the vendor's own domain, a subdomain of it, or a
  host explicitly allow-listed per-vendor (for vendor-run CDNs); enforced
  centrally in `_download_pdf` so it applies uniformly to sitemap, search,
  and recursive-crawl discovery alike
- PDF validation (size, `%PDF` magic-byte content check)
- Deduplication by file hash (SHA-256)
- Concurrent crawling (configurable workers, default 3)
- Timeout protection and retry logic
- Windows-safe path handling

**Config Options:**
- `max_concurrent` (default: 3) — concurrent workers
- `request_delay` (default: 2.0s) — rate limiting
- `page_timeout` (default: 15s) — per-page timeout
- `max_pages_per_site` (default: 50)
- `max_pdf_size_mb` (default: 100)
- `min_pdf_size_bytes` (default: 512)
- `skip_recent_sites` (default: True) — avoid re-scraping recent sites
- `days_before_rescrape` (default: 7)

**Input:** Supplier Excel file (`supplier_excel`)  
**Output:** PDFs in `pdf_dir`

---

### Stage 2: Classification
**Module:** `src/services/classify/`  
**Class:** `AdaptiveExcelProcessor` (in `adaptive_excel_processor.py`)

Machine-learning based classification of Excel items into three categories:
1. **Research Instruments** (HW) — scientific/lab equipment
2. **Software** (SW) — applications, tools, platforms
3. **Non-Instruments** (NI) — office supplies, furniture, services

**Features:**
- Self-learning keyword system with configurable thresholds
- Confidence scoring (default: 0.7 threshold)
- Vendor-based classification for high-confidence matches
- Technical indicator detection (meter, analyzer, spectrometer, etc.)
- Unit detection (volts, watts, ml, kg, etc.)
- Learning mode tracks new keywords (min_occurrences: 5)

**Keyword Files:**
- `research_instrument_keywords.txt` — HW keywords
- `software_keywords.txt` — SW keywords  
- `non_instrument_keywords.txt` — NI keywords

**Config Options:**
- `learning_mode` (default: True) — auto-discover new keywords
- `min_occurrences` (default: 5) — frequency threshold for learning
- `confidence_threshold` (default: 0.7)

**Input:** Raw Excel files from `input_excel_dir`  
**Output:** Labeled Excel files in `labeled_dir` (suffix: `_labeled.xlsx`)

---

### Stage 2b: Supplier Resolution (Optional)
**Module:** `src/services/supplier-resolution/`  
**Function:** `resolve_suppliers(cfg)`

Resolves unknown suppliers via web search:
- Extracts unique supplier names from classified Excel
- Cross-references against master list
- Uses web search (DuckDuckGo, Bing) for unknown suppliers
- Confidence scoring (`pick_best_url`)
- Creates pending list for manual review
- Appends high-confidence suppliers to master list

**Tools:**
- `web_searcher.py` — `find_supplier_url(query)` performs web search
- `confidence_scorer.py` — `pick_best_url(candidates)` scores results

**Output:** 
- Pending list (Excel with unresolved suppliers)
- Updated master list (appended with resolved suppliers)

---

### Stage 3: Cross-Reference (PDF Linking)
**Module:** `src/services/cross-reference/`  
**Class:** `CrossReferenceEngine` (in `crossref_standalone_fast.py`)

Links classified Excel records to downloaded PDFs using fuzzy matching:
- PDF text extraction (PyPDF2 + pdfplumber)
- Multi-threaded and process-pooled PDF analysis
- Fuzzy filename matching (SequenceMatcher)
- Deduplication by normalized filename
- High-performance matching with recovery logic
- Process termination safety

**Features:**
- Threshold-based matching (default: 60%)
- Clean output mode (default: True)
- Low CPU mode (default: True)
- Process recovery from failures
- Global stop flag for safe shutdown

**Utilities (crossref_utils.py):**
- `normalize_filename()` — strips version/year/suffix patterns
- `deduplicate_matches()` — keeps best score per PDF

**Config Options:**
- `threshold` (default: 60) — match score threshold
- `test_mode` (default: False)
- `low_cpu_mode` (default: True)
- `clean_output` (default: True)

**Input:** Labeled Excel, Master Excel, PDF directory  
**Output:** Results Excel in `results_dir` (timestamped)

---

## Configuration

**Main Config File:** `src/services/pipeline_config.json`

**Pipeline Control:**
```json
{
  "pipeline": {
    "run_data_cleaner": true,
    "run_scraper": true,
    "run_classify": true,
    "run_supplier_resolution": true,
    "run_crossref": true,
    "stop_on_failure": false
  },
  "paths": {
    "supplier_excel": "...",
    "pdf_dir": "...",
    "input_excel_dir": "...",
    "labeled_dir": "...",
    "master_excel": "...",
    "master_list": "...",
    "results_dir": "..."
  }
}
```

**CLI Overrides:**
```bash
python pipeline.py --only-scraper          # Run scraper only
python pipeline.py --skip-classify         # Skip classification
python pipeline.py --dry-run               # Validate config only
```

---

## Data Flow

```
Raw Excel Files
      ↓
[Stage 0: Data Cleaning]
      ↓
Cleaned Data
      ↓
[Stage 1: Scraper] ← Supplier List
      ↓
Downloaded PDFs
      ↓
[Stage 2: Classify]
      ↓
Labeled Excel (_labeled.xlsx)
      ↓
[Stage 2b: Supplier Resolution] (Optional)
      ↓
Updated Master List + Pending List
      ↓
[Stage 3: Cross-Reference] ← Master Excel, PDFs
      ↓
Results Excel (crossref_results_[timestamp].xlsx)
```

---

## Key Dependencies

**Core Libraries:**
- `pandas` — Excel/CSV data handling
- `openpyxl` — Excel workbook manipulation
- `requests` — HTTP requests with retry logic
- `BeautifulSoup4` — HTML parsing
- `PyPDF2` — PDF text extraction
- `pdfplumber` — Alternative PDF extraction

**Concurrency:**
- `threading` — Thread pools for I/O operations
- `multiprocessing` — Process pools for CPU-intensive PDF analysis

---

## Testing

**Test Directories:**
- `src/services/*/tests/unit/` — Unit tests per service
- `src/services/*/tests/` — Integration tests

---

## Performance

**Typical Execution Time:**
- Full pipeline: 75-120 minutes
- Scraper: 30-60 min (web-dependent)
- Classify: 10-20 min
- Cross-ref: 30-45 min

---

## Quick Reference

**Entry Point:** `src/services/pipeline.py`  
**Config:** `src/services/pipeline_config.json`  
**Logs:** `results_dir/pipeline_YYYYMMDD_HHMMSS.log`  
**Service Modules:** `src/services/{data-cleaning,scraper-full,classify,supplier-resolution,cross-reference}/`  

