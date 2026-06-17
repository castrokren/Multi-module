# Crawler Project — Terminology & Standards

**Last updated:** 2026-05-18

## Glossary (Classification Focus)

### Core Classification Terms

| Term | Definition | Example |
|------|-----------|---------|
| **HW** | Hardware — physical instruments, equipment, devices | Microscope, spectrometer, computer workstation |
| **SW** | Software — licenses, applications, digital tools | MATLAB, Adobe Creative Suite, database license |
| **NI** | Non-Instrument — office supplies, furniture, consumables | Paper, pens, desk chairs, cleaning supplies |
| **Confidence Score** | Probability (0-1) of classification accuracy | 0.95 = high confidence, 0.55 = borderline |
| **Learning Log** | JSON file tracking borderline cases for continuous improvement | `learning_log.json` in output directory |
| **Vendor Intelligence** | Recognition of vendor names for accurate HW/SW classification | Knowing "Dell" = hardware vendor, "Adobe" = software |
| **Adaptive Learning** | Self-learning system improving classification accuracy over time | System tracks and learns from manual corrections |
| **Watch Directory** | Source folder monitored for new Excel files to classify | Configured in config.ini `watch_directory` |
| **Output Directory** | Destination for classified results and logs | Configured in config.ini `output_directory` |
| **Confidence Threshold** | Minimum score to auto-classify; below triggers manual review | Default: 0.7 (70%) |

---

### Pipeline & Architecture Terms

| Term | Definition | Context |
|------|-----------|---------|
| **Stage 1: Scraper** | Web crawl & download PDFs from supplier sites | `pdf_crawler_gui.py`, concurrent downloads with retry |
| **Stage 2: Classify** | Auto-classify documents into HW/SW/NI | `adaptive_excel_processor.py`, 50 items/min |
| **Stage 3: CrossRef** | Link PDFs to institutional records & vendor patterns | `crossref_standalone.py`, 30 PDFs/min |
| **7-Day Smart Detection** | Feature skipping suppliers scraped < 7 days ago | Reduces runtime 95% on subsequent runs |
| **State File** | Persisted JSON tracking scraper metadata | `.scraper_state.json`, timestamp per supplier |
| **Pipeline** | Orchestrator running all three stages | `pipeline.py`, entry point |

---

### Configuration Terms

| Term | Definition | File |
|------|-----------|------|
| **config.ini** | Master configuration file with all settings | `PROJECTS/config.ini` |
| **keywords_hw.txt** | Hardware keyword list for classification | Updated by learning system |
| **keywords_sw.txt** | Software keyword list for classification | Updated by learning system |
| **keywords_ni.txt** | Non-Instrument keyword list for classification | Updated by learning system |
| **pipeline_config.json** | Pipeline-specific settings (skip_recent_sites, days_before_rescrape) | `PROJECTS/src/services/pipeline_config.json` |

---

### Deployment Terms

| Term | Definition | Location |
|------|-----------|----------|
| **Auto-Updater** | Script checking GitHub daily for updates | `PROJECTS/update.bat` |
| **Task Scheduler** | Windows service running auto-updater at 6:00 AM daily | Set up by `setup_deployment.ps1` |
| **Deployment Log** | Record of all auto-update runs | `PROJECTS/logs/deployment.log` |
| **Backup** | Timestamped snapshot created before each deploy | Auto-retained (last 5 only) |
| **Commit Hash** | Git identifier for current deployed version | Checked daily against remote |

---

## Project Voice & Standards

### Writing Style for Documentation

**Tone:** Direct, technical, operator-focused. Assume Python competence; explain system architecture clearly.

**Structure:**
- Lead with purpose ("Why are we doing this?")
- Follow with action ("What do we do?")
- Close with verification ("How do we know it worked?")

**Examples:**

✅ Good: "Classification needs confidence >0.7 to auto-assign. Below 0.7, items go to manual review queue. Check learning_log.json for borderline cases."

❌ Avoid: "The system classifies things. Sometimes it's not sure. You might need to look at a log file."

---

### Naming Conventions

**Files:**
- Core logic: `{module}_processor.py` or `{module}_engine.py`
- UIs: `{module}_UI.py` or `{module}_gui.py`
- Utilities: `{module}_utils.py` or `run_{module}_cli.py`
- Tests: `test_{feature}.py`
- Config: `config.ini` or `{module}_config.json`

**Variables & Functions:**
- Classification results: `classifications`, `confidence_scores`, `classification_log`
- File lists: `pdf_list`, `excel_files`, `supplier_urls`
- State/tracking: `last_scrape_date`, `processed_count`, `error_log`

**Directories:**
- Working code: `{MODULE}/`
- Legacy code: `{MODULE}/older/` (archive, don't delete)
- Tests: `tests/unit/`, `tests/integration/`
- Config: `config/` or at root level
- Output: `output/` or `results/`
- Logs: `logs/`

---

### Code Standards

**Error Handling:**
- All file operations use try/except with logging
- CrossRef operations are resumable (recovery.py pattern)
- Scraper has retry logic with exponential backoff

**Logging:**
- Log level: INFO for key milestones, WARNING for edge cases, ERROR for failures
- Format: `[TIMESTAMP] [LEVEL] {module}: message`
- Destination: log file + console (configurable)

**Testing:**
- Unit tests for classification accuracy (keyword matching, confidence scoring)
- Integration tests for full pipeline runs
- Regression tests for known edge cases (multiline text, vendor aliases)

---

## Quick Reference: Which Module Does What?

### I want to... → Go to...

| Need | Module | File | Command |
|------|--------|------|---------|
| Classify Excel file | Classify | `adaptive_excel_processor.py` | `python Updated_Monitor_UI.py` |
| Link PDFs to records | CrossRef | `crossref_standalone.py` | `python run_crossref_cli.py` |
| Download PDFs | Scraper | `pdf_crawler_gui.py` | `python pdf_crawler_gui.py` |
| Run full pipeline | Services | `pipeline.py` | `python pipeline.py` |
| Fix import error | CrossRef | `crossref_standalone_fast.py` | (line 8-15 sys.path setup) |
| Check scraper state | Scraper | `.scraper_state.json` | (JSON file, human-readable) |
| Deploy updates | Services | `update.bat` / `setup_deployment.ps1` | (Task Scheduler, 6 AM daily) |
| Understand status | This Project | `CONTEXT.md` | (full state snapshot) |

---

## Project Phases (Reference)

**Phase 1: Classification (Current — May 2026)**
- ✅ Build adaptive_excel_processor
- ✅ Implement HW/SW/NI classification
- ✅ Add file monitoring and batch processing
- ⚠️ Expand test coverage (in progress)

**Phase 2: Cross-Reference (Complete — May 14, 2026)**
- ✅ Build PDF cross-referencing engine
- ✅ Implement error recovery system
- ✅ Fix import error (resolved 5/14)

**Phase 3: Scraping (Complete — May 14, 2026)**
- ✅ Build web scraper with concurrent downloads
- ✅ Implement 7-day smart detection (resolved 5/14)

**Phase 4: Deployment (Complete — May 14, 2026)**
- ✅ Build auto-updater with GitHub integration
- ✅ Set up Task Scheduler automation

**Phase 5 (Future): Optimization**
- Code audit and consolidation
- Performance profiling
- Extended test coverage

---

## Success Metrics by Module

### Classification Module
- Speed: ~50 items/min (single processor)
- Accuracy: >90% for common vendors
- Coverage: HW/SW/NI correctly identified
- Confidence: Threshold 0.7 catches 95% of borderline cases

### Cross-Reference Module
- Speed: ~30 PDFs/min (with validation)
- Coverage: Links 98%+ of PDFs to records
- Recovery: Can resume from any point without data loss

### Scraper Module
- Speed: ~10 PDFs/min (concurrent, 3-5 threads)
- Smart Detection: 95% runtime reduction on day 2+
- Reliability: Retry logic handles 99% of transient failures

### Pipeline (Full System)
- First run: ~2 hours (with web scraping)
- Subsequent runs: ~10 minutes (7-day detection active)
- Deployment: Zero-downtime updates, auto-verified

---

## Common Tasks (Quick Lookup)

### "I found a classification error"
→ See learning_log.json in output directory  
→ Update keywords_hw.txt / keywords_sw.txt  
→ Re-run pipeline with `--skip-scraper` flag  
→ Verify correction in next output

### "CrossRef crashed mid-run"
→ Check crossref_recovery.py — it auto-resumes  
→ Run `python run_crossref_cli.py` again  
→ Check logs for error details

### "Scraper is taking too long"
→ Check .scraper_state.json — is 7-day detection enabled?  
→ Verify pipeline_config.json has `skip_recent_sites: true`  
→ First run is slow (~2h); subsequent runs ~10min

### "I need to deploy a fix"
→ Push to GitHub main branch  
→ update.bat runs at 6:00 AM next day  
→ Or manually run update.bat for immediate deploy  
→ Check logs/deployment.log to verify

### "I don't know where a file is"
→ See CONTEXT.md → Directory Structure  
→ Or search PROJECTS/ for filename

---

## Related Resources

- **CLAUDE.md** — Routing map (where to go for what)
- **CONTEXT.md** — Full project state and workspace details
- **DEPLOYMENT.md** — Detailed deployment & auto-updater docs
- **/memory/MEMORY.md** — Session-persistent findings

---

**Document Purpose:** Ground-truth reference for terminology, voice, and standards  
**Last Updated:** 2026-05-18  
**For questions:** See CONTEXT.md or CLAUDE.md routing table
