# AGENTS.md — Crawler Pipeline

Python document scraping, classification, and cross-reference pipeline. Production-deployed on Windows.

## Working directory

The actual codebase is under `PROJECTS/`. The repo root (`C:\Projects\Crawler\`) mainly holds sibling folders (`ops/`, `src/`, `backups/`, `logs/`) and convenience scripts (`setup.bat`, `start.bat`, `stop.bat`, `run_full_scraper.py`).

**Always `cd PROJECTS/` first** unless you know exactly why you are in the root.

## Entry points

| What | Command (from PROJECTS/) |
|------|--------------------------|
| Full pipeline (all 5 stages) | `cd src/services && python pipeline.py` |
| Scraper only | `python src/services/pipeline.py --only-scraper` |
| Classify only | `python src/services/pipeline.py --only-classify` |
| Cross-ref only | `python src/services/pipeline.py --only-crossref` |
| Dry-run validation | `python src/services/pipeline.py --dry-run` |
| Classify GUI | `python Classify/Updated_Monitor_UI.py` |
| Scraper GUI | `python Scraper_full/pdf_crawler_gui.py` |
| CrossRef CLI | `python Cross-reference/run_crossref_cli.py` |

## Pipeline stages (5 stages, config-driven)

0. `src/services/data-cleaning/` — Normalize supplier names, fix corrupted fields
1. `src/services/scraper-full/` — Crawl supplier websites, download PDFs (ScraperEngine in `scraper_engine.py`)
2. `src/services/classify/` — Classify items as Hardware/Software/Non-Instrument (AdaptiveExcelProcessor in `adaptive_excel_processor.py`)
2b. `src/services/supplier-resolution/` — (Optional) Web search unknown suppliers
3. `src/services/cross-reference/` — Link classified items to PDFs using fuzzy matching (CrossReferenceEngine in `crossref_standalone_fast.py`)

Config: `src/services/pipeline_config.json`
Master config (keywords etc): `config.ini`

## Code layout: TWO parallel directory trees

The project has **two concurrently active layouts**. Both hold working code. Do not assume one is stale.

**Legacy layout** (per-module):
- `Classify/` — classification code
- `Cross-reference/` — cross-reference code
- `Scraper_full/` — scraper code

**New layout** (services under src):
- `src/services/classify/` — classification code
- `src/services/cross-reference/` — cross-reference code
- `src/services/scraper-full/` — scraper code (note: hyphen, not underscore)

The pipeline (`pipeline.py`) uses the **new layout** paths. Individual GUI/CLI scripts use the **legacy layout** paths. Both are valid entry points.

## External data (NOT in repo)

All data lives at `C:\Data\Crawler\`:
- `input/` — Raw supplier requisition Excel files
- `labeled/` — Classified Excel files (with TYPE column)
- `output/` — Downloaded PDFs organized by supplier folder

Pipeline config (`pipeline_config.json`) points to these paths. Do not move data into the repo.

## Testing

Three test locations with different import setups:

| Location | Run command (from PROJECTS/) | Import setup |
|----------|------------------------------|--------------|
| Root tests | `python -m pytest tests/ -v` | `pytest.ini` sets `pythonpath = src` |
| Per-service unit tests | `python -m pytest src/services/*/tests/unit/ -v` | Each `conftest.py` does `sys.path.insert(0, ...)` |
| GUI tests | `python -m pytest tests/gui/ -v` | Mocks Tkinter, no window created |

**Batch convenience**: `RUN_TESTS.bat all|scraper|classify|crossref|coverage|fast`

Test markers (in `pytest.ini`): `unit`, `integration`, `slow`.

### Test import quirk
The root `pytest.ini` sets `pythonpath = src`, which resolves imports like `from services.pipeline import ...`. But per-service `conftest.py` files do their own `sys.path.insert(0, ...)` for direct imports (e.g. `from scraper_engine import ScraperEngine`). If adding tests to a service directory, match that pattern.

## Key quirks an agent WILL need

### CrossRef import fix
`crossref_standalone_fast.py` inserts its own directory into `sys.path` at import time (lines 10-15). This is needed because `pipeline.py` loads it via `importlib.util.spec_from_file_location`, which doesn't set up the module's path for local imports (e.g. `from crossref_utils import ...`). **If you refactor imports in cross-reference, preserve this pattern or switch to a proper package structure.**

### 7-day smart detection (scraper)
State file: `.scraper_state.json` in the output directory. Config keys in `pipeline_config.json`: `scraper.skip_recent_sites` (bool) and `scraper.days_before_rescrape` (int, default 7). First pipeline run takes ~2h; subsequent runs within 7 days take ~10min.

### Pipeline uses dynamic imports
`pipeline.py` loads stage modules via `_import_from_file()` (wraps `importlib.util.spec_from_file_location`). Stages are NOT imported as Python packages. This means:
- Each stage file must be runnable standalone or importable via sys.path tricks
- Refactoring stage locations may break the dynamic load path

### Two config files
- `config.ini` — classification keywords, scraper defaults (legacy config)
- `src/services/pipeline_config.json` — pipeline orchestration (stages, paths), also duplicates some scraper/classify/crossref settings

When changing settings, prefer `pipeline_config.json`. `config.ini` is read by individual module scripts (legacy entry points).

### Windows-only deployment
- Batch files (`.bat`) for starting/stopping services: `start.bat`, `stop.bat`
- PowerShell scripts (`.ps1`) for setup: `setup_deployment.ps1`, `setup_task_scheduler.ps1`
- Task Scheduler runs auto-updater daily at 6:00 AM
- Git may ask for credentials differently on Windows (PAT or SSH)
- Path handling: use `pathlib` not string concatenation; backslashes are normal

### Dynamic import pattern for cmd-line scripts
Several scripts in `claude-commands/` (like `james.md`, `aisha.md`, `marcus.md`) define agent roles used via OpenCode's Task tool. These are not code files — they are agent role prompts. Do not treat them as Python modules.

## Existing instruction files (read these)

| File | What it contains | When to consult |
|------|------------------|-----------------|
| `CLAUDE.md` | Routing table (where to go for what) | Starting any work |
| `CONTEXT.md` | Full project state, workspace details, priorities | Understanding current status |
| `REFERENCES.md` | Terminology, naming conventions, quick command lookup | Writing docs, naming things |
| `CODEBASE.md` | Architecture docs, class/function reference | Deep code changes |
| `DEPLOYMENT.md` | Auto-updater, Task Scheduler setup, monitoring | Deployment/ops work |
| `ops/README.md` | Operation guide, dashboard, monitoring | Running services |

## Git notes

- The repo root is `C:\Projects\Crawler\` (has `.git/`)
- `PROJECTS/` is tracked under this root repo
- `PROJECTS/Multi-module/` has a **nested** `.git/` directory (a separate embedded repo)
- Data files (`*.xlsx`, `*.csv`, `*.pdf`) are gitignored via root `.gitignore`
