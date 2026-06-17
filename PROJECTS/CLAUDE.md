# My App

Crawler Projects - Python-based document scraping, classification, and cross-reference workflow.

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