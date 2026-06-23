# Crawler Adjustments Implementation Plan

**Goal:** 4 interconnected improvements to data handling, PDF management, and classification learning.

---

## Data Flow

```
Original Excel (all columns)
    ↓
[Phase 1] Data-Cleaning → filters to B, G, I, O only → outputs cleaned Excel
    ↓
[Stage 1] Scraper → reads cleaned Excel (already filtered)
    ↓
[Stage 2] Classify → processes cleaned data
    ↓
[Stage 3] Cross-Ref → dedup + linking
```

**Key insight:** Phase 1 is the gatekeeper. Once data is filtered to B, G, I, O, all downstream stages automatically receive filtered data.

---

## Phase 0: Current State Documentation

### Column Filtering
- **Current:** Data flows through all columns in Excel files
- **Target:** Filter to columns B (Requisition ID), G (Supplier Name), I (Item Description), O (Comments)
- **Affected files:**
  - `src/services/data-cleaning/data_cleaner.py` — reads original Excel, outputs cleaned + filtered
  - `src/services/classify/adaptive_excel_processor.py` — reads cleaned Excel from Phase 1
  - `src/services/cross-reference/crossref_standalone_fast.py` — reads cleaned Excel from Phase 1
  - **Note:** `scraper_engine.py` reads cleaned Excel output from Phase 1 (no changes needed)

### Auto-Learning (Software/Research/Non-Instrument)
- **Current:** `adaptive_excel_processor.py` has learning_mode=True
  - Tracks `candidate_keywords` with confidence scores
  - Calls `promote_candidate_keywords()` to auto-promote when min_occurrences hit
  - Already validates keywords before promotion
  - Backs up old keyword files before updating
  - Generates learning reports and analytics
- **Target:** Make approval workflow explicit (currently auto-promotes, we want flagging)
- **Affected files:**
  - `src/services/classify/adaptive_excel_processor.py:promote_candidate_keywords()` — promotion logic
  - Keyword files: `hw_keywords_file`, `sw_keywords_file`, `ni_keywords_file`

### PDF Deduplication
- **Current:** `scraper_engine.py:_StateDB` tracks `seen_urls` table
  - Checks `is_seen(url)` before downloading
  - Only dedup by URL, not by description
  - Doesn't handle same item appearing twice in input
- **Target:** Track by *both* URL and description
  - If same description appears twice, download once, reference twice
  - If same URL appears twice, definitely skip second
- **Affected files:**
  - `src/services/scraper-full/scraper_engine.py:_StateDB` — add description tracking
  - PDF naming/storage logic

### Item Deduplication
- **Current:** Cross-ref matches items to PDFs by description
  - No de-duping of identical items in input
- **Target:** Detect duplicate items (same description from same supplier)
  - Download PDF once
  - Both rows reference the same PDF
- **Affected files:**
  - `src/services/cross-reference/crossref_standalone_fast.py` — matching/linking logic

---

## Phase 1: Column Filtering (B, G, I, O only) — THE GATEKEEPER

This phase runs first and outputs cleaned, filtered Excel. All downstream stages read this output.

### 1.1 Update data_cleaner.py to select columns on read

**What:** Filter original Excel to only columns B, G, I, O  
**File:** `src/services/data-cleaning/data_cleaner.py`  
**Current:** Reads all columns, optionally cleans supplier names  
**Changes:**
- Modify Excel read to use `usecols=['B', 'G', 'I', 'O']`
- Rename columns to meaningful names: `requisition_id`, `supplier_name`, `item_description`, `comments`
- Update all column references throughout the file to use new names
- Output cleaned Excel with *only these 4 columns*

**Verify Phase 1 works:**
```bash
# Run data cleaner on original Excel
python src/services/data-cleaning/data_cleaner.py --input original.xlsx --output cleaned.xlsx

# Check output
import pandas as pd
df = pd.read_excel('cleaned.xlsx')
print(df.columns)
# Expected: ['requisition_id', 'supplier_name', 'item_description', 'comments']
print(len(df.columns))
# Expected: 4
```

---

### 1.2 Update adaptive_excel_processor.py to expect pre-filtered data

**What:** Adapt classifier to work with 4-column input from Phase 1  
**File:** `src/services/classify/adaptive_excel_processor.py`  
**Current:** Uses `find_description_column()` and `find_supplier_column()` to auto-detect columns  
**Changes:**
- In `read_excel_file()`: No changes needed (already reads Excel)
- Update `find_description_column()`: Since column I is always description now, return it directly
- Update `find_supplier_column()`: Since column G is always supplier now, return it directly
- OR: Remove `find_*_column()` entirely and assume fixed column order (simpler)

**Verify Phase 1+2 work:**
```bash
# Run pipeline up to classify stage
python src/services/pipeline.py --only-classify

# Check output has description + classification
# Verify no "column not found" errors
```

---

### 1.3 Update crossref_standalone_fast.py for filtered data

**What:** Cross-ref expects 4-column input from Phase 1  
**File:** `src/services/cross-reference/crossref_standalone_fast.py`  
**Current:** Searches for supplier/description columns dynamically  
**Changes:**
- Assume columns are: `requisition_id`, `supplier_name`, `item_description`, `comments`
- Remove dynamic column discovery
- Use fixed column names throughout

**Verify Phase 1-3 work:**
```bash
# Run full pipeline
python src/services/pipeline.py

# Check all output files have expected 4 columns
# Check no column lookup errors in logs
```

---

### No changes to scraper_engine.py

**Why:** Scraper reads the cleaned Excel output from Phase 1 (already filtered). The engine extracts supplier names and PDFs—it doesn't need column filtering logic.



---

## Phase 2: PDF Deduplication by Description

### 2.1 Extend _StateDB to track descriptions

**File:** `src/services/scraper-full/scraper_engine.py:_StateDB`  
**Current schema:**
```sql
CREATE TABLE seen_urls (url TEXT PRIMARY KEY, status TEXT, ts TEXT);
CREATE TABLE downloaded (path TEXT PRIMARY KEY, url TEXT, supplier TEXT, ts TEXT);
```

**New schema:** Add description-based tracking
```sql
CREATE TABLE seen_items (
    item_description TEXT,
    supplier TEXT,
    url TEXT,
    downloaded_path TEXT,
    PRIMARY KEY (item_description, supplier)
);
```

**Changes:**
- Add `is_item_seen(description, supplier)` → returns (bool, path)
- Add `mark_item_downloaded(description, supplier, url, path)` 
- Existing `is_seen(url)` stays for URL dedup

**Logic:**
1. Before download: check both `is_seen(url)` AND `is_item_seen(description, supplier)`
2. If URL seen → skip (same PDF, different context)
3. If description+supplier seen → skip, reuse existing path
4. Otherwise → download, mark both tables

### 2.2 Update scraper to use description-based dedup

**File:** `src/services/scraper-full/scraper_engine.py` (PDF download section)  
**Changes:** In the main download loop, call new dedup checks before fetching

**Verification:**
```bash
# Run scraper with duplicate URLs in input
# Verify only one PDF downloaded per unique description
# Check .scraper_dedup.db has entries in seen_items table
```

---

## Phase 3: Item Deduplication in Cross-Ref

### 3.1 Detect duplicate items during cross-ref

**File:** `src/services/cross-reference/crossref_standalone_fast.py`  
**Changes:**
- Before linking items to PDFs, group by (supplier_name, item_description)
- For each group:
  - If N rows with same item → assign same PDF to all N
  - Track which row is "primary" (first occurrence)
  - Mark duplicates with reference to primary row

**Logic:**
```python
# Pseudo-code
items = load_items()  # B, G, I, O columns
grouped = items.groupby(['supplier', 'description'])

for (supplier, desc), group_rows in grouped:
    pdf_path = find_pdf_for_item(supplier, desc)
    primary_row = group_rows.iloc[0]
    
    for idx, row in group_rows.iterrows():
        if idx == primary_row.index:
            output[idx] = {requisition_id, supplier, desc, pdf_path, is_primary=True}
        else:
            output[idx] = {requisition_id, supplier, desc, pdf_path, is_primary=False, primary_ref=primary_row.requisition_id}
```

**Verification:**
```bash
# Run cross-ref on input with duplicate items
# Check output: duplicates have same PDF path
# Check output: duplicates marked with primary_ref field
```

---

## Phase 4: Auto-Learning Approval Workflow

### 4.1 Flag unclassified items instead of Unknown

**File:** `src/services/classify/adaptive_excel_processor.py:classify_item()`  
**Current:** Returns "Unknown" for items with no keyword match  
**Change:** 
- Still return "Unknown" but also add row-level flag: `NEEDS_REVIEW_INSTRUMENT_TYPE`
- Store in output Excel with comment

**Verification:**
```bash
# Classify file with borderline items
# Check output has NEEDS_REVIEW_INSTRUMENT_TYPE flag in comments column
```

### 4.2 Create promotion workflow

**File:** `src/services/classify/adaptive_excel_processor.py`  
**Change:**
- After classification run, call `promote_candidate_keywords(min_occurrences=5)` (or config value)
- This already exists, but:
  - Write promoted keywords to a `suggested_keywords.log` file with counts
  - Don't auto-save to keyword files; require manual review + commit
  - OR: Set a flag that blocks next run until manual approval

**Promotion file format:** `suggested_keywords.log`
```
=== Keywords Ready for Promotion ===
Hardware:
  - keyword1: 7 occurrences (confidence 2.1)
  - keyword2: 5 occurrences (confidence 1.8)

Software:
  - (none ready)

Non-Instrument:
  - keyword3: 6 occurrences (confidence 1.5)
```

**Manual approval:** Edit `hw_keywords.txt`, `sw_keywords.txt`, `ni_keywords.txt` directly, then re-run pipeline

**Verification:**
```bash
# Run classification on file with 5+ unclassified items
# Check suggested_keywords.log is created
# Verify keywords are not auto-added to keyword files
# Manually add keyword, re-run, verify it's used in classification
```

---

## Phase 5: Integration & Testing

### 5.1 Update pipeline.py

- Ensure column filtering happens at data-cleaning stage
- Learning report is generated at end of classify stage
- Cross-ref uses filtered columns

### 5.2 End-to-end test

**Input:** Excel with 10 items, 3 duplicates, some unclassified  
**Expected output:**
- Only 4 columns in all intermediate files
- Duplicate items reference same PDF
- New keywords flagged for review but not auto-promoted
- Learning report shows candidates

---

## Implementation Order

1. **Phase 1:** Column filtering (simplest, impacts all downstream)
2. **Phase 2:** PDF dedup by description (no dependencies)
3. **Phase 3:** Item dedup in cross-ref (depends on Phase 1)
4. **Phase 4:** Learning approval (already mostly built, just disable auto-save)
5. **Phase 5:** Integration & testing

**Estimated effort:**
- **Phase 1:** 3 files (data_cleaner, adaptive_excel_processor, crossref), ~60 lines total
  - data_cleaner: column filtering + rename
  - adaptive_excel_processor: remove dynamic detection, assume fixed columns
  - crossref: remove dynamic detection, assume fixed columns
- **Phase 2:** 1 file (scraper_engine), ~40 lines (add description-based dedup table + logic)
- **Phase 3:** 1 file (crossref), ~60 lines (group by supplier+description, assign same PDF)
- **Phase 4:** 1 file (adaptive_excel_processor), ~20 lines (disable auto-save, write suggested_keywords.log)
- **Phase 5:** validation + minor pipeline config updates

---

## Files to Modify

1. `src/services/data-cleaning/data_cleaner.py` — **Phase 1: Column filtering (gatekeeper)**
2. `src/services/classify/adaptive_excel_processor.py` — **Phase 1: Expect fixed 4-column input**
3. `src/services/cross-reference/crossref_standalone_fast.py` — **Phase 1: Expect fixed 4-column input**
4. `src/services/scraper-full/scraper_engine.py` — ~~Phase 1~~ **No changes** (uses Phase 1 output)
5. `src/services/pipeline.py` — **Phase 5: Minor config/logging updates**

## Files to Review Before Starting

- `PROJECTS/CLAUDE.md` — project structure & conventions
- `PROJECTS/CONTEXT.md` — current implementation state
- `pipeline_config.json` — which stages are enabled

---

## Execution Checklist

### Before You Start
- [ ] Read CLAUDE.md, CONTEXT.md to understand project layout
- [ ] Verify `pipeline_config.json` has all stages enabled
- [ ] Backup current keyword files (hw_keywords.txt, sw_keywords.txt, ni_keywords.txt)
- [ ] Create a test Excel file with:
  - 10 items total
  - 3 duplicate items (same description from same supplier)
  - 2 items with unknown classification
  - Include all columns B, F, G, I, O (F is noise column to drop)

### Phase 1 Execution
- [ ] **1.1** Update data_cleaner.py: add `usecols=['B', 'G', 'I', 'O']`, rename columns
- [ ] **1.2** Update adaptive_excel_processor.py: remove dynamic column detection
- [ ] **1.3** Update crossref_standalone_fast.py: remove dynamic column detection
- [ ] Test Phase 1: Run data cleaner on test file, verify 4-column output
- [ ] Test Phase 1→2: Run classify stage, verify no column lookup errors

### Phase 2 Execution
- [ ] **2.1** Extend _StateDB in scraper_engine.py: add `seen_items` table
- [ ] **2.2** Update scraper PDF download loop: check description-based dedup before fetching
- [ ] Test Phase 2: Run scraper with duplicate URLs in input, verify only one PDF downloaded

### Phase 3 Execution
- [ ] **3.1** Update crossref_standalone_fast.py: add groupby logic for duplicate items
- [ ] Test Phase 3: Run cross-ref on test file with duplicates, verify same PDF for all copies

### Phase 4 Execution
- [ ] **4.1** Update classify_item() to flag unclassified with `NEEDS_REVIEW_INSTRUMENT_TYPE`
- [ ] **4.2** Disable auto-save of promoted keywords, write `suggested_keywords.log` instead
- [ ] Test Phase 4: Run classify on file with unclassified items, verify log file created

### Phase 5 Execution
- [ ] Update pipeline.py logging to confirm filtered columns flowing through
- [ ] Run full pipeline on test file
- [ ] Verify all 4 phases work end-to-end
- [ ] Check output Excel has expected columns + dedup + learning log

### Post-Implementation
- [ ] Delete test Excel file
- [ ] Restore keyword files if test modified them
- [ ] Document any config changes in CLAUDE.md
- [ ] Commit changes to git
