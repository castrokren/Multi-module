@echo off
REM GUI Test Runner Script for Crawler Projects
REM Provides convenient commands for running tests

setlocal enabledelayedexpansion

if "%1"=="" goto help

if /i "%1"=="all" goto all_tests
if /i "%1"=="main" goto main_tests
if /i "%1"=="file" goto file_tests
if /i "%1"=="scan" goto scan_tests
if /i "%1"=="crossref" goto crossref_tests
if /i "%1"=="coverage" goto coverage
if /i "%1"=="help" goto help
if /i "%1"=="verbose" goto verbose

echo Unknown command: %1
goto help

:all_tests
echo Running all GUI tests...
pytest tests/gui/ -v
goto end

:main_tests
echo Running main window tests...
pytest tests/gui/test_main_window.py -v
goto end

:file_tests
echo Running file selection tests...
pytest tests/gui/test_file_selection_workflow.py -v
goto end

:scan_tests
echo Running scanning and display tests...
pytest tests/gui/test_scanning_and_display.py -v
goto end

:crossref_tests
echo Running cross-reference tests...
pytest tests/gui/test_crossref_operations.py -v
goto end

:coverage
echo Running tests with coverage report...
pytest tests/gui/ --cov=src/services/scraper-full/pdf_crawler_gui_2 --cov-report=html --cov-report=term
echo Coverage report generated in htmlcov/index.html
goto end

:verbose
echo Running all tests with verbose output...
pytest tests/gui/ -vv -s
goto end

:help
echo.
echo GUI Test Runner for Crawler Projects
echo ====================================
echo.
echo Usage: run_tests.bat [COMMAND]
echo.
echo Commands:
echo   all       - Run all GUI tests
echo   main      - Run main window tests only
echo   file      - Run file selection workflow tests
echo   scan      - Run scanning and display tests
echo   crossref  - Run cross-reference operation tests
echo   coverage  - Run tests with coverage report
echo   verbose   - Run tests with detailed output
echo   help      - Show this help message
echo.
echo Examples:
echo   run_tests.bat all
echo   run_tests.bat main
echo   run_tests.bat coverage
echo.

:end
endlocal
