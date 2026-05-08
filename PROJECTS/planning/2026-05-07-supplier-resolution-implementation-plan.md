# Supplier Resolution Stage — Implementation Plan
**Date:** 2026-05-07  
**Branch:** `feature/supplier-resolution`  
**Spec:** `planning/specs/2026-05-07-supplier-resolution-spec.md`  
**Estimated tasks:** 8

---

## Pre-flight

```powershell
cd C:\Projects\Crawler\PROJECTS
git checkout main
git checkout -b feature/supplier-resolution
git status
```

Verify you are on the new branch before touching any files.

Install required dependencies:
```powershell
pip install requests beautifulsoup4 openpyxl
```

---

## Task 1 — Scaffold the module

**Create the folder structure:**
```powershell
mkdir src\services\supplier-resolution
mkdir src\services\supplier-resolution\tests
mkdir src\services\supplier-resolution\tests\unit
type nul > src\services\supplier-resolution\__init__.py
type nul > src\services\supplier-resolution\supplier_resolver.py
type nul > src\services\supplier-resolution\web_searcher.py
type nul > src\services\supplier-resolution\confidence_scorer.py
type nul > src\services\supplier-resolution\tests\unit\__init__.py
type nul > src\services\supplier-resolution\tests\unit\test_confidence_scorer.py
type nul > src\services\supplier-resolution\tests\unit\test_supplier_extractor.py
mkdir data\supplier-pending
```

**Verification:**
```powershell
dir src\services\supplier-resolution\
```

---

## Task 2 — Write `confidence_scorer.py`

**Why first:** Pure logic, no I/O, easiest to test in isolation.

```python
# src/services/supplier-resolution/confidence_scorer.py

from urllib.parse import urlparse
import re

DIRECTORY_BLOCKLIST = [
    "amazon", "alibaba", "linkedin", "yellowpages", "thomasnet",
    "globalspec", "grainger", "fishersci", "directindustry", "kompass",
    "selectscience", "labcompare", "capterra", "g2", "yelp"
]

def extract_domain(url: str) -> str:
    """Extract bare domain from URL e.g. https://www.ancare.com/ -> ancare.com"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain
    except Exception:
        return ""

def domain_matches_supplier(domain: str, supplier_name: str) -> bool:
    """Check if domain contains meaningful words from supplier name."""
    # Normalize supplier name: lowercase, remove common suffixes
    name = supplier_name.lower()
    for suffix in [" inc", " llc", " corp", " ltd", " co", " gmbh",
                   " usa", " us", " na", " north america", " corporation",
                   " company", " technologies", " scientific", " medical"]:
        name = name.replace(suffix, "")
    words = [w for w in re.split(r'\s+|-', name) if len(w) > 2]
    return any(word in domain for word in words)

def is_directory(domain: str) -> bool:
    return any(blocked in domain for blocked in DIRECTORY_BLOCKLIST)

def score_url(url: str, supplier_name: str, ddg_urls: list,
              bing_urls: list) -> int:
    """Score a candidate URL for a supplier. Returns 0-130."""
    if not url:
        return 0

    score = 0
    domain = extract_domain(url)
    if not domain:
        return 0

    # Both engines agree
    ddg_domains = [extract_domain(u) for u in ddg_urls[:1]]
    bing_domains = [extract_domain(u) for u in bing_urls[:1]]
    if ddg_domains and bing_domains and ddg_domains[0] == bing_domains[0]:
        score += 40
    elif ddg_domains or bing_domains:
        score += 10

    # Domain contains supplier name words
    if domain_matches_supplier(domain, supplier_name):
        score += 25

    # HTTPS
    if url.startswith("https://"):
        score += 15

    # TLD
    tld = domain.split(".")[-1] if "." in domain else ""
    if tld in ("com", "org", "us", "edu"):
        score += 10

    # Not a directory
    if not is_directory(domain):
        score += 20

    return score

def pick_best_url(ddg_urls: list, bing_urls: list,
                  supplier_name: str) -> tuple[str, int]:
    """
    Pick the best URL from combined search results.
    Returns (url, score). Returns ("", 0) if nothing found.
    """
    candidates = []
    seen = set()
    for url in (ddg_urls[:3] + bing_urls[:3]):
        domain = extract_domain(url)
        if domain and domain not in seen:
            seen.add(domain)
            candidates.append(url)

    if not candidates:
        return "", 0

    scored = [
        (url, score_url(url, supplier_name, ddg_urls, bing_urls))
        for url in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0]
```

**Verification:** No imports needed — run inline:
```powershell
python -c "
import sys; sys.path.insert(0, 'src/services/supplier-resolution')
from confidence_scorer import pick_best_url
url, score = pick_best_url(
    ['https://www.ancare.com/'],
    ['https://www.ancare.com/'],
    'ANCARE CORP'
)
print(f'URL: {url}, Score: {score}')
assert score >= 70, f'Expected high confidence, got {score}'
print('PASS')
"
```

---

## Task 3 — Write `web_searcher.py`

```python
# src/services/supplier-resolution/web_searcher.py

import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def search_duckduckgo(query: str, timeout: int = 10,
                      max_results: int = 3) -> list[str]:
    """Search DuckDuckGo HTML interface. Returns list of result URLs."""
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        resp = requests.post(url, data=params, headers=HEADERS,
                             timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select("a.result__url"):
            href = a.get("href", "")
            if href.startswith("http"):
                results.append(href)
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []

def search_bing(query: str, timeout: int = 10,
                max_results: int = 3) -> list[str]:
    """Search Bing HTML interface. Returns list of result URLs."""
    try:
        url = "https://www.bing.com/search"
        params = {"q": query}
        resp = requests.get(url, params=params, headers=HEADERS,
                            timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for cite in soup.select("cite"):
            text = cite.get_text(strip=True)
            if text.startswith("http"):
                results.append(text)
            elif "." in text:
                results.append("https://" + text)
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []

def find_supplier_url(supplier_name: str, delay: float = 1.5,
                      timeout: int = 10) -> tuple[list, list]:
    """
    Search both engines for a supplier.
    Returns (ddg_urls, bing_urls).
    Applies delay between requests to avoid rate limiting.
    """
    query = f'"{supplier_name}" official website'
    ddg_urls = search_duckduckgo(query, timeout=timeout)
    time.sleep(delay)
    bing_urls = search_bing(query, timeout=timeout)
    time.sleep(delay)
    return ddg_urls, bing_urls
```

**Verification:**
```powershell
python -c "
import sys; sys.path.insert(0, 'src/services/supplier-resolution')
from web_searcher import find_supplier_url
ddg, bing = find_supplier_url('ANCARE CORP', delay=1.0)
print('DuckDuckGo:', ddg)
print('Bing:', bing)
assert isinstance(ddg, list) and isinstance(bing, list)
print('PASS')
"
```

---

## Task 4 — Write `supplier_resolver.py`

```python
# src/services/supplier-resolution/supplier_resolver.py

"""
Supplier Resolution Stage
Sits between classify and scrape in the pipeline.

Entry point: resolve_suppliers(cfg)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd

# Allow imports from sibling modules
sys.path.insert(0, str(Path(__file__).parent))
from web_searcher import find_supplier_url
from confidence_scorer import pick_best_url


def _load_master_list(path: str) -> dict[str, str]:
    """Load master list into {supplier_name: website} dict."""
    df = pd.read_excel(path, usecols=["Supplier Name", "Website"])
    return {
        str(row["Supplier Name"]).strip().upper(): str(row["Website"]).strip()
        for _, row in df.iterrows()
        if row["Supplier Name"] and row["Website"]
    }


def _extract_suppliers(classified_excel: str) -> list[str]:
    """Extract unique supplier names from classified Excel."""
    df = pd.read_excel(classified_excel)
    col = next(
        (c for c in df.columns if "supplier" in c.lower()),
        None
    )
    if not col:
        raise ValueError(
            f"No supplier column found in {classified_excel}. "
            f"Columns: {list(df.columns)}"
        )
    return list(df[col].dropna().str.strip().str.upper().unique())


def _append_to_pending(path: str, rows: list[dict]) -> None:
    """Append rows to pending list Excel. Creates file if absent."""
    headers = [
        "Supplier Name", "Suggested URL", "Confidence Score",
        "Search Query", "DuckDuckGo Result", "Bing Result",
        "Status", "Date Added"
    ]
    if os.path.exists(path):
        wb = openpyxl.load_workbook(path)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)

    existing = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
    for row in rows:
        if row["Supplier Name"] not in existing:
            ws.append([row.get(h, "") for h in headers])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)


def _append_to_master_list(path: str, rows: list[dict]) -> None:
    """Append high-confidence suppliers to master list."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    existing = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
    for row in rows:
        if row["Supplier Name"] not in existing:
            ws.append([row["Supplier Name"], row["Suggested URL"], None])
    wb.save(path)


def _write_resolved_list(path: str, suppliers: list[dict]) -> None:
    """Write resolved supplier list for scraper consumption."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Supplier Name", "Website", "Source"])
    for s in suppliers:
        ws.append([s["Supplier Name"], s["Website"], s["Source"]])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)


def resolve_suppliers(cfg: dict) -> bool:
    """
    Pipeline stage entry point.
    cfg keys used:
      - classified_excel: path to labeled Excel from classify stage
      - master_list: path to updated_master_list.xlsx
      - supplier_resolution.pending_list_path
      - supplier_resolution.resolved_list_path
      - supplier_resolution.confidence_threshold (default 70)
      - supplier_resolution.search_delay_seconds (default 1.5)
      - supplier_resolution.search_timeout_seconds (default 10)
    Returns True on success, False on failure.
    """
    try:
        res_cfg = cfg.get("supplier_resolution", {})
        master_list_path = cfg["master_list"]
        classified_excel = cfg["classified_excel"]
        pending_path = res_cfg.get(
            "pending_list_path", "data/supplier-pending/new_suppliers_pending.xlsx"
        )
        resolved_path = res_cfg.get(
            "resolved_list_path", "data/supplier-pending/resolved_suppliers.xlsx"
        )
        threshold = res_cfg.get("confidence_threshold", 70)
        delay = res_cfg.get("search_delay_seconds", 1.5)
        timeout = res_cfg.get("search_timeout_seconds", 10)

        print(f"[supplier_resolution] Loading master list: {master_list_path}")
        master = _load_master_list(master_list_path)

        print(f"[supplier_resolution] Extracting suppliers from: {classified_excel}")
        all_suppliers = _extract_suppliers(classified_excel)
        print(f"[supplier_resolution] Found {len(all_suppliers)} unique suppliers")

        known = []
        to_resolve = []
        for name in all_suppliers:
            if name in master:
                known.append({
                    "Supplier Name": name,
                    "Website": master[name],
                    "Source": "master_list"
                })
            else:
                to_resolve.append(name)

        print(f"[supplier_resolution] Known: {len(known)}, Unknown: {len(to_resolve)}")

        high_confidence = []
        low_confidence = []
        now = datetime.now().strftime("%Y-%m-%d")

        for name in to_resolve:
            print(f"[supplier_resolution] Resolving: {name}")
            query = f'"{name}" official website'
            ddg_urls, bing_urls = find_supplier_url(name, delay=delay,
                                                     timeout=timeout)
            best_url, score = pick_best_url(ddg_urls, bing_urls, name)

            row = {
                "Supplier Name": name,
                "Suggested URL": best_url,
                "Confidence Score": score,
                "Search Query": query,
                "DuckDuckGo Result": ddg_urls[0] if ddg_urls else "",
                "Bing Result": bing_urls[0] if bing_urls else "",
                "Date Added": now,
            }

            if score >= threshold and best_url:
                print(f"  → High confidence ({score}): {best_url}")
                row["Status"] = "Auto-Added"
                high_confidence.append(row)
            else:
                print(f"  → Low confidence ({score}): {best_url or 'no result'}")
                row["Status"] = "Pending Review"
                low_confidence.append(row)

        # Write high confidence to master list BEFORE scrape
        if high_confidence:
            print(f"[supplier_resolution] Adding {len(high_confidence)} to master list")
            _append_to_master_list(master_list_path, high_confidence)

        # Write low confidence to pending list
        if low_confidence:
            print(f"[supplier_resolution] Writing {len(low_confidence)} to pending list")
            _append_to_pending(pending_path, low_confidence)

        # Write resolved list for scraper
        scrape_list = known + [
            {"Supplier Name": r["Supplier Name"],
             "Website": r["Suggested URL"],
             "Source": "auto_resolved"}
            for r in high_confidence
        ]
        _write_resolved_list(resolved_path, scrape_list)
        print(f"[supplier_resolution] Resolved list written: {len(scrape_list)} suppliers")
        print(f"[supplier_resolution] Done. High: {len(high_confidence)}, "
              f"Low: {len(low_confidence)}, Known: {len(known)}")

        return True

    except Exception as e:
        print(f"[supplier_resolution] ERROR: {e}")
        return False
```

**Verification:**
```powershell
python -c "
import sys; sys.path.insert(0, 'src/services/supplier-resolution')
from supplier_resolver import resolve_suppliers
print('Import OK')
"
```

---

## Task 5 — Update `pipeline_config.json`

Add the `supplier_resolution` section:
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

Also add `master_list` path to the top-level config:
```json
{
  "master_list": "docs/guides/documents/updated_master_list.xlsx"
}
```

---

## Task 6 — Wire into `pipeline.py`

Read `pipeline.py` lines 1-50 and 124-170 to understand existing stage wiring, then:

1. Add `supplier_resolution` to the `stages` dict (after `classify`, before `scrape`):
```python
stages = {
    "classify": ...,
    "supplier_resolution": cfg.get("stages", {}).get("supplier_resolution", True),
    "scrape": ...,
    "crossref": ...
}
```

2. Add `run_supplier_resolution(cfg)` function following the same pattern as `run_classify`:
```python
def run_supplier_resolution(cfg):
    resolver = _import_from_file(
        "supplier_resolver",
        Path(cfg["project_root"]) / "src/services/supplier-resolution/supplier_resolver.py"
    )
    return resolver.resolve_suppliers(cfg)
```

3. Add CLI flags to argparse:
```python
parser.add_argument("--skip-supplier-resolution", action="store_true")
parser.add_argument("--only-supplier-resolution", action="store_true")
```

4. Update scraper stage to use `resolved_suppliers.xlsx` instead of `master_list` directly:
   - In `run_scraper(cfg)`, check if `resolved_list_path` exists in cfg
   - If yes, pass that to `ScraperEngine.run()` instead of `master_list`

**Verification:**
```powershell
python src\services\pipeline.py --only-supplier-resolution --dry-run
```

---

## Task 7 — Write tests

**`test_confidence_scorer.py`:**
- `test_both_engines_agree_high_score` — same domain from both → score ≥ 70
- `test_only_one_engine_lower_score` — one engine empty → score < both-agree score
- `test_directory_domain_penalized` — amazon.com → is_directory returns True
- `test_domain_matches_supplier_name` — "ancare.com" + "ANCARE CORP" → True
- `test_no_results_returns_zero` — empty lists → score 0
- `test_https_bonus` — https URL scores higher than http

**`test_supplier_extractor.py`:**
- `test_extracts_unique_suppliers` — 10 rows, 3 unique suppliers → returns 3
- `test_missing_supplier_column_raises` — Excel with no supplier column → ValueError
- `test_normalizes_to_uppercase` — mixed case → all uppercase
- `test_skips_null_values` — NaN rows → excluded

Run:
```powershell
python -m pytest src\services\supplier-resolution\tests\unit\ -v
```

---

## Task 8 — End-to-end smoke test

Run the full pipeline with `--only-supplier-resolution` against a small test Excel:

```powershell
python -c "
import openpyxl, os
# Create test classified Excel with 2 known + 1 unknown supplier
wb = openpyxl.Workbook()
ws = wb.active
ws.append(['TYPE', 'Supplier Name', 'Item Description'])
ws.append(['Instrument', 'ANCARE CORP', 'Animal cage'])
ws.append(['Instrument', 'BECKMAN COULTER INC', 'Centrifuge'])
ws.append(['Instrument', 'TOTALLY FAKE SUPPLIER XYZ INC', 'Unknown device'])
wb.save('data/test_classified.xlsx')
print('Test file created.')
"

python src\services\pipeline.py --only-supplier-resolution --config src\services\pipeline_config.json
```

Check outputs:
```powershell
dir data\supplier-pending\
type data\supplier-pending\new_suppliers_pending.xlsx
```

**Expected:**
- `resolved_suppliers.xlsx` has ANCARE CORP + BECKMAN COULTER INC
- `new_suppliers_pending.xlsx` has TOTALLY FAKE SUPPLIER XYZ INC
- `updated_master_list.xlsx` unchanged (fake supplier didn't get high confidence)

---

## Wrap-up

After all tasks pass:
```powershell
git add -A
git commit -m "feat(supplier-resolution): add supplier resolution pipeline stage"
git push origin feature/supplier-resolution
```

Coverage check:
```powershell
python -m pytest src\services\supplier-resolution\tests\ -v --cov=src\services\supplier-resolution --cov-report=term-missing
```

Target: ≥70% on `confidence_scorer.py` and `supplier_resolver.py`.

---

## Notes for Claude Code execution

- Use `executing-plans` skill to work through task by task
- Use `systematic-debugging` if any search returns unexpected results
- Use `verification-before-completion` before final commit
- Task 2 and 3 can be done in parallel (no dependencies between them)
- Task 6 (pipeline wiring) requires reading pipeline.py carefully before editing
- Rate limiting (1.5s delay) is important — don't remove it or searches will get blocked
