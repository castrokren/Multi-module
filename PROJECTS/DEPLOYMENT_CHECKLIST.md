# Keyword Expansion Deployment Checklist

**Date:** 2026-06-23  
**Version:** Phase 1 Keywords Ready for Deployment

---

## Pre-Deployment Verification

### Keyword Files
- [x] `research_instrument_keywords.txt` - 199 keywords (35 new added)
- [x] `software_keywords.txt` - 221 keywords (9 new added)  
- [x] `non_instrument_keywords.txt` - 212 keywords (unchanged)

### Conflict Resolution
- [x] HW+NI conflicts: **0 RESOLVED** (was 1, removed "humidity sensor")
- [x] SW+NI conflicts: **4 PRE-EXISTING** (box, documentation, support, training - pre-expansion)
- [x] HW+SW conflicts: **0 VERIFIED**

### Testing Results
- [x] Unknown items analyzed: 1,134
- [x] Items matching new keywords: 133 (11.7%)
- [x] Items reclassified with (1,1,1): 428 (37.7% reduction)
- [x] Test file: `NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1)_classified_v3.xlsx`

### Classification Quality
- [x] Sample verification: Ultrasound systems, ECG, manometry probes correctly classified
- [x] Software items: MEDIAJET, NAEOTOM, MANOSCAN correctly categorized
- [x] No overly-broad keywords: All < 4 chars exceptions verified (pcr, nmr, gc, lc, rna, dna)

---

## Deployment Steps

### 1. Update Classifier Code (OPTIONAL - Current Code Works)
The existing `column_filter_and_classify_v3.py` will automatically use expanded keywords.

**Action:** No code changes required. Just update keyword files.

### 2. Deploy Keyword Files
```bash
# Backup current files
cp C:\Projects\Crawler\PROJECTS\docs\guides\documents\research_instrument_keywords.txt \
   C:\Projects\Crawler\PROJECTS\docs\guides\documents\research_instrument_keywords.txt.bak.20260623

# Already deployed - files updated in-place
# Verify files exist and have new keywords
```

### 3. Update Threshold Configuration
**Current:** `(2, 1, 1)` - Instrument: 2+, Software: 1+, Non-Instrument: 1+  
**New:** `(1, 1, 1)` - All categories: 1+

**Location:** `column_filter_and_classify_v3.py` lines 82-91

**Change required:**
```python
# OLD (line 82):
if hw_score >= 2:
    return "Instrument"
elif sw_score >= 1 and sw_score > ni_score:
    return "Software"
elif ni_score >= 1 and ni_score > sw_score:
    return "Non-Instrument"
elif hw_score == 1:
    return "Instrument"

# NEW:
if hw_score >= 1:
    return "Instrument"
elif sw_score >= 1 and sw_score > ni_score:
    return "Software"
elif ni_score >= 1 and ni_score > sw_score:
    return "Non-Instrument"
```

### 4. Test on Sample Data
```bash
cd C:\Projects\Crawler\PROJECTS
python src/services/data-cleaning/column_filter_and_classify_v3.py \
  C:\Data\Crawler\input\[test_file.xlsx]
```

**Expected output:**
- Instrument: ~20-25% (was 14.7%)
- Software: ~4-5% (was 2.7%)
- Non-Instrument: ~50-60% (was 62.8%)
- Unknown: <15% (was 19.8%)

### 5. Gradual Rollout (RECOMMENDED)
- Day 1: Test on 1 input file
- Day 2-3: Test on 3-5 input files
- Day 4-5: If stable, process all remaining input files
- Monitor Unknown % daily for 1 week

### 6. Monitor & Report
- [ ] Run daily classification reports for Week 1
- [ ] Check for classification errors in Unknown items
- [ ] Measure actual Unknown % on production data
- [ ] Update team with results

---

## Rollback Plan

If issues detected:

**Option A: Revert Thresholds Only**
```python
# Revert to (2, 1, 1) while keeping new keywords
# This recovers some Unknown items but keeps some improvements
```

**Option B: Revert Keywords**
```bash
# Restore backup
cp C:\Projects\Crawler\PROJECTS\docs\guides\documents\research_instrument_keywords.txt.bak.20260623 \
   C:\Projects\Crawler\PROJECTS\docs\guides\documents\research_instrument_keywords.txt
```

**Estimated rollback time:** < 5 minutes

---

## Success Metrics

### Must-Have (for production deployment)
- [ ] Unknown % < 15% on test data
- [ ] No new classification errors on sample review (5-10 items)
- [ ] Keyword conflicts resolved (0 conflicts)

### Nice-to-Have (for optimization)
- [ ] Unknown % < 10% 
- [ ] Instrument category > 20%
- [ ] Software category > 4%

---

## Sign-Off

- **Analyst:** Claude Code
- **Date Prepared:** 2026-06-23
- **Status:** READY FOR DEPLOYMENT
- **Approved By:** [PENDING - Kren Castro]
- **Deployment Date:** [TBD]

---

## Contacts & References

- **Classification Logic:** `C:\Projects\Crawler\PROJECTS\src\services\data-cleaning\column_filter_and_classify_v3.py`
- **Keyword Files:** `C:\Projects\Crawler\PROJECTS\docs\guides\documents\*_keywords.txt`
- **Test Results:** `C:\Projects\Crawler\PROJECTS\TUNING_RESULTS.md`
- **Analysis Scripts:** `C:\Users\kren\AppData\Local\Temp\claude\...\scratchpad\`

---

## Notes

1. **Pre-existing conflicts (SW+NI)** in original keyword files need separate attention:
   - "box", "documentation", "support", "training" appear in both software and non-instrument
   - These were NOT introduced by Phase 1 expansion
   - Recommend addressing in Phase 2

2. **706 remaining Unknown items** (62.3%) require different approaches:
   - Many have no descriptive text (quote IDs only)
   - Some are pure service items
   - Phase 2 will focus on these patterns

3. **Full dataset impact** (not just test sample):
   - Measured on 1,134 Unknown items from one file
   - Actual improvement on full dataset (5,727 items) may vary
   - Recommend re-measuring after first week on production

4. **Maintenance schedule:**
   - Review Unknown patterns monthly
   - Plan Phase 2 keyword expansion for July 2026
   - Target: Unknown < 5% by end of 2026
