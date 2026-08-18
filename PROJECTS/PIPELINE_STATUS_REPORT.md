# Pipeline Status Report — 2026-05-12

## Current Run Status

**Pipeline Started**: 14:04:34 UTC  
**Current Stage**: Stage 1 (Scraper) — in progress  
**Expected Duration**: 75-120 minutes (Scraper dominates timeline)  
**Log File**: `src/services/cross-reference/results/pipeline_20260512_140434.log`

---

## WHAT THE PIPELINE DOES — END-TO-END FLOW

### The Core Question
**"Which items from our procurement Excel files are documented in supplier PDFs?"**

### The Solution
The pipeline automatically:
1. Downloads PDFs from 247 supplier websites
2. Classifies items from procurement Excel files (Instrument/Software/Non-Instrument)
3. Resolves unknown suppliers via web search
4. Cross-references items to PDFs with confidence scoring

---

## COMPLETE DATA FLOW

```
INPUT                          PROCESSING                    OUTPUT
─────────────────────────────────────────────────────────────────────

Procurement Excel Files        Stage 0: Clean                 Cleaned Excel
(SOM - Statement of Materials) ──────────────────────────→   (in-place)
                                   ↓

Supplier Master List           Stage 1: Scraper              Downloaded PDFs
(247 suppliers with URLs)      ──────────────────────────→   data/scraped-pdfs/
                                   ↓                         (4,000-6,000 files)

Classified Items               Stage 2: Classify              Labeled Excel
(from Procurement)             ──────────────────────────→   (+ Classification column)
                                   ↓

Unknown Suppliers              Stage 2b: Resolve              Resolved & Pending
(from classified items)        ──────────────────────────→   Supplier Lists
                                   ↓

Labeled Items + PDFs +         Stage 3: Cross-Ref             ⭐ FINAL PRODUCT
Supplier Master                ──────────────────────────→   crossref_results_
                                                              [timestamp].xlsx
```

---

## FINAL PRODUCT: crossref_results_[timestamp].xlsx

**Location**: `C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results\`

**What It Contains**:
| Column | Description |
|--------|-------------|
| Match Result | ✅ MATCH! PDF N/M: filename (Score: X.X%) |
| Item Code | Item ID from procurement Excel |
| Description | Item description from procurement Excel |
| Category | Classification: Instrument/Software/Non-Instrument |
| PDF File | Name of matched PDF document |
| Match Score (%) | Confidence score (0-100) |
| Supplier | Supplier company name |

**Example Data** (from last successful run):
```
RAMM-BASIC microscope framework 
→ MIM & RAMM Manual.pdf (52.8% confidence, Applied Scientific Instrumentation Inc)
→ RAMM Microscope Configuration Guide.pdf (53.2% confidence)
→ TN128 RAMM-CDZ Assembly Instructions.pdf (35.7% confidence)
```

**What This Means**:
- Research team can see which procurement items are documented
- Each item can have multiple matching PDFs from the same supplier
- Confidence scores show how likely the match is accurate (60%+ = threshold)
- Can trace items directly to supplier documentation

---

## LATEST SUCCESSFUL RUN

**Date**: 2026-05-11 (May 11)  
**Log**: `pipeline_20260511_121827.log` (616 KB)

**Results**:
- ✅ Stage 0 (Data Cleaning): 2 files, 0 rows cleaned
- ✅ Stage 1 (Scraper): Downloaded PDFs from 245 suppliers
- ✅ Stage 2 (Classify): 2 files processed in 4 seconds
- ✅ Stage 2b (Supplier Resolution): 8 seconds (success)
- ❌ Stage 3 (Cross-Ref): Failed - missing module (crossref_utils)
- **Final Result**: 81 matched items (from previous working run)

---

## TODAY'S RUN (2026-05-12)

**Status**: IN PROGRESS (Stage 1 — Scraper)  
**Loaded**: 245 valid suppliers from master list  
**Progress**: Batch 1/25 (suppliers 1-10 processing)

### What's Happening Right Now
The scraper is:
- Fetching each supplier's website
- Finding PDFs to download
- Extracting text from PDFs for matching
- Organizing downloaded files by supplier

**Expected Timeline**:
- Scraper: ~60-90 minutes (batched, rate-limited at 2s/request)
- Classify: ~2-5 minutes
- Supplier Resolution: ~5-15 minutes
- Cross-Ref: ~5-10 minutes
- **Total**: ~75-120 minutes

**Scraper Details**:
- 245 suppliers to process
- 25 batches of 10 suppliers each
- 3 concurrent requests max (to avoid overwhelming servers)
- 2 second delay between requests
- Max 50 pages per supplier
- Max 100MB per PDF
- ~4,000-6,000 PDFs expected

---

## PIPELINE CONFIGURATION

**File**: `src/services/pipeline_config.json`

```json
{
  "paths": {
    "supplier_excel": "data/masterlist/updated_master_list.xlsx",
    "pdf_dir": "data/scraped-pdfs",
    "input_excel_dir": "data/som-in",
    "labeled_dir": "data/som-in-labeled",
    "master_excel": "data/masterlist/updated_master_list.xlsx",
    "results_dir": "src/services/cross-reference/results"
  },
  "pipeline": {
    "run_data_cleaner": true,
    "run_scraper": true,
    "run_classify": true,
    "run_supplier_resolution": true,
    "run_crossref": true
  }
}
```

---

## KEY METRICS

### Master List (Updated 2026-05-11)
- **Before**: 190 suppliers
- **After**: 247 suppliers
- **New Suppliers Added**: 57 (from pending resolution)
- **Duplicates Removed**: 2
- **Data Gap**: 2 suppliers without websites

### Data Cleaner
- **Status**: ✅ All 31 tests passing
- **Ready for**: Integration as Stage 0
- **Fixes Applied**: 3 implementation bugs, 1 test expectation

### Supplier Resolution
- **Status**: ✅ Production-ready
- **Tests Passing**: 29/29
- **Confidence Threshold**: 70%
- **Last Run Result**: 60 suppliers → 0 pending (all resolved)

### Expected Output (this run)
- **PDFs Downloaded**: ~4,000-6,000 files
- **Items to Match**: ~500+ (from procurement Excel)
- **Expected Matches**: 60-150+ (based on historical 15-30% match rate)
- **Output File**: `crossref_results_20260512_[HH]:[MM]:[SS].xlsx`

---

## HOW TO MONITOR THE PIPELINE

**Watch the Log**:
```powershell
tail -f "src/services/cross-reference/results/pipeline_20260512_140434.log"
```

**Key Milestones to Look For**:
```
✅ "Data cleaning finished"  → Stage 0 complete
✅ "Scraper finished in X s" → Stage 1 complete (bulk of time)
✅ "Classify finished in X s" → Stage 2 complete
✅ "Supplier resolution finished" → Stage 2b complete
✅ "Cross-ref finished in X s — M match(es) saved" → Stage 3 complete (FINAL PRODUCT)
```

**Check Results**:
```powershell
ls -la "src/services/cross-reference/results/crossref_results_*.xlsx"
```

---

## WHAT HAPPENS AFTER THE PIPELINE

**Result File Analysis**:
```excel
✅ Row 1: Item Code → Description → PDF → Confidence Score
✅ Row 2: Item Code → Description → PDF → Confidence Score
...
```

**Next Steps**:
1. Open `crossref_results_[timestamp].xlsx` in Excel
2. Sort by confidence score (highest first)
3. Review high-confidence matches (80%+)
4. Identify items with no matches (research gap)
5. Validate manually for critical items
6. Integrate PDF links into procurement system

---

## TROUBLESHOOTING

If pipeline fails at any stage:

**Check Stage 0 (Data Cleaning)**:
- Verify `data/som-in` has readable .xlsx files
- Check for corrupted Excel formats

**Check Stage 1 (Scraper)**:
- Network connectivity to supplier websites
- Some sites may block automated scraping (403 errors are normal)
- Check `pipeline_*.log` for specific URL failures

**Check Stage 2 (Classify)**:
- Keyword files must exist in `src/services/classify/`
- Verify column headers in input Excel files

**Check Stage 2b (Supplier Resolution)**:
- Master list must have supplier names and URLs
- Web searches require internet connectivity

**Check Stage 3 (Cross-Ref)**:
- PDFs must exist in `data/scraped-pdfs/`
- Master Excel must have valid supplier list
- Labeled Excel must have classification column

---

## QUESTIONS ANSWERED

**Q: Where are the results of the PDFs cross-referenced with downloads?**  
**A**: `src/services/cross-reference/results/crossref_results_[timestamp].xlsx`

**Q: Where does the pipeline lead (end)?**  
**A**: Stage 3 (Cross-Reference) → Final output Excel file with matched items-to-PDFs

**Q: What is the product at the end?**  
**A**: Excel file containing all procurement items that matched with downloaded supplier PDFs, with confidence scores and PDF file names

---

*Report Generated: 2026-05-12 14:05 UTC*
*Pipeline Status: IN PROGRESS (Stage 1 - Scraper running)*
