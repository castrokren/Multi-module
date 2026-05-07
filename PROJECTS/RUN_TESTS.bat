@echo off
REM Batch script to run pytest tests for Crawler Projects
REM Usage: RUN_TESTS.bat [options]

REM Check if pytest is installed
python -m pytest --version > nul 2>&1
if errorlevel 1 (
    echo Error: pytest not found. Installing dependencies...
    pip install -r requirements-test.txt
)

REM Default action: run all tests
if "%1"=="" (
    echo Running all unit tests...
    python -m pytest -v
    goto end
)

REM Handle different options
if "%1"=="all" (
    echo Running all tests with coverage...
    python -m pytest --cov=src/services --cov-report=html -v
    goto end
)

if "%1"=="scraper" (
    echo Running scraper-full tests...
    python -m pytest src/services/scraper-full/tests/unit/ -v
    goto end
)

if "%1"=="classify" (
    echo Running classify tests...
    python -m pytest src/services/classify/tests/unit/ -v
    goto end
)

if "%1"=="crossref" (
    echo Running cross-reference tests...
    python -m pytest src/services/cross-reference/tests/unit/ -v
    goto end
)

if "%1"=="coverage" (
    echo Running tests with coverage report...
    python -m pytest --cov=src/services --cov-report=term-missing --cov-report=html -v
    echo Coverage report generated in htmlcov/index.html
    goto end
)

if "%1"=="fast" (
    echo Running tests in parallel...
    python -m pytest -n auto -v
    goto end
)

if "%1"=="help" (
    echo.
    echo Usage: RUN_TESTS.bat [option]
    echo.
    echo Options:
    echo   (none)     Run all tests
    echo   all        Run all tests with coverage
    echo   scraper    Run scraper-full tests only
    echo   classify   Run classify tests only
    echo   crossref   Run cross-reference tests only
    echo   coverage   Run tests with detailed coverage report
    echo   fast       Run tests in parallel (requires pytest-xdist)
    echo   help       Show this message
    echo.
    goto end
)

REM If argument not recognized, treat as pytest argument
echo Running with custom arguments: %*
python -m pytest %*

:end
echo.
echo Done.
