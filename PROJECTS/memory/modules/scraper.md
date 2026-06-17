# SCRAPER_FULL Module - Overview

**Status**: Phase 3 (Pending)
**Purpose**: Web scraping & PDF downloading
**Lines of Code**: Unknown (TBD)

---

## What It Does

Crawls websites for PDF resources and downloads them with intelligent retry logic and concurrent connections.

---

## Core Components

| Component | Purpose |
|-----------|---------|
| `pdf_crawler_gui.py` | GUI for web scraping & PDF downloads |
| Download logic | Concurrent downloads with retry & timeout handling |
| Content filtering | Filter non-relevant PDFs |

---

## Key Features

- 🕷️ Intelligent web crawling
- ⬇️ Concurrent downloads
- 🔁 Retry logic for failures
- ⏱️ Smart timeout handling
- 🔍 Content filtering
- 📊 Progress reporting

---

## Performance

- ~10 PDFs/min (with concurrent connections)

---

## Running

```bash
python PROJECTS/Scraper_full/pdf_crawler_gui.py
```

---

## Phase 3 Action Items

- [ ] Audit code structure
- [ ] Optimize concurrent download logic
- [ ] Add error handling
- [ ] Performance testing
- [ ] Expand test coverage

---

## Last Reviewed
May 14, 2026
