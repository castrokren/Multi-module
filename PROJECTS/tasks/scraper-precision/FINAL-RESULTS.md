# Final Results — Keyword Audit Complete

**Status:** ✅ APPROVED BY KREN — Ready for full pipeline run

## Kren's Decisions (Applied)

### Software (285 → 157 terms, -128 removals)

**Removed per Kren's judgment:**
- Non-scientific brands: adobe, autocad, visio, revit, salesforce, intel
- Optical term that's not software: prism
- Learning-mode junk: gmpe, pmml

**Result:** Software list now contains only genuine research software and scientific tools.

### Non-Instrument (928 → 478 terms, -450 removals)

**Removed per Kren's judgment:**
- Vendor/brand names: zebra, nomad, joel, jess, york, rice

**Kept per Kren:**
- axon (Molecular Devices amplifiers — deliberate non-instrument)
- barco, cisco, sony (vendor equipment)

**Result:** Non-Instrument list now precisely targets actual non-equipment items.

## Final Metrics (3 files, 17,201 rows)

| Metric | Value |
|--------|-------|
| **Software keywords (cleaned)** | 157 |
| **Non-Instrument keywords (cleaned)** | 478 |
| **Instrument keywords (locked)** | 160 ✓ |
| **Total junk removed** | 578 terms (-34%) |
| **Suppliers with keywords** | 100 |
| **Total keyword tokens** | 1,682 |

### Classification Results

| Type | File 1 | File 2 | File 3 | Average | Total |
|------|--------|--------|--------|---------|-------|
| Instrument | 1,249 | 1,249 | 1,251 | 1,250 | 3,749 |
| Software | 174 | 174 | 174 | 174 | 522 |
| Non-Instrument | 2,814 | 2,818 | 2,822 | 2,818 | 8,454 |
| Unknown | 1,490 | 1,492 | 1,494 | 1,492 | 4,476 |
| **Total** | 5,727 | 5,733 | 5,741 | | **17,201** |

### Rule Impact

- **Rule A (Prior Context):** ~146 items/file reclassified (Unknown → Instrument)
- **Rule B (Supplier Metadata):** ~631 items/file reclassified (Unknown → Instrument, price ≥ $1k)
- **Rule C (Bundle Analysis):** ~15 items/file reclassified (Unknown → extracted first item)

## Test Status

✅ **All tests passing (7/7):**
- test_word_boundary
- test_strong_vs_weak
- test_real_keyword_lists
- test_riders_and_price_gate
- test_software_classification (pCLAMP + INCUCYTE assertions)
- test_prune
- test_type_gate

## Changes Made

**File:** `src/services/data-cleaning/column_filter_and_classify_v3.py`

1. `_JUNK_SW` frozenset: 50 terms (IT/DevOps + stopwords + fragments + non-scientific brands)
2. `_JUNK_NI` frozenset: 40 terms (stopwords + fragments + vendor names)
3. Both wired into `load_and_clean_keywords()` function

**File:** `tests/test_classify_v3.py`

- New assertions: pCLAMP and INCUCYTE Software classification

## Interpretation

1. **Keyword quality:** Aggressive but precise cleanup. 578 junk terms removed (34% reduction).

2. **Software list now focused:** From 285 generic terms to 157 genuine research software packages. Non-scientific brands (Adobe, Autocad, Visio, Revit, Salesforce, Intel) removed.

3. **Non-Instrument precision:** Vendor/person names (Zebra, Nomad, Joel, Jess, York, Rice) removed while keeping load-bearing terms and Kren's deliberate Non-Instrument classifications (axon, barco, cisco, sony).

4. **Supplier gate effective:** 100 suppliers retain unique keywords after pruning (~63% filtered as too generic).

5. **Classification balanced:**
   - Instrument: 21.8% of rows
   - Software: 3.0% of rows
   - Non-Instrument: 49.1% of rows
   - Unknown: 26.0% of rows (acceptable; Rule B/C reclassifications add Instrument)

## Ready for Next Phase

✅ Code changes approved and tested
✅ Keyword lists finalized
✅ All tests passing
✅ Metrics captured

**Next:** Run full pipeline (scraper stage) to validate PDF downloads are now Instrument/Software-focused, not generic vendor crawls.

---

**Completed:** 2026-07-13 20:00 EDT
**Branch:** cleanup/ponytail-audit
**Status:** READY FOR DEPLOYMENT
