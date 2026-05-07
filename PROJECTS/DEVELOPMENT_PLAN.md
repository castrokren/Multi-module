# Local Crawler Project - Development Plan

**Goal**: Systematically improve the local project across 4 dimensions:
1. ✅ Fix bugs & improve stability
2. ✅ Add new capabilities  
3. ✅ Improve performance
4. ✅ Make it more maintainable

**Timeline**: Work through each module (Classify → Cross-reference → Scraper_full → Consolidation)

---

## Phase 1: Classification Module (Current)
**Current State**: 16 files, 1.2M, many duplicates

### Issues Identified
- **Redundancy**: Multiple monitor variations (simple_monitor.py, standalone_monitor.py, service_script.py, simple_W_service.py)
- **Duplicated Logic**: Both `adaptive_excel_processor.py` and `excel_processor.py` exist
- **Deprecated Code**: `older/` directory with legacy versions still present
- **Testing**: Only 2 test files present (test_adaptive_processor.py, test_xls_support.py)
- **UI Fragmentation**: Updated_Monitor_UI.py is only modern UI; older versions in /older

### Action Plan

#### 1a. Code Audit & Deduplication (Stability)
- [ ] Compare excel_processor.py vs adaptive_excel_processor.py
  - Merge or deprecate one
  - Keep adaptive version as primary (has learning capabilities)
- [ ] Consolidate monitor variations:
  - `simple_monitor.py` → Core functionality
  - `simple_W_service.py` → Windows service wrapper
  - `service_script.py` → Legacy, evaluate for removal
  - `standalone_monitor.py` → Legacy, evaluate for removal
- [ ] Archive /older directory (don't delete, but move to archive)

#### 1b. Testing & Stability Improvements
- [ ] Expand test coverage for adaptive_excel_processor.py
- [ ] Add error handling tests
- [ ] Add integration tests for monitor with UI
- [ ] Test all file extension handling (.xls, .xlsx)
- [ ] Add timeout/recovery tests (process_timeout=30)

#### 1c. Performance Optimization
- [ ] Profile adaptive_excel_processor performance
- [ ] Optimize keyword matching algorithm
- [ ] Add caching for repeated classifications
- [ ] Optimize learning_log.json writes
- [ ] Batch Excel file processing

#### 1d. Maintainability Improvements
- [ ] Create CLASSIFY_MODULE.md documentation
- [ ] Add type hints throughout
- [ ] Refactor into sub-modules:
  - processors.py (core Excel logic)
  - monitor.py (file watching)
  - service.py (Windows service integration)
  - ui.py (UI components)
- [ ] Standardize logging across all files
- [ ] Create requirements_classify.txt for dependencies

---

## Phase 2: Cross-reference Module
**Current State**: 15 files, 700K

### Estimated Issues
- Recovery and validation logic may have redundancy
- Performance on large PDF collections unknown
- Testing coverage likely limited

### Action Plan
- [ ] Audit crossref_recovery.py vs crossref_standalone.py
- [ ] Consolidate progress checking (check_progress.py, check_results.py)
- [ ] Add comprehensive error handling
- [ ] Performance test on 1000+ PDF collections
- [ ] Expand test coverage
- [ ] Create CROSSREFERENCE_MODULE.md

---

## Phase 3: Scraper_full Module
**Current State**: 24 files, 159MB (data-heavy)

### Estimated Issues
- Large size likely due to cached data, not code
- Need to separate code from data
- Web scraping patterns may have performance issues

### Action Plan
- [ ] Separate code from data directories
- [ ] Create .gitignore to exclude data
- [ ] Audit scraping performance
- [ ] Implement rate limiting and retry logic
- [ ] Add comprehensive error recovery
- [ ] Create SCRAPER_MODULE.md

---

## Phase 4: Cross-Module Integration & Cleanup
**Current State**: Multiple modules with unclear integration points

### Action Plan
- [ ] Map module dependencies
- [ ] Create unified entry point / orchestration layer
- [ ] Establish data flow between modules
- [ ] Create main_pipeline.py for end-to-end processing
- [ ] Add configuration for module interaction
- [ ] Create system architecture diagram

---

## Phase 5: Project-wide Improvements

### Version Control & Reproducibility
- [ ] Initialize git repository
- [ ] Create .gitignore
  - Exclude: venv/, *.log, data/, *.xlsx (unless templates)
  - Include: all .py, config templates, documentation
- [ ] Document Python version (3.8+?)
- [ ] Create requirements_all.txt with all dependencies
- [ ] Document setup instructions

### Documentation
- [ ] Create ROOT README.md explaining project structure
- [ ] Add module-specific documentation:
  - Classify/README.md
  - Cross-reference/README.md
  - Scraper_full/README.md
- [ ] Create ARCHITECTURE.md showing data flow
- [ ] Add INSTALLATION.md with setup steps
- [ ] Create CONTRIBUTING.md for development guidelines

### Code Quality
- [ ] Add type hints across all modules
- [ ] Increase test coverage to 70%+
- [ ] Add pre-commit hooks (black, flake8, mypy)
- [ ] Document all configuration options
- [ ] Create logging standards

### Performance Baseline
- [ ] Profile each module individually
- [ ] Document current performance metrics
- [ ] Identify bottlenecks
- [ ] Set performance targets

---

## Deliverables Checklist

### By Phase 1 Complete
- [ ] Consolidated Classification module (unique file purposes)
- [ ] Test coverage ≥60% for Classify
- [ ] CLASSIFY_MODULE.md documentation
- [ ] Identified and archived redundant code

### By Phase 2 Complete
- [ ] Consolidated Cross-reference module
- [ ] Test coverage ≥60% for Cross-reference
- [ ] CROSSREFERENCE_MODULE.md documentation

### By Phase 3 Complete
- [ ] Scraper_full code/data separation
- [ ] Performance baseline documented
- [ ] SCRAPER_MODULE.md documentation

### By Phase 5 Complete
- [ ] Git repository initialized
- [ ] Full documentation suite
- [ ] 70%+ test coverage across project
- [ ] Performance improvements documented with metrics
- [ ] Ready for public release or internal standardization

---

## Next Immediate Steps

1. **Read and compare** excel_processor.py vs adaptive_excel_processor.py
2. **List all monitor variations** and their specific purposes
3. **Create consolidation strategy** for monitor files
4. **Archive /older directory** contents
5. **Begin writing comprehensive tests** for Classification module

---

## Notes
- Original GitHub version (_repo_tmp/) has only 5 core files - we can use as inspiration for simplified versions
- Local project's comprehensive nature is valuable - consolidation should enhance, not remove capability
- Data in Scraper_full (159MB) should be externalized for better maintainability
- Current scale (1,757 files) suggests need for clear organization and documentation

