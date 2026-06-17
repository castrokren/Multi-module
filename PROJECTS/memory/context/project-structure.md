# Project Structure & Environment

---

## Directory Layout

```
C:\Projects\Crawler\PROJECTS/
├── CLAUDE.md                          ← Hot cache (this project's memory)
├── memory/                            ← Deep memory storage
│   ├── glossary.md                    (full decoder ring)
│   ├── modules/                       (detailed module docs)
│   │   ├── classify.md
│   │   ├── cross-reference.md
│   │   └── scraper.md
│   └── context/                       (project context)
│       ├── development-phases.md
│       └── project-structure.md       (this file)
│
├── PROJECTS/                          ← Main application code
│   ├── Classify/                      (Module 1 - PRIMARY PHASE 1)
│   │   ├── adaptive_excel_processor.py    (698 lines, core)
│   │   ├── Updated_Monitor_UI.py         (41KB, GUI)
│   │   ├── simple_monitor.py             (123 lines, watcher)
│   │   ├── config.py                     (configuration)
│   │   ├── process_all_files.py          (batch processing)
│   │   ├── integrate_adaptive_processor.py
│   │   │
│   │   ├── excel_processor.py            (DEPRECATED - legacy)
│   │   ├── standalone_monitor.py         (LEGACY - consolidate)
│   │   ├── service_script.py             (LEGACY - evaluate)
│   │   ├── simple_W_service.py           (LEGACY - evaluate)
│   │   │
│   │   ├── older/                        (archive directory)
│   │   │   └── [legacy versions...]
│   │   │
│   │   ├── tests/
│   │   │   ├── test_adaptive_processor.py
│   │   │   └── test_xls_support.py
│   │   │
│   │   ├── keywords_hw.txt               (Hardware keywords)
│   │   ├── keywords_sw.txt               (Software keywords)
│   │   ├── keywords_ni.txt               (Non-Instrument keywords)
│   │   ├── learning_log.json             (adaptive learning log)
│   │   └── config.ini                    (local config)
│   │
│   ├── Cross-reference/                 (Module 2 - Phase 2)
│   │   ├── crossref_standalone.py        (primary engine)
│   │   ├── crossref_recovery.py          (resumable operations)
│   │   ├── instrument_labeling_manager.py
│   │   ├── run_crossref_cli.py           (CLI interface)
│   │   ├── check_progress.py
│   │   ├── check_results.py
│   │   ├── INSTRUMENT_LABELING_GUIDE.md
│   │   ├── PSUTIL_README.md
│   │   └── tests/ [limited coverage]
│   │
│   ├── Scraper_full/                    (Module 3 - Phase 3)
│   │   ├── pdf_crawler_gui.py            (GUI interface)
│   │   ├── [crawler logic]
│   │   └── [download logic]
│   │
│   ├── Documents/                       (Reference docs)
│   │   └── [project documentation]
│   │
│   └── Monitoring services/             (Service configs)
│       └── [Windows service setup]
│
├── config.ini                           (root configuration)
├── monitor_config.json                  (monitoring config)
├── .gitignore                           (git exclusions)
├── requirements.txt                     (Python dependencies)
│
├── README.md                            (project overview)
├── MODULE_OVERVIEW.md                   (detailed module docs)
├── CLASSIFY_ANALYSIS.md                 (classification analysis)
├── DEVELOPMENT_PLAN.md                  (development roadmap)
├── PROJECT_COMPARISON.md                (local vs GitHub versions)
│
├── .claude/                             (Claude Code workspaces)
│   └── worktrees/
│       ├── nostalgic-dirac-e12c1c/
│       ├── cool-wescoff-18ae7a/
│       ├── loving-saha-40303c/
│       ├── sleepy-mcnulty-d01652/
│       ├── distracted-goldberg-f3daa5/
│       └── elated-diffie-32ebee/        (multiple development branches)
│
└── .pytest_cache/                       (pytest cache)
```

---

## Configuration Files

### Root config.ini
```ini
[Classify]
watch_directory = C:/Data/Incoming
output_directory = C:/Data/Classified
hardware_keywords_file = keywords_hw.txt
software_keywords_file = keywords_sw.txt
non_instrument_keywords_file = keywords_ni.txt
confidence_threshold = 0.7
learning_enabled = true
process_timeout = 30

[CrossReference]
input_directory = C:/Data/PDFs
output_directory = C:/Data/CrossRef_Results
validation_enabled = true

[Scraper]
output_directory = C:/Data/Downloaded_PDFs
concurrent_downloads = 4
retry_attempts = 3
timeout_seconds = 30
```

### CLASSIFY-Specific Config
Located in: `PROJECTS/Classify/config.ini`
(May have local overrides)

### monitor_config.json
Monitoring configuration for watch directories and behavior.

---

## Dependencies

### Core Python Packages
- openpyxl / xlrd (Excel processing)
- watchdog (file monitoring)
- pytest (testing)
- [others - check requirements.txt]

### System Requirements
- Python 3.8+
- Windows (for service integration)
- ~100MB RAM for typical operations

---

## Git & Version Control

### Branches (inferred from worktree names)
Multiple development branches exist:
- `nostalgic-dirac-e12c1c`
- `cool-wescoff-18ae7a`
- `loving-saha-40303c`
- `sleepy-mcnulty-d01652`
- `distracted-goldberg-f3daa5`
- `elated-diffie-32ebee`

(Suggests active, parallel development)

---

## Development Environment

### IDE/Editor
- VS Code (likely, given .claude/ structure)
- Python 3.8+

### Testing
- Framework: pytest
- Coverage: Low (2 test files in Classify/)
- Location: `PROJECTS/Classify/tests/`

### Profiling
- Tools: cProfile (standard Python)
- Needed: memory_profiler for deep analysis

---

## Key Directories by Purpose

| Directory | Purpose |
|-----------|---------|
| `/PROJECTS/` | Application source code |
| `/PROJECTS/Classify/` | Module 1 (primary focus) |
| `/PROJECTS/Cross-reference/` | Module 2 |
| `/PROJECTS/Scraper_full/` | Module 3 |
| `/PROJECTS/Documents/` | Reference docs |
| `/memory/` | Project memory (this system) |
| `/.claude/` | Claude Code development workspaces |
| Root files | Config, README, documentation |

---

## File Size Overview

| Component | Size | Status |
|-----------|------|--------|
| Classify module | 1.2MB | 🔴 Needs consolidation |
| Cross-reference module | 700KB | 📋 Phase 2 |
| Scraper module | Unknown | 📋 Phase 3 |
| Documentation | ~200KB | ✅ Good |
| **Total** | ~2.1MB | ✅ Manageable |

---

## Access & Permissions

- **Repository**: Local filesystem (C:\Projects\Crawler\PROJECTS)
- **Git**: Configured (check .gitignore)
- **Owner**: Kren Castro

---

## Environment Variables (TODO)

Currently hardcoded in config files. Should migrate to env vars for portability:

```bash
CRAWLER_WATCH_DIR=path/to/watch
CRAWLER_OUTPUT_DIR=path/to/output
CRAWLER_HW_KEYWORDS=path/to/keywords_hw.txt
CRAWLER_SW_KEYWORDS=path/to/keywords_sw.txt
CRAWLER_CONFIDENCE_THRESHOLD=0.7
```

---

## Last Updated
May 14, 2026
