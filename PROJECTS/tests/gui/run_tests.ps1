# GUI Test Runner Script for Crawler Projects
# PowerShell version for Windows environments

param(
    [string]$Command = "help"
)

function Show-Help {
    Write-Host @"
GUI Test Runner for Crawler Projects
====================================

Usage: .\run_tests.ps1 -Command <command>

Commands:
  all       - Run all GUI tests
  main      - Run main window tests only
  file      - Run file selection workflow tests
  scan      - Run scanning and display tests
  crossref  - Run cross-reference operation tests
  coverage  - Run tests with coverage report
  verbose   - Run tests with detailed output
  help      - Show this help message

Examples:
  .\run_tests.ps1 -Command all
  .\run_tests.ps1 -Command main
  .\run_tests.ps1 -Command coverage
"@
}

function Run-AllTests {
    Write-Host "Running all GUI tests..." -ForegroundColor Green
    & pytest tests/gui/ -v
}

function Run-MainTests {
    Write-Host "Running main window tests..." -ForegroundColor Green
    & pytest tests/gui/test_main_window.py -v
}

function Run-FileTests {
    Write-Host "Running file selection tests..." -ForegroundColor Green
    & pytest tests/gui/test_file_selection_workflow.py -v
}

function Run-ScanTests {
    Write-Host "Running scanning and display tests..." -ForegroundColor Green
    & pytest tests/gui/test_scanning_and_display.py -v
}

function Run-CrossrefTests {
    Write-Host "Running cross-reference tests..." -ForegroundColor Green
    & pytest tests/gui/test_crossref_operations.py -v
}

function Run-Coverage {
    Write-Host "Running tests with coverage report..." -ForegroundColor Green
    & pytest tests/gui/ `
        --cov=src/services/scraper-full/pdf_crawler_gui_2 `
        --cov-report=html `
        --cov-report=term
    Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor Yellow
}

function Run-Verbose {
    Write-Host "Running all tests with verbose output..." -ForegroundColor Green
    & pytest tests/gui/ -vv -s
}

# Route to appropriate function
switch -CaseSensitive ($Command.ToLower()) {
    "all"       { Run-AllTests }
    "main"      { Run-MainTests }
    "file"      { Run-FileTests }
    "scan"      { Run-ScanTests }
    "crossref"  { Run-CrossrefTests }
    "coverage"  { Run-Coverage }
    "verbose"   { Run-Verbose }
    "help"      { Show-Help }
    default     {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
    }
}
