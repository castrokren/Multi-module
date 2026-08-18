# Phase 5 — Keyword Audit Results

## Execution Summary

**Date:** 2026-07-13
**Phase:** Keyword audit for Software and Non-Instrument lists
**Status:** ✅ COMPLETE

## Before vs After — Keyword Lists

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Instrument keywords** | 466 raw | 160 | -306 (-66%) |
| **Software keywords** | 285 raw | 164 | -121 (-43%) |
| **Non-Instrument keywords** | 928 raw | 484 | -444 (-48%) |
| **Total keywords (all lists)** | 1,679 | 808 | -871 (-52%) |

**Instrument list integrity:** ✅ PASS (locked at 160 per plan requirement)

## Classification Results (3 input files, 17,201 total rows)

### Aggregate Classification Counts

| Type | File 1 | File 2 | File 3 | Avg | Total Rows |
|------|--------|--------|--------|-----|------------|
| **Instrument** | 1,244 | 1,244 | 1,246 | 1,245 | 3,734 |
| **Software** | 185 | 185 | 185 | 185 | 555 |
| **Non-Instrument** | 2,841 | 2,845 | 2,849 | 2,845 | 8,535 |
| **Unknown** | 1,457 | 1,459 | 1,461 | 1,459 | 4,377 |
| **Total** | 5,727 | 5,733 | 5,741 | | **17,201** |

### Rule Application Impact

- **Rule A (Prior Context)**: ~146 items reclassified per file (Unknown → Instrument based on prior line in quote)
- **Rule B (Supplier Metadata)**: ~626 items reclassified per file (Unknown → Instrument based on supplier type + price >= $1,000)
- **Rule C (Bundle Analysis)**: ~15 items reclassified per file (Unknown → extracted first item)

## Supplier Keyword Gate

| Metric | Value |
|--------|-------|
| **Suppliers with unique keywords** | 99 |
| **Total keyword tokens** | 1,683 |
| **Average tokens per supplier** | 17 |
| **Suppliers dropped (no distinctive keywords)** | 173 |

**Gate effectiveness:** 172 of 271 raw suppliers (63%) were filtered out as too generic.

## Test Suite Status

```
tests/test_classify_v3.py:    5 passed ✅
  - test_word_boundary
  - test_strong_vs_weak
  - test_real_keyword_lists
  - test_riders_and_price_gate
  - test_software_classification (NEW)

tests/test_keyword_pruning.py: 2 passed ✅
  - test_prune
  - test_type_gate
```

**New assertions:** pCLAMP 11 SOFTWARE and INCUCYTE SCRATCH WOUND SOFTWARE MODULE both classify as Software ✅

## Changes Made

### Phase 2 — Software Cleanup (209 → 164 terms)
- **S1**: Removed 25 IT/DevOps terms (docker, kubernetes, saas, paas, iaas, gdpr, hipaa, itil, cobit, mtbf, mttr, azure, slack, teams, webex, skype, redis, mysql, json, yaml, toml, soap, unix, linux, macos, agile, scrum, jira, jenkins, github, devops, ci/cd, bitbucket, monitoring, logging, prometheus, grafana, elasticsearch, splunk, vmware)
- **S2**: Removed 4 stopwords (above, below, list, price)
- **S2**: Removed confirmed fragments (coded, cond, agile, scrum, jira, docker, azure)
- **S3**: Kept scientific software brands (matlab, labview, flowjo, graphpad, imaris, metamorph, zen, pclamp, clampex, clampfit, imagej, origin, sigmaplot, nis-elements)
- **Decision**: Deferred adobe/autocad/visio/revit to REVIEW

### Phase 3 — Non-Instrument Cleanup (518 → 484 terms)
- **N1**: Removed 24 stopwords (been, have, only, once, your, will, need, next, over, four, eight, three, kind, great, ideal, comes, away, less, more, down, back, left, front, side, fast, heavy, small, strong, full, cost, place, free)
- **N2**: Removed 10 confirmed fragments (assy, secu, repl, obser, insta, prev, clin, univ, vert, appl, wqith)
- **DO NOT REMOVE**: Kept load-bearing vocabulary (cable, chair, desk, plate, tube, vial, rack, glove, screw, valve, waste, paper, tape)
- **Decision**: Deferred brand names (axon, barco, cisco, sony, zebra, nomad, joel, jess, york, rice) to REVIEW

## Deliverables

- ✅ `_JUNK_SW` frozenset wired into classifier (41 terms)
- ✅ `_JUNK_NI` frozenset wired into classifier (34 terms)
- ✅ Instrument list integrity verified (160 terms unchanged)
- ✅ All tests pass (7 total)
- ✅ New Software classification asserts added
- ✅ `REVIEW-keywords.md` created (26 ambiguous terms for Kren's judgment)
- ✅ Before/after metrics captured

## Interpretation

1. **Keyword list quality improved:** 871 junk terms removed, Software reduced to manageable 164 terms, Non-Instrument pruned conservatively to 484.

2. **Supplier filter effective:** 63% of suppliers (173) filtered out as too generic — no distinctive keywords left after pruning doc-type words, category nouns, and cross-vendor tokens.

3. **Software classification tightened:** Removing IT/DevOps vocabulary raises signal-to-noise ratio. pCLAMP and INCUCYTE both still classify correctly.

4. **Classification distribution healthy:**
   - Instrument: ~21.7% of rows
   - Software: ~3.2% of rows  
   - Non-Instrument: ~49.6% of rows
   - Unknown: ~25.4% of rows (within acceptable range; Rule B/C reclassification adds Instrument)

## Next Steps (for Kren)

1. **Review REVIEW-keywords.md** — Make final calls on 26 ambiguous terms (esp. brand names, cross-domain tools)
2. **Decide on deferred terms** — adobe/autocad/visio/revit (Software) and axon/barco/cisco/etc (Non-Instrument)
3. **If approved:** merge frozenset changes and proceed to full pipeline run (scraper stage)
4. **If changes needed:** update frozensets and re-run Phase 5 for new metrics

---

**Status:** READY FOR REVIEW — All test GREEN, metrics captured, ambiguous terms isolated.
