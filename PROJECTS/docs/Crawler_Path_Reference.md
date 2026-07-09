# Crawler Path Reference

## Overview

This document captures all machine-specific paths and directory structures used by the Crawler pipeline. Referenced by the main technical reference doc.

## 1. External Data Directory Tree

```
C:\Data\Crawler\
├── input\           # Raw supplier requisition files (.xlsx, .csv)
├── labeled\         # Classified output files (_classified_v3.xlsx, _labeled.xlsx)
├── output\          # Downloaded PDFs
│   ├── {Supplier Name}\  # One folder per supplier
│   ├── .scraper_dedup.db # SQLite dedup database
│   └── .scraper_state.json # 7-day freshness state
└── pdf_discovery\   # Extracted PDF text (by crossref)
    └── documents_text\
```

## 2. Project Repository Tree

```
PROJECTS\                          # Project root (C:\Projects\Crawler\PROJECTS\)
├── src\services\
│   ├── pipeline.py
│   ├── pipeline_config.json
│   ├── config.ini
│   ├── data-cleaning\data_cleaner.py
│   ├── scraper-full\scraper_engine.py
│   ├── classify\
│   │   ├── adaptive_excel_processor.py
│   │   ├── config.py
│   │   ├── research_instrument_keywords.txt
│   │   ├── software_keywords.txt
│   │   ├── non_instrument_keywords.txt
│   │   ├── learning_log.json
│   │   ├── monitor_config.json
│   │   ├── service_config.json
│   │   ├── simple_W_service.py
│   │   └── simple_monitor.py
│   ├── data-cleaning\column_filter_and_classify_v3.py
│   ├── supplier-resolution\
│   │   ├── supplier_resolver.py
│   │   ├── web_searcher.py
│   │   └── confidence_scorer.py
│   ├── cross-reference\
│   │   ├── crossref_standalone_fast.py
│   │   ├── crossref_utils.py
│   │   └── results\            # crossref_results_*.xlsx output
│   └── monitoring\phase4_analysis.py
├── data\
│   ├── masterlist\updated_master_list.xlsx  # 247 suppliers
│   └── supplier-pending\
│       ├── new_suppliers_pending.xlsx
│       └── resolved_suppliers.xlsx
├── docs\
│   ├── references\supplier_classification.json
│   ├── Crawler_Technical_Reference.md
│   └── Crawler_Path_Reference.md          # ← this file
└── config.ini
```

## 3. All Absolute Path References (Alphabetical)

| # | Path | Used By | Purpose | Stage |
|---|------|---------|---------|-------|
| 1 | `C:\Data\Crawler\input\` | pipeline, data_cleaner, classify | Raw supplier requisition files | 0, 2 |
| 2 | `C:\Data\Crawler\labeled\` | pipeline, classify, crossref, monitoring | Classified Excel output | 2, 3 |
| 3 | `C:\Data\Crawler\labeled\hardware_keywords_ACTIVE.txt` | scraper (Camofox) | Hardware keyword filter | 1 |
| 4 | `C:\Data\Crawler\labeled\software_keywords_ACTIVE.txt` | scraper (Camofox) | Software keyword filter | 1 |
| 5 | `C:\Data\Crawler\output\` | pipeline, scraper, crossref | Downloaded PDFs by supplier | 1, 3 |
| 6 | `C:\Data\Crawler\output\{supplier_name}\.scraper_dedup.db` | scraper | SQLite dedup database | 1 |
| 7 | `C:\Data\Crawler\output\{supplier_name}\.scraper_state.json` | scraper | 7-day freshness state | 1 |
| 8 | `C:\Projects\Crawler\PROJECTS\` | pipeline | Project root for relative path resolution | ALL |
| 9 | `C:\Projects\Crawler\PROJECTS\data\masterlist\updated_master_list.xlsx` | pipeline, scraper, crossref, supplier_resolver | Master supplier list (~247 suppliers) | 1, 2b, 3 |
| 10 | `C:\Projects\Crawler\PROJECTS\data\supplier-pending\` | supplier_resolver | Pending/resolved supplier files | 2b |
| 11 | `C:\Projects\Crawler\PROJECTS\docs\references\supplier_classification.json` | classify, monitoring | Supplier classification DB | 2 |
| 12 | `C:\Projects\Crawler\PROJECTS\src\services\` | pipeline | CODE_ROOT for stage module discovery | ALL |

## 4. Relative Project Paths

| Path | Type | Purpose |
|------|------|---------|
| `src/services/pipeline.py` | Code | Pipeline orchestrator entry point |
| `src/services/pipeline_config.json` | Config | Primary pipeline configuration |
| `src/services/config.ini` | Config | Legacy scraper configuration |
| `src/services/data-cleaning/data_cleaner.py` | Code | Stage 0 — Data cleaning |
| `src/services/scraper-full/scraper_engine.py` | Code | Stage 1 — Web scraper engine |
| `src/services/data-cleaning/column_filter_and_classify_v3.py` | Code | Stage 2 — v3 classifier |
| `src/services/classify/adaptive_excel_processor.py` | Code | Stage 2 — Adaptive classifier |
| `src/services/classify/research_instrument_keywords.txt` | Data | Hardware/instrument keyword list |
| `src/services/classify/software_keywords.txt` | Data | Software keyword list |
| `src/services/classify/non_instrument_keywords.txt` | Data | Non-instrument keyword list |
| `src/services/classify/learning_log.json` | Data | Self-learning keyword candidates |
| `src/services/classify/monitor_config.json` | Config | Windows service monitor config |
| `src/services/classify/service_config.json` | Config | Windows service registration |
| `src/services/classify/simple_W_service.py` | Code | Windows service wrapper |
| `src/services/supplier-resolution/supplier_resolver.py` | Code | Stage 2b — Supplier resolution |
| `src/services/supplier-resolution/web_searcher.py` | Code | DuckDuckGo + Bing search |
| `src/services/supplier-resolution/confidence_scorer.py` | Code | URL confidence scoring |
| `src/services/cross-reference/crossref_standalone_fast.py` | Code | Stage 3 — Cross-reference engine |
| `src/services/cross-reference/crossref_utils.py` | Code | Cross-reference utilities |
| `src/services/cross-reference/results/` | Output | crossref_results_*.xlsx output |
| `src/services/monitoring/phase4_analysis.py` | Code | Post-run classification analysis |
| `data/masterlist/updated_master_list.xlsx` | Data | Master supplier list |
| `data/supplier-pending/new_suppliers_pending.xlsx` | Output | Low-confidence suppliers |
| `data/supplier-pending/resolved_suppliers.xlsx` | Output | High-confidence resolved suppliers |
| `docs/references/supplier_classification.json` | Data | Supplier classification database |

## 5. Config Paths Reference

| Config Key | Meaning | Default (relative) | Default (absolute) |
|-----------|---------|-------------------|-------------------|
| `paths.supplier_excel` | Master supplier list workbook | `data/masterlist/updated_master_list.xlsx` | `C:\Projects\Crawler\PROJECTS\data\masterlist\updated_master_list.xlsx` |
| `paths.pdf_dir` | Downloaded PDF root directory | `C:/Data/Crawler/output` | `C:\Data\Crawler\output` |
| `paths.input_excel_dir` | Raw supplier requisition files | `C:/Data/Crawler/input` | `C:\Data\Crawler\input` |
| `paths.labeled_dir` | Classified output files | `C:/Data/Crawler/labeled` | `C:\Data\Crawler\labeled` |
| `paths.master_excel` | Master list (cross-ref reads it) | `data/masterlist/updated_master_list.xlsx` | Same as `supplier_excel` |
| `paths.master_list` | Master list (resolution reads it) | `data/masterlist/updated_master_list.xlsx` | Same as `supplier_excel` |
| `paths.results_dir` | Cross-reference results output | `src/services/cross-reference/results` | `C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results` |
| `classify.hw_keywords_file` | Hardware keyword list | `src/services/classify/research_instrument_keywords.txt` | `C:\Projects\Crawler\PROJECTS\src\services\classify\research_instrument_keywords.txt` |
| `classify.sw_keywords_file` | Software keyword list | `src/services/classify/software_keywords.txt` | Same pattern |
| `classify.ni_keywords_file` | Non-instrument keyword list | `src/services/classify/non_instrument_keywords.txt` | Same pattern |
| `supplier_resolution.pending_list_path` | Low-confidence supplier output | `data/supplier-pending/new_suppliers_pending.xlsx` | `C:\Projects\Crawler\PROJECTS\data\supplier-pending\new_suppliers_pending.xlsx` |
| `supplier_resolution.resolved_list_path` | High-confidence supplier output | `data/supplier-pending/resolved_suppliers.xlsx` | Same pattern |
| `paths.results_dir` | Crossref results directory | `src/services/cross-reference/results` | `C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results` |

## 6. How Path Resolution Works

- `_resolve_path(raw_path)` converts relative paths to absolute against PROJECT_ROOT (which is `C:\Projects\Crawler\PROJECTS\`)
- If the path is already absolute (e.g., `C:/Data/Crawler/input`), it's used as-is
- All `paths.*` keys in pipeline_config.json are resolved through this function at startup
- Non-path config keys (scraper.*, classify.*, etc.) are passed through without resolution
- CLI `--config` flag can override the config file path

## 7. monitor_config.json Paths

| Key | Purpose | Default |
|-----|---------|---------|
| `watch_directory` | Network directory to monitor for new files | (configurable) |
| `output_directory` | Where to write classified files | (configurable) |
| `hardware_keywords_file` | Hardware keyword list path | Same as classify.hw_keywords_file |
| `software_keywords_file` | Software keyword list path | Same pattern |
| `non_instrument_keywords_file` | Non-instrument keyword list path | Same pattern |
