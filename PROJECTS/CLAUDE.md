# Crawler

Crawler Projects - Python-based document scraping, classification, and cross-reference workflow.

> Global rules for all projects: [../../CLAUDE.md](../../CLAUDE.md) (identity, shared conventions, environment). This file adds Crawler-specific rules on top.

## Tech Stack
- Frontend: Tkinter (desktop GUI components)
- Backend: Python
- Database: File-based (Excel/JSON outputs)
- Deploy: Windows scripts/services

## Workspaces
- /planning - Specs, architecture, decisions
- /src - Application code
- /docs - Documentation
- /ops - Deployment and operations

## Routing
| Task | Go to | Read | Skills |
|------|-------|------|--------|
| Spec a feature | /planning | CONTEXT.md | - |
| Write code | /src | CONTEXT.md | testing-skill |
| Write docs | /docs | CONTEXT.md | doc-authoring-skill |
| Deploy or debug | /ops | CONTEXT.md | - |

## Crawl Engine (single source of truth)

All crawling goes through `src/services/scraper-full/scraper_engine.py` —
the pipeline, the GUI, and `pdf_discovery_pipeline.py` all use it. Do NOT
add a second download path; the engine owns the accuracy guardrails:
only CSV-listed vendors crawled, fail-closed supplier keyword filter,
allowlist/blocklist, `%PDF` magic-byte check, first-page content check,
content-hash dedup.

Automatic runs: `src/services/watch_input.py` watches the input dir and
runs `pipeline.py` on new files. Ops/setup guide: `docs/RUNBOOK.md`.
Old binaries `Crawlers.exe` / `WebScrapper.exe` predate the guardrails —
the current build is `scraper-full/dist/PDF_Crawler_GUI.exe`.

## Data Directories (CRITICAL - Do not change)
**All data lives in `C:\Data\Crawler\` - NOT in the project repo**

- `C:\Data\Crawler\input\` - Raw CSV input files (supplier requisitions)
- `C:\Data\Crawler\labeled\` - Classified Excel files (with TYPE column)
- `C:\Data\Crawler\output\` - Scraped PDFs organized by supplier folder
- Pipeline config points to these external directories in `pipeline_config.json`

## Naming conventions
- Service folders: kebab-case (`cross-reference`, `scraper-full`)
- Python files: snake_case.py
- Python classes: PascalCase
- Functions and variables: snake_case
- Tests: test_<feature>.py
- Specs: <feature>_spec.md
- Decision records: YYYY-MM-DD-<decision-title>.md