# Crawler Projects - Complete Pipeline Flow

## Input → Process → Output

### INPUT DATA
- **Supplier Master List**: C:\Projects\Crawler\PROJECTS\data\masterlist\updated_master_list.xlsx
  - 247 suppliers with website URLs
  - Updated from 190 → 247 after resolving new vendors (2026-05-11)

- **Input Excel Files**: C:\Projects\Crawler\PROJECTS\data\som-in
  - SOM (Statement of Materials) procurement files
  - Example: NQ_DG_RESEARCH_CAPITAL_V2-40827854.xlsx
  - Contains items to be classified and matched

---

## PIPELINE STAGES (5 Stages Total)

### STAGE 0: Data Cleaning
**Purpose**: Normalize and clean supplier names before processing
**Input**: Raw Excel files in `data/som-in`
**Output**: Same files, cleaned in-place
**Process**: 
- Remove asterisks (***ACME***) → ACME
- Remove USE codes (USE V#1) → removed
- Trim whitespace
- Normalize multiple spaces

---

### STAGE 1: Scraper (Downloads PDFs from Suppliers)
**Purpose**: Download PDFs from supplier websites
**Input**: Supplier master list (245-247 suppliers)
**Output**: PDF files downloaded to `data/scraped-pdfs/`
**Process**:
- For each supplier website URL:
  1. Discover pages (sitemap or recursive crawl)
  2. Find links to PDF files
  3. Download PDFs (100MB max size)
  4. Organize by supplier folder
  5. Extract text from each PDF for later matching

**Performance**: 60-90 minutes for 247 suppliers (with 2s delay between requests)
**Result**: ~4,000-6,000 PDFs downloaded (depending on supplier size)

Example structure:
```
data/scraped-pdfs/
├── 10X GENOMICS INC/
│   ├── 10x-technical-reference.pdf
│   ├── chromium-user-guide.pdf
│   └── [more PDFs...]
├── AGILENT TECHNOLOGIES INC/
│   ├── agilent-gcms-manual.pdf
│   └── [more PDFs...]
└── [247 supplier folders]
```

---

### STAGE 2: Classify (Categorize Excel Items)
**Purpose**: Categorize each item in Excel files as Instrument/Software/Non-Instrument
**Input**: Excel files from `data/som-in`
**Output**: Classified Excel → `data/som-in-labeled/`
**Process**:
- Read each row (item description)
- Score against keyword lists:
  - Hardware Keywords (research_instrument_keywords.txt)
  - Software Keywords (software_keywords.txt)
  - Non-Instrument Keywords (non_instrument_keywords.txt)
- Assign category: [Instrument] | [Software] | [Non-Instrument]
- Learning Mode: Auto-promote new keywords based on frequency
- Output: Same Excel with new "Classification" column

**Performance**: 2-5 minutes for typical files
**Files Processed**: 2 files (same files as Stage 0)

---

### STAGE 2b: Supplier Resolution (Resolve Unknown Suppliers)
**Purpose**: Find websites for suppliers mentioned in Excel but not in master list
**Input**: 
  - Classified Excel file (from Stage 2)
  - Master supplier list (247 suppliers)
**Output**: 
  - `data/supplier-pending/resolved_suppliers.xlsx` (high confidence matches to use in scraper)
  - `data/supplier-pending/new_suppliers_pending.xlsx` (low confidence → manual review)
**Process**:
- Extract unique supplier names from classified Excel
- Compare against master list
- For unknown suppliers:
  1. Search via DuckDuckGo: "{SUPPLIER NAME}" official website
  2. Search via Bing: "{SUPPLIER NAME}" official website
  3. Score results 0-130:
     - Both engines agree: +40
     - Domain matches name: +25
     - HTTPS: +15
     - TLD (.com/.org/.us/.edu): +10
     - Not marketplace: +20
- Route results:
  - ≥70 confidence → `resolved_suppliers.xlsx` (use in next scrape)
  - <70 confidence → `new_suppliers_pending.xlsx` (manual review)

**Performance**: 5-15 minutes for web searches (1.5s delay between requests)

---

### STAGE 3: Cross-Reference (THE FINAL PRODUCT)
**Purpose**: LINK CLASSIFIED ITEMS TO DOWNLOADED PDFs
**Input**:
- Classified Excel file (from Stage 2) with item descriptions
- Master supplier list (247 suppliers)
- Downloaded PDFs (from Stage 1) organized by supplier
**Output**: `src/services/cross-reference/results/crossref_results_[timestamp].xlsx`

**THE FINAL PRODUCT** is this Excel file containing:
```
MATCHED ROWS with columns:
- Item Row Number
- Item Description (from original Excel)
- Supplier Name
- PDF File Name
- Match Confidence Score
- PDF Content Preview (text extract)
- Match Details/Reasoning
```

**Process**:
1. For each classified item in Excel:
   - Extract item description text
   - Find supplier from master list
   - Search downloaded PDFs from that supplier
   - Score semantic match (keyword overlap, text similarity)
   - If confidence ≥ threshold (60):
     → Add to results

2. Export matched pairs to Excel with confidence scores

**Performance**: 5-10 minutes for 4,000+ PDFs vs 500+ items
**Result**: List of items successfully linked to supporting PDFs from suppliers

---

## COMPLETE DATA FLOW VISUALIZATION

```
INPUT EXCEL FILES          SUPPLIER MASTER LIST        DOWNLOADED PDFs
   (Items to find)         (Suppliers 1-247)           (from websites)
         |                       |                            |
         v                       v                            v
    STAGE 0              +-- STAGE 1 ----+
  (Data Clean)           |  (Scraper)    |
     |                   |               |
     v                   |    Downloads  |
   Clean Items           |    PDFs       |
     |                   +---------------+
     |
     v
  STAGE 2 (Classify)
     |
     v
  Classified Items + Label (Instrument/Software/Non)
     |                   |
     +---STAGE 2b--------+
     |  (Supplier Resolve)
     |
     v
  Classified Items + Supplier Name
     |
     +------+
            |
            v
       STAGE 3 (Cross-Ref)
       MATCHES ITEMS TO PDFs
            |
            v
    FINAL PRODUCT
  crossref_results_
  [timestamp].xlsx
  
  (Item → PDF Mapping
   with confidence scores)
```

---

## FINAL PRODUCT DETAILS

**File Location**: 
```
C:\Projects\Crawler\PROJECTS\src\services\cross-reference\results\
crossref_results_[TIMESTAMP].xlsx
```

**What It Contains**:
- All items from input Excel that matched with PDFs
- Supplier names from master list
- PDF file paths/names
- Confidence scores (0-100)
- Text previews from matching PDFs

**Purpose**: 
Document cross-reference report showing which procurement items were found in supplier documentation

**Use Case**:
Research team can now:
1. See which items are documented in supplier materials
2. Access the PDF files containing relevant documentation
3. Identify gaps (items with no matching PDFs)
4. Trace procurement items to source material

