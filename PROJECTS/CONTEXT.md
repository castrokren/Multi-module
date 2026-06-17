# Crawler Projects — Current Status

**Last updated:** 2026-05-22

## Project Overview

Python-based document scraping, classification, and cross-reference workflow. The system extracts and enriches supplier/vendor data through OCR, classification into three semantic categories (Hardware/Software/Non-Instrument), and cross-referencing against known patterns. Production-ready with automated deployment system.

---

## Current State (Updated May 18, 2026)

### Active Status
- **Classification (Phase 1):** ✅ Working — adaptive_excel_processor running smoothly
- **Cross-Reference (Phase 2):** ✅ Working — Import fix verified on remote machines (5/14)
- **Scraper (Phase 3):** ✅ Working — 7-day smart detection reducing runtime 2h → 10min (5/14)
- **Deployment:** ✅ Automated — Task Scheduler daily updates at 6:00 AM

### Recent Wins
1. **CrossRef Import Error (5/14)** — Fixed ModuleNotFoundError in dynamic import by adding sys.path setup to crossref_standalone_fast.py
2. **7-Day Smart Detection (5/14)** — Implemented supplier cache (`.scraper_state.json`) to skip recent scrapes, reducing pipeline runtime by 95%
3. **Deployment Automation (5/14)** — Auto-updater script with Task Scheduler, zero-downtime updates via GitHub

### Known Issues (Not Blocking)
- **Code Redundancy:** 4 monitor variations exist; need consolidation (not critical for Phase 1)
- **Hardcoded Paths:** Some paths in code, should migrate to config.ini
- **Limited Tests:** 2 test files only; should expand adaptive_excel_processor coverage

---

## Workspace Details

### Classification Workspace
**Purpose:** Auto-classify documents into Hardware/Software/Non-Instrument

**Core Files:**
- `adaptive_excel_processor.py` (698 lines) — PRIMARY, smart Excel processing with self-learning
- `Updated_Monitor_UI.py` (41KB) — Modern GUI for monitoring classifications
- `simple_monitor.py` (123 lines) — File watcher using watchdog library
- `config.py` — Centralized configuration
- `process_all_files.py` — Batch processing utility

**Pipeline Command:**
```bash
cd PROJECTS/src/services
py pipeline.py --only-classify    # Classification stage only
```

**Performance:** ~50 items/min (single processor baseline)

**Next Phase:** Consolidate 4 monitor variations, expand test coverage

---

### Cross-Reference Workspace
**Purpose:** Link PDFs to institutional records and patterns

**Core Files:**
- `crossref_standalone.py` — PRIMARY, PDF cross-referencing engine
- `crossref_recovery.py` — Resumable operations & error recovery
- `run_crossref_cli.py` — CLI interface
- `check_progress.py` — Progress tracking

**Pipeline Command:**
```bash
py pipeline.py --only-crossref    # Cross-ref stage only (test)
```

**Performance:** ~30 PDFs/min with validation

**Last Fix:** Import error resolved (5/14) — all Stage 3 operations now complete

---

### Scraping Workspace
**Purpose:** Web crawl and download PDFs from suppliers

**Core Files:**
- `pdf_crawler_gui.py` — Web scraping & PDF download UI
- `scraper_engine.py` — Core scraping logic with 7-day detection
- `.scraper_state.json` — State file tracking last-scrape timestamps per supplier

**Pipeline Command:**
```bash
py pipeline.py --only-scraper     # Scraper stage only (re-download)
py pipeline.py --skip-scraper     # Skip scraper, test new classification data
```

**Performance:** ~10 PDFs/min with concurrent connections

**Smart Detection (5/14):**
- Enabled: `skip_recent_sites: true` in pipeline_config.json
- Threshold: `days_before_rescrape: 7` (configurable)
- Impact: Subsequent runs ~2h → ~10min

---

### Deployment Workspace
**Purpose:** Automated CI/CD with zero-downtime updates

**Core Files:**
- `update.bat` — Auto-updater (checks GitHub daily, deploys updates)
- `setup_deployment.ps1` — Task Scheduler setup (run as Administrator)
- `DEPLOYMENT.md` — Full documentation
- `logs/deployment.log` — Deployment log
- `logs/.last_deployed_hash` — State tracking

**How It Works:**
1. Daily at 6:00 AM, update.bat runs `git fetch origin main`
2. Compares current commit hash with remote
3. If outdated, creates timestamped backup then runs `git pull origin main`
4. Verifies critical files exist post-deploy
5. Logs all activity to deployment.log

**Current Git Status:**
- Commit: 2d3b83f
- Message: "Deploy: Add 7-day smart detection for scraper and cross-ref import fix"
- Files deployed:
  - PROJECTS/src/services/scraper-full/scraper_engine.py
  - PROJECTS/src/services/pipeline.py
  - PROJECTS/src/services/pipeline_config.json

---

## Configuration Reference

### Main Settings (config.ini)
```ini
[Classify]
watch_directory = path/to/watch
output_directory = path/to/output
hardware_keywords_file = keywords_hw.txt
software_keywords_file = keywords_sw.txt
confidence_threshold = 0.7
learning_enabled = true
process_timeout = 30

[Scraper]
skip_recent_sites = true
days_before_rescrape = 7
```

### Pipeline Commands (Full Ref)
```bash
cd PROJECTS/src/services

py pipeline.py                      # All stages (Scraper → Classify → CrossRef)
py pipeline.py --only-scraper      # Stage 1 only
py pipeline.py --only-classify     # Stage 2 only (if data exists)
py pipeline.py --only-crossref     # Stage 3 only
py pipeline.py --skip-scraper      # Skip Stage 1, test Classify+CrossRef
```

### Individual Module Commands (Legacy)
```bash
# CLASSIFY
python PROJECTS/Classify/Updated_Monitor_UI.py

# CROSS-REFERENCE
python PROJECTS/Cross-reference/run_crossref_cli.py

# SCRAPER
python PROJECTS/Scraper_full/pdf_crawler_gui.py
```

---

## Development Priorities (Phase 1)

### 1a. Code Audit & Deduplication (Stability) 🔴 CRITICAL
- [ ] Consolidate 4 monitor variations (simple_monitor, standalone_monitor, service_script, simple_W_service)
- [ ] Keep adaptive_excel_processor, deprecate excel_processor.py
- [ ] Archive /older directory (don't delete)

### 1b. Testing & Stability ⚠️ HIGH
- [ ] Expand adaptive_excel_processor tests (currently minimal)
- [ ] Add error handling tests for edge cases
- [ ] Test all extensions (.xls, .xlsx, .csv)

### 1c. Performance Optimization ⚠️ MEDIUM
- [ ] Profile adaptive_excel_processor keyword matching
- [ ] Optimize regex for HW/SW/NI detection
- [ ] Add classification caching for repeats

### 1d. Maintainability ⚠️ MEDIUM
- [ ] Refactor into sub-modules (processors, monitor, service, ui)
- [ ] Add type hints across all modules
- [ ] Create CLASSIFY_MODULE.md documentation

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Classification Speed | ~50 items/min | Single processor baseline |
| Cross-ref Speed | ~30 PDFs/min | With institutional validation |
| Scraper Speed | ~10 PDFs/min | With concurrent connections (3-5 threads) |
| Pipeline Full Run | ~2 hours | Initial run with scraper |
| Pipeline Subsequent | ~10 minutes | With 7-day smart detection |
| Test Coverage | 2 files | Should expand to adaptive_excel_processor |

---

## Directory Structure (Active Only)

```
PROJECTS/
├── Classify/                    # Classification workspace
│   ├── adaptive_excel_processor.py    (698 lines, PRIMARY)
│   ├── Updated_Monitor_UI.py          (41KB modern GUI)
│   ├── simple_monitor.py              (123 lines, watchdog)
│   ├── config.py
│   ├── process_all_files.py
│   ├── older/                         (legacy, archive)
│   └── tests/
│
├── Cross-reference/             # Cross-reference workspace
│   ├── crossref_standalone.py         (PRIMARY)
│   ├── crossref_recovery.py           (error recovery)
│   ├── run_crossref_cli.py
│   ├── check_progress.py
│   └── check_results.py
│
├── Scraper_full/                # Scraping workspace
│   ├── pdf_crawler_gui.py             (UI)
│   ├── scraper_engine.py              (7-day detection)
│   └── download logic files
│
├── src/services/                # Deployment workspace
│   ├── pipeline.py                    (orchestrator)
│   ├── pipeline_config.json           (master config)
│   └── scraper-full/
│
├── CLAUDE.md                    (routing map)
├── CONTEXT.md                   (this file, current state)
├── REFERENCES.md                (terminology & voice)
├── DEPLOYMENT.md                (deployment docs)
├── update.bat                   (auto-updater)
├── setup_deployment.ps1         (scheduler setup)
└── logs/                        (deployment logs)
```

---

## Memory & Context Files

- **CLAUDE.md** — Routing map (this project)
- **CONTEXT.md** — Current state & workspace details (this file)
- **REFERENCES.md** — Terminology, voice, standards
- **/memory/MEMORY.md** — Session-persistent memory index
- **/memory/*.md** — Individual memory files (fixes, features, status)

---

## Next Steps (When Ready)

1. **Test Expansion** — Add comprehensive tests to adaptive_excel_processor
2. **Monitor Consolidation** — Merge 4 monitor variations into single Updated_Monitor_UI
3. **Path Portability** — Migrate hardcoded paths to config.ini with env variables
4. **Documentation** — Create CLASSIFY_MODULE.md and workspace-specific guides
5. **Performance** — Profile and optimize keyword matching in classification

---

## Success Criteria

- ✅ All pipeline stages complete without error
- ✅ CrossRef import working on remote machines
- ✅ 7-day smart detection reducing runtime 95%
- ✅ Deployment automation verified (6/day at 6:00 AM)
- ⚠️ Test coverage needs expansion (currently 2 files)
- ⚠️ Code consolidation needed (4 monitors → 1)

---

**Project Status:** Production-Ready (Phase 1 Complete)  
**Last Session:** May 22, 2026  
**Next Review:** May 29, 2026
