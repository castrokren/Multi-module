# Crawler Pipeline Runbook

How to install and run the crawler pipeline on a new Windows server.
Covers: dependencies, directory setup, manual runs, automatic runs
(input-directory watcher), the GUI, and troubleshooting.

Last verified: 2026-07-09.

---

## 1. What runs where

| Component | Path | Purpose |
|---|---|---|
| Pipeline orchestrator | `src/services/pipeline.py` | Runs all stages: data cleaning → scraper → classify → cross-reference |
| Crawl engine | `src/services/scraper-full/scraper_engine.py` | Shared crawler (filters, rate limiting, dedup). Used by pipeline AND GUI |
| Input watcher | `src/services/watch_input.py` | Watches the input dir, runs the pipeline when files arrive |
| GUI (optional) | `src/services/scraper-full/dist/PDF_Crawler_GUI.exe` | Manual crawling + cross-reference tools. Self-contained exe |
| Pipeline config | `src/services/pipeline_config.json` | All paths and stage toggles |

## 2. Prerequisites

- **Windows 10/11 or Server 2019+** (paths and the watcher's Task Scheduler
  setup assume Windows).
- **Python 3.10+** (developed and tested on 3.13). Not needed if you only
  run the GUI exe — it is self-contained.
- Outbound HTTPS (443) to supplier websites. DuckDuckGo/Bing reachability
  is optional (used as a PDF-discovery fallback).
- No database server needed — state lives in SQLite/JSON files created
  automatically in the output directory.

### Install dependencies

```powershell
cd <repo>\src\services
python -m pip install -r requirements.txt
```

That single file covers every stage, the watcher, and (if you ever rebuild
the exe) everything except `pyinstaller` itself.

## 3. Directory + config setup

All data lives OUTSIDE the repo, in `C:\Data\Crawler\`:

```powershell
New-Item -ItemType Directory -Force C:\Data\Crawler\input    # raw supplier requisition CSVs land here
New-Item -ItemType Directory -Force C:\Data\Crawler\labeled  # classified Excel output (TYPE column)
New-Item -ItemType Directory -Force C:\Data\Crawler\output   # scraped PDFs, one folder per supplier
```

Then check `src/services/pipeline_config.json`:

- `paths.input_excel_dir` / `labeled_dir` / `pdf_dir` → the three dirs above.
- `paths.supplier_excel` / `master_excel` → the master list
  (`data/masterlist/updated_master_list.xlsx`, ships with the repo —
  needs `Supplier Name` and `Website` columns).
- `pipeline.*` → enable/disable stages.
- `scraper.allowlist_only` → keep `true` (only product-doc PDFs).

Optional: `C:\Data\Crawler\labeled\hardware_keywords_ACTIVE.txt` and
`software_keywords_ACTIVE.txt` (one keyword per line) enable the
homepage keyword pre-check. Missing files are fine — the check is skipped.

### Accuracy guardrails (do not bypass)

- **Only vendors present in the input CSVs are crawled.** A master-list
  supplier with no requisition rows is skipped, with a warning naming it.
  To crawl a vendor, it must appear in an input CSV with `Supplier Name`
  and `Item Description` columns.
- Every PDF must pass: allowlist/blocklist URL filter → per-supplier keyword
  match (URL path + link text) → `%PDF` magic-byte check → first-page
  content keyword check → content-hash dedup.

## 4. Running manually

```powershell
cd <repo>\src\services
python pipeline.py                 # all enabled stages
python pipeline.py --dry-run       # validate paths only, do nothing
python pipeline.py --skip-scraper  # skip crawling
python pipeline.py --only-crossref # cross-reference only
```

Logs: one timestamped file per run under
`src/services/cross-reference/results/pipeline_<timestamp>.log`
(falls back to `ops/monitoring/pipeline-logs/` if that drive is missing).

## 5. Running automatically (input watcher)

The watcher runs the pipeline whenever CSV/Excel files land in the
input directory:

```powershell
cd <repo>\src\services
python watch_input.py          # run in foreground (Ctrl+C to stop)
python watch_input.py --once   # process pending changes, then exit
```

Behavior:
- Reacts to `.csv` / `.xlsx` / `.xls`; ignores Excel `~$` lock files.
- 30 s debounce — a drop of many files (or a slow copy) = one pipeline run.
- Files arriving mid-run queue exactly one follow-up run.
- Pipeline runs as a subprocess; a pipeline crash never kills the watcher.
- Log: `src/services/watch_input.log`.

### Start at logon (Task Scheduler)

```powershell
schtasks /create /tn "CrawlerInputWatcher" /sc onlogon `
  /tr "\"C:\Path\To\python.exe\" \"<repo>\src\services\watch_input.py\""
```

For an unattended server, create the task with **Run whether user is
logged on or not** under a service account instead (`taskschd.msc`,
point it at the same command). Alternative without a resident process:
schedule `watch_input.py --once` every N minutes.

## 6. GUI (optional, manual use)

`src/services/scraper-full/dist/PDF_Crawler_GUI.exe` is self-contained —
no Python needed on the target machine. It uses the same crawl engine and
filters as the pipeline. Older binaries in `scraper-full/`
(`Crawlers.exe`, `WebScrapper.exe`) predate the filters — do not use them.

Rebuild after code changes:

```powershell
cd <repo>\src\services\scraper-full
python -m pip install pyinstaller
python -m PyInstaller pdf_crawler_gui_2.spec --noconfirm
# result: dist\PDF_Crawler_GUI.exe
```

## 7. State files & maintenance

| File | Location | Purpose | Safe to delete? |
|---|---|---|---|
| `.scraper_dedup.db` | output dir | URLs seen + content hashes; prevents re-downloads | Yes — forces full re-crawl |
| `.scraper_state.json` | output dir | Per-supplier last-crawl dates (7-day freshness skip) | Yes — re-crawls everything |
| `watch_input.log` | `src/services/` | Watcher activity | Yes |
| `pipeline_*.log` | results dir | Per-run pipeline logs | Yes |

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Supplier skipped with "No supplier keywords loaded" | Vendor has no rows in any input CSV. Add its requisition rows (with `Item Description`) to a CSV in the input dir |
| "Skipping N supplier(s) with no rows in input CSVs" | Same as above — by design, not an error |
| No PDFs for a supplier that used to get many | Filters working as intended; check the log for `no_keyword_match` / `rejected_content` reasons |
| Nothing re-downloads | Dedup DB — delete `.scraper_dedup.db` for a fresh crawl |
| Supplier crawled recently and skipped | 7-day freshness window (`scraper.days_before_rescrape`) or delete `.scraper_state.json` |
| Watcher doesn't trigger | Confirm the file suffix is `.csv`/`.xlsx`/`.xls` and check `watch_input.log`; verify `paths.input_excel_dir` in `pipeline_config.json` |
| `Cannot find Supplier Name / Website columns` | Master list is missing those column headers |

## 9. Verify the install

```powershell
cd <repo>\src\services
python pipeline.py --dry-run                       # paths OK?
python test_watch_input.py                          # watcher self-check
cd scraper-full; python -m pytest tests/unit -q     # engine test suite (136 tests)
```

All three passing = the server is ready. Drop a CSV into
`C:\Data\Crawler\input` and watch `watch_input.log` for the run.
