# STATE — ponytail audit cleanup

## Goal
Remove the duplicate-copy bloat the ponytail audit found, without breaking the
pipeline or the test suite.

## Invariants / decisions
- `src/services/` is the canonical tree. `pipeline.py` resolves every stage
  through `SERVICES_ROOT`; `tests/conftest.py` puts only `src/services` on
  `sys.path`. Nothing else is on the runtime path.
- Verification gate for every deletion: `pytest --collect-only -q` must stay at
  **479 collected / 5 errors**, and `pytest src/services/cross-reference/tests/unit -q`
  must stay at **105 passed**. Run both before and after. (Was 408/9 before
  `2b195a5` repaired an unparseable module.)
- Repo size is a *history* problem, not a tip problem. `.git` is 154 MB, and
  158 MB of that is the two `.exe` blobs, still reachable from old commits.
  Deleting them from the tip reclaims **zero** bytes. Reclaiming needs
  `git filter-repo` across 37 branches — decided **not worth it**.
- `PROJECTS/.venv_test` was untracked with `git rm --cached`, not deleted. It
  is the interpreter the suite runs under. **Never `git clean -fdx`.**
- `Multi-module` is a git submodule (gitlink), a separate repo. Out of scope.
- Deliberate deletions are named explicitly by the user before execution.

## Done
- `826f14c` untrack `.venv_test` (6,392 files) + `.coverage`; gitignore `.venv*/`
- `efaf49b` gitignore agent/tool scratch (`.understand-anything/`, `.workflow/`)
- `10ee889` commit pre-existing WIP: single crawl engine + input watcher
- `bd5bb48` commit pre-existing WIP: crossref timeout suite + trimmed integration test
- `c4b996b` commit pre-existing WIP: emoji -> ASCII sweep
- `5dcb70f` commit pre-existing WIP: docs, runbook, decision record
- `168fe80` delete 4 duplicate trees (26 files, ~13,600 lines):
  `PROJECTS/Cross-reference/`, `PROJECTS/Scraper_full/`,
  `PROJECTS/crossref_standalone_fast.py`, root `ops/`
- `5fde9e9` delete spent one-shots `push_crossref_fixes.ps1`, `apply_crossref_fix.ps1`
- `cc9ccad` fix: custom `TimeoutError` no longer shadows the builtin
- `2b195a5` fix: repair `adaptive_excel_processor.py` (unparseable since `fb78256`);
  collection 408/9 errors -> 479/5 errors

## In-progress
- Nothing. Tree is clean except the `PROJECTS/Multi-module` submodule pointer,
  left deliberately untouched.

## Next
1. **Fix the 5 remaining pytest collection errors.** Pre-existing, unrelated to
   the cleanup; deleting files will not touch them. Current state after
   `2b195a5`: **479 collected, 5 errors**.
   - `ModuleNotFoundError: watchdog` — 2 files (`test_watch_input.py` imports
     `watch_input.py`; `v2_monitor/tests/test_monitor.py`). `watchdog>=6.0` is
     in `src/services/requirements.txt` but not installed in `.venv_test`.
   - `ModuleNotFoundError: chardet` — 1 file (`data-cleaning` test).
   - `FileNotFoundError: C:\Data\Crawler\labeled\NQ_DG_RESEARCH_CAPITAL_V2-43882500(sheet1)_labeled.xlsx`
     — a test hardcoded to a machine-local data file. Needs a fixture or skip.
   - `FileNotFoundError: research_instrument_keywords.txt` — resolved relative to
     cwd, not to the module. Newly visible now that `classify` imports again.
   Start with `pip install -r src/services/requirements.txt` into `.venv_test`;
   that should clear 3 of 5, leaving the two path-resolution bugs.
2. **Add `.gitattributes` with `* text=auto`.** Not cosmetic. The emoji sweep
   (`fb78256`) wrote `\r\r\n` into **45 tracked .py files**; Python reads the
   stray CR as a line terminator, which silently broke the one file that used a
   backslash continuation (`adaptive_excel_processor.py`, fixed in `2b195a5`).
   The other 44 still carry the corruption and parse only by luck — any future
   `\` continuation in them breaks the module. This is the root cause; fix it
   before the next sweep.
3. **Delete `archive/` dirs** (19 files, 3,155 lines). Verified unreferenced and
   not collected by pytest. Blocked pending explicit path naming:
   `src/services/classify/archive`, `src/services/cross-reference/archive`,
   `src/services/scraper-full/archive`, `src/services/scraper-full/tests/archive`
4. **Delete the debug-script bucket** (1,671 lines). `test_processor.py` and
   `test_keyword_matching.py` are scripts with zero test functions that error on
   import. Keep `test_xls_support.py` — it has a real test.

## Open questions
- `PROJECTS/ops/key.pem` and `cert.pem` are committed — a **private key in git
  history**. Out of scope for the audit (security), but deleting the file does
  not purge history. Rotate the key; decide whether history rewrite is warranted.
- `WebScrapper.exe` (96 MB) has no working build path: `build_configs/WebScrapper.spec`
  names `pdf_crawler_gui_2.py` with `pathex=[]`, but that source is in
  `scraper-full/`. Fix `pathex` before ever removing the binary.
  `PDF_Crawler_GUI.spec` is likewise broken — its `datas` wants 5 files, 1 exists.
- `PROJECTS/Multi-module` submodule holds its own copies of the same forked
  files. Separate cleanup, separate repo.

## File map
- `PROJECTS/src/services/pipeline.py` — resolves all stages via `SERVICES_ROOT`
- `PROJECTS/src/services/cross-reference/crossref_standalone_fast.py` — canonical copy
- `PROJECTS/src/services/cross-reference/tests/unit/test_crossref_timeout.py` — 16 of the 105 guard tests
- `PROJECTS/ops/` — the live ops tree (root `ops/` was the duplicate, now deleted)
