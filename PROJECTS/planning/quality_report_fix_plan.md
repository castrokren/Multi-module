# Implementation Plan: Quality Report Fixes (P1–P5)

**Current Score: 30/100 — CONCERNING**
**Goal:** Address critical/high-priority findings out of 18 discovered defects, targeting a score of ~**70/100 — NEEDS IMPROVEMENT**.

---

## P1: Deduplicate Cross-Reference Module (Expected Score Impact: +15)

**Goal:** Consolidate the 5 copies of `crossref_standalone_fast.py` into one primary canonical copy, fix the critical `timeout_handler` defect, and update all callers.

### Steps:

**1.1 Designate the New Layout as the Canonical Copy (0.5h)**
- **Decision:** `src/services/cross-reference/crossref_standalone_fast.py` (3187 lines) will be the canonical copy. Rationale: It includes the `crossref_utils.py` sibling module, has a `tests/` subdirectory, and is the path loaded by `pipeline.py`.
- The other 4 copies will be replaced with redirection stubs.

**1.2 Fix the Critical `timeout_handler` Defect (1h)**
- The `timeout_handler` function is defined twice in the file:
  - Line ~72: raises `TimeoutException` (custom exception at ~line 58)
  - Line ~128: raises `TimeoutError` (Python built-in) — this shadows the first.
- **Fix:** Remove the second `timeout_handler` definition (at ~line 128). Redirect the signal binding at ~line 2338 to the first handler. Verify that `TimeoutException` is correctly caught.
- **File:** `src/services/cross-reference/crossref_standalone_fast.py`

**1.3 Replace 4 of the 5 Copies with Redirection Stubs (1h)**
- Create stub files at the following locations, containing only:
  ```python
  import sys, pathlib
  _DIR = pathlib.Path(__file__).resolve().parent
  # Redirect to canonical copy
  _CANONICAL = _DIR.parent.parent / "src" / "services" / "cross-reference" / "crossref_standalone_fast.py"
  sys.path.insert(0, str(_CANONICAL.parent))
  from crossref_standalone_fast import *
  ```
  Adjust the relative path for `_CANONICAL` based on each stub's location.
- **Affected Files:**
  - `crossref_standalone_fast.py` (project root)
  - `Cross-reference/crossref_standalone_fast.py`
  - `Multi-module/PROJECTS/Cross-reference/crossref_standalone_fast.py`
  - `Multi-module/PROJECTS/src/services/cross-reference/crossref_standalone_fast.py`

**1.4 Update All Imports/References to Point to the Canonical Copy (1h)**
- **Files to Update:**
  - `Cross-reference/run_crossref_cli.py` (line 11) — update to point to the canonical path or use the stub.
  - `src/services/cross-reference/run_crossref_cli.py` (line 35) — this should already be correct, but verify it uses the local stub or imports correctly.
  - `tests/integration/test_pipeline_stages.py` (lines 55-56) — update path.
  - `test_crossref_fixes.py` (lines 58, 90, 139) — update paths.
  - `src/services/debug_crossref.py` (line 272) — update path.
  - `apply_crossref_fix.ps1` (line 5) — update path.
  - `push_crossref_fixes.ps1` / `.bat` — update paths.
  - All files in `Scraper_full/tests/*.py` and `src/services/scraper-full/tests/*.py` that reference `crossref_dir` — update to use stub-based paths.
- **Note:** The existing `sys.path.insert(0, str(_MODULE_DIR))` within `src/services/cross-reference/crossref_standalone_fast.py` **must be preserved**, as `pipeline.py` loads this file via `importlib` (which needs this path patching for dynamic loading setups). See AGENTS.md, "CrossRef import fix".

**1.5 Remove Redundant Copies of `Cross-reference/crossref_standalone.py` and Archived Files (1h)**
- This file (495 lines) is an older, standalone version not used by any active pipeline. Archive or delete it.
- Clean up unnecessary files in `src/services/cross-reference/archive/`.

**1.6 Verify No Regressions (1h)**
- Run: `python -m pytest src/services/cross-reference/tests/ -v`
- Run: `python -m pytest tests/ -v`
- Run: `python src/services/pipeline.py --dry-run`
- Run: `python Cross-reference/run_crossref_cli.py --help`
- Verify `test_duplicate_detection.py` still identifies this as a unified file.

**P1 Estimated Effort: ~4.5 hours**

---

## P2: Add Tests for Scraper Core (Expected Score Impact: +15)

**Goal:** Increase L1 coverage of `scraper_engine.py` from 17% to 60%.

### Steps:

**2.1 Refactor Scraper for Testability - Inject HTTP Session (2h)**
- **Current:** `_make_session()` internally creates `requests.Session()`; all discovery/download methods use this internal session.
- Abstract the session factory out of `_make_session()` to allow it to be mocked.
- Modify `ScraperEngine.__init__()` to accept an optional `session_factory` parameter (default: `lambda: requests.Session()`).
- This will enable tests to pass a factory that returns a `responses.RequestsMock` object.

**2.2 Add Tests for Scraper Discovery Chain (3h)**
- **Methods to cover:**
  - `_discover_via_sitemap()` — provide mock HTTP responses for `robots.txt` and sitemap XML.
  - `_discover_via_search()` — provide mock HTML for DuckDuckGo/Bing search results.
  - `_crawl_recursive()` — provide mock pages with HTML link structures.
  - `_crawl_supplier()` — orchestrates the above; test that it correctly dispatches to each discovery strategy.
- **Test scenarios:**
  - Normal discovery (PDF found on page 1).
  - Empty results (no PDF links).
  - HTTP errors (500, 404, timeouts).
  - Redirect loops.
  - Encoding errors (non-UTF-8 pages).
  - Page structure changes (unexpected HTML).

**2.3 Add Tests for PDF Download Logic (2h)**
- **Methods to cover:**
  - `_download_pdf()` — mock HEAD requests + streaming GET requests.
  - `_should_download()` — use allowlist/blocklist/keyword scoring.
  - Size validation (file too big/small).
  - Type validation (Content-Type not `application/pdf`).
  - Deduplication (`_StateDB.is_seen` / `mark_seen`).
  - Partial downloads (connection interrupted).
- Use the `responses` library for HTTP mocking (add to dev dependencies if not already there).

**2.4 Add Tests for 7-Day Smart Detection Logic (1h)**
- `_load_scrape_state()`, `_save_scrape_state()`, `_is_due()`
- Use a temporary directory and mock file system.
- Scenarios: expired state file, fresh state file, no state file, corrupted state JSON.

**2.5 Add Tests for Keyword Loading and Webpage Keyword Checking (0.5h)**
- `_load_keywords()` — file exists, file missing, empty file.
- `_check_page_keywords()` — keywords match, no match, partial match.

**P2 Estimated Effort: ~8.5 hours**

---

## P3: Add pipeline.py Integration Tests (Expected Score Impact: +10)

**Goal:** Increase `pipeline.py` L1 coverage to 70% and L2 coverage to 60%.

### Steps:

**3.1 Refactor Stage Runners for Testability (1h)**
- **Current:** `run_data_cleaner()`, `run_scraper()`, `run_classify()`, etc., each call `_import_from_file()` then instantiate the module.
- Extract a generic `_run_stage(cfg, stage_name, stage_config)` helper function to facilitate testing of single-stage execution flow.
- Make stage discovery an injectable dependency (for mock stages in tests).

**3.2 Add Tests for Stage Sequencing and Config Loading (1.5h)**
- Test that `main()` correctly reads `pipeline_config.json`.
- Test that CLI flags like `--only-scraper`, `--only-classify` correctly enable/disable stages.
- Test that `--dry-run` mode performs validation without executing stages.
- Test `stop-on-failure` logic — does a stage failure halt subsequent stages?

**3.3 Add Tests for Error Propagation (1h)**
- Mock a stage to throw an exception; verify error is caught and logged.
- Verify `stop_on_failure=True` halts the pipeline after a stage failure.
- Verify `stop_on_failure=False` allows the pipeline to continue.

**3.4 Add Integration Tests for `_normalized_config` Path Resolution (1h)**
- Test relative path resolution (from `pipeline_config.json`).
- Test absolute path overrides (from CLI args).
- Test path templating with `_path_subs`.
- Test invalid/missing paths fail gracefully.

**P3 Estimated Effort: ~4.5 hours**

---

## P4: Eliminate Dangerous Patterns (Expected Score Impact: +10)

**Goal:** Eliminate critical and high-severity runtime security risks.

### Steps:

**4.1 Replace `os._exit(1)` — Production Code Only (1h)**
- **File:** `src/services/cross-reference/crossref_standalone_fast.py` (line ~99)
- **Current context** (lines ~96-99):
  ```python
  import os
  import sys
  # Force terminate the process
  os._exit(1)
  ```
  This is in a global scope, terminating the process if `psutil` import fails.
- **Fix:** Replace `os._exit(1)` with a guard that logs the error and raises a `RuntimeError`:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.error("psutil import failed — multiprocessing management disabled")
  raise ImportError("psutil is required for cross-reference multiprocessing")
  ```
- **Do NOT** remove `os._exit(1)` from test files in `Scraper_full/tests/` (tests may have their own kill-this-process patterns for timeout watchdogs). However, consider implementing safer alternatives for watchdog threads in `Scraper_full/tests/`.

**4.2 Fix Bare `except:` in `src/services/cross-reference/crossref_standalone_fast.py` (2h)**
- There are ~27 bare `except:` statements in this file.
- **Fix:** At a minimum, upgrade them to `except Exception:` (this still catches `KeyboardInterrupt` and `SystemExit`, but is a manageable improvement).
- For each, assess if it should be further narrowed:
  - `except (pdfplumber.PDFSyntaxError, IndexError, KeyError):` for PDF parsing blocks.
  - `except OSError:` for file operations.
  - `except requests.exceptions.RequestException:` for network calls.
- Apply this fix to the canonical `crossref_standalone_fast.py`.

**4.3 Fix Bare `except:` in `Cross-reference/crossref_recovery.py` and `instrument_labeling_manager.py` (1.5h)**
- `crossref_recovery.py`: ~9 bare `except:` statements. Apply similar specific exception handling.
- `instrument_labeling_manager.py`: ~3 bare `except:` statements. Apply specific exception handling.

**4.4 Restructure `sys.path.insert` Hacks — Focus on Production Code (2.5h)**
- **Problem:** ~15 production/script files use `sys.path.insert` or `sys.path.append`. This creates brittle import paths.
- **Fix:**
  - For entry points like `run_full_scraper.py`, `verify_dedup.py`, `test_scraper_run.py`: use relative imports based on a properly structured `PYTHONPATH` or move logic into a package. Avoid `sys.path.insert` from root scripts if possible.
  - For module-internal `sys.path.insert` (e.g., `column_filter_and_classify.py`, `pdf_discovery_pipeline.py`, `Updated_Monitor_UI.py`):
    - **Long-term:** Refactor these modules into proper Python packages with `__init__.py` files and relative imports.
    - **Short-term:** For `column_filter_and_classify*.py` (lines ~14), consider if `from . import classify` or `from ..classify import ...` is appropriate, assuming the `classify` directory is a package.
    - For `crossref_standalone_fast.py` (line ~15): As noted in P1.4, this **must be preserved** due to `importlib` loading. Document this as an acceptable deviation.
    - For `src/services/classify/pdf_discovery_pipeline.py` (line ~118): `sys.path.insert(0, str(self.scraper_engine_path.parent))` is concerning. Abstract `scraper_engine_path` as a configurable dependency or ensure it's on `PYTHONPATH`.
- Prioritize fixing `sys.path.insert` in production code. Test files can be less stringent for now, but note for future cleanup.

**P4 Estimated Effort: ~7 hours**

---

## P5: Eliminate Path Drift (Expected Score Impact: +5)

**Goal:** Centralize and validate all external/production paths to prevent environment-specific breakage.

### Steps:

**5.1 Move Hardcoded `C:\Data\Crawler\` Paths to `pipeline_config.json` (2h)**
- **Files Affected:** ~12 production files (e.g., `run_full_scraper.py`, `column_filter_and_classify*.py`, `scraper_engine.py`, `crossref_standalone_fast.py`, various `src/services/...` utilities).
- **Fix:**
  - In `pipeline_config.json`, ensure all `C:/Data/Crawler` paths are correctly defined (e.g., `paths.pdf_dir`, `paths.input_excel_dir`, `paths.labeled_dir`). These already exist, but consolidate all references here.
  - Modify code to read these paths from `pipeline_config.json` via the `pipeline.py` config loader. Use `pathlib` for path manipulation.
  - Examples:
    - Replace `open("C:\\Data\\Crawler\\labeled\\hardware_keywords_ACTIVE.txt", ...)` with `open(cfg.paths.labeled_dir / "hardware_keywords_ACTIVE.txt", ...)`
    - Replace hardcoded `C:/Data/Crawler/output` with `cfg.paths.pdf_dir`

**5.2 Address UNC Path in `classify/config.py` (0.5h)**
- **File:** `C:\Projects\Crawler\PROJECTS\src\services\classify\config.py` (line ~14)
- **Fix:** Replace `"\\\\\\\\research-cifs.nyumc.org\\\\omero_dev\\\\kren\\\\SOM_in"` with a configurable entry in `pipeline_config.json`. This should likely be part of the `classify` stage configuration.

**5.3 Address Hardcoded `D:\SOM_in_labeled` Paths (1h)**
- **Files Affected:** ~5 production files (e.g., `adaptive_excel_processor.py`, `Updated_Monitor_UI.py`).
- **Fix:** Similar to `C:\Data\Crawler` paths, abstract these into `pipeline_config.json` (e.g., `paths.alternate_labeled_dir` or `classify.labeled_input_dir`) and read them programmatically.

**5.4 Validate All Config Paths at Pipeline Startup (1h)**
- **File:** `pipeline.py` (within `_validate_paths` or a new `_validate_external_paths` function).
- **Fix:** Extend existing path validation to cover all newly centralized paths in `pipeline_config.json`. Check for existence and correct type (directory).
- Add logging for missing/invalid paths.

**5.5 Clean Up Stale User Paths (`castrk05_adm`) from Test Files (0.5h)**
- **Files Affected:** ~10 test files in both `Scraper_full/tests/` and `src/services/scraper-full/tests/`.
- **Fix:** Replace these hardcoded user paths with relative paths, temporary test directories, or paths derived from a common test config.

**P5 Estimated Effort: ~5 hours**

---

**Total Estimated Implementation Effort (Initial Pass): ~29.5 hours**

---
