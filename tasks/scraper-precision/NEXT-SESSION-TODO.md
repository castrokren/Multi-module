# Quick Start — Next Session TODO

**Goal:** Validate the audited keyword lists with a clean full pipeline run

## Step 1: Run Pipeline (15-20 min)

```powershell
cd "C:\Projects\Crawler\PROJECTS"
python src/services/pipeline.py
```

Watch for these log lines:
- `Keyword gate: ... suppliers ...` — should show ~100 suppliers, ~1,600 tokens
- `Crawl finished - pages=X pdfs=Y suppliers=Z` — PDF count is critical metric
- Any `Per-supplier PDF cap (50) reached` warnings — means junk keyword leaked through

**Expected:** ~50-200 PDFs (vs baseline 566 pre-audit)

## Step 2: Spot-Check Broadax (5 min)

```powershell
ls "C:\Data\Crawler\output\BROADAX*" -Recurse | Measure-Object
```

**Expected:** Should be EMPTY or very few PDFs (was 500+ in the problem)

## Step 3: Review Results (5 min)

If Broadax is empty/minimal AND Keyword gate shows ~100 suppliers:
- ✅ Audit validated
- ✅ Ready to commit

If anything unexpected:
- Dig into the log file: `C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results\pipeline_*.log`
- Look for supplier names in the scrape output

## Step 4: Commit (2 min)

```powershell
cd "C:\Projects\Crawler"
git add PROJECTS/src/services/data-cleaning/column_filter_and_classify_v3.py PROJECTS/tests/test_classify_v3.py
git commit -m "Approve keyword audit: _JUNK_SW (50 terms) + _JUNK_NI (40 terms)

- Software: 285 -> 157 keywords
- Non-Instrument: 928 -> 478 keywords  
- Instrument: 160 (locked)
- Kren reviewed 26 ambiguous terms (REVIEW-keywords.md)
- All 7 tests passing

Co-Authored-By: Kren Castro <castrokren@gmail.com>"
```

## Optional Step 5: Cleanup

```powershell
rm -r "C:\Data\Crawler\output_backup_2026-07-13"
rm "C:\Projects\Crawler\PROJECTS\tools\audit_keywords.py"
```

---

## If Anything Goes Wrong

1. Check the full pipeline log for errors
2. Look for suppliers that downloaded 0 PDFs (might be genuine, might be freshness skip again)
3. If state files are blocking: move `C:\Data\Crawler\output\.*` to backup again
4. Re-run from Step 1

---

**Key facts:**
- Code is ready ✅
- Tests pass ✅
- Kren decisions applied ✅
- Output directory is clean ✅
- Just need validation now

**Timeline:** ~30 minutes total if no issues
