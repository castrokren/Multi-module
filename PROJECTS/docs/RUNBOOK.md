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

## 8. Malware scanning control (Windows Defender)

Every PDF the pipeline touches is gated through Microsoft Defender (the
OS-native engine, `MpCmdRun.exe`) **synchronously and inline**, before the
file is stored, parsed, or transferred. This is a compliance control, not
reliant on real-time on-access protection.

### The three gates

| Gate | Location | Trigger | On infected/error |
|---|---|---|---|
| G1 — pre-storage | `scraper_engine.py::_download_pdf` | After download, before the staging file is renamed into the supplier's `output\` folder | Quarantined; `seen_urls.status` = `malware_detected` / `scan_error` |
| G2 — pre-parse | `crossref_standalone_fast.py` (both extraction paths) | Before any PDF parser opens the file | Quarantined; logged; skipped for the run |
| G3 — pre-transfer | `pipeline.py::_collect_matched_pdfs` | Before a matched PDF is copied into the review folder | Quarantined; not copied |

All three gates are **fail-closed**: scanner missing, timeout, or
unrecognized output is treated exactly like an infection. A file that can
never be scanned is never stored, parsed, or transferred.

### Quarantine directory

Flagged files move to `C:\Data\Crawler\quarantine\<supplier>\`, timestamped,
never deleted automatically. To **review and release a false positive**:

```powershell
# 1. Inspect the scan reason from the audit log
Get-Content "$(Get-ChildItem src\services\cross-reference\results\security_scan_*.log | Sort-Object Name | Select-Object -Last 1)"

# 2. Confirm the file is genuinely clean (real-time scan + manual review)
# 3. Manually move it back into its supplier folder under C:\Data\Crawler\output\
#    and delete the stale quarantine copy. Releasing is ALWAYS manual - the
#    pipeline will never un-quarantine a file by itself.
```

### Audit log

Every verdict is written to `security_scan_<ts>.log` in the results
directory (one line per file: path, verdict, detail). This is the artifact
a compliance reviewer will ask for.

### Configuration (`pipeline_config.json`)

```json
"security": {
  "malware_scan_enabled": true,
  "scan_timeout_seconds": 60,
  "max_concurrent_scans": 4
}
```

`malware_scan_enabled` is a **hard kill-switch**. Default is `true`; flipping
it to `false` disables the entire control and requires the same sign-off as
removing a Defender exclusion (below) — it deliberately turns off the
mechanism this whole section exists to provide.

### Host-level Defender configuration (do once on the server)

```powershell
# 1. Confirm real-time protection is on and signatures are fresh
Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated
Set-MpPreference -DisableRealtimeMonitoring $false

# 2. Force a signature update before trusting any scan result
& "C:\Program Files\Windows Defender\MpCmdRun.exe" -SignatureUpdate

# 3. Nightly full sweep of the data tree (backstop independent of the gates)
$mp = "C:\Program Files\Windows Defender\MpCmdRun.exe"
$action = New-ScheduledTaskAction -Execute $mp -Argument '-Scan -ScanType 3 -File "C:\Data\Crawler"'
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "CrawlerDataDefenderSweep" -Action $action -Trigger $trigger -Description "Nightly Defender sweep of C:\Data\Crawler as a backstop to the pipeline's inline scan gates"
```

**Exclusion check (re-verify after any Defender policy change):**
`ExclusionPath` must **not** contain `C:\Data\Crawler\` or any parent of it
— an exclusion there blinds real-time protection to that tree. Check with
`Get-MpPreference | Select-Object -ExpandProperty ExclusionPath`; if one
appears (e.g. re-added by group policy), remove it
(`Remove-MpPreference -ExclusionPath <path>`) with sign-off.

### Troubleshooting the gates

| Symptom | Cause / fix |
|---|---|
| File quarantined with `scan_error` / `scanner_not_found` | `MpCmdRun.exe` path changed, Defender service stopped, or scan timed out. Check `security_scan_*.log`. The pipeline is behaving correctly — it fails closed. |
| EICAR test file reaches `quarantine\` | Gate working as designed (see acceptance test below). |
| Sudden `malware_detected` on files ingested earlier | Defender signature update since ingest — the correct, intended catch at G3. Not a G1 bug. |

## 8b. Egress proxy control (`network.*`)

The scraper's HTTP egress is governed by the `network` block in
`pipeline_config.json` — the single source of truth. By default the
session **ignores** `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` env vars so
behavior doesn't silently depend on whatever the host environment happens
to have set:

```json
"network": {
  "https_proxy": "",
  "http_proxy": "",
  "require_proxy": false,
  "trust_env_proxy": false
}
```

| Key | Meaning |
|---|---|
| `https_proxy` / `http_proxy` | Explicit proxy URL per scheme, e.g. `"http://proxy.corp.internal:8080"`. Empty string = no proxy for that scheme. |
| `require_proxy` | Fail-closed switch. `true` + no proxy configured = the pipeline refuses to start (`RuntimeError`, caught in `run_scraper`; also caught by `--dry-run`). Mirrors the `malware_scan_enabled` kill-switch. |
| `trust_env_proxy` | `false` (default): `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` env vars are ignored. Flip to `true` **only** if IT wants env-var-managed proxying (e.g. centrally pushed via GPO) instead of file-based config. |

The GUI (`pdf_crawler_gui_2.py`) and `pdf_discovery_pipeline.py` read the
same `network` block, so no entry point can bypass the control.

**To point at a corporate proxy once IT confirms it is mandatory:**

1. Set `https_proxy` (and `http_proxy` if targets use plain HTTP) to the
   corporate proxy URL.
2. Run a crawl and confirm requests actually transit it (check the
   proxy-side access log for the crawler's User-Agent / source IP).
3. Set `require_proxy` to `true`. Verify fail-closed: point the proxy URL
   at an unreachable host and confirm the pipeline refuses to start with a
   clear error instead of silently falling back to direct egress.

**Credentials:** never put plaintext credentials in `pipeline_config.json`.
If the proxy requires auth, interpolate the credential-bearing URL from an
environment variable at runtime (set through Windows Credential Manager /
whatever secret store the ops team uses) — e.g. `https_proxy` =
`os.environ["CRAWLER_PROXY_URL"]`. Not confirmed as needed on this host as
of 2026-08-19; do not add credentials without an IT decision on where they
live.

## 8c. HTTPS-only egress (`security.allow_http_hosts` / `https_upgrade_attempt`)

The scraper is **HTTPS-only by default**: `_validate_url()` rejects any
plain `http://` URL, and blocked URLs are recorded in the dedup DB with
status `blocked_insecure_scheme`. This closes the audit gap where plain
HTTP was accepted but never required.

### Configuration (`pipeline_config.json`)

```json
"security": {
  "malware_scan_enabled": true,
  "allow_http_hosts": [],
  "https_upgrade_attempt": true
}
```

| Key | Meaning |
|---|---|
| `allow_http_hosts` | Explicit exception list of hostnames that may be fetched over plain HTTP. Starts **empty** (clean cutover). Each addition is a real security exception and requires the same sign-off as flipping `malware_scan_enabled` off (see section 8). |
| `https_upgrade_attempt` | Default `true`. When an `http://` PDF link is found and its host is not in `allow_http_hosts`, the URL is rewritten to `https://` and fetched over HTTPS before blocking. URL-string rewrite only — no plaintext request is ever made to test reachability. If the upgraded HTTPS URL is unreachable it fails downstream like any other unreachable HTTPS URL; there is **no fallback to plaintext**. |

**To add a genuine exception (only after confirming the vendor has no HTTPS
endpoint):**

1. Confirm the host really is HTTPS-incapable before accepting the
   exception — many "http-only" links are just authored lazily and the site
   serves HTTPS fine:
   ```powershell
   curl.exe -I https://<host>
   ```
2. Add the hostname to `security.allow_http_hosts` in
   `pipeline_config.json` and document who approved it and why in this
   section — same review bar as removing a Defender exclusion.

A blocked `http://` PDF shows up in the run log as
`Blocked insecure URL` (or `Blocked insecure URL (no HTTPS upgrade available)`
when the upgraded variant fails validation) and in `.scraper_dedup.db` with
status `blocked_insecure_scheme`.

## 9. General troubleshooting

| Symptom | Cause / fix |
|---|---|
| Supplier skipped with "No supplier keywords loaded" | Vendor has no rows in any input CSV. Add its requisition rows (with `Item Description`) to a CSV in the input dir |
| "Skipping N supplier(s) with no rows in input CSVs" | Same as above — by design, not an error |
| No PDFs for a supplier that used to get many | Filters working as intended; check the log for `no_keyword_match` / `rejected_content` reasons |
| Nothing re-downloads | Dedup DB — delete `.scraper_dedup.db` for a fresh crawl |
| Supplier crawled recently and skipped | 7-day freshness window (`scraper.days_before_rescrape`) or delete `.scraper_state.json` |
| Watcher doesn't trigger | Confirm the file suffix is `.csv`/`.xlsx`/`.xls` and check `watch_input.log`; verify `paths.input_excel_dir` in `pipeline_config.json` |
| `Cannot find Supplier Name / Website columns` | Master list is missing those column headers |

## 10. Verify the install

```powershell
cd <repo>\src\services
python pipeline.py --dry-run                       # paths OK?
python test_watch_input.py                          # watcher self-check
cd scraper-full; python -m pytest tests/unit -q     # engine test suite (172 tests)
```

All three passing = the server is ready. Drop a CSV into
`C:\Data\Crawler\input` and watch `watch_input.log` for the run.
