# Supplier Resolution Stage — Design Spec
**Date:** 2026-05-07  
**Author:** Kren Castro  
**Status:** Approved for implementation

---

## Problem

New procurement documents frequently contain suppliers not in `updated_master_list.xlsx`.
When this happens, the scraper skips those suppliers entirely — no PDFs are downloaded,
and cross-referencing is incomplete. With new suppliers appearing daily, this gap compounds
over time.

---

## Solution

Add a `supplier_resolution` stage to `pipeline.py` between `classify` and `scrape`. The
stage extracts unknown suppliers from the classified Excel, searches for their websites
using DuckDuckGo and Bing (free, no API key), scores the results for confidence, and
routes them to either:
- **High confidence (≥70)** → added to the active crawl list for this run
- **Low confidence (<70)** → written to `new_suppliers_pending.xlsx` for manual review

Known suppliers pass through unchanged.

---

## Pipeline Position

```
1. classify          — labels items Hardware / Software / Non-Instrument
2. supplier_resolution  ← NEW
3. scrape            — crawls supplier websites
4. crossref          — matches items to PDFs
```

---

## Module

**File:** `PROJECTS/src/services/supplier-resolution/supplier_resolver.py`  
**Entry point:** `resolve_suppliers(classified_excel, master_list, pending_list, cfg)`  
**Called from:** `pipeline.py` via `_import_from_file()` (same pattern as other stages)

---

## Architecture

### Inputs
- `classified_excel` — labeled Excel from classify stage (has `Supplier Name` column)
- `master_list` — `updated_master_list.xlsx` (has `Supplier Name` + `Website`)
- `pending_list` — `data/supplier-pending/new_suppliers_pending.xlsx` (created if absent)
- `cfg` — pipeline config dict

### Outputs
- `resolved_suppliers.xlsx` — temporary file: known + high-confidence suppliers with URLs,
  used by scraper stage for this run only (written to `data/supplier-pending/`)
- `new_suppliers_pending.xlsx` — updated with low-confidence entries for manual review

### Components

**`SupplierExtractor`**
- Reads classified Excel, extracts unique `Supplier Name` values
- Splits into `known` (in master list) and `unknown` (not in master list)

**`WebSearcher`**
- `search_duckduckgo(query)` → returns top 3 result URLs (HTML scraping, no API)
- `search_bing(query)` → returns top 3 result URLs (HTML scraping, no API)
- Query format: `"{SUPPLIER NAME}" official website`
- Timeout: 10s per search, retries: 2
- Rate limiting: 1.5s delay between requests (avoid blocks)

**`ConfidenceScorer`**
- Takes DuckDuckGo results + Bing results for a supplier
- Scores the top candidate URL:

| Signal | Points |
|--------|--------|
| DuckDuckGo and Bing agree on same domain | +40 |
| Only one engine returns a result | +10 |
| Domain contains supplier name words | +25 |
| HTTPS | +15 |
| TLD is .com/.org/.us/.edu | +10 |
| Not a directory/marketplace | +20 |

- Directories/marketplaces blocklist: amazon, alibaba, linkedin, yellowpages,
  thomasnet, globalspec, grainger, fishersci, directindustry, kompass
- **Score ≥ 70** → high confidence
- **Score < 70** → low confidence

**`PendingListWriter`**
- Appends low-confidence entries to `new_suppliers_pending.xlsx`
- Columns: `Supplier Name`, `Suggested URL`, `Confidence Score`, `Search Query`,
  `DuckDuckGo Result`, `Bing Result`, `Status`, `Date Added`
- Status values: `Pending Review`, `Auto-Added` (for high confidence)
- Never duplicates — checks existing entries before appending

**`ResolvedListWriter`**
- Writes `resolved_suppliers.xlsx` for this run:
  known suppliers + high-confidence new suppliers
- Columns: `Supplier Name`, `Website`, `Source` (master_list / auto_resolved)
- This file is consumed by the scraper stage and discarded after the run

---

## Confidence Scoring Example

Supplier: `ANCARE CORP`  
Query: `"ANCARE CORP" official website`

| Engine | Top result |
|--------|-----------|
| DuckDuckGo | https://www.ancare.com/ |
| Bing | https://www.ancare.com/ |

Scoring:
- Both agree on same domain → +40
- Domain contains "ancare" (from "ANCARE CORP") → +25
- HTTPS → +15
- .com TLD → +10
- Not a directory → +20
- **Total: 110** → High confidence ✅

---

## Error Handling

- Search timeout/failure for one engine → use the other engine only, apply single-engine penalty
- Both engines fail → write to pending list with score 0, status `Search Failed`
- Classified Excel missing `Supplier Name` column → raise `ValueError`, abort stage
- Master list missing → raise `FileNotFoundError`, abort stage
- Pending list missing → create it with headers, continue

---

## Pipeline Config

Add to `pipeline_config.json`:
```json
{
  "supplier_resolution": {
    "enabled": true,
    "confidence_threshold": 70,
    "search_delay_seconds": 1.5,
    "search_timeout_seconds": 10,
    "pending_list_path": "data/supplier-pending/new_suppliers_pending.xlsx",
    "resolved_list_path": "data/supplier-pending/resolved_suppliers.xlsx"
  }
}
```

Pipeline stage flag: `--skip-supplier-resolution` / `--only-supplier-resolution`

---

## File Layout

```
PROJECTS/src/services/supplier-resolution/
├── supplier_resolver.py      ← main stage entry point
├── web_searcher.py           ← DuckDuckGo + Bing search
├── confidence_scorer.py      ← URL scoring logic
├── tests/
│   └── unit/
│       ├── __init__.py
│       ├── test_confidence_scorer.py
│       └── test_supplier_extractor.py
```

---

## Out of Scope

- Writing directly to `updated_master_list.xlsx` (manual merge only for now)
- Google Custom Search API (free approach only)
- UI for reviewing pending list (Excel is sufficient for now)
- Automatic retry of failed searches in subsequent runs

---

## Success Criteria

- Known suppliers pass through with zero latency
- New suppliers with high confidence are scraped in the same run
- Low confidence suppliers are written to pending list with enough context to manually verify
- Pipeline runs end-to-end without breaking existing stages
- No supplier is silently dropped — every unknown gets either resolved or logged
