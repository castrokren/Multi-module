# 2026-07-09 — Single crawl engine, accuracy guardrails, input watcher

## Context

The crawler was downloading hundreds of irrelevant PDFs despite configured
constraints (`allowlist_only: true` + supplier keywords). Replaying the
filters against the 324-PDF corpus showed only 79 should have passed.
Root causes:

1. **Fail-open supplier filter** — a supplier missing from the keyword dict
   (32 of 247 master-list vendors had no input-CSV rows) skipped filtering
   entirely: 134/324 PDFs.
2. **Junk keyword tokens** — the tokenizer kept any digit-bearing token, so
   `"2"`, `"10"` became keywords and substring matching let them match
   nearly every filename: 102/324 PDFs.
3. **Duplicate crawler** — the Tkinter GUI (`pdf_crawler_gui_2.py`, built
   into `Crawlers.exe`/`WebScrapper.exe`) had its own crawl/download path
   with no relevance filtering at all.

## Decisions

1. **`scraper_engine.py` is the only crawl path.** The GUI's homegrown
   crawler (~420 lines) was deleted; the GUI now builds keywords from its
   input file and calls `ScraperEngine.run()`. Any future crawl feature
   goes in the engine, never in a caller.
2. **Filters fail closed.** Supplier not in the keyword dict → no downloads
   for that supplier (`no_supplier_keywords`), and the CSV-vendor guardrail
   in `run()` drops such vendors before crawling starts. Only vendors
   present in the input CSVs are crawled. Rationale: no requisition rows =
   nothing to judge relevance against.
3. **Content-level validation.** `%PDF` magic bytes on the first chunk;
   first-page text must contain a supplier keyword (fails open for scanned
   PDFs — Stage 3 judges those); SHA-256 content-hash dedup via a new
   `hashes` table in `.scraper_dedup.db`.
4. **Matching rules.** Keywords match the full URL path + anchor text, not
   just the filename. Tokens < 5 chars need exact word match; ≥ 5 chars may
   match as substrings. Tokenizer drops all tokens < 3 chars and bare
   numbers < 4 digits.
5. **Automatic runs via `watch_input.py`** (watchdog, already a dep):
   watches `paths.input_excel_dir`, 30 s debounce, one coalesced pipeline
   subprocess per drop. Registered via Task Scheduler at logon.

## Consequences

- Master-list vendors without input-CSV rows are no longer crawled at all.
  To include one, add its requisition rows to a CSV in the input dir.
- Hash dedup is forward-only; the pre-existing corpus was not retroactively
  deduplicated.
- `PDF_Crawler_GUI.exe` (rebuilt 2026-07-09, spec bundles `pipeline` +
  `scraper_engine`) replaces `Crawlers.exe`/`WebScrapper.exe`, which are
  retained on disk but must not be used.
- Coverage: `scraper-full/tests/unit/test_scraper_keyword_filter.py`
  (filters, guardrail, magic bytes, dedup) and
  `services/test_watch_input.py` (debounce/coalescing). Suite: 136 tests.
- Ops/setup for new servers: `docs/RUNBOOK.md`; deps:
  `src/services/requirements.txt`.
