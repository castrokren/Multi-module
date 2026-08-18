# CROSS-REFERENCE Module - Overview

**Status**: Phase 2 (Pending, after CLASSIFY completes) — but actively patched as part of pipeline deployment
**Lines of Code**: ~1500+
**Test Coverage**: Unknown (likely limited)

---

## What It Does

Links PDFs to institutional records and creates cross-reference mappings. Validates relationships and can recover from interrupted operations.

---

## Core Components

| Component | Purpose |
|-----------|---------|
| `crossref_standalone_fast.py` | **NEW PRIMARY**: Fast cross-reference engine (paths fixed May 2026) |
| `crossref_standalone.py` | Original engine (may still be in use) |
| `crossref_recovery.py` | Resume interrupted operations, error recovery |
| `instrument_labeling_manager.py` | Identify & label instruments in PDFs |
| `run_crossref_cli.py` | Command-line interface |
| `check_progress.py` | Show operation progress |
| `check_results.py` | Validate cross-reference results |

---

## Workflow

1. **Input**: Collection of PDF files
2. **Extraction**: Read metadata & content from PDFs
3. **Matching**: Link PDFs to institutional records
4. **Validation**: Verify links are correct
5. **Output**: Generate mapping files & reports

---

## Key Features

- 🔗 Automated PDF-to-record linking
- ✅ Cross-reference validation
- 🔄 Operation recovery (resume on failure)
- 📊 Progress tracking
- 🐛 Error handling & reporting

---

## Known Issues

- ~~Hardcoded paths~~ ✅ Fixed May 2026 (crossref_standalone_fast.py)
- ~~sys.path import errors~~ ✅ Fixed May 2026
- ~~pipeline_config.json path mismatch~~ ✅ Fixed May 2026
- Possible redundancy between standalone.py and recovery.py (still needs audit)
- May have duplicate progress checking (check_progress.py vs check_results.py)
- Performance unknown on large collections (1000+ PDFs)
- Testing coverage likely limited

---

## Phase 2 Action Items

- [ ] Audit crossref_standalone.py vs crossref_recovery.py
- [ ] Consolidate progress checking
- [ ] Add comprehensive error handling
- [ ] Performance test on 1000+ PDF collections
- [ ] Expand test coverage
- [ ] Create CROSSREFERENCE_MODULE.md

---

## Running

```bash
python PROJECTS/Cross-reference/run_crossref_cli.py
```

---

## Last Reviewed
May 28, 2026
