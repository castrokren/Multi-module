# Development Roadmap - Multi-Phase Plan

**Overall Goal**: Systematically improve Crawler across 4 dimensions:
1. ✅ Fix bugs & improve stability
2. ✅ Add new capabilities  
3. ✅ Improve performance
4. ✅ Make it more maintainable

**Timeline**: Work through each module sequentially

---

## Phase 1: CLASSIFY Module (CURRENT)

**Duration**: 6 weeks (May-June 2026)
**Status**: 🔴 ACTIVE
**Current State**: 16 files, 1.2MB, many redundancies

### 1a. Code Audit & Deduplication (Week 1) - CRITICAL
**Status**: ❌ Not started
- [ ] Compare excel_processor.py vs adaptive_excel_processor.py
  - Decision: Keep adaptive (has learning), deprecate legacy
- [ ] Consolidate monitor variations (4 versions):
  - Keep: `simple_monitor.py` (core watchdog)
  - Archive: `standalone_monitor.py`, `service_script.py`, `simple_W_service.py`
- [ ] Archive `/older/` directory (safe storage)
- **Deliverable**: Single monitor, clean codebase

### 1b. Testing & Stability Improvements (Week 2-3) - HIGH
**Status**: ❌ Not started
- [ ] Expand adaptive_excel_processor.py tests
- [ ] Add error handling tests (corrupt files, missing keywords)
- [ ] Add integration tests (monitor → processor → output)
- [ ] Test all file extensions (.xls, .xlsx, edge cases)
- [ ] Test timeout/recovery (process_timeout=30)
- [ ] Target: 60%+ test coverage
- **Deliverable**: Comprehensive test suite

### 1c. Performance Optimization (Week 4) - MEDIUM
**Status**: ❌ Not started
- [ ] Profile adaptive_excel_processor performance
- [ ] Optimize keyword matching algorithm
- [ ] Add caching for repeated classifications
- [ ] Optimize learning_log.json writes
- [ ] Batch Excel file processing
- [ ] Target: 75+ items/min on avg hardware
- **Deliverable**: Performance improvements, profiling data

### 1d. Maintainability Improvements (Week 5-6) - MEDIUM
**Status**: ❌ Not started
- [ ] Create CLASSIFY_MODULE.md (comprehensive docs)
- [ ] Add type hints throughout codebase
- [ ] Refactor into sub-modules:
  - processors.py (core Excel logic)
  - monitor.py (file watching)
  - service.py (Windows service integration)
  - ui.py (UI components)
- [ ] Standardize logging across all files
- [ ] Create requirements_classify.txt
- **Deliverable**: Clean, modular, well-documented code

### Phase 1 Success Criteria
✅ Single monitor implementation
✅ 60%+ test coverage
✅ 75+ items/min performance
✅ Type hints on all functions
✅ Sub-module refactoring complete
✅ CLASSIFY_MODULE.md documentation

---

## Phase 2: CROSS-REFERENCE Module

**Duration**: 4-5 weeks (after Phase 1)
**Status**: 📋 PENDING
**Current State**: 15 files, 700KB

### 2a. Code Audit & Consolidation
- [ ] Audit crossref_standalone.py vs crossref_recovery.py
- [ ] Consolidate progress checking (check_progress.py, check_results.py)
- [ ] Clean up redundancy

### 2b. Testing & Stability
- [ ] Add comprehensive error handling
- [ ] Performance test on 1000+ PDF collections
- [ ] Expand test coverage to 50%+

### 2c. Performance Optimization
- [ ] Profile large PDF collection processing
- [ ] Optimize matching algorithm
- [ ] Improve recovery/resumption logic

### 2d. Maintainability
- [ ] Create CROSSREFERENCE_MODULE.md
- [ ] Add type hints
- [ ] Refactor into sub-modules

### Phase 2 Success Criteria
✅ No redundancy between standalone & recovery
✅ Consolidated progress checking
✅ 50%+ test coverage
✅ Performance tested on 1000+ PDFs
✅ Type hints on all functions

---

## Phase 3: SCRAPER_FULL Module

**Duration**: 4 weeks (after Phase 2)
**Status**: 📋 PENDING

### 3a. Code Structure & Optimization
- [ ] Audit current code structure
- [ ] Optimize concurrent download logic
- [ ] Improve timeout/retry handling

### 3b. Testing & Stability
- [ ] Add comprehensive error handling
- [ ] Test on various websites
- [ ] Expand test coverage

### 3c. Performance & Features
- [ ] Optimize concurrent connections
- [ ] Improve content filtering
- [ ] Add progress reporting

### 3d. Maintainability
- [ ] Create SCRAPER_MODULE.md
- [ ] Add type hints
- [ ] Refactor if needed

---

## Phase 4: Consolidation & Integration

**Duration**: 2-3 weeks (after all modules)
**Status**: 📋 PENDING

### 4a. End-to-End Testing
- [ ] Test full workflow: Scrape → Classify → Cross-ref
- [ ] Test error handling across all modules
- [ ] Test performance at scale

### 4b. Documentation
- [ ] Update main README.md
- [ ] Create integration guide
- [ ] Create deployment guide

### 4c. Performance Profiling
- [ ] Full system performance test
- [ ] Identify bottlenecks
- [ ] Optimize critical paths

### 4d. Release Preparation
- [ ] Version bump (1.0.0 → 1.1.0)
- [ ] Create release notes
- [ ] Final testing

---

## Timeline Summary

```
May 2026:       Phase 1 (CLASSIFY) - Weeks 1-6
June 2026:      Phase 2 (CROSS-REFERENCE) - Weeks 7-10
July 2026:      Phase 3 (SCRAPER) - Weeks 11-14
August 2026:    Phase 4 (Consolidation) - Weeks 15-17
September 2026: Release v1.1.0
```

---

## Current Blockers

None (ready to start Phase 1a)

---

## Resources Needed

- Testing framework: pytest (✅ available)
- Profiling tools: cProfile, memory_profiler
- Type checking: mypy, pyright
- Documentation: Sphinx (optional)

---

## Success Metrics (End of All Phases)

| Metric | Target |
|--------|--------|
| Test Coverage | 70%+ |
| Type Hints | 100% |
| Code Duplication | <5% |
| Performance (Classify) | 75+ items/min |
| Performance (Cross-ref) | 40+ PDFs/min |
| Performance (Scraper) | 15+ PDFs/min |
| Documentation | 100% modules covered |
| Code Review | 100% modules reviewed |

---

## Last Updated
May 14, 2026
