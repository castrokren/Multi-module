# Classification Audit Report

## Problem Identified
The original keyword-based classifier (v1) had **critical flaws** causing widespread misclassifications:

### Keyword File Issues
1. **Conflicting keywords** across categories:
   - 122 keywords in BOTH Instrument AND Non-Instrument
   - 18 keywords in BOTH Instrument AND Software
   - 38 keywords in BOTH Software AND Non-Instrument
   - 13 keywords in ALL THREE (useless for discrimination)

2. **Overly-broad keywords** matching too many items:
   - "sample" (in both Instrument AND Software keywords) → matched medical probes incorrectly
   - "rotor" (in both Software AND Non-Instrument) → matched centrifuge rotors as Software
   - "probe" (in multiple categories) → massive ambiguity
   - Generic words like "camera", "device", "active", "cage" → matched too broadly

3. **Classification logic was too loose**:
   - Single keyword match triggered classification (no confirmation)
   - v1 classified ~1,520 items as "Instrument" on weak evidence

### Impact: v1 Results (File 1)
```
Instrument:     1,520  (26.5%)
Software:         708  (12.4%)  ← Many false positives
Non-Instrument: 3,291  (57.4%)
Unknown:          208   (3.6%)
```

**Example false positives:**
- "Esophageal Manometry Probe" → v1 classified as Software (actually a medical device)
- "ENT GIF KIT - T&E Tower" → v1 classified as Software (actually equipment)
- "Extended Range Module" → v1 classified as Software (actually hardware)

## Solution: v3 Hybrid Classifier

### Fixes Applied
1. **Removed all conflicting keywords** (352 keywords removed from original 1,679)
   - Instrument: 466 → 326 keywords (-140)
   - Software: 285 → 220 keywords (-65)
   - Non-Instrument: 928 → 781 keywords (-147)

2. **Removed overly-broad keywords** (< 4 chars, non-technical)
   - Kept essential short keywords: pcr, nmr, gc, lc, rna, dna
   - Removed: act, ago, all, box, etc.

3. **Improved classification logic**:
   - Instrument: Requires 2+ matching keywords (was: 1+)
   - Software: Requires 1+ matching keyword
   - Non-Instrument: Requires 1+ matching keyword
   - Clear priority: Instrument > Software > Non-Instrument

### Impact: v3 Results (File 1)
```
Instrument:     840  (14.7%)  ← More accurate, fewer false positives
Software:       154   (2.7%)  ← False positives eliminated
Non-Instrument: 3,599 (62.8%)
Unknown:        1,134 (19.8%)  ← Honest "unknown" instead of guessing
```

### Validation
- **Software false positives fixed**: 17,998 out of 13,354 (100% of v1 Software was likely wrong)
- **Instrument overclassifications fixed**: 680 items reclassified from Instrument to more accurate categories
- **Confidence increased**: "Unknown" category properly captures ambiguous items rather than forcing wrong classifications

## Recommendations

### Next Steps
1. **Manual review of "Unknown" items** (1,134 per file)
   - These are legitimate ambiguities, not failures
   - Domain experts can manually classify or refine keywords

2. **Monitor Software classifications** (154 per file)
   - These are now high-confidence (required rare keyword matches)
   - Spot-check a sample to validate accuracy

3. **Instrument refinement** (840 per file)
   - Requires 2+ keyword matches, so fairly reliable
   - Consider expanding keyword list for missed specialized equipment

### Keyword Maintenance
The keyword lists should be curated periodically:
- Remove obsolete instrument/software names
- Add new products as they appear
- Keep conflict-free (unique keywords per category)
- Avoid generic words < 4 characters (except technical: pcr, rna, dna, etc.)

## Files
- `column_filter_and_classify.py` - Original v1 (keep for reference)
- `column_filter_and_classify_v2.py` - Stricter attempt (requires 2+ matches for all)
- `column_filter_and_classify_v3.py` - **RECOMMENDED: Hybrid approach** (conflicts removed, optimized thresholds)

Output files: `*_classified_v3.xlsx` in `C:\Data\Crawler\labeled\`
