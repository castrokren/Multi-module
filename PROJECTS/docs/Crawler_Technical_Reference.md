# Crawler Technical Reference

> **Application:** Crawler Pipeline v1.1
> **Document Version:** 1.1
> **Last Updated:** 2026-07-09
>
> v1.1: scraper accuracy overhaul (fail-closed keyword filter, CSV-vendor
> guardrail, magic-byte + first-page content checks, content-hash dedup),
> GUI crawler retired in favor of `ScraperEngine`, new input watcher
> (`watch_input.py`) for automatic runs. Ops guide: `docs/RUNBOOK.md`.

---

# Section 1: Document Overview

## 1.1 Purpose & Audience

This document is the single authoritative technical reference for the Crawler application. It describes the architecture, data contracts, algorithms, configuration surface, and operational behavior of every component in the pipeline.

The document is designed for two distinct audiences, indicated by inline tags throughout:

| Tag | Reader | Needs |
|-----|--------|-------|
| `[Architect]` | System architect, tech lead, integrator | System-level understanding — stage boundaries, data flow, config surface, failure modes |
| `[AI Engineer]` | Engineer implementing or extending a stage | Entry points, public API signatures, algorithm details, config keys, known quirks |
| `[Both]` | All readers | Foundational information — purpose, data contracts, terminology |

**Scope:** This document covers the full 5 processing stages (0, 1, 2, 2b, 3) — Data Cleaning (Stage 0), Web Scraper (Stage 1), Classification (Stage 2), Supplier Resolution (Stage 2b), and Cross-Reference (Stage 3) — plus the Orchestrator (`pipeline.py`) that coordinates them.

**Out of scope:** Deployment scripts (`setup_deployment.ps1`, `setup_task_scheduler.ps1`), Git repository setup, installer tooling, diagnostic/debug scripts (listed in Appendix A only as references), and the legacy Tkinter GUI monitors.

## 1.2 How to Read This Document

**Recommended reading paths:**

- **Architects** — Read Sections 1 → 2 → 3 → 4 → 5 → 8 for a top-down understanding of the pipeline architecture, stage boundaries, configuration, and operational considerations.
- **AI Engineers** — Read all sections. Section 6 (Stage Details) contains the implementation-level material you need for extension work.

**Structural conventions:**

- Sections are ordered sequentially by pipeline stage (Stage 0 through Stage 3).
- Each stage section follows a consistent template: **Purpose → Data Flow → Public API → Algorithm → Configuration → Known Quirks**.
- Stage sections are designed for independent reading. Cross-references to config keys and data contracts are provided so any section can be understood without reading preceding sections.
- The Glossary (Section 1.3) and Data Path Conventions (Section 1.4) are prerequisites for all readers.

## 1.3 Terminology & Glossary

| Term | Definition |
|------|-----------|
| **Supplier** | A vendor/manufacturer whose products appear in procurement requisitions |
| **Requisition** | A procurement request file (Excel/CSV) listing items to purchase |
| **Item** | A single line in a requisition with a product description, code, and quantity |
| **Label / Classification** | The category assigned to an item: Research Instrument, Software, or Non-Instrument |
| **Research Instrument** | A physical device used in scientific research (e.g., microscope, spectrometer) |
| **Software** | A computer program or license (e.g., MATLAB, Adobe license) |
| **Non-Instrument** | A supply, consumable, service, or furniture item |
| **PDF Match** | A successful link between a classified item and a downloaded PDF document |
| **Pipeline** | The 5 processing stages (0, 1, 2, 2b, 3) sequential processing system coordinated by `pipeline.py` |
| **Orchestrator** | `pipeline.py` — the config-driven entry point that runs stages |
| **Config Surface** | All configuration keys across all config files that control pipeline behavior |
| **Cross-Reference** | The process of matching classified items to downloaded PDFs via fuzzy text matching |
| **Supplier Resolution** | The (optional) process of finding website URLs for unknown suppliers |
| **Smart Detection** | The 7-day freshness mechanism that skips recently-crawled suppliers |
| **Stage** | One of the 5 sequential phases in the pipeline (Stage 0–3, plus Stage 2b) |

## 1.4 Data Path Conventions

All data paths used by the pipeline are configured in `pipeline_config.json`. A separate document (`Crawler_Path_Reference.md`) contains the full deployment-specific path mappings.

| Store | Content | Stage |
|-------|---------|-------|
| Input Directory | Raw supplier requisition Excel/CSV files | 0, 2 |
| Labeled Directory | Classified Excel files (after Stage 2) | 2, 3 |
| PDF Output Directory | Downloaded PDFs organized in per-supplier subdirectories | 1, 3 |
| Master Supplier List | Supplier names with website URLs | 1, 2b, 3 |
| Crossref Results Directory | Output for `crossref_results_*.xlsx` | 3 |
| Supplier Pending Directory | Pending and resolved supplier files | 2b |

## 1.5 Pipeline Stage Summary Table

The table below defines the complete 5 processing stages (0, 1, 2, 2b, 3). Stage execution order is fixed: 0 → 1 → 2 → 2b → 3. Each stage can be individually enabled or disabled via `pipeline_config.json` or CLI flags.

| # | Stage Name | Module | Entry Function | Input | Output | Lines |
|---|-----------|--------|---------------|-------|--------|-------|
| 0 | Data Cleaning | `data_cleaner.py` | `clean_all_input_excels()` | Raw Excel/CSV from the Input Directory | Cleaned files (in-place) | 558 |
| 1 | Web Scraper | `scraper_engine.py` | `ScraperEngine(config).run()` | Master supplier list | PDFs in the PDF Output Directory + SQLite dedup DB | 2,128 |
| 2 | Classification | `column_filter_and_classify_v3.py` (pipeline) / `adaptive_excel_processor.py` (standalone) | `process_all_inputs()` / `process_directory()` | Cleaned Excel files from the Input Directory | Labeled files in the Labeled Directory | 273 / 1,458 |
| 2b | Supplier Resolution | `supplier_resolver.py` | `resolve_suppliers()` | Labeled Excel | Pending/Resolved lists | 194 |
| 3 | Cross-Reference | `crossref_standalone_fast.py` | `CrossReferenceEngine().run_cross_reference_high_performance()` | Labeled Excel + PDFs | `crossref_results_timestamp.xlsx` | 3,187 |

> **Note on Stage 2:** The pipeline (`pipeline.py`) uses `column_filter_and_classify_v3.py` via `process_all_inputs()`. The standalone classifier `adaptive_excel_processor.py` via `process_directory()` is used by the legacy GUI monitor. Both produce the same output schema for the Labeled Directory.

---

# Section 2: System Architecture [Both]

## 2.1 High-Level Component Diagram

The pipeline is a config-driven, sequentially staged system. Each stage is an independent Python module loaded dynamically by the orchestrator at runtime.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                          pipeline_config.json                                 │
│  paths, pipeline.* (booleans), scraper{}, classify{}, crossref{}              │
└───────────────────┬───────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼───────────────────────────────────────────────────────────┐
│                        pipeline.py (Orchestrator)                              │
│  - Loads config via json.load(), normalizes paths via _resolve_path()         │
│  - Uses importlib.util.spec_from_file_location to dynamically load stages     │
│  - Sequentially calls run_*() for each enabled stage                          │
│  - CLI: --skip-*, --only-*, --dry-run, --config                               │
│  - Optionally stop_on_failure (pipeline_config.json -> pipeline.stop_on_failure)│
└──┬──────────┬──────────┬──────────┬──────────┬────────────────────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌───────────┐ ┌──────────────┐
│Stage 0 │ │Stage 1 │ │Stage 2 │ │ Stage 2b  │ │  Stage 3     │
│ Data   │ │Scraper │ │Classify│ │ Supplier  │ │ Cross-Ref    │
│Cleaning│ │Engine  │ │v3 +    │ │Resolution │ │ Engine       │
│        │ │        │ │Adaptive│ │(disabled) │ │              │
└────────┘ └────────┘ └────────┘ └───────────┘ └──────────────┘
```

**Stage summary:**

| Stage | Module | Entry Function | Enabled By Default |
|-------|--------|---------------|-------------------|
| 0 | `data-cleaning/data_cleaner.py` | `run_data_cleaning()` | `pipeline.stage_0` |
| 1 | `scraper-full/scraper_engine.py` | `run_scraper()` | `pipeline.stage_1` |
| 2 | `data-cleaning/column_filter_and_classify_v3.py` | `run_classify()` | `pipeline.stage_2` |
| 2b | `supplier-resolution/supplier_resolver.py` | `run_supplier_resolution()` | `pipeline.stage_2b` (disabled) |
| 3 | `cross-reference/crossref_standalone_fast.py` | `run_crossref()` | `pipeline.stage_3` |

---

## 2.2 Pipeline State Machine [Architect]

The orchestrator follows a deterministic state machine with exactly one terminal state (success or failure). There is no retry or branching within a single invocation.

```
                        ┌──────────────┐
                        │    START     │
                        └──────┬───────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Load pipeline_config │
                   │  .json via json.load  │
                   └───────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Resolve all paths:   │
                   │  _resolve_path(val,   │
                   │    PROJECT_ROOT)      │
                   └───────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Parse CLI flags:     │
                   │  --skip-*, --only-*,  │
                   │  --dry-run, --config  │
                   └───────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Determine active     │
                   │  stages: config       │
                   │  booleans + CLI       │
                   │  overrides (CLI wins) │
                   └───────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Validate required    │
                   │  paths for active     │
                   │  stages exist         │
                   └───────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
          ┌─────────────────┐   ┌──────────────────┐
          │ Paths valid     │   │ Paths missing    │
          └────────┬────────┘   └────────┬─────────┘
                   │                     │
                   ▼                     ▼
          ┌─────────────────┐   ┌──────────────────┐
          │ Run active      │   │ Log error for    │
          │ stages: 0 → 1 → │   │ each missing     │
          │ 2 → 2b → 3     │   │ path → EXIT(1)   │
          └────────┬────────┘   └──────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
 ┌───────────────┐   ┌────────────────┐
 │ Stage passes  │   │ Stage fails &  │
 │ → next stage  │   │ stop_on_failure│
 └───────┬───────┘   └───────┬────────┘
         │                   │
         ▼                   ▼
 ┌──────────────┐   ┌────────────────┐
 │ All stages   │   │ Log error →    │
 │ complete     │   │ EXIT(1)        │
 └───────┬──────┘   └────────────────┘
         │
         ▼
 ┌────────────────┐
 │ Log summary →  │
 │ EXIT(0)        │
 └────────────────┘
```

**Key behaviors:**

- **Stage ordering is fixed:** 0 → 1 → 2 → 2b → 3. The orchestrator iterates over this ordered list; it does not reorder based on config.
- **CLI override precedence:** If `--only-scraper` is passed, only Stage 1 runs regardless of `pipeline.stage_0`, `pipeline.stage_2`, etc. in config.
- **Dry-run mode:** With `--dry-run`, the orchestrator performs steps 1–4 and logs which stages *would* run, then exits(0) without executing any stage.
- **Failure propagation:** When `stop_on_failure` is `true`, a single failing stage terminates the pipeline immediately. When `false`, the orchestrator logs the failure and continues to the next stage.

---

## 2.3 Data Flow Diagram [Architect]

Data flows unidirectionally through the pipeline. Each stage reads from one or more locations and writes to a location consumed by a later stage.

```
  Input Directory              Labeled Directory              PDF Output Directory
   (raw .xlsx/.csv)              (classified .xlsx)              (PDFs/supplier/)
         │                              ▲                              │
         │                              │                              │
         ▼                              │                              │
   ┌───────────┐                 ┌────────────┐                ┌──────────────┐
   │  Stage 0  │                 │  Stage 2   │                │  Stage 1     │
   │   Data    │                 │  Classify  │                │  Scraper     │
   │  Cleaner  │────────────────▶│ (v3 +      │                │  (per-domain │
   │           │  cleaned file   │  Adaptive) │                │   threads)   │
   │(in-place) │  (in-place or   │            │                │              │
   └───────────┘  new file)      │  Type col  │                │ .scraper_    │
                                  │ added     │                │ dedup.db     │
                                  └─────┬──────┘                │ .scraper_    │
                                        │                       │ state.json   │
                                        │                       └──────────────┘
                                        │                              │
                                        │                              │
                                 ┌──────▼──────┐                      │
                                 │  Stage 2b   │                      │
                                 │  Supplier   │  (disabled by        │
                                 │  Resolution │   default)            │
                                 │  (DuckDuckGo│                      │
                                 │   + Bing)   │                      │
                                 └──────┬──────┘                      │
                                        │                              │
                                        ▼                              ▼
                          ┌───────────────────────────────────────────────────┐
                          │              Stage 3: Cross-Reference Engine       │
                          │  Links classified items → matching PDFs by        │
                          │  supplier using fuzzy text matching               │
                          │                                                    │
                           │  Inputs:  Labeled Directory (classified .xlsx)    │
                           │           PDF Output Directory (PDFs by supplier)│
                           │           Master Supplier List workbook          │
                          │                                                    │
                          │  Output: crossref_results_<timestamp>.xlsx        │
                          │          columns: Match Result, Item Code,        │
                          │          Description, Category, PDF File,         │
                          │          Match Score (%), Supplier                │
                          └───────────────────────────────────────────────────┘
```

**Cross-boundary data locations:**

| From | To | Data | Medium |
|------|----|------|--------|
| Stage 0 | Stage 2 | Cleaned Excel files in the Input Directory | `.xlsx` / `.csv` |
| Stage 1 | Stage 3 | Downloaded PDFs in the PDF Output Directory by supplier | PDF files on disk |
| Stage 2 | Stage 3 | Labeled Excel files in the Labeled Directory | `.xlsx` with `Type` column |
| Master list | Stage 1, Stage 3 | Supplier names + website URLs | `.xlsx` (~247 rows) |
| Stage 2b | Stage 2 | Resolved supplier URLs | `.xlsx` written to the Supplier Pending Directory |

---

## 2.4 Cross-Boundary Data Contracts [Architect]

Each boundary crossing has a defined schema. All stages within the pipeline must agree on column positions, data types, and file formats.

### Input Excel (Raw Supplier Requisition) — read by Stage 0 & 2

| Property | Value |
|----------|-------|
| **Format** | `.xlsx` (openpyxl) or `.csv` (pandas + chardet encoding detection) |
| **Required columns** (by position for v3 classifier) | B = Req ID, F = Supplier ID, G = Supplier Name, I = Item Description, O = Req Line Item |
| **Encoding (CSV)** | Auto-detected via `chardet` library |
| **Expected row structure** | Header row, 1 data row per requisition line item |

### Cleaned Excel (After Stage 0)

| Property | Value |
|----------|-------|
| **Format** | Same as input (`.xlsx` or `.csv`) |
| **Schema** | Same column set as input, with content modifications |
| **Modifications** | Supplier names normalized (artifacts removed, common suffixes stripped). Unicode replacement characters (`\uFFFD`, `�`) removed from description columns. |
| **Write behavior** | In-place modification of input files by default |

### Labeled Excel (After Stage 2)

| Property | Value |
|----------|-------|
| **Format** | `.xlsx` |
| **Schema** | All input columns plus added columns below |
| **v3 classifier filename suffix** | `_classified_v3.xlsx` |
| **Adaptive processor filename suffix** | `_labeled.xlsx` |

**Added columns:**

| Column | Type | Values | Source |
|--------|------|--------|--------|
| `Type` | `string` | `"Instrument"`, `"Software"`, `"Non-Instrument"`, or `"Unknown"` | v3 classifier |
| `Confidence Score` | `float` (0.0–1.0) | Confidence of classification | Adaptive processor only |
| `Match Reason` | `string` | Keyword or rule that triggered match | Adaptive processor only |

### Master List Schema (read by Stage 1 & 3)

| Property | Value |
|----------|-------|
| **Format** | `.xlsx` |
| **Approximate row count** | ~247 |
| **Columns** | Supplier Name, Website, Category notes |

This file maps each known supplier to its website URL. Stage 1 uses the URL to begin crawling. Stage 3 uses the URL to verify PDF origin during cross-referencing. When a supplier is not in the master list, Stage 2b (supplier resolution) attempts to find its URL via web search.

### Crossref Results Schema (Stage 3 output)

| Property | Value |
|----------|-------|
| **Format** | `.xlsx` |
| **Timestamp format** | `YYYYMMDD_HHMMSS` |

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `Match Result` | `string` | `"Match"` or `"No Match"` |
| `Item Code` | `string` | Requisition line item code (column O in input) |
| `Description` | `string` | Item description (column I in input) |
| `Category` | `string` | Classification from Stage 2 |
| `PDF File` | `string` | Filename of matched PDF (including `.pdf`), or empty |
| `Match Score` | `integer` (0–100) | Fuzzy match percentage |
| `Supplier` | `string` | Normalized supplier name |

**Match criteria:**

- A match is recorded when `Match Score >= 60`
- Matching is performed between item description text and PDF text content
- Scoring uses fuzzy string comparison (Levenshtein distance via `rapidfuzz` or `fuzzywuzzy`)
- Each item matched against all PDFs belonging to the same supplier

---

## 2.5 Code Layout [Both]

The project maintains two concurrent directory trees. The pipeline exclusively uses the `src/services/` layout. Legacy directories exist at the repo root for backward compatibility with GUI/CLI scripts.

### Active layout (used by pipeline.py)

```
src/services/
│
├── pipeline.py                                        ← Orchestrator (entry point)
├── pipeline_config.json                               ← Primary configuration file
├── __init__.py
│
├── data-cleaning/
│   ├── data_cleaner.py                                ← Stage 0: Data Cleaning
│   └── column_filter_and_classify_v3.py               ← Stage 2: Pipeline classifier
│
├── scraper-full/
│   ├── scraper_engine.py                              ← Stage 1: Web Scraper Engine
│   └── ... (site-specific crawlers, utilities)
│
├── classify/
│   └── adaptive_excel_processor.py                    ← Stage 2: Standalone classifier (legacy GUI)
│
├── supplier-resolution/
│   └── supplier_resolver.py                           ← Stage 2b: Supplier Resolution
│
├── cross-reference/
│   ├── crossref_standalone_fast.py                    ← Stage 3: Cross-Reference Engine
│   ├── crossref_utils.py                              ← Shared utilities (fuzzy matching, etc.)
│   └── results/                                       ← Output directory for crossref_results_*.xlsx
│
└── monitoring/
    └── phase4_analysis.py                             ← Post-run analysis script
```

### Legacy layout (NOT used by pipeline)

```
legacy/
├── Classify/                          ← Standalone classification GUI scripts
├── Cross-reference/                   ← Standalone cross-reference CLI/GUI scripts
├── Scraper_full/                      ← Standalone scraper GUI scripts
├── run_full_scraper.py                ← Scraper-only entry point (repo root)
├── setup.bat / start.bat / stop.bat   ← Service management scripts
```

> **Important:** The pipeline (`pipeline.py`) dynamically imports stage modules by their full file path under the services directory. It does **not** use Python package imports. The legacy directories are used only by individual GUI/CLI scripts that predate the pipeline orchestrator.

---

## 2.6 Entry Points Table [Both]

| Entry Point | Command | Purpose | When to Use |
|------------|---------|---------|-------------|
| **Full Pipeline** | `python pipeline.py --config pipeline_config.json` | Runs all enabled stages 0→1→2→2b→3 sequentially | Scheduled runs, production |
| **Input Watcher (automatic)** | `python watch_input.py` | Watches the input directory; runs the full pipeline when CSV/Excel files arrive (30 s debounce, coalesced runs) | Unattended production — register at logon via Task Scheduler. See `docs/RUNBOOK.md` |
| **Crawler GUI** | `scraper-full\dist\PDF_Crawler_GUI.exe` | Manual one-shot crawl + cross-reference tools; uses the same `ScraperEngine` and filters as the pipeline | Ad-hoc supervised runs. Older `Crawlers.exe`/`WebScrapper.exe` predate the filters — do not use |
| **Scraper Only** | `python run_full_scraper.py` | Runs Stage 1 only for all suppliers, no freshness check | Ad-hoc rescrapes, testing new crawl targets |
| **Scraper (pipeline)** | `python pipeline.py --only-scraper --skip-recent-sites=False` | Forces Stage 1 rescrape for all suppliers ignoring 7-day cache | After config changes, adding new suppliers |
| **Classify + Crossref** | `python pipeline.py --skip-scraper --skip-supplier-resolution` | Runs Stages 2 and 3 only, reuses existing PDFs | Iterative classification development |
| **Cross-Ref GUI** | `python -m cross-reference.crossref_standalone_fast` | Launches Tkinter GUI for interactive cross-reference debugging | Interactive debugging, manual verification |
| **Dry-Run** | `python pipeline.py --dry-run` | Validates config and paths without executing any stage | Pre-deployment validation |
| **Classify (standalone)** | `python data-cleaning/column_filter_and_classify_v3.py` | Runs Stage 2 classification without pipeline | Testing classifier changes in isolation |
| **Post-Run Analysis** | `python monitoring/phase4_analysis.py` | Analyzes cross-reference results and generates summary stats | Post-pipeline analysis, reporting |

**CLI flags for `pipeline.py`:**

| Flag | Effect |
|------|--------|
| `--config <path>` | Use alternate config file (default: `pipeline_config.json`) |
| `--dry-run` | Validate config + paths, print active stages, exit without executing |
| `--skip-scraper` | Disable Stage 1 regardless of config boolean |
| `--skip-classify` | Disable Stage 2 regardless of config boolean |
| `--skip-supplier-resolution` | Disable Stage 2b regardless of config boolean |
| `--skip-crossref` | Disable Stage 3 regardless of config boolean |
| `--only-scraper` | Run only Stage 1 (disables all others) |
| `--only-classify` | Run only Stage 2 (disables all others) |
| `--only-crossref` | Run only Stage 3 (disables all others) |

**Override precedence (highest to lowest):** `--only-*` flags > `--skip-*` flags > `pipeline_config.json` booleans.

---

# Section 3: Configuration Surface [Both]

## 3.1 Config File Inventory

| File | Location | Purpose | Stage | Priority |
|------|----------|---------|-------|----------|
| `pipeline_config.json` | the pipeline config file | Primary pipeline config — stages, paths, per-stage settings | All | Highest (CLI overrides) |
| `config.ini` | the legacy config file | Legacy INI config — scraper defaults | Stage 1 | Fallback (overridden by JSON) |
| `monitor_config.json` | the monitor config file | Windows service monitor for classification | Stage 2 | Standalone only |
| `service_config.json` | the service config file | Windows service registration | Stage 2 | Standalone only |

## 3.2 pipeline_config.json — Full Schema

Each row documents one config key as it appears in the pipeline config file. Types are Python runtime types. Defaults reflect the values set when the file ships.

| Key | Type | Default | Stage | Description |
|-----|------|---------|-------|-------------|
| `paths.supplier_excel` | string | (configurable — see Path Reference doc) | 1 | Path to master supplier list |
| `paths.pdf_dir` | string | (configurable — see Path Reference doc) | 1, 3 | Root directory for downloaded PDFs |
| `paths.input_excel_dir` | string | (configurable — see Path Reference doc) | 0, 2 | Directory containing raw supplier requisition files |
| `paths.labeled_dir` | string | (configurable — see Path Reference doc) | 2, 3 | Directory for classified output files |
| `paths.master_excel` | string | (configurable — see Path Reference doc) | 3 | Master supplier list (cross-ref reads it) |
| `paths.master_list` | string | (configurable — see Path Reference doc) | 2b | Master supplier list (resolution reads it) |
| `paths.results_dir` | string | (configurable — see Path Reference doc) | 3 | Output directory for crossref results |
| `pipeline.run_data_cleaner` | bool | `true` | 0 | Enable Stage 0 |
| `pipeline.run_scraper` | bool | `true` | 1 | Enable Stage 1 |
| `pipeline.run_classify` | bool | `true` | 2 | Enable Stage 2 |
| `pipeline.run_supplier_resolution` | bool | `false` | 2b | Enable Stage 2b (disabled by default) |
| `pipeline.run_crossref` | bool | `true` | 3 | Enable Stage 3 |
| `pipeline.stop_on_failure` | bool | `false` | All | Exit immediately on stage failure |
| `scraper.max_concurrent` | int | `3` | 1 | Max simultaneous domain threads (note: modern code uses threading, this may be historical) |
| `scraper.request_delay` | float | `2.0` | 1 | Seconds between requests on same domain |
| `scraper.page_timeout` | int | `15` | 1 | HTTP request timeout in seconds |
| `scraper.max_pages_per_site` | int | `50` | 1 | Max pages to crawl on a single site |
| `scraper.max_pdf_size_mb` | int | `100` | 1 | Max PDF file size in MB |
| `scraper.min_pdf_size_bytes` | int | `512` | 1 | Minimum PDF size; smaller files deleted |
| `scraper.strict_content_validation` | bool | `false` | 1 | Require Content-Type: application/pdf on HEAD |
| `scraper.verbose` | bool | `false` | 1 | Verbose logging |
| `scraper.batch_size` | int | `10` | 1 | Suppliers per batch |
| `scraper.skip_recent_sites` | bool | `true` | 1 | Skip suppliers crawled within days_before_rescrape |
| `scraper.days_before_rescrape` | int | `7` | 1 | Freshness window in days |
| `scraper.allowlist_only` | bool | `true` | 1 | Only download PDFs matching allowlist patterns |
| `classify.learning_mode` | bool | `true` | 2 | Enable self-learning keyword promotion |
| `classify.min_occurrences` | int | `5` | 2 | Min occurrences before keyword promotion |
| `classify.confidence_threshold` | float | `0.7` | 2 | Min confidence for keyword promotion |
| `classify.hw_keywords_file` | string | (configurable — see Path Reference doc) | 2 | Hardware/Instrument keyword list |
| `classify.sw_keywords_file` | string | (configurable — see Path Reference doc) | 2 | Software keyword list |
| `classify.ni_keywords_file` | string | (configurable — see Path Reference doc) | 2 | Non-Instrument keyword list |
| `supplier_resolution.enabled` | bool | `false` | 2b | Master switch for supplier resolution |
| `supplier_resolution.confidence_threshold` | int | `70` | 2b | Min URL confidence score to auto-resolve (range 0-110) |
| `supplier_resolution.search_delay_seconds` | float | `1.5` | 2b | Delay between search engine requests |
| `supplier_resolution.search_timeout_seconds` | int | `10` | 2b | HTTP timeout per search request |
| `supplier_resolution.pending_list_path` | string | (configurable — see Path Reference doc) | 2b | Output path for low-confidence suppliers needing manual review |
| `supplier_resolution.resolved_list_path` | string | (configurable — see Path Reference doc) | 2b | Output path for high-confidence resolved suppliers |
| `crossref.threshold` | int | `60` | 3 | Minimum match score (0-100) to keep a result |
| `crossref.test_mode` | bool | `false` | 3 | Limit processing (5 suppliers, 100 PDFs/batch, 20 items) |
| `crossref.low_cpu_mode` | bool | `true` | 3 | Sequential PDF processing (uses ProcessPoolExecutor with 1 worker) |
| `crossref.clean_output` | bool | `true` | 3 | Clean formatting in output Excel |

## 3.3 config.ini — Legacy Settings

This file exists for legacy compatibility. The values are overridden by `pipeline_config.json` when the pipeline runs. Used only when the scraper is invoked directly via `run_full_scraper.py` or other scripts that read `configparser` directly instead of going through `pipeline.py`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_concurrent` | int | `3` | Max simultaneous domain threads |
| `request_delay` | float | `2.0` | Per-domain request delay |
| `page_timeout` | int | `15` | HTTP timeout |
| `max_pages_per_site` | int | `50` | Maximum pages to visit |
| `match_threshold` | int | `60` | Cross-ref match threshold (legacy — now in pipeline_config.json) |
| `max_pdf_size_mb` | int | `100` | Max PDF size |
| `min_pdf_size_bytes` | int | `512` | Min PDF size |
| `strict_content_validation` | bool | `False` | Require content-type header |

## 3.4 classify/monitor_config.json

This configures the Windows service that watches a network share for new Excel files and runs classification automatically. It is consumed by `classify/monitor_service.py` and is **not** used by the pipeline orchestrator.

| Key | Type | Description |
|-----|------|-------------|
| `watch_directory` | string | Network directory to monitor for new Excel/CSV files |
| `output_directory` | string | Directory where classified output files are written |
| `hardware_keywords_file` | string | Path to the hardware/instrument keyword file |
| `software_keywords_file` | string | Path to the software keyword file |
| `non_instrument_keywords_file` | string | Path to the non-instrument keyword file |
| `service_name` | string | Windows service short name (used with `sc.exe`) |
| `service_display_name` | string | Windows service display name (shown in Services console) |
| `log_level` | string | Logging verbosity (e.g., `INFO`, `DEBUG`) |
| `process_timeout` | int | Max processing time per file in seconds before the watchdog cancels |

## 3.5 classify/service_config.json

Additional Windows service configuration consumed by the service wrapper in `classify/simple_W_service.py`. This file covers operational concerns such as process heartbeats, restart policy, and Windows SCM dependency declarations.

Key fields include:

- `heartbeat_interval_seconds` — how often the service writes a heartbeat timestamp
- `restart_delay_seconds` — pause before automatic restart after unexpected exit
- `max_restarts` — maximum consecutive restarts before the service enters a stopped state
- `dependencies` — list of Windows service names that must be running before this service starts

## 3.6 Runtime Resolution Order

The order of precedence for all config values (highest wins):

1. **CLI flags** (`--skip-*`, `--only-*`, `--dry-run`, `--config`) — override everything
2. **pipeline_config.json** — primary config source
3. **config.ini** — legacy fallback for scraper defaults
4. **Code defaults** — hardcoded constructor parameter defaults (lowest priority)

For boolean pipeline stage toggles, CLI `--skip-*` forces `false` on that stage regardless of config. CLI `--only-*` forces `true` for that stage and `false` for all others. This means `--only-scraper --skip-classify` resolves to only the scraper running, since `--only-*` logic overrides `--skip-*` by zeroing all non-target stages first.

---

# Section 4: Stage 0 — Data Cleaning [Both]

## 4.1 Purpose & Data Flow

- **Input:** Raw supplier requisition Excel/CSV files from the input directory
- **Processing:** Normalizes supplier names, removes merge artifacts, fixes Unicode replacement characters
- **Output:** Modified files written in-place (or to alternate path in dry-run mode)
- **Runtime:** ~1–5 minutes depending on file count
- **When it runs:** Before Stage 2 (Classification) — ensures clean supplier names for classification matching

## 4.2 Module: data_cleaner.py [AI Engineer]

**File:** `data_cleaner.py` — 558 lines

### clean_supplier_name(name: str) → str

Applies five regex-based cleanup rules in the order listed below, then strips leading/trailing whitespace.

| Order | Pattern Key | Regex | Removes |
|-------|-------------|-------|---------|
| 1 | `use_code_suffix` | `\*\*\*USE V#\d+\*\*\*` | `***USE V#79***` merge artifacts (applied with `re.IGNORECASE`) |
| 2 | `use_code_parens` | `\(USE[^)]*\)` | `(USE CODE 123)` parenthetical blocks (applied with `re.IGNORECASE`) |
| 3 | `leading_asterisks` | `^\*+` | Leading asterisk runs (e.g. `**** Acme`) |
| 4 | `trailing_asterisks` | `\*+$` | Trailing asterisk runs (e.g. `Acme ***`) |
| 5 | `multiple_spaces` | `\s+` | Consecutive whitespace → single space |

**Null handling:** Returns the value unchanged if `pd.isna(name)` is true. Returns `""` if the cleaned result is empty.

**SUPPLIER_SUFFIXES_TO_REMOVE** (defined at module level, 16 entries — available for suffix-stripping pipelines):

| # | Suffix | # | Suffix |
|---|--------|---|--------|
| 1 | `" - USA"` | 9 | `" CORP"` |
| 2 | `" USA"` | 10 | `" CORPORATION"` |
| 3 | `" NORTH AMERICA"` | 11 | `" INC"` |
| 4 | `" NA"` | 12 | `" LLC"` |
| 5 | `" DIVISION"` | 13 | `" LTD"` |
| 6 | `" SUBSIDIARY"` | 14 | `" CO"` |
| 7 | `" AFFILIATE"` | 15 | `" SALES"` |
| 8 | `" SERVICES"` | 16 | `" SOLUTIONS"` |

> **Note:** `SUPPLIER_SUFFIXES_TO_REMOVE` is defined as a module constant but is not currently consumed by `clean_supplier_name` or any other function in `data_cleaner.py`. It exists for use by downstream or future suffix-normalization steps.

### detect_corrupted_names(df: pd.DataFrame, supplier_col: str = "Supplier Name") → pd.DataFrame

Iterates every row in `supplier_col`, checking each non-null value against four of the five `CLEANUP_PATTERNS` (excludes `multiple_spaces`). Returns a DataFrame with columns:

| Column | Type | Description |
|--------|------|-------------|
| `index` | int | Original row index from input DataFrame |
| `original` | str | Raw supplier name as read |
| `issues` | list[str] | List of pattern keys that matched |

Returns an **empty DataFrame** when no issues are found.

### clean_excel_file(excel_path: str, output_path: str | None = None, supplier_col: str = "Supplier Name", dry_run: bool = False) → dict

**CSV loading:** Uses `detect_file_encoding()` (reads first 10 KB via `chardet`) to determine encoding, then calls `pd.read_csv(encoding=...)`.

**Unicode fix:** Replaces the replacement character `\ufffd` (literal `�`) with empty string in three columns: `Item Description`, `Req Header Comments`, `Req Line Comments`.

**Return schema:**

| Key | Type | Present In | Description |
|-----|------|------------|-------------|
| `input_file` | str | Always | Path to source file |
| `output_file` | str | Non-dry-run only | Path where cleaned file was saved |
| `rows_total` | int | Always | Total row count in file |
| `rows_cleaned` | int | Always | Number of supplier names modified |
| `dry_run` | bool | Always | `true` when no changes were written |
| `status` | str | Always | `"dry_run_complete"` or `"success"` |

### clean_all_input_excels(input_dir: str, dry_run: bool = False) → dict

Iterates all `.xlsx`, `.xls`, and `.csv` files in `input_dir` via `Path.glob`. Calls `clean_excel_file()` for each. Collects per-file results.

**Return schema:**

| Key | Type | Description |
|-----|------|-------------|
| `input_directory` | str | The directory scanned |
| `files_processed` | int | Number of files found and attempted |
| `total_rows` | int | Sum of all rows across all files |
| `total_rows_cleaned` | int | Sum of all cleaned supplier names |
| `results` | list[dict] | Per-file result dicts (may include error entries) |
| `dry_run` | bool | Whether run was read-only |

**Error handling per file:** If `clean_excel_file()` raises, the error is caught and recorded as a result entry with `"status": "error"` and an `"error"` key containing the exception message. Processing continues to the next file.

## 4.3 Unicode Fix — Affected Columns [AI Engineer]

| Column | Issue | Fix Applied |
|--------|-------|-------------|
| `Item Description` | Contains replacement character `\ufffd` (�) | Stripped via `str.replace("�", "", regex=False)` |
| `Req Header Comments` | Contains replacement character `\ufffd` (�) | Same |
| `Req Line Comments` | Contains replacement character `\ufffd` (�) | Same |

The fix is applied unconditionally to all three columns if they exist in the DataFrame. No other columns are touched.

## 4.4 Dry-Run Mode [Both]

- When `dry_run=True`, the cleaner loads and processes files but does **not** write changes to disk
- Returns the same structured dict with `"dry_run": true` and `"status": "dry_run_complete"`
- No `output_file` key is present in the per-file result
- Used for preview before destructive in-place modification

## 4.5 Config Keys Consumed [Architect]

From `pipeline_config.json`:

| Key | Purpose |
|-----|---------|
| `paths.input_excel_dir` | Directory to scan for raw Excel/CSV files |

No other config keys are read by `data_cleaner.py`.

## 4.6 Failure Modes [AI Engineer]

| Condition | Behavior |
|-----------|----------|
| The input directory does not exist | `FileNotFoundError` raised by `clean_all_input_excels()` |
| CSV encoding detection fails | `detect_file_encoding()` falls back to `'utf-8'`; `pd.read_csv` may raise `UnicodeDecodeError` |
| Supplier column is missing | `ValueError` raised by both `clean_excel_file()` and `detect_corrupted_names()` with a message listing available columns |
| All supplier values are empty/NaN | Rows silently pass through; `rows_cleaned` is 0 |
| Output path directory doesn't exist | `clean_excel_file()` raises `FileNotFoundError` (no fallback is implemented) |
| Corrupted Excel file | `pd.read_excel()` propagates the exception up; caught by `clean_all_input_excels()` per-file error handler |
| Inaccessible file (permissions) | `pd.read_excel()` or `pd.read_csv()` raises; caught and reported as error entry |

---

# Section 5: Stage 1 — Scraper Engine [AI Engineer]

## 5.1 Purpose & Data Flow [Both]

- **Input:** Master supplier list (247 suppliers with website URLs) from the master supplier list workbook
- **Processing:** Per-domain threaded web crawling to discover and download PDF product documents
- **Output:** PDF files organized in per-supplier subdirectories in the PDF output directory + SQLite dedup DB (`.scraper_dedup.db`) + state JSON (`.scraper_state.json`)
- **Runtime:** ~60-90 min full crawl, ~10 min smart rescrape (when all suppliers are within the 7-day freshness window)

## 5.2 Class: ScraperEngine [AI Engineer]

Defined at `scraper_engine.py:779`. The top-level crawler that orchestrates per-domain threaded discovery and download.

**Constructor:**

```python
__init__(
    page_timeout: int = 15,
    max_pdf_size_mb: int = 100,
    min_pdf_size_bytes: int = 512,
    strict_content_validation: bool = False,
    verbose: bool = False,
    skip_recent_sites: bool = True,
    days_before_rescrape: int = 7,
    use_relevance_filter: bool = True,
    allowlist_only: bool = False,
    site_config_path: str | None = None,
    use_keyword_filter: bool = True,
    supplier_keywords: dict[str, list[str]] | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page_timeout` | `int` | `15` | Per-request HTTP timeout in seconds |
| `max_pdf_size_mb` | `int` | `100` | Skip PDFs larger than this threshold (checked via HEAD and mid-stream) |
| `min_pdf_size_bytes` | `int` | `512` | Delete downloaded files smaller than this (post-download check) |
| `strict_content_validation` | `bool` | `False` | Reject responses whose `Content-Type` header is not `application/pdf` |
| `verbose` | `bool` | `False` | Log every URL visited during link-walking |
| `skip_recent_sites` | `bool` | `True` | Skip suppliers crawled within `days_before_rescrape` days |
| `days_before_rescrape` | `int` | `7` | Freshness window in days; suppliers crawled more recently are skipped |
| `use_relevance_filter` | `bool` | `True` | Apply blocklist check before each download |
| `allowlist_only` | `bool` | `False` | Only download PDFs matching product-doc allowlist patterns. Note: The pipeline_config.json default is `true`, which overrides this constructor default at runtime when the pipeline runs. |
| `site_config_path` | `str \| None` | `None` | Path to per-domain JSON override file (optional) |
| `use_keyword_filter` | `bool` | `True` | Enable Camofox-based page keyword check before crawling |
| `supplier_keywords` | `dict[str, list[str]] \| None` | `None` | Loaded from pipeline after construction; maps lowercase supplier name to keyword tokens for filename-level filtering |

**Public API:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `run` | `(supplier_excel: str, output_dir: str) -> dict` | `{"pages": int, "pdfs": int, "suppliers": int}` | Main entry point. Loads suppliers, applies freshness filter, spawns per-domain threads, blocks until all complete, saves state |
| `stop` | `() -> None` | `None` | Signals all worker threads to stop via `self._stop_event.set()` |
| `running` | `(property) -> bool` | `bool` | Returns `not self._stop_event.is_set()` |

**Internal state attributes (set in `__init__`):**

| Attribute | Type | Description |
|-----------|------|-------------|
| `self._stop_event` | `threading.Event` | Thread-safe stop signal; cleared on `run()`, set on `stop()` |
| `self._rate_limiter` | `_DomainRateLimiter` | Per-domain delay enforcer shared across all workers |
| `self._site_overrides` | `dict` | Per-domain config overrides loaded from JSON file (merged onto `DEFAULT_SITE_CONFIG`) |
| `self.supplier_keywords` | `dict[str, list[str]]` | Supplier-specific keyword tokens for filename-level filtering (loaded externally, set after construction) |
| `self.keywords` | `set` | Hardware + software keyword set loaded from `hardware_keywords_ACTIVE.txt` / `software_keywords_ACTIVE.txt` |
| `self.page_count` | `int` | Running count of pages visited (thread-safe via `self._count_lock`) |
| `self.pdf_count` | `int` | Running count of PDFs successfully downloaded (thread-safe via `self._count_lock`) |
| `self._count_lock` | `threading.Lock` | Mutex protecting `page_count` / `pdf_count` increments |

**Note:** There is no `self.session` or `self.state_db` stored on the engine at the instance level. Each domain worker creates its own HTTP session via `_make_session()`. The `_StateDB` instance is created as a local variable in `run()` and passed to workers as a parameter. Thread references are also local to `run()` (the `threads` list).

## 5.3 Threading Model [AI Engineer]

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Main Thread (run())                          │
│  Load suppliers → group by domain → spawn workers → join all       │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
     ┌────────────┼────────────┬──────────────────┐
     ▼            ▼            ▼                  ▼
┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────┐
│ Worker   │ │ Worker   │ │ Worker   │ ... │ Worker   │
│ domain-A │ │ domain-B │ │ domain-C │     │ domain-N │
│ daemon   │ │ daemon   │ │ daemon   │     │ daemon   │
└────┬─────┘ └────┬─────┘ └────┬─────┘     └────┬─────┘
     │            │            │                  │
     │  ┌─────────┐            │                  │
     │  │_Domain  │            │                  │
     │  │RateLim  │ (shared instance, keyed by domain)
     │  └─────────┘            │                  │
     ▼            ▼            ▼                  ▼
┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────┐
│threading │ │threading │ │threading │     │threading │
│ .local() │ │ .local() │ │ .local() │     │ .local() │
│ SQLite   │ │ SQLite   │ │ SQLite   │     │ SQLite   │
│ conn     │ │ conn     │ │ conn     │     │ conn     │
└──────────┘ └──────────┘ └──────────┘     └──────────┘

  Stop signal: self._stop_event (threading.Event) ──→ checked at every
                                                      iteration boundary
```

**Per-Domain Worker Architecture:**

- One thread per unique domain extracted from supplier URLs (daemon=True)
- All domains crawl concurrently; within a single domain, requests are serialized via `_DomainRateLimiter`
- Daemon threads die automatically when the main thread exits
- Workers are joined with a 600-second (10-minute) per-thread timeout

**_DomainRateLimiter Algorithm** (`scraper_engine.py:425`):

```python
class _DomainRateLimiter:
    _lock: threading.Lock
    _last: dict[str, float]   # domain → last_request_timestamp

    def wait(domain, delay):
        # Acquire lock → compute elapsed = now - _last.get(domain, 0)
        # Sleep for (delay - elapsed) if positive
        # Release lock → update _last[domain] = now
```

- Thread-safe via `threading.Lock`
- Sleep granularity: `time.sleep()` with fractional seconds
- Domain keys are normalized `urlparse(url).netloc` values

**Stop Signaling:**
- `threading.Event` stored as `self._stop_event`
- All loops check `self.running` (`not self._stop_event.is_set()`) at each iteration
- `stop()` calls `self._stop_event.set()` → all threads exit at next check point
- Mid-download stop: partial files are deleted via `os.remove(file_path)` before returning

## 5.4 Deduplication & Resume [AI Engineer]

**_StateDB Class** (`scraper_engine.py:467`):

- SQLite database file: `{output_dir}/.scraper_dedup.db`
- Connection per thread via `threading.local()` with `check_same_thread=False`
- WAL journal mode (`PRAGMA journal_mode=WAL`) for concurrent read/write access

**Schema (DDL):**

```sql
CREATE TABLE IF NOT EXISTS seen_urls (
    url     TEXT PRIMARY KEY,
    status  TEXT,       -- 'queued', 'downloaded', 'exists', 'skipped_size', 'skipped_type', 'skipped_small', 'timeout', 'error'
    ts      TEXT        -- ISO timestamp (datetime.utcnow().isoformat())
);

CREATE TABLE IF NOT EXISTS downloaded (
    path     TEXT PRIMARY KEY,
    url      TEXT,
    supplier TEXT,
    ts       TEXT        -- ISO timestamp
);
```

**Method signatures:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(db_path: str)` | Creates DB, calls `_init_schema()` which runs `CREATE TABLE IF NOT EXISTS` |
| `_conn` | `() -> sqlite3.Connection` | Returns thread-local connection; creates if missing, sets WAL mode on first call |
| `is_seen` | `(url: str) -> bool` | `SELECT 1 FROM seen_urls WHERE url=?` |
| `mark_seen` | `(url: str, status="queued")` | `INSERT OR IGNORE INTO seen_urls` |
| `update_status` | `(url: str, status: str)` | `UPDATE seen_urls SET status=?,ts=? WHERE url=?` |
| `is_downloaded` | `(path: str) -> bool` | `SELECT 1 FROM downloaded WHERE path=?` |
| `mark_downloaded` | `(path: str, url: str, supplier: str)` | `INSERT OR REPLACE INTO downloaded` |
| `close` | `() -> None` | Closes thread-local connection if present |

**Dedup Flow:**

1. **Before downloading:** `state_db.is_seen(pdf_url)` — skip if URL already exists in `seen_urls` with any status
2. **Before saving:** `state_db.is_downloaded(file_path)` — skip if path already recorded in `downloaded`
3. **On download success:** `state_db.mark_downloaded(file_path, pdf_url, supplier)` + `state_db.update_status(pdf_url, "downloaded")`

## 5.5 Document Discovery Pipeline [AI Engineer]

Each supplier is crawled in the following discovery order. The chain **stops at the first method that yields results** — if the sitemap produces PDFs, search and recursive walk are skipped.

```
  _crawl_supplier(supplier, url, domain, ...)
         │
         ▼
  ┌──────────────────────┐
  │ 1. Sitemap Discovery │  ← cfg["use_sitemap"] must be True
  │  _discover_via_site- │     (default: True)
  │  map(base_url,       │
  │      domain, session,│
  │      cfg)            │
  └──────────┬───────────┘
             │
      PDFs found? ──yes──→ download each → DONE
             │
            no
             │
             ▼
  ┌──────────────────────┐
  │ 2. Search Engine     │  ← cfg["use_search"] must be True AND
  │    Discovery         │     _HAS_WEB_SEARCHER must be True
  │  _discover_via_search│     (default: True)
  │  (domain, supplier)  │
  └──────────┬───────────┘
             │
      PDFs found? ──yes──→ download each → DONE
             │
            no
             │
             ▼
  ┌──────────────────────┐
  │ 3. Recursive Link-   │  ← cfg["use_recursive"] must be True
  │    Walking (last     │     (default: True)
  │    resort)           │
  │  _crawl_recursive(   │
  │  url, vendor_folder, │
  │  supplier, domain,   │
  │  session, state_db,  │
  │  cfg, visited, depth)│
  └──────────┬───────────┘
             │
             ▼
  Done (may have found 0..N PDFs)
```

**Discovery 1 — Sitemap Discovery** (`_discover_via_sitemap`, line 1437):

1. Fetch `robots.txt` from domain root → extract `Sitemap:` directives
2. If robots.txt has no sitemaps, try common paths: `/sitemap.xml`, `/sitemap_index.xml`
3. Parse sitemap XML with `BeautifulSoup(resp.content, "xml")`, extract all `<loc>` elements ending in `.pdf`
4. Rate-limited per request via `self._rate_limiter.wait(domain, cfg["delay"])`

**Discovery 2 — Search Engine Discovery** (`_discover_via_search`, line 1559):

1. Build query: `f"site:{domain} filetype:pdf"`
2. Call `search_duckduckgo(query, timeout=10, max_results=30)`
3. Filter results: must end with `.pdf` and contain domain
4. Fallback: if DuckDuckGo returns zero results, try `search_bing(query, timeout=10, max_results=30)` with same filter
5. Never touches the supplier's own web server

**Discovery 3 — Recursive Link-Walking** (`_crawl_recursive`, line 1617):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_depth` | `2` (from `DEFAULT_SITE_CONFIG`) | Max link depth from homepage |
| `max_pages` | `50` (from `DEFAULT_SITE_CONFIG`) | Hard cap on total pages visited |
| Links per depth | `10` (hardcoded `page_links[:10]`) | Max page links followed at each depth level |

- Starts from the supplier's homepage URL
- Parses HTML with `BeautifulSoup(resp.content, "html.parser")`
- Collects `<a href>` links: same-domain PDFs go to download queue; same-domain HTML pages go to recursive crawl stack
- Rejects `#`, `mailto:`, `tel:` links and cross-domain URLs
- If the visited URL itself is a `.pdf`, downloads it immediately (no deeper crawl)
- `_validate_url()` check applied before each request

## 5.6 PDF Relevance Filtering [AI Engineer]

**_score_pdf_relevance(url, anchor_text="") → tuple[bool, str]** (`scraper_engine.py:323`):

Combines URL and anchor text into a single lowercase string, then tests against two compiled regex patterns.

**Blocklist regex** (`_PDF_BLOCKLIST`, line 265) — if matched, returns `(False, "blocklist_match")`:

Patterns (all case-insensitive, `re.IGNORECASE`):
```
terms[_-\s]?of[_-\s]?(use|service)   privacy[_-\s]?policy     cookie[_-\s]?policy
warranty                               return[_-\s]?policy      refund
invoice                                receipt                  purchase[_-\s]?order
msds                                   sds                      safety[_-\s]?data
material[_-\s]?safety                  annual[_-\s]?report      financial[_-\s]?report
10\-?k                                10\-?q                    press[_-\s]?release
newsletter                             whitepaper               case[_-\s]?study
compliance                             regulatory               iso[_-\s]?cert
certificate[_-\s]?of                   nda                      agreement
contract                               legal                    disclaimer
map                                    directions               parking
exhibit[_-\s]?hall                     irs                      tax
form[_-\s]?(w2|1040|1099|941|940|990|k1|ct[_\-]?1)
w\-?2                                 1099                     941
940                                   990                      k\-?1
ct[_\-]?1                              earnings                 payroll
deduction                              withhold                 federal
state[_-\s]?tax
```

**Allowlist regex** (`_PDF_ALLOWLIST`, line 295) — if matched, returns `(True, "allowlist_match")`:

Patterns (all case-insensitive, `re.IGNORECASE`):
```
catalog             catalogue            datasheet
data[_\-]?sheet     spec(ification)?s?   product[_\-]?(guide|list|range|brochure|sheet|info|overview)
price[_\-]?list     pricelist            part[_\-]?list
parts[_\-]?list     technical            install(ation)?
manual               guide               brochure
ifu                  instructions?       accessory
accessories          selection[_\-]?guide flyer
bulletin            literature           resource
quickstart          quick[_\-]?start     user[_\-]?guide
reference[_\-]?guide operator[_\-]?manual service[_\-]?manual
maintenance         setup                configuration
protocol            application[_\-]?note app[_\-]?note
tech[_\-]?note
```

If neither regex matches, returns `(True, "default_allow")` — **permissive by default**.

**_should_download(pdf_url, anchor, supplier="") → tuple[bool, str]** (`scraper_engine.py`):

Decision logic (updated 2026-07-09):

1. If `self.use_relevance_filter` is `False` → `(True, "filter_disabled")`
2. Call `_score_pdf_relevance(url, anchor_text)`:
   - If blocklist matches → `(False, "blocklist_match")`
   - If allowlist matches → proceed
3. If `self.allowlist_only` is `True` AND result was `"default_allow"` (neither regex matched) → `(False, "no_allowlist_match")`
4. **Supplier keyword filter** (if `self.supplier_keywords` is non-empty AND `supplier` is non-empty):
   - Look up `supplier.lower()` in `self.supplier_keywords`
   - **Fail closed:** supplier NOT in the dict → `(False, "no_supplier_keywords")`
     (logged once per supplier). A supplier with no item descriptions has
     nothing that can be judged relevant.
   - Match text = **full URL path + anchor text** (not just the filename —
     product identity often lives in the folder path or link text),
     lowercased, `/ - _` converted to spaces, extension stripped
   - Keyword matching via `_keywords_match()`: tokens < 5 chars require an
     exact word match ("kit", "lab"); tokens ≥ 5 chars match as substrings
     ("microscope" matches "microscopes")
   - If no keyword matches → `(False, "no_keyword_match")`
5. Passes all checks → return `(True, reason)`

**CSV-vendor guardrail** (in `run()`, before the freshness filter): when
`supplier_keywords` is loaded, master-list suppliers with no rows in the
input CSVs are dropped from the crawl list entirely (warning names them).
Only vendors present in the input CSVs are crawled. An empty keyword dict
(standalone use) disables the guardrail.

## 5.7 Download Pipeline [AI Engineer]

All download operations flow through `_download_pdf()` (line 1865).

**URL Validation** (`_validate_url`, line 351):

- Scheme must be `http` or `https`
- Hostname must contain at least one dot (`.`) — rejects bare hostnames
- Explicitly blocks `localhost` and `127.0.0.1` in hostname
- Returns `False` on any exception

**Path Sanitization** (`_sanitize_path`, line 381):

```python
path = path.replace("..", "").replace("/", "_").replace("\\", "_")
for ch in '<>:"|?*':
    path = path.replace(ch, "_")
```

- Removes directory traversal sequences (`..`)
- Converts path separators (`/`, `\`) to underscores
- Replaces Windows-invalid filename characters (`< > : " | ? *`) with underscores

**HEAD Pre-check** (lines 1959-1993):

1. Sends `HEAD` request with `allow_redirects=True`
2. Checks `Content-Length` header: if `int(cl) > max_pdf_size_mb * 1024 * 1024` → skip with `"skipped_size"`
3. If `strict_content_validation` is `True` AND `"pdf" not in ct` AND URL doesn't end with `.pdf` → skip with `"skipped_type"`
4. On HEAD failure (timeout, connection error, etc.) → **proceeds to GET anyway** (graceful degradation)

**Full Download with Streaming** (updated 2026-07-09):

1. `requests.get(pdf_url, stream=True, timeout=self.page_timeout)`
2. Re-checks `Content-Type` and `Content-Length` on response headers
3. **Magic-byte check**: the first streamed chunk must contain `%PDF` within
   its first 1024 bytes, otherwise reject with `"rejected_not_pdf"` before
   anything touches disk (catches HTML error/login pages served at `.pdf`
   URLs, independent of `strict_content_validation`)
4. `iter_content(chunk_size=8192)` loop:
   - Checks `self.running` at every chunk → deletes partial file on stop
   - Tracks `downloaded` byte count; if exceeds `max_bytes` → deletes file, marks `"skipped_size"`
5. Post-download validation, in order:
   - `os.path.getsize(file_path) < self.min_pdf_size_bytes` → delete, mark `"skipped_small"`
   - **Content-hash dedup**: SHA-256 via `_file_hash()`; if the hash exists in
     the state DB `hashes` table → delete, mark `"duplicate"` (same catalog
     PDF served at several URLs is kept once)
   - **First-page content check** (`_content_relevant()`): page-1 text
     (pdfplumber) must contain ≥ 1 supplier keyword → else delete, mark
     `"rejected_content"`. Fails open when the supplier has no keywords,
     pdfplumber is unavailable, or the PDF has no text layer (scanned docs
     are judged later by Stage 3)
6. On success: `state_db.mark_downloaded(...)` + hash recorded + `state_db.update_status(pdf_url, "downloaded")`
7. `self.pdf_count += 1` (under `self._count_lock`)

## 5.8 7-Day Freshness System [Both]

**State file** (`.scraper_state.json`, stored in `output_dir`):

```json
{
  "Thermo Fisher Scientific": "2026-06-29T10:30:00",
  "Agilent Technologies": "2026-07-01T14:15:00",
  ...
}
```

Format: `{supplier_name: ISO_timestamp}` — flat JSON object, one entry per crawled supplier.

**_is_due(supplier_name, state_dict) → bool** (line 981):

1. Look up `supplier_name` in the state dict
2. If not found → `True` (due — needs crawling)
3. If found → parse `datetime.fromisoformat(state[name])` → compute `(datetime.utcnow() - last).days`
4. Return `days >= self.days_before_rescrape` (default 7)
5. If `self.skip_recent_sites` is `False` → all suppliers are due regardless (this filter is applied before `_is_due` is called, in the `run()` method)
6. Parse errors → return `True` (conservative: crawl on bad data)

**State Update Flow** (in `_domain_worker`, line 1297):

After successfully crawling a supplier, `scrape_state[supplier] = datetime.utcnow().isoformat()` is set on the shared dict. The full dict is written to disk once after all workers complete.

**Atomic Update Pattern** (`_save_scrape_state`, line 957):

1. Deep-copy the in-memory state dict (not formally deep-copied; mutated in-place then saved)
2. Write to `.scraper_state.json.tmp` (temp file in same directory)
3. If the target `.scraper_state.json` exists, `os.remove(p)` first
4. `os.rename(tmp, p)` — atomic rename on the same filesystem
5. On crash: state file is either completely old or completely new — never corrupted (the `.tmp` file may remain; it is ignored on next load)

**Freshness filter application** (in `run()`, line 1127-1135):

```python
if self.skip_recent_sites:
    pairs = [(n, u) for n, u in pairs if self._is_due(n, scrape_state)]
```

If all suppliers are up to date, `run()` returns `{"pages": 0, "pdfs": 0, "suppliers": 0}` immediately without spawning any threads.

## 5.9 Supplier List Loading [Architect]

**_load_supplier_pairs(supplier_excel) → list[tuple[str, str]]** (line 1007):

1. Reads Excel via `pd.read_excel(supplier_excel, engine="openpyxl")`
2. Strips whitespace from all column names via `df.columns = [str(c).strip() for c in df.columns]`
3. **Column detection** (fuzzy match):
   - Name column: try column with `"supplier"` AND `"name"` in name → fallback to column with `"supplier"` in name
   - URL column: column with `"website"` or `"url"` in name
4. Iterates rows, builds `(name, url)` tuples:
   - Skips rows where name or url is empty/None/`"nan"`
   - Prepends `https://` if URL lacks scheme
   - Validates URL via `_validate_url()` (drops invalid URLs with warning)
5. Returns list of valid `(supplier_name, website_url)` pairs

**Supplier keyword loading** (in `pipeline.py:281`):

`load_supplier_keywords(input_dir)` reads all CSV files from the input directory:

1. Lists all `*.csv` files in `input_dir` via `Path(input_dir).glob("*.csv")`
2. For each CSV: reads with `pd.read_csv()`, expects columns `"Supplier Name"` and `"Item Description"`
3. Groups keyword tokens by supplier name (lowercased)
4. Token extraction via `_extract_keyword_tokens(description)` (updated 2026-07-09):
   - Removes non-alphanumeric characters (except hyphens) via `re.sub(r'[^\w\s\-]', ' ', text)`
   - Filters through `_STOP_WORDS` frozenset (~60 words: articles, prepositions, common verbs, quantifiers)
   - Rejects ALL tokens < 3 characters, and bare numbers < 4 digits
     (`"2"`, `"10"`, `"100"` used to match every PDF filename as substrings;
     real part numbers are 4+ chars)
   - Adds hyphen-stripped variants (e.g., `"920-2"` → also adds `"9202"`)
5. Returns `dict[str, list[str]]` — e.g., `{"thermo fisher scientific": ["spectrometer", "microscope", ...]}`

**Post-construction assignment** (pipeline.py:566-568):

```python
supplier_keywords = load_supplier_keywords(input_excel_dir)
engine.supplier_keywords = supplier_keywords
```

The keyword dict is NOT passed via the constructor — it is set as an attribute directly after construction.

## 5.10 Per-Site Configuration [AI Engineer]

**DEFAULT_SITE_CONFIG** (`scraper_engine.py:643`):

```python
DEFAULT_SITE_CONFIG = {
    "delay": 2.0,           # seconds between requests to this domain
    "max_pages": 50,        # hard cap on link-walk pages
    "use_sitemap": True,    # attempt sitemap discovery
    "use_search": True,     # attempt filetype:pdf search discovery
    "use_recursive": True,  # fall back to recursive link-walking
    "max_depth": 2,         # recursive crawl depth
}
```

**Per-site JSON file** (`_load_site_configs`, line 663) — optional, loaded from path passed via `site_config_path`:

```json
{
  "example.com": {
    "delay": 5.0,
    "max_pages": 100,
    "use_sitemap": true,
    "use_search": true,
    "use_recursive": false,
    "max_depth": 3
  },
  "slow-site.net": {
    "delay": 10.0,
    "max_pages": 20
  }
}
```

**Merge order** (`_site_cfg`, line 705):

1. Start with `dict(DEFAULT_SITE_CONFIG)` — copies all defaults
2. `base.update(overrides.get(domain, {}))` — override with per-site values for matching domain
3. Per-site file is optional; if path is `None` or file doesn't exist, returns `{}` (no overrides)
4. Any key not in the per-site entry uses the DEFAULT value

## 5.11 Camofox Integration (Optional) [AI Engineer]

- **Best-effort import:** No import — the Camofox integration is always compiled in. At runtime, `_check_page_keywords()` (line 191) sends a POST to `http://localhost:8000/api/browse` with `{"url": url}`.
- Camofox availability is determined by connection success (not ImportError).
- Response: expects JSON with `snapshot` field → page text is checked against `self.keywords` loaded from `hardware_keywords_ACTIVE.txt` and `software_keywords_ACTIVE.txt`.
- If any keyword is found in the snapshot text → page passes (return `True`).
- **Fallback on failure:** Connection refused (`requests.exceptions.ConnectionError`) or any exception → return `True` (allow page). The system never blocks a page because Camofox is unavailable.
- **Disabled by default:** `use_keyword_filter` defaults to `True`, but `self.keywords` is empty unless the Camofox keyword files exist.

## 5.12 Known Quirks & Edge Cases [AI Engineer]

- **sys.path hack** (lines 117-125): `sys.path` is modified at import time to insert the supplier resolution module directory, enabling `from web_searcher import search_duckduckgo, search_bing`. This is a side effect — importing `scraper_engine.py` mutates the global module search path.
- **supplier_keywords**: Set as an attribute after construction (`engine.supplier_keywords = loaded_dict`), NOT via the constructor. The `supplier_keywords` constructor parameter defaults to `None` and is converted to `{}` if not provided, but the real keyword data is loaded by `pipeline.py` and assigned externally.
- **10-link cap per depth level**: Link-walking caps at `page_links[:10]` — only 10 HTML links are followed at each depth level, which limits coverage but prevents explosion on large sites.
- **TMP→RENAME pattern**: State file writes to `.scraper_state.json.tmp` first, then removes the target and renames. The `os.remove(p)` before rename means there is a brief window with no state file at all (not truly atomic), but the `.tmp` approach prevents half-written corruption.
- **Supplier name normalization**: SQLite dedup uses raw supplier names as keys (from the Excel file), but directory names on disk use the same raw names. If supplier names differ between runs (whitespace, casing), both the dedup and directory lookup may produce duplicates.
- **HEAD → GET fallback**: If the HEAD request fails (timeout, connection error), the pipeline proceeds with the full GET anyway. This means oversized or non-PDF files may only be caught mid-stream.
- **No SHA-256 dedup in download path**: The `_file_hash()` function exists at module level but is never called by `_download_pdf`. File-level hash dedup is not actually performed — only path-based dedup via `state_db.is_downloaded(file_path)`.
- **`_count_lock` scope**: The `page_count` and `pdf_count` counters are protected by `self._count_lock`, but `page_count` is incremented inside `_crawl_recursive` (line 1667) while `pdf_count` is incremented inside `_download_pdf` (line 2092). Both use `with self._count_lock:`, but the lock is reentrant-safe since it's a standard `threading.Lock`.
- **Web searcher import may fail silently**: If `web_searcher` cannot be imported (e.g., dependencies missing), `_HAS_WEB_SEARCHER` is set to `False`, and search-based discovery is silently skipped for all suppliers.
- **Per-thread SQLite collisions**: `_StateDB._conn()` creates a new connection per thread via `threading.local()`. The WAL mode allows concurrent reads but concurrent writes from multiple domain workers may still encounter `SQLITE_BUSY`. The code does not implement a retry loop for busy conditions.

## 5.13 Config Keys Consumed [Architect]

From `pipeline_config.json` — all keys under `scraper.*`, plus path keys:

| Config Key | Type | Default | Maps To |
|-----------|------|---------|---------|
| `paths.supplier_excel` | string | (configurable — see Path Reference doc) | `run(supplier_excel, ...)` |
| `paths.pdf_dir` | string | (configurable — see Path Reference doc) | `run(..., output_dir)` |
| `paths.input_excel_dir` | string | (configurable — see Path Reference doc) | Used by `pipeline.py` to call `load_supplier_keywords()` |
| `scraper.page_timeout` | int | `15` | `ScraperEngine(page_timeout=...)` |
| `scraper.max_pdf_size_mb` | int | `100` | `ScraperEngine(max_pdf_size_mb=...)` |
| `scraper.min_pdf_size_bytes` | int | `512` | `ScraperEngine(min_pdf_size_bytes=...)` |
| `scraper.strict_content_validation` | bool | `false` | `ScraperEngine(strict_content_validation=...)` |
| `scraper.verbose` | bool | `false` | `ScraperEngine(verbose=...)` |
| `scraper.skip_recent_sites` | bool | `true` | `ScraperEngine(skip_recent_sites=...)` |
| `scraper.days_before_rescrape` | int | `7` | `ScraperEngine(days_before_rescrape=...)` |
| `scraper.allowlist_only` | bool | `true` | `ScraperEngine(allowlist_only=...)` |
| `scraper.request_delay` | float | `2.0` | Part of `DEFAULT_SITE_CONFIG["delay"]` |
| `scraper.max_pages_per_site` | int | `50` | Part of `DEFAULT_SITE_CONFIG["max_pages"]` |
| `scraper.max_concurrent` | int | `3` | Historical — not consumed by current code (all domains run concurrently)

---

# Section 6: Stage 2 — Classification [Both]

## 6.1 Purpose & Data Flow

- **Input:** Cleaned supplier requisition Excel/CSV files from the input directory
- **Processing:** Classifies each line item as one of 3 categories using keyword scoring + context rules
- **Output:** Labeled Excel files with `Type` column, written to the labeled directory
- **Runtime:** ~2-5 minutes

## 6.2 Dual-Implementation Architecture [Architect]

There are **two** classification implementations that run independently:

| Aspect | Classifier A: AdaptiveExcelProcessor | Classifier B: ColumnFilterClassifyV3 |
|--------|--------------------------------------|--------------------------------------|
| **Module** | `classify/adaptive_excel_processor.py` | `data-cleaning/column_filter_and_classify_v3.py` |
| **Lines** | 1,458 | 273 |
| **Used by pipeline?** | No (standalone / Windows service) | Yes (pipeline Stage 2 entry via `process_all_inputs()`) |
| **Algorithm** | Priority chain of signal tables | Keyword vote counting + 3 context rules |
| **Self-learning** | Yes — keyword promotion with confidence scoring | No |
| **Output suffix** | `_labeled.xlsx` | `_classified_v3.xlsx` |
| **Type column value** | `"Research Instrument"` / `"Software"` / `"Non-Instrument"` / `"Unknown"` | `"Instrument"` / `"Software"` / `"Non-Instrument"` / `"Unknown"` |
| **Column discovery** | Heuristic column name matching (`find_description_column`, `find_supplier_column`) | Fixed position-based mapping with name-based fallback |

## 6.3 Classifier A: AdaptiveExcelProcessor [AI Engineer]

### 6.3.1 Constructor Signature

```python
def __init__(
    self,
    hw_keywords_file=None,
    sw_keywords_file=None,
    ni_keywords_file=None,
    output_dir=None,
    learning_mode=True,
    min_occurrences=5,
    confidence_threshold=0.7
)
```

Instance variables initialized:
- `self.hw_keywords, self.sw_keywords, self.ni_keywords` — empty lists, populated by `load_keywords()`
- `self.candidate_keywords` — `{'hw': Counter(), 'sw': Counter(), 'ni': Counter()}` — learning accumulation
- `self.learning_log` — Path to `learning_log.json` in `output_dir`
- `self.stopwords` — 37 hardcoded stopwords (common English + procurement terms like `model`, `part`, `serial`, `unit`, `each`, etc.)
- `self.technical_indicators` — 18 terms: `meter`, `analyzer`, `spectrometer`, `chromatograph`, `microscope`, `detector`, `sensor`, `instrument`, `measurement`, `analysis`, `testing`, `calibration`, `precision`, `accuracy`, `resolution`, `sensitivity`, `monitor`, `controller`, `regulator`, `transducer`, `transmitter`
- `self.units` — 20 measurement units: `cu`, `ft`, `volts`, `watts`, `amps`, `hertz`, `pounds`, `inches`, `mm`, `cm`, `kg`, `g`, `mg`, `ml`, `l`, `gal`, `psi`, `bar`, `pa`, `celsius`, `fahrenheit`, `kelvin`, `rpm`, `hz`, `db`, `lux`

### 6.3.2 Classification Priority Chain

The `classify_item(description, vendor=None)` method applies rules in strict order — first match wins:

1. **Vendor name match** — `classify_by_vendor(vendor)` checks supplier name against `vendor_keywords` tables (HW→Research Instrument, SW→Software, NI→Non-Instrument). Triggers `_learn_from_classification()` if learning is enabled.
2. **Furniture signals** — checks description for furniture-related terms → Non-Instrument
3. **Consumable signals** — checks description for consumable/supply terms → Non-Instrument
4. **Service signals** — checks description for service/maintenance terms → Non-Instrument
5. **Strong software signals** — checks for strong software keyword matches → Software
6. **Strong hardware signals** — checks for strong instrument keyword matches → Research Instrument
7. **Default: Unknown** — falls through if no signals match

### 6.3.3 Signal Keyword Tables (defined as inline lists in `classify_item`)

**vendor_keywords (hw):** `thermo fisher scientific`, `agilent technologies`, `waters corporation`, `beckman coulter`, `bio-rad laboratories`, `qiagen`, `promega`, `zeiss`, `leica microsystems`, `olympus`, `eppendorf`, `sartorius`, `applied biosystems`, `illumina`, `roche`, `abbott`

**vendor_keywords (sw):** `microsoft`, `adobe`, `autodesk`, `mathworks`, `graphpad`, `spss`, `oracle`, `salesforce`, `tableau`

**vendor_keywords (ni):** `empire office inc`, `office depot`, `staples`, `amazon business`, `steelcase`, `herman miller`, `knoll`, `haworth`, `humanscale`, `ups`, `fedex`, `dhl`

**furniture_signals:** `cabinet`, `desk`, `table`, `chair`, `shelf`, `shelving`, `storage`, `steelcase`, `worksurface`, `tackboard`, `end panel`, `desk legs`, `ufb bracket`, `light shelf`, `led`, `locks`, `furniture`, `bench`

**consumable_signals:** `kit`, `reagent`, `consumable`, `tube`, `tip`, `plate`, `vial`, `filter`, `cable`, `adapter`, `power supply`, `battery`, `rack`, `stand`, `mount`, `holder`, `box`, `bottle`, `accessory`, `part`

**service_signals:** `service`, `installation`, `calibration`, `shipping`, `delivery`, `training`, `support`, `maintenance`, `repair`, `consulting`

**strong_sw_signals (18):** `software`, `license`, `licence`, `subscription`, `activation`, `key`, `matlab`, `labview`, `flowjo`, `graphpad`, `prism`, `imagej`, `zen`, `microsoft`, `adobe`, `autodesk`, `solidworks`

**strong_hw_signals (22):** `microscope`, `spectrometer`, `chromatograph`, `centrifuge`, `incubator`, `autoclave`, `pcr`, `thermocycler`, `flowcytometer`, `plate reader`, `imager`, `imaging`, `luminometer`, `sonicator`, `electrophoresis`, `transilluminator`, `bioreactor`, `analyzer`, `balance`, `tem`, `sem`, `nmr`

### 6.3.4 Rule-Based Classification Logic (Decision Tree)

The `classify_item` method implements a winner-takes-all decision tree:

```
vendor = classify_by_vendor(supplier_name)
IF vendor IS NOT None → RETURN vendor (HW→"Research Instrument", SW→"Software", NI→"Non-Instrument")

description_lower = description.lower()

IF any(furniture_signal in description_lower) → RETURN "Non-Instrument"
IF any(consumable_signal in description_lower) → RETURN "Non-Instrument"
IF any(service_signal in description_lower) → RETURN "Non-Instrument"
IF any(strong_sw_signal in description_lower) → RETURN "Software"
IF any(strong_hw_signal in description_lower) → RETURN "Research Instrument"

RETURN "Unknown"
```

Each non-fallthrough branch calls `_learn_from_classification(description, category)` when `self.learning_mode=True`, which extracts keywords from the description and increments their confidence-weighted counter in `self.candidate_keywords[category]`.

### 6.3.5 Self-Learning System

**`extract_keywords_from_description(description) → list[str]`:**
1. Return `[]` if `None`, `pd.isna()`, or not a string
2. Lowercase the description
3. Strip model numbers: `re.sub(r'\b[A-Z0-9\-]{6,}\b', '', desc_clean)` — removes tokens like `MDF-C2156VANC-PA`
4. Strip measurements: `re.sub(r'\b(?:\d+|\d+\.\d+)\s*(cu\.ft\.|volts?|v|w|a|hz|rpm|db|lux|psi|bar)\b', '', desc_clean)`
5. Split on whitespace
6. For each word: strip punctuation `.,;:()[]{}'"-`, keep if `len >= 3`, not a stopword, not `isdigit()`, not in `self.units`, not matching `^\d+[a-z]*$`
7. Return remaining tokens

**`calculate_keyword_confidence(keyword, description) → float`:**
| Step | Condition | Multiplier |
|------|-----------|-----------|
| Start | Always | 1.0 |
| Technical context | `any(indicator in description for indicator in self.technical_indicators)` | × 1.5 |
| Common word | keyword in `{'system', 'device', 'equipment', 'machine', 'tool', 'unit'}` | × 0.5 |
| Compound technical term | `len(keyword) > 8` AND any tech suffix in keyword (`meter`, `scope`, `graph`, `analyzer`) | × 1.3 |
| Short word | `len(keyword) < 4` | × 0.7 |
| Long word | `len(keyword) > 20` | × 0.8 |
| Cap | Returns `min(confidence, 3.0)` | — |

**`validate_keyword(keyword, category) → tuple[bool, str]`:**

| Condition | Returns |
|-----------|---------|
| `len(keyword) < 3` | `(False, "Too short")` |
| keyword in `self.units` | `(False, "Measurement unit")` |
| `re.match(r'^[a-z0-9\-]{2,}$', keyword)` AND `len > 6` | `(False, "Model number pattern")` |
| `re.match(r'^\d+[a-z]*$', keyword)` | `(False, "Number pattern")` |
| keyword in `self.stopwords` | `(False, "Common stopword")` |
| any technical indicator in keyword (`meter`, `scope`, `graph`, `analyzer`, `detector`, `sensor`) | `(True, "Technical term")` |
| `4 <= len(keyword) <= 15` | `(True, "Valid keyword")` |
| Otherwise | `(False, "Failed validation")` |

**`promote_candidate_keywords(min_occurrences=None) → tuple[dict, dict]`:**

1. For each category `['hw', 'sw', 'ni']`:
   - Iterate `self.candidate_keywords[category].items()`
   - If `count >= min_occurrences` AND keyword not already in the keyword list:
     - `validate_keyword(keyword, category)`
     - If valid → append to `keywords_list`, record in `promoted[category]`
     - If invalid → record in `rejected[category]`
2. If any promotions exist: call `backup_keywords_before_update()` to create timestamped copies in `output_dir/#backup_logs/`
3. Write updated keyword files via `_save_keywords(file_path, sorted(keywords))`
4. Return `(promoted, rejected)`

**`backup_keywords_before_update()`:** Creates timestamped backups of all 3 keyword files in `output_dir / "#backup_logs" / f"{name}_keywords_backup_{YYYYMMDD_HHMMSS}.txt"`.

**`learning_log.json` schema:**

```json
{
  "hw_candidates": {"microscope": 12, "centrifuge": 8},
  "sw_candidates": {"license": 15},
  "ni_candidates": {"glove": 20},
  "last_updated": "2026-07-06T10:30:00",
  "settings": {
    "min_occurrences": 5,
    "confidence_threshold": 0.7,
    "learning_mode": true
  }
}
```

### 6.3.6 File Processing Pipeline

`process_file(file_path, auto_promote=True, min_occurrences=None, test_mode=False) → bool`:

1. **`should_process(file_path)`** — returns `False` if filename starts with `~$` (temp file) or ends with `_labeled` (already processed). Only processes `.xls`, `.xlsx`, `.csv`.
2. **Read file** — `read_excel_file(file_path)`: CSV → pandas + `chardet` encoding detection; `.xls` → `xlrd` engine; `.xlsx` → `openpyxl` engine
3. **Find columns** — `find_description_column(df)`: priority search for `description` in column name, fallback to `desc`, `item`, `name`, `title`, `product`, `material`. **`find_supplier_column(df)`: priority search for `supplier`, fallback to `vendor`, `company`, `manufacturer`, `distributor`, `source` — returns `None` if not found.
4. **`clean_dataframe(df)`** — drops columns by position indices: `[0..6)`, `[7]`, `[9..13)`, `[15..32)` if within range
5. **Classify each row** — `df.apply(lambda row: self.classify_item(desc, supplier), axis=1)` with learning accumulation
6. **Auto-promote** — `promote_candidate_keywords(min_occurrences)` if `auto_promote=True` and `learning_mode=True` and `test_mode=False`
7. **Save learning log** — `save_learning_log()` writes `learning_log.json`
8. **Save labeled output** — `df.to_excel(output_dir / f"{stem}_labeled.xlsx", index=False)`

`process_directory(directory_path, auto_promote=True, min_occurrences=None, test_mode=False) → int`:
- Iterates `*.xls`, `*.xlsx`, `*.csv` in directory
- Calls `process_file()` for each with `auto_promote=False` (defers promotion to batch end)
- After all files: calls `promote_candidate_keywords()` once, saves learning log, prints learning report
- Returns file count

## 6.4 Classifier B: ColumnFilterClassifyV3 [AI Engineer]

### 6.4.1 Column Position Mapping

| Logical Name | Excel Column | Index (0-based) | Notes |
|-------------|-------------|----------------|-------|
| Req ID | B | 1 | — |
| Supplier ID | F | 5 | — |
| Supplier Name | G | 6 | Used for Rule B supplier DB matching |
| Item Description | I | 8 | Primary classification text |
| Req Line Item | O | 14 | Concatenated with description for keyword matching |

Column detection falls back to name-based matching if position-based mapping fails (i.e., `len(df.columns) < max(col_indices) + 1`).

### 6.4.2 Keyword Conflict Removal Algorithm

`load_and_clean_keywords() → tuple[set, set, set]`:

1. Load all 3 keyword lists from files in the keywords directory (`research_instrument_keywords.txt`, `software_keywords.txt`, `non_instrument_keywords.txt`) — one keyword per line, stripped, lowered
2. Compute intersections: `hw ∩ sw`, `hw ∩ ni`, `sw ∩ ni`, `hw ∩ sw ∩ ni`
3. Remove ALL keywords found in any intersection from ALL lists
4. Also remove keywords that are `< 4` chars AND purely alphabetic AND not in the exception set `{"pcr", "nmr", "gc", "lc", "rna", "dna"}`
5. Result: each keyword belongs to exactly ONE category — no ambiguity between lists

### 6.4.3 `classify_item()` Vote Thresholds

```python
def classify_item(req_line: str, item_desc: str, hw_kw: set, sw_kw: set, ni_kw: set) -> str:
    text = (str(req_line) + " " + str(item_desc)).lower()
    hw_score = sum(1 for kw in hw_kw if kw in text)
    sw_score = sum(1 for kw in sw_kw if kw in text)
    ni_score = sum(1 for kw in ni_kw if kw in text)

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
```

Priority order: Instrument > Software > Non-Instrument. Instrument requires 2+ matches (high bar) OR exactly 1 match (lower bar fallback). Software and Non-Instrument require 1+ match with a comparative > check against each other.

### 6.4.4 Rule A: Prior Context

Applied AFTER initial classification pass. For each group of items sharing the same Req ID (column B):
- Iterate group in order; for each item with index `i > 0`:
  - If `previous.Type == "Instrument"` AND `current.Type == "Unknown"` → reclassify current as `"Instrument"`
- Rationale: Items within the same requisition tend to belong to the same category

### 6.4.5 Rule B: Supplier Metadata Context

Applied AFTER Rules A and C (actual execution order: A → C → B). Loads supplier classification DB from `supplier_classification.json` via `load_supplier_classification()`.

DB discovery path (tried in order):
1. The supplier classification database at the project root
2. Relative lookup in `src/docs/`
3. Relative lookup in `docs/`

DB maps supplier names to a category string. For each `"Unknown"` item:
- If `supplier_db.get(supplier_name) in ["lab_equipment", "medical_equipment", "research_equipment"]` → reclassify as `"Instrument"`

### 6.4.6 Rule C: Bundle Analysis

Applied AFTER Rule A, BEFORE Rule B (actual execution order: A → C → B). For remaining `"Unknown"` items:
- Parse bundled descriptions by splitting on delimiters in order: `;` → `,` → `/`
- Take first segment after the first delimiter found
- If first segment is `> 5` chars AND does not start with a digit:
  - Re-classify the segment independently via `classify_item("", first_part, hw_kw, sw_kw, ni_kw)`
  - If result != `"Unknown"` → apply the new classification
- Rationale: Bundled descriptions often list multiple items; the first is usually the primary

Note: `filter_and_classify` also tracks rule application counts per file via `rule_a_count`, `rule_b_count`, `rule_c_count` variables.

## 6.5 Keyword File Format & Locations [Architect]

| File | Location | Purpose |
|------|----------|---------|
| `research_instrument_keywords.txt` | the keywords directory | Hardware/Instrument keywords |
| `software_keywords.txt` | the keywords directory | Software keywords |
| `non_instrument_keywords.txt` | the keywords directory | Non-instrument keywords |

**Format:** One keyword per line, plain UTF-8 text. Empty lines and lines starting with `#` (comments) are ignored.

**Config keys consumed** (from `pipeline_config.json`):
| Key | Maps to |
|-----|---------|
| `classify.hw_keywords_file` | the hardware/instrument keyword file |
| `classify.sw_keywords_file` | the software keyword file |
| `classify.ni_keywords_file` | the non-instrument keyword file |

## 6.6 Error Handling & Failure Modes [AI Engineer]

| Condition | Classifier A | Classifier B |
|-----------|-------------|-------------|
| Missing description column | `ValueError` raised listing first 10 available columns | Falls back to name-based column mapping; raises `ValueError` if column unresolvable |
| Missing supplier column | Returns `None` gracefully; vendor-based classification disabled | Fixed position (G→index 6); falls back if out of range |
| Empty keyword files | All items classify as `"Unknown"` (no keyword matches) | All items classify as `"Unknown"` (zero keyword scores) |
| `learning_log.json` not found | Silent fallback — empty `Counter()` objects initialized | N/A |
| Temp files (`~$`) | Silently skipped via `should_process()` | Not filtered; loaded by pandas (corrupt data, may crash) |
| Unreadable Excel | Exception propagates from `pd.read_excel()`; caught by `process_file()` → returns `False` | Exception propagates; caught by `process_all_inputs()` per-file handler |
| Corrupted keyword file (bad encoding) | Exception propagates from `Path.read_text()` in `load_keywords()` | `UnicodeDecodeError` from `open()` propagates up |
| No files in input directory | `process_directory()` returns 0 | `process_all_inputs()` prints `Found 0 files`, returns `{"files_processed": 0}` |

## 6.7 Config Keys Consumed [Architect]

From `pipeline_config.json`:

| Key | Used By | Purpose |
|-----|---------|---------|
| `paths.input_excel_dir` | Both | Input directory for raw Excel/CSV files |
| `paths.labeled_dir` | Both | Labeled output directory for classified files |
| `classify.learning_mode` | Classifier A | Enable/disable self-learning keyword promotion |
| `classify.min_occurrences` | Classifier A | Minimum occurrence count before keyword promotion (default: 5) |
| `classify.confidence_threshold` | Classifier A | Minimum confidence score for promotion (default: 0.7) |
| `classify.hw_keywords_file` | Both | Path to the hardware/instrument keyword file |
| `classify.sw_keywords_file` | Both | Path to the software keyword file |
| `classify.ni_keywords_file` | Both | Path to the non-instrument keyword file |

---

# Section 7: Stage 2b — Supplier Resolution [AI Engineer]

## 7.1 Purpose & Current Status [Both]

- **Purpose:** Find website URLs for suppliers that are not yet in the master supplier list, using web search
- **Status: DISABLED by default** (`pipeline_config.json: "pipeline.run_supplier_resolution": false`)
- When enabled, runs between Stage 2 (Classification) and Stage 3 (Cross-Reference)
- Searches DuckDuckGo and Bing for `"{supplier_name}" official website`
- Routes results: high-confidence (≥70) → appended to master list, low-confidence → pending review list

## 7.2 Module: supplier_resolver.py [AI Engineer]

**File:** `supplier_resolver.py` — 194 lines

**Entry point:** `resolve_suppliers(cfg) → bool`

- `cfg` keys consumed: `master_list`, `classified_excel` (resolved by pipeline), `supplier_resolution.*`
- Flow:
  1. Load master supplier list from Excel → `{uppercase_name: website}` dict
  2. Extract all unique supplier names from classified Excel files
  3. Identify which suppliers are NOT in the master list
  4. For each unknown supplier: search DuckDuckGo + Bing
  5. Score each found URL (0–110)
  6. Confidence ≥ threshold (70) → append to master list + resolved list
  7. Confidence < threshold → append to pending review list

**_load_master_list(path: str) → dict[str, str]:**
- Reads Excel via `pd.read_excel(path, usecols=["Supplier Name", "Website"])`
- Returns `{uppercase_name.strip(): website.strip()}` — only rows where both columns are non-empty

**_extract_suppliers(classified_excel: str) → list[str]:**
- Reads classified Excel (labeled output from Stage 2)
- Finds first column whose name contains `"supplier"` (case-insensitive)
- Extracts all unique supplier names, drops NaN, strips whitespace, uppercases
- Returns `list[str]` of unique uppercase names

**_append_to_pending(path: str, rows: list) → None:**
- If file exists, loads workbook and appends; otherwise creates new workbook with header row
- Schema: `[Supplier Name, Suggested URL, Confidence Score, Search Query, DuckDuckGo Result, Bing Result, Status, Date Added]`
- Deduplicates by supplier name before writing
- Creates parent directory if absent

**_append_to_master_list(path: str, rows: list) → None:**
- Loads existing master list workbook and appends rows
- Writes `[Supplier Name, Suggested URL, None]` (third column reserved for category notes)
- Deduplicates by supplier name

**_write_resolved_list(path: str, suppliers: list) → None:**
- Creates new workbook with header row
- Schema: `[Supplier Name, Website, Source]`
- Contains known suppliers (from master list) + auto-resolved suppliers (source: `"auto_resolved"`)

## 7.3 Module: web_searcher.py [AI Engineer]

**File:** `web_searcher.py` — 96 lines

**search_duckduckgo(query, timeout=10, max_results=3) → list[str]:**
- POST to `https://html.duckduckgo.com/html/` with form data `{q: query}`
- HTTP timeout: connect 5s, read `timeout`s
- Uses headers with Chrome 120 User-Agent
- Parses response with BeautifulSoup: extract `a.result__url` hrefs
- Filters to only `http`-prefixed URLs (https excluded by `startswith("http")`)
- Returns up to `max_results` items
- On timeout or request error: logs warning, returns `[]`

**search_bing(query, timeout=10, max_results=3) → list[str]:**
- GET to `https://www.bing.com/search?q={query}`
- HTTP timeout: connect 5s, read `timeout`s
- Parses response with BeautifulSoup: extract `cite` element text
- If text starts with `"http"` → used as-is; if contains `"."` → `"https://"` prepended
- Returns up to `max_results` items
- On timeout or request error: logs warning, returns `[]`

**find_supplier_url(supplier_name, delay=1.5, timeout=10) → tuple:**
- Builds query: `'"{supplier_name}" official website'`
- Calls `search_duckduckgo(query, timeout)` → `sleep(delay)` → `search_bing(query, timeout)` → `sleep(delay)`
- Returns `(ddg_urls: list[str], bing_urls: list[str])`

## 7.4 Module: confidence_scorer.py [AI Engineer]

**File:** `confidence_scorer.py` — 97 lines

**URL Scoring Formula (max 110 points):**

| Component | Max Points | Condition |
|-----------|-----------|-----------|
| Cross-engine agreement | 40 | Top result domain matches across DuckDuckGo AND Bing (10 pts if only one engine has results) |
| Domain match | 25 | Domain contains meaningful supplier name words |
| HTTPS | 15 | URL uses `https://` |
| TLD quality | 10 | TLD is `.com`, `.org`, `.us`, or `.edu` |
| Not marketplace | 20 | Domain NOT in `DIRECTORY_BLOCKLIST` |
| **Total** | **110** | - |

**Directory Blocklist (15 domains):**

`amazon`, `alibaba`, `linkedin`, `yellowpages`, `thomasnet`, `globalspec`, `grainger`, `fishersci`, `directindustry`, `kompass`, `selectscience`, `labcompare`, `capterra`, `g2`, `yelp`

**extract_domain(url: str) → str:**
- Parses URL via `urlparse`, extracts `netloc`, strips `www.` prefix, lowercases

**domain_matches_supplier(domain: str, supplier_name: str) → bool:**
- Lowercases supplier name
- Strips legal suffixes: `inc`, `llc`, `corp`, `ltd`, `co`, `gmbh`, `usa`, `us`, `na`, `north america`, `corporation`, `company`, `technologies`, `scientific`, `medical`
- Splits remaining name on whitespace and hyphens, keeps words > 2 characters
- Returns `True` if any remaining word appears in the domain (substring match)

**is_directory(domain: str) → bool:**
- Returns `True` if any blocked domain string is a substring of the candidate domain

**score_url(url, supplier_name, ddg_urls, bing_urls) → int:**
- Returns 0 for empty/invalid URL
- Cross-engine: compares `extract_domain()` of top result from each engine; full match = 40 pts, any result = 10 pts
- Domain match: calls `domain_matches_supplier()` → 25 pts
- HTTPS: checks `url.startswith("https://")` → 15 pts
- TLD: extracts last segment after `.` → 10 pts if `com`, `org`, `us`, `edu`
- Not marketplace: 20 pts if `is_directory()` returns `False`

**pick_best_url(ddg_urls, bing_urls, supplier_name) → (best_url, best_score):**
- Combines top 3 URLs from each engine into a candidate pool
- Deduplicates by domain (first unique domain wins)
- Scores each candidate via `score_url()`
- Returns the URL with the highest score, or `("", 0)` if no candidates

## 7.5 Config Keys Consumed [Architect]

From `pipeline_config.json`:

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `paths.master_list` | string | (configurable — see Path Reference doc) | Path to master supplier list |
| `paths.labeled_dir` | string | (configurable — see Path Reference doc) | Directory containing Stage 2 classified Excel files |
| `supplier_resolution.enabled` | bool | `false` | Master switch for the stage |
| `supplier_resolution.confidence_threshold` | int | `70` | Minimum confidence score (0–110) to auto-resolve |
| `supplier_resolution.search_delay_seconds` | float | `1.5` | Seconds between DuckDuckGo and Bing requests |
| `supplier_resolution.search_timeout_seconds` | int | `10` | HTTP read timeout per search request |
| `supplier_resolution.pending_list_path` | string | (configurable — see Path Reference doc) | Output path for low-confidence suppliers needing manual review |
| `supplier_resolution.resolved_list_path` | string | (configurable — see Path Reference doc) | Output path for the combined known + resolved supplier list |

---

# Section 8: Stage 3 — Cross-Reference Engine [AI Engineer]

## 8.1 Purpose & Data Flow [Both]

- **Input:** Labeled Excel files from the labeled directory + PDFs from the PDF output directory + master supplier list
- **Processing:** Matches classified items to downloaded PDFs by supplier, using fuzzy text matching
- **Output:** `crossref_results_<timestamp>.xlsx` in the cross-reference results directory
- **Runtime:** ~30-60 min (60-90 min in low_cpu_mode)

## 8.2 Multi-Process Architecture [AI Engineer]

```
┌──────────────────────────────────────────────────────────┐
│                 CrossReferenceEngine                      │
│                                                          │
│  For each supplier (alphabetical):                       │
│    ┌──────────────────────────────────────┐             │
│    │  process_supplier_items()            │             │
│    │     │                                │             │
│    │     ▼                                │             │
│    │  find_items_for_supplier()           │             │
│    │     │                                │             │
│    │     ▼                                │             │
│    │  PDFSmartFilter.filter_and_prioritize│             │
│    │     │                                │             │
│    │     ▼                                │             │
│    │  process_pdfs_with_recovery()        │             │
│    │     │                                ▼             │
│    │     │  ProcessPoolExecutor(1) ─── process_single_pdf()
│    │     │  or sequential fallback       │              │
│    │     │                                │             │
│    │     ▼                                │             │
│    │  deduplicate_matches()              │             │
│    └──────────────────────────────────────┘             │
│                                                          │
│  GlobalStopManager (thread/process-safe stop)            │
│  PDF text cache (LRU, 300 entries)                       │
└──────────────────────────────────────────────────────────┘
```

**GlobalStopManager Class:**
- Singleton-style stop flag via classmethods
- `set_stop_flag(value)` — if `true`, calls `terminate_all_processes()`
- `should_stop()` — returns `_stop_flag`
- `register_process(process)` — tracks child processes
- `terminate_all_processes()` — iterates tracked processes: `terminate()` → `join(timeout=2)` → `kill()` if still alive
- Thread-safe and process-safe (no locks — operates on class-level list)

**process_single_pdf(args) → dict | None:**
- Standalone module-level function (NOT a class method) — defined at module top level for multiprocessing pickling
- Args tuple: `(pdf_path, search_keywords: list[str], description: str, threshold: int)`
- Returns: `{'pdf_path': str, 'score': float, 'supplier': str}` or `None` if below threshold
- Calls `extract_pdf_text_standalone()` then `calculate_match_score_standalone()`
- Checks `GlobalStopManager.should_stop()` at multiple points

**ProcessPoolExecutor Usage:**
- Created in `process_pdfs_parallel()` with `max_workers=1` (even when not in low_cpu_mode — conservative)
- Each PDF future has a per-result timeout of 120 seconds (2 minutes)
- Overall timeout: 1800 seconds (30 minutes) for the full batch via `as_completed(timeout=1800)`
- Fallback chain: parallel → `process_pdfs_sequential()` on any exception
- Executor shutdown: `shutdown(wait=False, cancel_futures=True)`

## 8.3 PDF Text Extraction [AI Engineer]

Two parallel implementations exist — one for multiprocessing workers, one for in-process use.

### Standalone Function: `extract_pdf_text_standalone(pdf_path, timeout_seconds=15, save_text=False) → str`

Used by `process_single_pdf()` (multiprocessing path). Multi-strategy chain:

1. **Header validation**: Check file starts with `%PDF` magic bytes (first 1024 bytes)
2. **File size check**: Skip if > 50 MB or == 0 bytes
3. **PyPDF2 extraction** (primary):
   - Open with `PdfReader(pdf_path)`
   - Skip if `reader.is_encrypted`
   - Limit to `max_pages = 5`
   - Extract text from each page via `page.extract_text()`
   - Truncate to `max_text_length = 5000` chars
   - Return first successful non-empty result
4. **pdfplumber fallback** (secondary):
   - Open with `pdfplumber.open(pdf_path)`
   - Limit to 3 pages
   - Two extraction sub-strategies per page:
     a. `page.extract_text()` — direct text extraction
     b. `page.extract_words()` → join word text fields
   - Truncate to 5000 chars
5. **Empty result**: Return `""` if all strategies fail

### Instance Method: `extract_pdf_text(pdf_path, timeout_seconds=30) → str`

Used by legacy `find_matching_pdfs()`. Adds caching on top of `_extract_pdf_text_uncached()`.

**Cache behavior:**
- `_pdf_text_cache: dict[str, str]` — path → extracted text
- Max 300 entries (`_PDF_CACHE_MAX = 300`)
- Eviction: `pop(next(iter(self._pdf_text_cache)))` — removes oldest insertion-ordered key
- Cache persists across all items within the same supplier processing batch
- NOT cleared between suppliers (survives across `run_cross_reference_by_supplier` items)

**`_extract_pdf_text_uncached(pdf_path, timeout_seconds=30) → str`:**
- Same header + file size checks as standalone
- Additional filename skip: `'novaseq'`, `'concordance'`, `'app-note'` in filename → skip
- Page limit: `max_pages = 20`
- Text limit: 20000 chars (20 KB)
- Windows branch: no SIGALRM, direct extraction with try/except per page
- Unix branch: wraps extraction in `signal.signal(SIGALRM, handler)` with `timeout_seconds` alarm
- pdfplumber fallback with all 3 sub-strategies (text, words, tables)

## 8.4 Match Scoring [AI Engineer]

### `calculate_match_score_standalone()` — Primary Formula (multiprocessing path)

```
score = (keyword_match_ratio * 60) + (similarity_ratio * 25) + (filename_score * 15)
score = max(0, score - filename_penalty)
score = min(100, score + filename_boost)
```

**Components:**
- **keyword_match_ratio** (60% weight): `len(matched_keywords) / len(keywords)` — keywords found as substrings in lowercased PDF text
- **similarity_ratio** (25% weight): `difflib.SequenceMatcher(None, description_lower, pdf_text_sample[:2000]).ratio()` — sample first 2000 chars of PDF text
- **filename_score** (15% weight): percentage of description words (>3 chars) found in lowercased filename

**Filename adjustment patterns:**

| Type | Patterns | Effect |
|------|----------|--------|
| Negative (14) | `price`, `price-sheet`, `executive`, `summary`, `sustainability`, `checklist`, `faq`, `one-pager`, `updated`, `catalog`, `flyer`, `poster`, `presentation`, `intro` | `filename_penalty += 15` (applied once, break on first match) |
| Positive (16) | `manual`, `instructions`, `ifu`, `datasheet`, `spec`, `specification`, `user-guide`, `user guide`, `installation`, `maintenance`, `service`, `technical`, `protocol`, `procedure`, `guide`, `handbook` | `filename_boost += 10` (applied once, break on first match) |

**Content quality filter:** If `len(pdf_text.strip()) < 200` → return `0.0`

### `calculate_match_score()` — Class Method (legacy path)

```
score = (keyword_match_ratio * 70) + (similarity_ratio * 30)
score = min(score, 100.0)
```

- **keyword_match_ratio** (70% weight): same ratio as standalone
- **similarity_ratio** (30% weight): `SequenceMatcher` ratio with 500-char PDF text sample (NOT 2000)
- No filename component, no penalty/boost adjustments

**Threshold:** Both formulas compare final score against `threshold` parameter (default 60 from config).

## 8.5 PDFSmartFilter [AI Engineer]

**Class PDFSmartFilter** — two parallel classification systems coexist in the same class.

### System A: `classify_pdf(filename) → (category: str, priority_score: int)`

Uses pre-compiled regex patterns (with `re.IGNORECASE`). This is the method actually called by `filter_and_prioritize_pdfs()`.

| Category | Patterns (regex) | Priority | Default Cap |
|----------|------------------|----------|-------------|
| high_priority (11) | `manual`, `instruction`, `guide`, `handbook`, `user.*guide`, `operation`, `setup`, `installation`, `configuration`, `reference`, `documentation` | 100 | 5 |
| medium_priority (5) | `specification`, `spec.*sheet`, `datasheet`, `technical.*data`, `product.*info` | 50 | 3 |
| noise (21) | `catalog.*drawing`, `\(catalog.*drawing\)`, `catalog`, `drawing`, `dwg`, `cad`, `schematic`, `reprint`, `flyer`, `poster`, `advertisement`, `ad.*sheet`, `marketing`, `sales.*sheet`, `carrier\d+`, `part.*list`, `parts.*catalog`, `price.*list`, `order.*form`, `color.*code.*parts.*list`, `self.*assessment` | 0 | 0 |
| unknown | (none matched) | 25 | 2 |

### System B: `get_priority_score(filename) → float`

Uses substring `in` keyword lists (not regex). **Not called anywhere in pipeline flow** — appears to be dead code.

| Priority | Keywords | Score |
|----------|----------|-------|
| High (17) | `manual`, `instruction`, `guide`, `handbook`, `user guide`, `operation`, `setup`, `installation`, `configuration`, `reference`, `documentation`, `datasheet`, `specification`, `spec sheet`, `technical data`, `product info` | +50.0 |
| Medium (2) | `product brief`, `overview` | 0.0 |
| Low (18) | `invoice`, `receipt`, `order`, `price list`, `catalog`, `drawing`, `dwg`, `cad`, `schematic`, `reprint`, `flyer`, `poster`, `advertisement`, `marketing`, `sales`, `part list`, `color code`, `brochure` | -50.0 |
| Unknown | (none matched) | 0.0 |

### `filter_and_prioritize_pdfs(pdf_files, max_pdfs_per_category=None) → list[tuple]`

- Sorts classified PDFs by priority score descending
- Applies per-category cap (defaults above)
- Returns list of `(filename, category, priority_score)` tuples

## 8.6 Supplier Matching Strategies [AI Engineer]

Used by `find_matching_pdfs()` (real implementation at line 1402) to locate the correct supplier directory for an item:

**Strategy 1: Exact Case-Insensitive Match**
- `current_supplier.lower() == available_supplier.lower()`

**Strategy 2: Partial Contains**
- `current_supplier.lower() in available_supplier.lower() or vice versa`

**Strategy 3: Word-Based (50% overlap)**
- Split both names into word sets
- `len(common_words) >= max(1, len(current_words) * 0.5)`

**Strategy 4: Suffix/Prefix Stripping**
- Suffixes stripped: `' inc', ' corp', ' ltd', ' llc', ' co', ' company', ' limited'`
- Prefixes stripped: `'the '`
- Cleaned names compared for equality

**Fallback: Cross-Directory Search**
- If no supplier-specific directory found, search ALL PDF directories
- Batch size: 10 PDFs per batch
- Uses instance method `self.extract_pdf_text()` (cached) + `self.calculate_match_score()` (class method)
- Lowest precision, highest recall

## 8.7 Processing Modes [Architect]

### Primary (Active): `run_cross_reference_by_supplier()`

- Entry point: `run_cross_reference_high_performance()` delegates here
- Processes suppliers in alphabetical directory order
- Per-supplier: finds matching items via `find_items_for_supplier()`, filters PDFs via `PDFSmartFilter`, processes matches
- 2-hour global timeout (7200 seconds)
- `gc.collect()` after each supplier

### Legacy (Retained): `run_cross_reference()`

- Iterates ALL items sequentially using legacy `find_matching_pdfs()` (line 1402)
- 1000-item safety cap: `input_df.head(1000)`
- 2-hour main loop timeout
- Skips items with TYPE column value `'non-instrument'`

### Batch Model: `process_pdfs_with_recovery()`

- Batch size: 25 PDFs per batch
- Each batch: try `process_pdfs_parallel()` → if exception, fallback to `process_pdfs_sequential()`
- Per-batch timeout: 600 seconds (10 minutes) — logged as warning, next batch continues
- Test mode: limits to first 100 PDFs
- Results collected and deduplicated per batch

### `process_pdfs_sequential()` — Fallback Path

- Iterates PDFs one at a time calling `process_single_pdf()` directly
- Garbage collection every 50 PDFs

### `process_pdfs_parallel()` — Parallel Path

- `ProcessPoolExecutor(max_workers=1)` — effectively serial but with process isolation
- Per-PDF timeout: 120 seconds via `future.result(timeout=120)`
- Overall timeout: 1800 seconds (30 minutes)
- `executor.shutdown(wait=False, cancel_futures=True)`

### low_cpu_mode

- Checked via `hasattr(self, 'low_cpu_mode') and self.low_cpu_mode`
- When `True`: `process_pdfs_with_recovery()` calls `process_pdfs_sequential()` directly
- When `False`: calls `process_pdfs_parallel()` (which still uses max_workers=1)
- Also checked via `hasattr` secondary detection — if attribute unset, defaults to not-low-cpu

## 8.8 Results Export [Architect]

**`export_results(output_file=None) → bool`**

- Creates list of dicts with columns: `Match Result`, `Item Code`, `Description`, `Category`, `PDF File`, `Match Score (%)`, `Supplier`
- `Match Result` is a formatted string: `[OK] MATCH! PDF {i}/{total}: {filename} (Score: {score:.1f}%)`
- `PDF File` contains just the basename
- Sorts by original insertion order
- Output: `pd.DataFrame(export_data).to_excel(output_file, index=False, engine='openpyxl')`
- Default filename: `crossref_results_{YYYYMMDD_HHMMSS}.xlsx`

Called from `pipeline.py:run_crossref()` with the results directory path.

## 8.9 Cross-Reference Utilities [AI Engineer]

**File:** `crossref_utils.py` (98 lines)

### `normalize_filename(filename) → str`

Strips extension via `os.path.splitext`, lowercases, then applies 5 regex transforms:

| Order | Pattern | Removes |
|-------|---------|---------|
| 1 | `[_\-\s]*\([0-9]+\)` | ` (1)`, `_2`, etc. |
| 2 | `[_\-\s]*v[0-9]+` | ` v2`, `_v3`, etc. |
| 3 | `[_\-\s]*20[0-9]{2}` | ` 2024`, `_2025`, etc. |
| 4 | `[_\-\s]*(updated\|final\|revised\|new\|latest)$` | trailing ` updated`, `_final` |
| 5 | `[_\-\s]+` | normalize all separators to `_` |

Final: `strip('_-. ')`.

### `deduplicate_matches(matches) → list`

- Groups by `normalize_filename(os.path.basename(match['pdf_path']))`
- Keeps entry with highest `match['score']`
- Logs dedup count

### `find_required_columns(df) → dict`

Returns `{'type_col', 'code_col', 'desc_col', 'supplier_col'}` — each `str | None`:

| Logical Column | Candidates |
|----------------|------------|
| `type_col` | `TYPE`, `Type`, `Item Type`, `Product Type` |
| `code_col` | `Item Code`, `ItemCode`, `Code`, `ID`, `Item ID`, `Item_ID` |
| `desc_col` | `Item Description`, `Description`, `ItemDescription`, `Name`, `Title`, `Product Name` |
| `supplier_col` | `Supplier Name`, `Supplier`, `Vendor`, `Company` |

## 8.10 Subsystems [AI Engineer]

### sys.path Import Hack (lines 10-15)

```python
_MODULE_DIR = Path(__file__).parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))
```

Without this, `from crossref_utils import ...` fails when loaded via `pipeline.py`'s dynamic `importlib.util.spec_from_file_location` mechanism.

### Memory Detection — `_get_fallback_memory_gb() → float`

Fallback chain when psutil is unavailable:

1. **Windows**: ctypes `GlobalMemoryStatusEx` → `MEMORYSTATUSEX.ullTotalPhys / (1024**3)`
2. **Linux**: Read `/proc/meminfo`, parse `MemTotal:` line
3. **macOS**: `subprocess.run(['sysctl', '-n', 'hw.memsize'])` → bytes → GB
4. **CPU-based estimation**: ≥16 cores → 32 GB, ≥8 cores → 16 GB, ≥4 cores → 8 GB, else 4 GB
5. **Final fallback**: 8.0 GB

### Process Cleanup — `cleanup_processes()`

- Iterates `self.parent_gui_processes`: `terminate()` → `join(timeout=1)` → `kill()` → `join(timeout=0.5)`
- If psutil available: recursive child termination via `psutil.Process(current_pid).children(recursive=True)`
- Forces `gc.collect()` after cleanup

### Tkinter GUI — `main()` (line 2588)

- `tk.Tk()` window with file dialogs (askopenfilename, asksaveasfilename, askdirectory)
- Analysis runs in a daemon `threading.Thread`
- Overrides `builtins.print` with `gui_print()` routing to `ScrolledText`
- Buttons: Run, Stop, Save Output, Create Test Data
- Default paths: the GUI default directories (different from the pipeline's standard data directories)

## 8.11 Known Quirks & Edge Cases [AI Engineer]

1. **Dual find_matching_pdfs definitions**: `find_matching_pdfs` defined at line 1281 (legacy stub returning empty matches) AND again at line 1402 (real implementation). The stub is dead code; Python uses the latest definition.

2. **low_cpu_mode dual check**: Checked via both constructor parameter AND `hasattr(self, 'low_cpu_mode')`. If the attribute is never set, `hasattr` returns `False` → may enable parallel mode unexpectedly.

3. **1000-item safety cap**: `run_cross_reference()` caps to `input_df.head(1000)` regardless of input size. `run_cross_reference_by_supplier()` has no such cap.

4. **Windows SIGALRM**: `signal.signal(signal.SIGALRM, handler)` is wrapped in `if not IS_WINDOWS`. SIGALRM is Unix-only. On Windows, timeout is managed via try/except without alarm — no operation timeout on PDF extraction.

5. **PDF text cache eviction**: `pop(next(iter(self._pdf_text_cache)))` removes oldest insertion-ordered key at 300 entries. No TTL. Cache survives across all items within `run_cross_reference_by_supplier`.

6. **Encrypted PDF handling**: Caught at `reader.is_encrypted` → return `""`. Also caught by generic `except` in standalone function.

7. **get_priority_score vs classify_pdf**: `PDFSmartFilter` has two independent classification methods with DIFFERENT pattern lists. `get_priority_score()` is never called — only `classify_pdf()` is used by the pipeline.

8. **GUI default paths diverge**: The standalone GUI defaults to different directories, while the pipeline uses the standard data directories. Running the GUI standalone will not find pipeline data without manual path selection.

9. **SequenceMatcher sample size**: Standalone formula uses 2000-char sample; class method uses 500-char sample. Same item yields different scores through different paths.

10. **Test mode inconsistencies**: Test mode in `run_cross_reference()` limits to 20 items; in `run_cross_reference_by_supplier()` limits to 5 suppliers; in `process_pdfs_with_recovery()` limits to 100 PDFs.

## 8.12 Config Keys Consumed [Architect]

From `pipeline_config.json`:

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `paths.labeled_dir` | string | (configurable — see Path Reference doc) | Directory with classified Excel files |
| `paths.pdf_dir` | string | (configurable — see Path Reference doc) | Root directory of supplier PDF folders |
| `paths.master_excel` | string | (configurable — see Path Reference doc) | Master supplier list |
| `paths.results_dir` | string | (configurable — see Path Reference doc) | Output directory for result Excel |
| `crossref.threshold` | int | `60` | Minimum match score (0–100) |
| `crossref.test_mode` | bool | `false` | Limit processing (5 suppliers, 100 PDFs, 20 items) |
| `crossref.low_cpu_mode` | bool | `true` | Skip parallel processing, use sequential |
| `crossref.clean_output` | bool | `true` | Clean formatting in output Excel |

**Pipeline entry (`pipeline.py:run_crossref()`):**
- Picks the most recent `*_labeled.xlsx` from the labeled directory; falls back to any `*.xlsx`
- Creates `CrossReferenceEngine()`, calls `run_cross_reference_high_performance()` with config values
- Calls `engine.export_results(output_file)` with path in the results directory

---

# Section 9: Monitoring & Analysis [Both]

## 9.1 Purpose

- Post-run analysis tool (NOT integrated into the pipeline — runs independently)
- Evaluates classification quality after Stage 2 completes
- Measures Rule B effectiveness (supplier metadata context)
- Tracks progress toward Phase 3 target: <400 Unknown items
- Designed for manual execution by operators/engineers reviewing pipeline output

## 9.2 analyze_classifications() Flow [AI Engineer]

**File:** `phase4_analysis.py` — 103 lines

`analyze_classifications()` function (no arguments, uses hardcoded paths to the labeled directory):

1. Scans the labeled directory for all `*_classified_v3.xlsx` files
2. Filters out `_v3_v3` duplicates (files that were processed twice)
3. For each file:
   - Loads classification data via `pd.read_excel()`
   - Concatenates all files into a single DataFrame
4. Counts by type: Instrument, Software, Non-Instrument, Unknown (via `value_counts()`)
5. Identifies Unknown items with their supplier names
6. Loads the supplier classification database
7. Computes metrics:
   - Total items per type (count and percentage)
   - Number of Unknown items by supplier (top 20)
   - How many Unknown items WOULD be resolved by Rule B (supplier DB coverage)
   - Phase 3 target check: is Unknown count < 400?

**Output:** Prints all results to stdout. Returns the combined DataFrame (or `None` if no files found).

**Error handling:** Per-file `try/except` around `pd.read_excel()` — if a file fails to load, it is skipped with an error message and processing continues to the next file.

**Key implementation details:**

| Aspect | Detail |
|--------|--------|
| Glob pattern | `*_classified_v3.xlsx` |
| Duplicate filter | `"_v3_v3" not in f.name` |
| Supplier DB path | the supplier classification database |
| Type column | `"Type"` — standard classifier output column |
| Grouping column | `"Supplier Name"` — used for per-supplier Unknown grouping |

## 9.3 Rule B Coverage Analysis [Architect]

- Measures the percentage of Unknown items whose suppliers exist in the supplier classification database
- **High coverage + high Unknown count** → classification improvements need keyword tuning (Rule A/C)
- **Low coverage + high Unknown count** → classification DB expansion needed (add more suppliers)
- **Low coverage + low Unknown count** → acceptable state; DB expansion is lower priority
- The analysis prints two counts:
  - `In database (should be reclassified)` — suppliers found in DB, item likely resolvable
  - `NOT in database (needs manual review)` — suppliers absent from DB, requires manual addition

**Strategic interpretation:**

| Coverage | Unknown Count | Recommended Action |
|----------|---------------|-------------------|
| High | High | Tune the keyword files in the keywords directory |
| Low | High | Expand the supplier classification database with missing suppliers |
| High | Low (<400) | Target met; monitor for regression |
| Low | Low (<400) | Target met; add suppliers opportunistically |

## 9.4 Phase 3 Target Metrics [Both]

- **Target:** <400 Unknown items remaining after Stage 2
- The script prints a summary block comparing achieved Unknown count against the target
- If above 400 (`Status: Above target`): recommends expanding supplier DB or tuning keyword files
- Prints actionable summary per supplier showing which suppliers contribute the most Unclassified items
- When target is met (`Status: TARGET MET`), prints a success message

**Example output structure:**

```
[Summary vs Phase 3 Target]
  Phase 3 goal: <400 Unknown items
  Achieved: 523 Unknown items
  Status: Above target
```

**Iteration guidance:** Run `phase4_analysis.py` after each classifier or keyword change to track progress. The tool is designed for rapid feedback — no arguments, no config, runs in seconds.

---

# Section 10: Appendices — Data Contracts

## Appendix A: Input Excel Schema (Raw Supplier Requisition)

**Required columns (by position in v3 classifier, by name in adaptive processor):**

| Logical Column | Excel Col (v3) | Name Match Priority | Type | Description |
|---------------|----------------|---------------------|------|-------------|
| Req ID | B | - | string | Procurement request identifier |
| Supplier ID | F | - | string | Supplier identifier code |
| Supplier Name | G | supplier, vendor, company, manufacturer, distributor, source | string | Supplier/vendor name |
| Item Description | I | description, desc, item, name, title, product, material | string | Product description text |
| Req Line Item | O | - | string | Line item identifier |

## Appendix B: Labeled Excel Schema (After Stage 2)

**v3 Classifier output:** `*_classified_v3.xlsx` (in the labeled directory)
**Adaptive Processor output:** `*_labeled.xlsx` (in the labeled directory)

| Column | v3 Included | Adaptive Included | Description |
|--------|-------------|-------------------|-------------|
| Input columns (Req ID, Supplier Name, Item Description, etc.) | Yes | Yes | All original columns preserved |
| Type | Yes | Yes | Classification: Instrument, Software, Non-Instrument, Unknown |
| Confidence Score | No | Yes | Classification confidence level |
| Match Reason | No | Yes | Which rule or keyword triggered the classification |

**Type values:**
- `Instrument` — Physical device used in scientific research
- `Software` — Computer program or license
- `Non-Instrument` — Supply, consumable, service, furniture
- `Unknown` — Could not be classified by any rule

## Appendix C: Master List Schema

| Column | Type | Description |
|--------|------|-------------|
| Supplier Name | string | Supplier/vendor name (key field, ~247 entries) |
| Website | string | Supplier's official website URL |
| Category | string (optional) | Supplier category notes |

## Appendix D: Crossref Results Schema

| Column | Type | Description |
|--------|------|-------------|
| Match Result | string | "Match" or "No Match" |
| Item Code | string | The item identifier from the requisition |
| Description | string | Item description text |
| Category | string | Classification (Instrument/Software/Non-Instrument) |
| PDF File | string | Filename of the matched PDF |
| Match Score (%) | int (0-100) | Match confidence score (threshold >= 60) |
| Supplier | string | Supplier name |

## Appendix E: Pending/Resolved List Schemas (Stage 2b)

**Pending list** (`new_suppliers_pending.xlsx`):

| Column | Type | Description |
|--------|------|-------------|
| Supplier Name | string | Unknown supplier name |
| Suggested URL | string | Best-guess website URL |
| Confidence Score | int (0-110) | URL confidence score |
| Search Query | string | The query used for search |
| DuckDuckGo Result | string | Top DDG result URL |
| Bing Result | string | Top Bing result URL |
| Status | string | Review status |
| Date Added | datetime | When entry was created |

**Resolved list** (`resolved_suppliers.xlsx`):

| Column | Type | Description |
|--------|------|-------------|
| Supplier Name | string | Resolved supplier name |
| Website | string | Confirmed website URL |
| Source | string | How the URL was found |

## Appendix F: State Files

**`.scraper_state.json`** — 7-day freshness tracking:

```json
{
  "Thermo Fisher Scientific": "2026-06-29T10:30:00",
  "Agilent Technologies": "2026-07-01T14:15:00"
}
```

- Location: `{output_dir}/.scraper_state.json`
- Format: `{supplier_name: ISO_8601_timestamp}`
- Written atomically via `.tmp` + rename pattern

**`.scraper_dedup.db`** — SQLite dedup database:

- Location: `{output_dir}/.scraper_dedup.db`
- Tables: `seen_urls(url, status, ts)`, `downloaded(path, url, supplier, ts)`
- Journal mode: WAL (Write-Ahead Logging) for concurrent access
- Connections: one per thread via `threading.local()`

## Appendix G: learning_log.json Schema (Adaptive Classifier)

```json
{
  "hw_candidates": {"microscope": 12, "spectrometer": 7},
  "sw_candidates": {"license": 15, "subscription": 6},
  "ni_candidates": {"filter_tip": 9, "glove": 20},
  "last_updated": "2026-07-06T10:30:00",
  "settings": {
    "min_occurrences": 5,
    "confidence_threshold": 0.7,
    "learning_mode": true
  }
}

---

# Section 11: Appendices — Known Issues & Quirks

This section consolidates all known issues and quirks from every stage into one reference list. Grouped by severity and stage.

### 11.1 Critical (May Cause Incorrect Results)

| # | Issue | Stage | Root Cause | Workaround / Implication |
|---|-------|-------|------------|-------------------------|
| 1 | **Dual find_matching_pdfs definitions** | 3 (Cross-Ref) | `crossref_standalone_fast.py` defines `find_matching_pdfs()` at ~line 1281 (stub, returns empty matches) and ~line 1402 (real implementation). The stub appears earlier in the file and is dead code — Python uses the latest definition, but any code path referencing the module's symbol table may resolve the wrong one. | Verify which definition is called. If calling from a dynamic import that only loads the first definition, zero matches are returned despite successful analysis. |
| 2 | **low_cpu_mode checked via both argument and hasattr** | 3 (Cross-Ref) | `process_pdfs_parallel()` checks both the `low_cpu_mode` constructor parameter AND `hasattr(self, 'low_cpu_mode')` as secondary detection. If attribute is unset, hasattr returns False, which may enable parallel mode unexpectedly. | Always pass `low_cpu_mode` explicitly. If adding new code paths, ensure the attribute is set before use. |
| 3 | **Windows SIGALRM unavailable** | 3 (Cross-Ref) | `signal.signal(signal.SIGALRM, handler)` used for PDF extraction timeout. SIGALRM is Unix-only; on Windows, `signal` module exists but SIGALRM raises AttributeError (caught by try/except). | Timeout is a no-op on Windows. Long-running PDF extractions may hang indefinitely. The fallback timeout mechanism uses `concurrent.futures.as_completed` with per-batch timeout, but individual extraction calls are not bounded. |
| 4 | **Cross-ref sys.path hack** | 3 (Cross-Ref) | Lines 10-15 insert the module directory into `sys.path` at import time to allow `from crossref_utils import ...` when loaded via dynamic import. This mutates global state. | If `crossref_standalone_fast` is imported while another module has modified sys.path, the insert may have unexpected side effects. The path is prepended (index 0), so it takes priority over all other paths. |
| 5 | **Keyword cross-contamination** | 2 (Classify) | v3 classifier's `load_and_clean_keywords()` removes ALL keywords found in ANY intersection across the 3 keyword lists. A keyword valid for two categories (e.g., "plate" as both instrument and consumable) is removed from ALL lists. | This is deliberate to enforce single-category classification. If a keyword legitimately belongs to multiple categories, items using it will be classified as Unknown. Add context-specific keywords instead of shared ones. |

### 11.2 High (May Cause Errors or Data Loss)

| # | Issue | Stage | Root Cause | Workaround / Implication |
|---|-------|-------|------------|-------------------------|
| 6 | **Dynamic import path caveat** | Orchestrator | `_import_from_file()` in pipeline.py uses `importlib.util.spec_from_file_location()`. Each stage file must be independently importable — no relative imports, no package-relative dependencies. | Any stage that imports from a sibling module must use sys.path manipulation (see #4) or absolute imports. Adding a new stage requires ensuring its module is self-contained. |
| 7 | **7-day state file atomic rename on Windows** | 1 (Scraper) | State file writes to `.scraper_state.json.tmp` then `os.remove(p); os.rename(tmp, p)`. The `os.remove` before `os.rename` creates a brief window with NO state file present. | If the process crashes between remove and rename, the state file is lost entirely. All suppliers will be re-crawled on the next run. The `.tmp` file prevents half-written corruption, but the operation is NOT truly atomic. |
| 8 | **Supplier name ↔ directory mismatch** | 3 (Cross-Ref) | Stage 1 creates directories by supplier name (raw from Excel). Stage 3 reads directory names and applies 4 matching strategies. If supplier names differ by whitespace, punctuation, or casing between runs, directories won't match. | The 4 matching strategies (exact → partial → word-based → suffix-stripped) mitigate this, but the cross-directory search fallback (strategy 5) has the lowest precision. |
| 9 | **No SHA-256 file dedup in download path** | 1 (Scraper) | `_file_hash()` function exists at module level but is never called by `_download_pdf()`. Only path-based dedup via `state_db.is_downloaded(file_path)` is performed. | The same PDF downloaded to different paths (e.g., renamed supplier directories) will be downloaded twice. No content-addressable dedup is performed. |
| 10 | **1000-item safety cap** | 3 (Cross-Ref) | Legacy `run_cross_reference()` method stops processing after 1000 items regardless of input size (`input_df.head(1000)`). | The active `run_cross_reference_by_supplier()` does not have this cap. Only affects code paths using the legacy method. |

### 11.3 Medium (May Cause Performance Issues or Suboptimal Results)

| # | Issue | Stage | Root Cause | Workaround / Implication |
|---|-------|-------|------------|-------------------------|
| 11 | **PDF text cache never cleared between suppliers** | 3 (Cross-Ref) | `self._pdf_text_cache` (LRU dict, max 300 entries) is only evicted when full — oldest entry removed via `pop(next(iter(...)))`. Not explicitly cleared between suppliers. | Cache entries from one supplier may persist into another supplier's processing. For large suppliers (>300 PDFs), the cache provides no benefit as entries are constantly evicted. |
| 12 | **HEAD→GET fallback on failure** | 1 (Scraper) | If the HEAD request fails (timeout, connection error), the pipeline proceeds with a full GET anyway. | Oversized or non-PDF files are only caught mid-stream during the full download. This wastes bandwidth and time on files that the HEAD check would have rejected. |
| 13 | **Per-thread SQLite busy collisions** | 1 (Scraper) | `_StateDB` uses WAL journal mode for concurrent access but does NOT implement retry logic for `SQLITE_BUSY` errors. | Under high concurrency (many domains simultaneously), write operations may conflict. WAL provides some protection but does not eliminate the race entirely. The code has no retry loop. |
| 14 | **Column position fragility (v3 classifier)** | 2 (Classify) | `column_filter_and_classify_v3.py` maps columns by hardcoded Excel position (B, F, G, I, O). If input file column order changes, classification silently reads wrong data. | The name-based fallback provides partial protection. If position and name both fail, items will be classified as Unknown or raise a KeyError. |
| 15 | **10-link cap per recursion depth** | 1 (Scraper) | Recursive link-walking caps at 10 HTML links per depth level (`page_links[:10]`). | Large sites with deep product hierarchies may not be fully explored. Increase `max_pages` and remove the `[:10]` slice for thorough crawling. |
| 16 | **Rate limiter granularity** | 1 (Scraper) | `_DomainRateLimiter` uses `time.sleep()` with sub-second float granularity (e.g., 2.0 seconds). | On some platforms, `time.sleep()` may round to clock tick boundaries (~15ms on Windows). Not typically an issue for 2-second delays, but may cause more aggressive crawling than configured on high-resolution timers. |
| 17 | **Supplier resolution disabled by default** | 2b | `pipeline_config.json` has `"pipeline.run_supplier_resolution": false` AND `"supplier_resolution.enabled": false`. The stage runner `run_supplier_resolution()` returns True immediately without any processing. | If supplier resolution is needed, BOTH the `pipeline.run_supplier_resolution` flag AND `supplier_resolution.enabled` must be set to `true`. Two separate toggles, both must agree. |

### 11.4 Low (Cosmetic or Documentation)

| # | Issue | Stage | Root Cause | Workaround / Implication |
|---|-------|-------|------------|-------------------------|
| 18 | **supplier_keywords set as attribute post-construction** | 1 (Scraper) | Pipeline sets `engine.supplier_keywords = loaded_dict` after construction (pipeline.py line 566-568) rather than passing via constructor. The constructor parameter defaults to `None`. | Type stubs and documentation should note this is a post-init assignment. Any code path creating `ScraperEngine` directly must set this attribute manually for keyword filtering to work. |
| 19 | **`_count_lock` scope visibility** | 1 (Scraper) | `page_count` is incremented in `_crawl_recursive` and `pdf_count` in `_download_pdf`. Both use `self._count_lock`, but the lock spans two methods. | Technically correct behavior — the same lock protects both counters. However, the split scope across two methods may confuse readers. |
| 20 | **SUPPLIER_SUFFIXES_TO_REMOVE defined but partially unused** | 0 (Cleaner) | `clean_supplier_name()` does not use `SUPPLIER_SUFFIXES_TO_REMOVE`. The list exists as a module-level constant with 16 entries (only some are commonly encountered). | No runtime impact. The list serves as documentation of all known removable suffixes for potential future use. |
| 21 | **config.ini vs pipeline_config.json redundancy** | All | Two config files control overlapping settings. `config.ini` is legacy; `pipeline_config.json` is the primary source. Both contain scraper defaults, match thresholds, etc. | The duplicate namespace creates confusion about which config is authoritative. The pipeline ignores `config.ini` entirely, but standalone scripts may read it. |
| 22 | **WebScrapper.exe binary in source tree** | 1 (Scraper) | Compiled binary `WebScrapper.exe` is checked into the `scraper-full/` directory. Its source and build process are not documented. | Treat as a build artifact. Do not rely on it for pipeline execution. Its purpose and origin are undocumented. |
| 23 | **SequenceMatcher sample size inconsistency** | 3 (Cross-Ref) | Standalone formula uses 2000-char PDF text sample; class method uses 500-char sample. | Same item yields different scores depending on which code path executes. The standalone path (multiprocessing) will generally produce higher match scores due to more text context. |
| 24 | **Test mode inconsistencies** | 3 (Cross-Ref) | `run_cross_reference()` test mode limits to 20 items; `run_cross_reference_by_supplier()` limits to 5 suppliers; `process_pdfs_with_recovery()` limits to 100 PDFs. | Test results are not directly comparable between the two entry points. Always state which entry point was used when reporting test results. |

---

# Section 12: Appendices — Error Reference & Failure Modes

## 12.1 Pipeline Orchestrator (pipeline.py)

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Config file not found | `--config` path doesn't exist, or `pipeline_config.json` missing | FileNotFoundError at startup | Verify config path. Pipeline exits with traceback. |
| Path validation failure | Required path for an enabled stage doesn't exist (e.g., `input_excel_dir`) | Error log: "Path validation failed: ..." → exit(1) | Create missing directory or disable the stage. |
| Stage import failure | `_import_from_file()` can't load module | ImportError → exit(1) with traceback | Verify stage file exists and is syntactically valid Python. |
| Stage function missing | Module loaded but doesn't expose expected `run_*()` function | AttributeError → exit(1) | Ensure stage module has the correctly named entry function. |
| Stage returns False + stop_on_failure=True | Stage encountered error | "STAGE [name] FAILED" → immediate exit(1) | Check stage logs, fix issue, re-run. |
| Dry-run mode | CLI `--dry-run` flag | All stages executed but no files written | Remove `--dry-run` for actual run. |

## 12.2 Stage 0: Data Cleaning

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Input directory missing | `input_excel_dir` doesn't exist | FileNotFoundError → stage returns False | Create directory or fix config path. |
| CSV encoding detection failure | `chardet` can't detect encoding | Falls back to UTF-8 → possible UnicodeDecodeError | Specify encoding manually or fix file encoding. |
| Corrupted Excel file | File is not a valid Excel format | pandas exception (XLRDError, BadZipFile) | Replace corrupted file with clean copy. |
| Empty supplier column | File has no recognizable supplier column | All rows pass through with empty cleaned_name | Verify file has a `Supplier Name` column. |
| Write permission error | Output directory not writable | PermissionError | Check file permissions on input directory. |

## 12.3 Stage 1: Web Scraper

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Invalid supplier URLs | Excel contains malformed or empty URLs | Warning log: "Invalid URL for supplier X" → supplier skipped | Fix URLs in master list Excel. |
| Empty supplier list | No valid (name, URL) pairs after loading and validation | Info log: "No suppliers to process" → stage returns 0/0/0 | Check master list Excel has data. |
| All suppliers up-to-date | `skip_recent_sites=True` and all within freshness window | Info log: "All suppliers are up-to-date" → stage returns 0/0/0 | Set `skip_recent_sites=False` or wait for `days_before_rescrape` to elapse. |
| Download timeout | Remote server doesn't respond within `page_timeout` | URL marked as 'timeout' in seen_urls DB | Increase `page_timeout` in config. The supplier may still be visited in a later run. |
| Download too large | PDF exceeds `max_pdf_size_mb` | URL marked as 'skipped_size' in seen_urls DB | Increase `max_pdf_size_mb` in config if legitimate large PDFs are being skipped. |
| Download too small | Downloaded file < `min_pdf_size_bytes` | File deleted, URL marked as 'skipped_small' | Decrease `min_pdf_size_bytes` if small legitimate files are being discarded. |
| Rate limiting by server | Server returns HTTP 429 | `Retry` adapter retries 3 times with backoff | Increase `request_delay` or add the domain to per-site config with higher delay. |
| All discovery methods fail | Sitemap, search, and recursive crawl return zero PDFs | Supplier processed but 0 PDFs downloaded | Check if supplier website is accessible. Verify domain is correct. |
| State file TMP→RENAME crash | Process crashes between os.remove and os.rename | State file is missing → all suppliers re-crawled on next run | Not recoverable mid-run. State loss is acceptable — it only means re-crawling. |

## 12.4 Stage 2: Classification

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Input directory missing | `input_excel_dir` doesn't exist | FileNotFoundError → stage returns False | Create directory or fix config. |
| No unprocessed files | All files already classified (end in `_labeled` or `_classified_v3`) | Stage runs but processes 0 files | Remove or move already-classified files, or add new input files. |
| Missing columns | Excel file doesn't have expected columns (v3: B,F,G,I,O by position) | KeyError during column access | Verify file format. The name-based fallback may help but some items will be Unknown. |
| Empty keyword files | Keyword files are empty or don't exist | All items classified as Unknown | Verify keyword files exist and have content. |
| Corrupted learning_log.json | JSON parse error | Silent fallback to empty candidate counters | Delete or fix learning_log.json. Candidate data loss is acceptable. |
| Temp file collision | Office lock file (`~$`) in directory | File silently skipped | Close Excel if it has the file open. |

## 12.5 Stage 2b: Supplier Resolution

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Disabled by default | `enabled: false` in config | Stage returns True immediately without processing | Set `supplier_resolution.enabled=true` AND `pipeline.run_supplier_resolution=true`. |
| Search engine rate limiting | DuckDuckGo/Bing blocks repeated requests | Search returns empty or error results | Increase `search_delay_seconds` or reduce number of unknown suppliers per run. |
| Search engine HTML change | DuckDuckGo or Bing changes their HTML structure | Parsing fails, no results extracted | Update `web_searcher.py` selectors to match new HTML structure. |
| All suppliers already known | No unknown suppliers found | Stage runs but appends 0 rows | Informational only — the master list is up to date. |

## 12.6 Stage 3: Cross-Reference Engine

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| Input file not found | Labeled Excel or master list file doesn't exist | FileNotFoundError → stage returns False | Verify labeled_dir and master_excel paths in config. |
| PDF directory not found | `pdf_dir` doesn't exist or is empty | Stage runs but 0 matches found (no PDFs to scan) | Verify Stage 1 has been run and PDFs exist in pdf_dir. |
| Encrypted PDF | PDF has owner/encryption protection | PyPDF2 raises error → PDF silently skipped | No recovery — encrypted PDFs cannot be read. |
| PDF extraction timeout | PDF is large or corrupted | Process timeout (10 min per batch) → batch falls back to sequential | For consistently problematic PDFs, remove or replace the file. |
| Out of memory | Too many PDFs processed simultaneously | Process crashes with OOM | Enable `low_cpu_mode` (default) to serialize processing. Reduce batch size. |
| Zombie processes | Process not properly terminated | Orphaned Python processes consuming memory | `cleanup_processes()` should handle this. If not, manually kill orphaned processes. |
| Zero matches (false negative) | Keyword mismatch between item and PDF | Item has 0 matches despite relevant PDF existing | Lower threshold, check keyword files, verify PDF text extraction quality. |
| 2-hour global timeout | Processing takes longer than 120 minutes | All processing stops, partial results exported | Increase timeout in code, or reduce input size (fewer suppliers/items). |
| process_single_pdf pickling error | Function or arguments not pickle-able | ProcessPoolExecutor raises PicklingError | Ensure all arguments to `process_single_pdf()` are simple types (strings, ints, lists). |

## 12.7 Monitoring (phase4_analysis.py)

| Failure Mode | Cause | Symptom | Recovery |
|-------------|-------|---------|----------|
| No classified files found | Stage 2 hasn't been run or files are in wrong directory | Returns None, prints "No files found" | Run Stage 2 first, or check labeled_dir path. |
| Corrupted Excel file in labeled directory | File cannot be read by pandas | Single file skipped, processing continues with remaining files | Remove or fix the corrupted file. |
| Supplier DB not found | The supplier classification database is missing | Rule B coverage analysis prints 0 in-database entries | Run Stage 2 first (it creates the file), or verify the path. |
```
