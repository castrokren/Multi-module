# Fix Plan

**Written:** 2026-09-01  
**Based on:** STATE.md audit + codebase inspection  
**Verification baseline:** `pytest --collect-only -q` → 479 collected / 5 errors; `pytest src/services/cross-reference/tests/unit -q` → 105 passed

Run both verification commands before and after each section to confirm nothing regressed.

---

## Issue 1 — `\r\r\n` line-ending corruption in 44 `.py` files

**Severity:** High — latent. Any backslash continuation added to one of the 44 affected files will break the module silently. One file (`adaptive_excel_processor.py`) already broke and had to be patched manually.

**Root cause:** The emoji-to-ASCII sweep (`fb78256`) ran under a git config that had no `* text=auto` normalization, so `\r\n` endings became `\r\r\n`. Python's tokenizer reads the bare `\r` as a line terminator, making the logical line shorter than intended.

**Affected files (confirmed by byte scan):**

Pipeline-critical files with `\r\r\n`:
- `src/services/data-cleaning/data_cleaner.py`
- `src/services/classify/Updated_Monitor_UI.py`
- `src/services/classify/test_adaptive_processor.py`
- `src/services/classify/test_xls_support.py`
- `src/services/cross-reference/run_crossref_cli.py`
- `src/services/cross-reference/tests/unit/test_crossref_standalone_fast.py`
- `src/services/supplier-resolution/tests/unit/test_confidence_scorer.py`
- Plus ~36 additional files in `archive/`, debug scripts, and scraper tests

**Fix steps:**

**Step 1a — Add `.gitattributes`** (do this first, before touching any file content)

Create `PROJECTS/.gitattributes`:
```
# Normalize all text files to LF in the repository; checkout with native endings.
* text=auto
*.py text eol=lf
*.md text eol=lf
*.json text eol=lf
*.txt text eol=lf
*.ini text eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

Without this, re-normalizing now and then running another sweep in the future would reproduce the problem.

**Step 1b — Re-normalize the 44 affected files**

Run from `PROJECTS/`:
```powershell
git add --renormalize .
git status  # confirm only line-ending changes, no content changes
git commit -m "fix: normalize line endings (remove stray CR from emoji sweep)"
```

`--renormalize` re-applies `.gitattributes` rules to all tracked files. It only touches line endings, not content. Review `git diff --stat` before committing to confirm scope.

**Step 1c — Verify**

```powershell
pytest --collect-only -q  # must still show 479 collected / 5 errors (not more)
pytest src/services/cross-reference/tests/unit -q  # must still show 105 passed
```

---

## Issue 2 — 5 pytest collection errors

**Severity:** Medium — the test suite reports errors on startup, masking real failures. Three are trivially fixed by installing missing packages; two require small code changes.

**Current errors:**

| # | File | Error | Fix type |
|---|------|-------|----------|
| 1 | `test_watch_input.py` | `ModuleNotFoundError: watchdog` | Install package |
| 2 | `v2_monitor/tests/test_monitor.py` | `ModuleNotFoundError: watchdog` | Install package |
| 3 | `data-cleaning/tests/` (one file) | `ModuleNotFoundError: chardet` | Install package |
| 4 | `tests/` (one file) | `FileNotFoundError: ...NQ_DG_RESEARCH_CAPITAL...labeled.xlsx` | Fix test |
| 5 | `classify/tests/` (one file) | `FileNotFoundError: research_instrument_keywords.txt` | Fix path |

**Fix steps:**

**Step 2a — Install missing packages into `.venv_test`**

```powershell
.venv_test\Scripts\pip install -r src\services\requirements.txt
```

This installs `watchdog>=6.0` and `chardet`, clearing errors 1–3. Verify with:
```powershell
pytest --collect-only -q  # should now show 479 collected / 2 errors
```

**Step 2b — Fix the hardcoded machine-local data path (error 4)**

Locate the test file that references `C:\Data\Crawler\labeled\NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx`.

Replace the hardcoded path with a pytest skip guard:
```python
import pytest, os

DATA_FILE = r"C:\Data\Crawler\labeled\NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx"

@pytest.mark.skipif(not os.path.exists(DATA_FILE), reason="machine-local data file not present")
def test_something():
    ...
```

The test still runs on the machine where the data exists; it skips gracefully everywhere else. Do not fabricate a fixture unless the test logic can be meaningfully exercised with synthetic data.

**Step 2c — Fix the CWD-relative keyword file path (error 5)**

The failing test imports a module that opens `research_instrument_keywords.txt` relative to the current working directory. Change the path resolution to be relative to the source file:

```python
# Before (breaks when pytest runs from a different cwd)
kw_file = "research_instrument_keywords.txt"

# After
from pathlib import Path
kw_file = Path(__file__).resolve().parent / "research_instrument_keywords.txt"
```

Apply the same fix to `software_keywords.txt` and `non_instrument_keywords.txt` in the same file if present.

**Verify:**
```powershell
pytest --collect-only -q  # target: 479 collected / 0 errors
pytest -q                 # full suite should now run cleanly
```

---

## Issue 3 — Private key committed to git history

**Severity:** N/A — **Closed. No action required.**

`ops/key.pem` and `cert.pem` are local self-signed keys that were already rotated. The files are in git history but pose no security risk. History rewrite is not warranted.

If `.pem` files should be kept out of future commits, optionally add to `.gitignore`:
```
*.pem
```

---

## Issue 4 — Duplicate method definitions in `crossref_standalone_fast.py`

**Severity:** Medium — Python silently uses the last definition. The first definitions at lines 1325–1444 are stubs that return empty lists and print "Legacy method called". They are dead code that makes the file confusing and hard to maintain.

**Duplicate pairs:**

| Method | Stub (dead) | Real implementation |
|--------|-------------|---------------------|
| `find_matching_pdfs` | line 1325 | line 1446 |
| `find_matching_pdfs_high_performance` | line 1340 | line 1823 |
| `extract_keywords` | line 1352 | line 2194 |
| `process_pdfs_parallel` | line 1375 | line 2031 |

**Fix steps:**

**Step 4a — Confirm the real implementations**

Before deleting, verify the implementations at lines 1446, 1823, 2031, and 2194 are complete and not themselves stubs. From the code inspection:
- Line 1446: `find_matching_pdfs` — full supplier-directory search with 4 matching strategies ✓
- Line 1823: `find_matching_pdfs_high_performance` — full implementation with multiprocessing ✓
- Line 2031: `process_pdfs_parallel` — full `ProcessPoolExecutor` implementation ✓
- Line 2194: `extract_keywords` — full NLP tokenization implementation ✓

The stubs at 1325–1444 are explicitly commented "kept for compatibility" but they return empty lists, so they provide no compatibility value.

**Step 4b — Delete the four stub definitions (lines 1325–1444)**

The entire block from `def find_matching_pdfs` at line 1325 through the closing of `process_pdfs_parallel` at approximately line 1444 should be removed. This is roughly 120 lines of dead code.

After deletion, run the verification gate:
```powershell
pytest src/services/cross-reference/tests/unit -q  # must still show 105 passed
pytest --collect-only -q                            # must stay at same count
```

**Step 4c — (Optional, lower priority)** The outer function `process_pdfs_parallel_with_timeout` at line 86 (module level, outside the class) wraps `self.process_pdfs_with_recovery` but references `self` — it is a loose function, not a method, and will fail at runtime if called. Verify whether anything calls it; if not, remove it.

---

## Issue 5 — `check_dependencies.py` silent pip failure

**Severity:** Medium — on remote machines, dependency installation failures are invisible. The existing `check_dependencies_FIXED.py` exists but has not replaced the original.

**Root cause:** The current `check_dependencies.py` runs pip with `-q` (suppresses all output), does not capture stderr, and does not verify packages are importable after installation. A failed install looks identical to a successful one.

**Fix steps:**

**Step 5a — Promote the fixed version**

The fixed version already exists at `check_dependencies_FIXED.py`. Inspect it to confirm it:
- Removes `-q` so pip output is visible
- Captures stdout and stderr
- Verifies each package is importable after install
- Returns a non-zero exit code on any failure

If it passes inspection:
```powershell
Copy-Item check_dependencies_FIXED.py check_dependencies.py  # overwrite
git rm check_dependencies_FIXED.py
git commit -m "fix: promote check_dependencies fix; remove _FIXED copy"
```

**Step 5b — If the fixed version is incomplete**, apply these changes to `check_dependencies.py`:
```python
# Replace silent install call:
subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])

# With verbose, exit-checked call:
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "-q"],
    capture_output=True, text=True
)
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", pkg],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"[ERROR] Failed to install {pkg}:\n{result.stderr}")
    sys.exit(1)

# Then verify the import works:
try:
    __import__(pkg.replace("-", "_").split(">=")[0].split("==")[0])
    print(f"[OK] {pkg} installed and importable")
except ImportError:
    print(f"[ERROR] {pkg} installed but not importable - check package name mapping")
    sys.exit(1)
```

**Step 5c — Update `update.bat` / deployment scripts** to call `check_dependencies.py` and treat a non-zero exit as a deployment failure (halt, log, alert).

---

## Issue 6 — `archive/` directories and debug scripts

**Severity:** Low — dead code that adds noise to searches and makes the repo harder to navigate. No runtime impact.

**Confirmed archive directories (verified unreferenced, not collected by pytest):**
- `src/services/classify/archive/` — 8 files, ~45KB
- `src/services/cross-reference/archive/` — 2 files, ~40KB  
- `src/services/scraper-full/archive/` — 1 file, ~13KB
- `src/services/scraper-full/tests/archive/` — 7 files (debug_test, diagnose_stuck_pdf, emergency_stop, fix_stuck_pdf, nuclear_test, ultra_safe_test, windows_safe_test)

**Debug scripts in active directories** (not in archive, not real tests):
- `src/services/test_keyword_matching.py` — 0 test functions, errors on import
- `src/services/classify/test_processor.py` — 0 test functions, errors on import
- `src/services/scraper-full/simple_test.py`, `test_crawler_fix.py`, `minimal_scraper.py`, `scraper_no_single_check.py`, `debug_scraper.py` — debug scripts, not tests
- `src/services/cross-reference/quick_info.py`, `quick_status.py`, `quick_instrument_demo.py`, `simple_check.py`, `resume_analysis.py` — one-off debug scripts

**Fix steps:**

**Step 6a — Delete `archive/` directories**

Run the verification gate first to record the baseline, then:
```powershell
git rm -r src/services/classify/archive
git rm -r src/services/cross-reference/archive
git rm -r src/services/scraper-full/archive
git rm -r src/services/scraper-full/tests/archive
git commit -m "chore: delete archive/ directories (verified unreferenced)"
```

Run the verification gate again to confirm counts are unchanged (minus the archived files themselves, which should not have been collected).

**Step 6b — Move or delete loose debug scripts**

For scripts that will never be run again: `git rm` them. For scripts that are occasionally useful for ad-hoc diagnosis (e.g. `run_crossref_cli.py`, `check_progress.py`), leave them but add a comment at the top:
```python
# Diagnostic script — not part of the pipeline. Run manually only.
```

Minimum deletions (zero test functions, import errors):
```powershell
git rm src/services/test_keyword_matching.py
git rm src/services/classify/test_processor.py
git commit -m "chore: remove debug scripts masquerading as test files"
```

Do not touch `test_xls_support.py` — it has a real test function.

---

## Issue 7 — `WebScrapper.exe` / `Crawlers.exe` broken build specs

**Severity:** Low — the binaries are committed to the repo (96MB + smaller), taking up space in every clone. They cannot be rebuilt from current source because the `.spec` files reference wrong paths.

**Current state:**
- `WebScrapper.exe` (96MB) — `build_configs/WebScrapper.spec` names `pdf_crawler_gui_2.py` with `pathex=[]`, but the source lives in `scraper-full/`
- `PDF_Crawler_GUI.spec` — `datas` references 5 files, only 1 exists
- `Crawlers.exe` — present, no matching functional `.spec`

**Fix steps:**

**Step 7a — Fix the `.spec` files before touching the binaries**

Update `WebScrapper.spec`:
```python
# Change:
pathex=[]
# To:
pathex=['src/services/scraper-full']

# Change the source script reference from:
'pdf_crawler_gui_2.py'
# To:
'src/services/scraper-full/pdf_crawler_gui_2.py'
```

Fix `PDF_Crawler_GUI.spec` `datas` list to reference only files that exist. Remove the 4 missing entries or replace them with the correct paths.

Verify the build actually produces a working executable before removing the committed binary.

**Step 7b — Once a working build is confirmed**, remove the binary from the repo tip:
```powershell
git rm src/services/scraper-full/WebScrapper.exe
git rm src/services/scraper-full/Crawlers.exe
git commit -m "chore: remove pre-built executables; build from spec instead"
```

Add to `.gitignore`:
```
*.exe
*.spec.bak
dist/
build/
```

Note: removing the executables from the tip does not recover the 96MB from `.git` history. That requires `git filter-repo` — the same decision as Issue 3 option B. If you decide to run `git filter-repo` for the private key, do both purges in one pass.

---

## Execution order

The issues above are independent; any can be addressed in isolation. Recommended sequencing based on risk and dependency:

1. **Issue 1** (line endings + `.gitattributes`) — do first, before any other file edits, so future commits don't re-introduce the corruption
2. **Issue 2** (pytest collection errors) — fixes the test signal so regressions are visible during all subsequent work
3. **Issue 4** (crossref duplicate methods) — straightforward deletion; safe once Issue 2 is green
4. **Issue 5** (check_dependencies) — deploy-path fix; do before the next remote deployment
5. **Issue 6** (archive cleanup) — low risk, low urgency; batch into one commit
6. **Issue 7** (build specs + executables) — only needed if the GUI apps need to be shipped as executables

---

## Verification commands (reference)

```powershell
# From PROJECTS/
pytest --collect-only -q                            # collection health
pytest src/services/cross-reference/tests/unit -q   # crossref unit suite
pytest -q                                           # full suite
```
