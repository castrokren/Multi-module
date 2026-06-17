# Crawler Project - Full Glossary

Complete decoder ring for all terms, acronyms, and project-specific language.

---

## Acronyms & Abbreviations

| Acronym | Meaning | Context | Status |
|---------|---------|---------|--------|
| **HW** | Hardware | Classification category - physical instruments/equipment | Active |
| **SW** | Software | Classification category - licenses/applications | Active |
| **NI** | Non-Instrument | Classification category - office supplies/furniture/consumables | Active |
| **CSV** | Comma-Separated Values | Data export format | Active |
| **JSON** | JavaScript Object Notation | Config & data files (learning_log.json) | Active |
| **XLS** | Microsoft Excel 97-2003 | Legacy spreadsheet format supported | Active |
| **XLSX** | Microsoft Excel 2007+ | Modern spreadsheet format (primary) | Active |
| **GUI** | Graphical User Interface | Updated_Monitor_UI.py | Active |
| **CLI** | Command-Line Interface | run_crossref_cli.py, text-based tools | Active |
| **PDF** | Portable Document Format | Document format for cross-ref & scraping | Active |

---

## Core Terminology (CLASSIFY Module)

| Term | Definition | Examples |
|------|-----------|----------|
| **Classification** | Automatic categorization of items into HW/SW/NI | "Classify this spreadsheet of 500 items" |
| **Confidence Score** | Probability (0.0-1.0) that classification is correct | 0.95 = very confident, 0.6 = borderline |
| **Keyword Matching** | Algorithm finding keywords in item names/descriptions | "Microscope" → HW, "Microsoft Office" → SW |
| **Adaptive Learning** | System learns from patterns to improve future classifications | Tracks borderline cases in learning_log.json |
| **Learning Log** | JSON file recording classifications for analysis & improvement | `learning_log.json` in Classify/ directory |
| **Vendor Intelligence** | Recognition of vendor/manufacturer names for context | "Dell" → likely HW, "Adobe" → likely SW |
| **Watch Directory** | Source folder monitored for new Excel files to classify | Set in config.ini: `watch_directory` |
| **Output Directory** | Destination folder where classified results are saved | Set in config.ini: `output_directory` |
| **Confidence Threshold** | Minimum score required to auto-classify (vs manual review) | Default: 0.7 (70% confidence) |

---

## Cross-Reference Module Terminology

| Term | Definition |
|------|-----------|
| **Cross-Reference** | Link between a PDF document and institutional record/instrument |
| **Instrument Labeling** | Process of identifying and marking instruments in PDFs |
| **Cross-ref Mapping** | Output file showing PDF-to-record relationships |
| **Recovery** | Ability to resume interrupted operations without restart |
| **Progress Tracking** | Real-time visibility into cross-ref operation status |
| **Validation** | Verification that cross-references are correct and complete |

---

## Scraper Module Terminology

| Term | Definition |
|------|-----------|
| **Web Crawling** | Automated traversal of websites to find PDF resources |
| **Concurrent Downloads** | Multiple PDFs downloaded simultaneously for speed |
| **Retry Logic** | Automatic retry of failed downloads (network errors, timeouts) |
| **Smart Timeout** | Intelligent timeout handling for slow/flaky connections |
| **Content Filtering** | Excluding non-relevant PDFs from download |
| **Progress Reporting** | Status updates during scraping operations |

---

## File/Directory Terms

| Term | Meaning |
|------|---------|
| **adaptive_excel_processor.py** | PRIMARY processor - intelligently classifies Excel with self-learning |
| **simple_monitor.py** | Core file watcher using watchdog library |
| **Updated_Monitor_UI.py** | Modern GUI for monitoring classification operations |
| **excel_processor.py** | Legacy processor (deprecated, use adaptive version) |
| **service_script.py** | Windows service wrapper (legacy, likely redundant) |
| **standalone_monitor.py** | Independent monitor (legacy, evaluate for removal) |
| **simple_W_service.py** | Monitor with service capabilities (evaluate necessity) |
| **/older/** | Archive directory with legacy/deprecated code |
| **/tests/** | Unit & integration tests (limited coverage: 2 files) |
| **learning_log.json** | JSON file tracking borderline classifications |
| **keywords_hw.txt** | Hardware keyword list |
| **keywords_sw.txt** | Software keyword list |
| **keywords_ni.txt** | Non-Instrument keyword list |
| **config.ini** | Central configuration (paths, thresholds, parameters) |
| **config.py** | Python config module (Classify/) |

---

## Status Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Active, in use, working well |
| 🔴 | Critical issue or high priority |
| ⚠️ | Medium priority, needs attention |
| 📋 | Planned/pending (not active yet) |
| ❌ | Deprecated, should be removed/archived |

---

## Performance Baselines

| Operation | Speed | Conditions |
|-----------|-------|-----------|
| Classification | ~50 items/min | Single processor, avg Excel row |
| Cross-reference | ~30 PDFs/min | With validation checks |
| PDF Scraping | ~10 PDFs/min | Concurrent connections, retries |

---

## Configuration Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `confidence_threshold` | 0.7 | Min score for auto-classification |
| `learning_enabled` | true | Enable adaptive learning |
| `process_timeout` | 30s | Max time per Excel file |
| `watch_directory` | [config.ini] | Source folder for monitoring |
| `output_directory` | [config.ini] | Destination for results |

---

## Project Metadata

| Field | Value |
|-------|-------|
| **Project Name** | PDF Crawler & Classification System |
| **Author** | Kren Castro (castrokren@gmail.com) |
| **Current Version** | 1.0.0 |
| **Last Updated** | May 5, 2026 |
| **Phase** | 1 (Classification module optimization) |
| **Repository** | Local C:\Projects\Crawler\PROJECTS |

---

## Last Reviewed
May 14, 2026
