# PDF Crawler & Classification System

A comprehensive multi-module system for processing, classifying, and managing PDF documents with institutional metadata.

## Project Overview

This project consists of three integrated modules:

1. **CLASSIFY** - Document classification and categorization
   - Automatically classifies items into Hardware, Software, and Non-Instrument categories
   - Monitors folders for new files and processes them automatically
   - Self-learning system that improves classification accuracy over time

2. **CROSS-REFERENCE** - PDF linking and validation
   - Links PDFs to institutional records
   - Creates cross-reference mappings between documents
   - Handles recovery and validation of failed operations

3. **SCRAPER_FULL** - Web scraping and PDF downloading
   - Crawls websites for PDF resources
   - Downloads PDFs with intelligent retry logic and concurrent connections
   - Manages and organizes downloaded content

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Crawler
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the project:
   - Edit `config.ini` with your settings
   - Set appropriate paths for your environment
   - Configure keyword files for classification

### Running the System

#### Classification Module
```bash
python PROJECTS/Classify/Updated_Monitor_UI.py
```

#### Cross-Reference Module
```bash
python PROJECTS/Cross-reference/run_crossref_cli.py
```

#### Scraper Module
```bash
python PROJECTS/Scraper_full/pdf_crawler_gui.py
```

## Project Structure

```
Crawler/
├── PROJECTS/
│   ├── Classify/           # Classification module
│   ├── Cross-reference/    # Cross-referencing module
│   ├── Scraper_full/       # Web scraping module
│   ├── Documents/          # Reference documentation
│   └── Monitoring services/ # Service configurations
├── config.ini              # Main configuration file
├── monitor_config.json     # Monitoring configuration
├── MODULE_OVERVIEW.md      # Detailed module documentation
├── CLASSIFY_ANALYSIS.md    # Classification module analysis
├── DEVELOPMENT_PLAN.md     # Development roadmap
└── .gitignore              # Git ignore rules
```

## Documentation

- **MODULE_OVERVIEW.md** - Detailed overview of all three modules
- **CLASSIFY_ANALYSIS.md** - In-depth analysis of the Classification module
- **DEVELOPMENT_PLAN.md** - Roadmap for improvements and development phases
- **PROJECT_COMPARISON.md** - Comparison between local and GitHub versions

## Configuration

### Main Settings (config.ini)
```ini
[Classify]
watch_directory = path/to/watch
output_directory = path/to/output
hardware_keywords_file = keywords_hw.txt
software_keywords_file = keywords_sw.txt
```

### Keywords Files
Classification uses three keyword files:
- Hardware keywords (instruments, equipment)
- Software keywords (applications, licenses)
- Non-Instrument keywords (office supplies, furniture)

## Features

### Classification Module
- ✅ Real-time file monitoring
- ✅ 3-category classification system
- ✅ Self-learning keyword discovery
- ✅ Confidence scoring
- ✅ GUI interface for monitoring
- ✅ Vendor-based classification

### Cross-Reference Module
- ✅ Automated PDF-to-record linking
- ✅ Validation and error checking
- ✅ Recovery from failures
- ✅ Progress tracking
- ✅ CLI and programmatic interfaces

### Scraper Module
- ✅ Intelligent web crawling
- ✅ Concurrent downloads
- ✅ Retry logic for failures
- ✅ Smart timeout handling
- ✅ Content filtering
- ✅ Progress reporting

## Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
The project is organized into modules with clear separation of concerns:
- Core processing logic separated from UI
- Configuration management centralized
- Error handling and recovery built-in

### Contributing
1. Create a new branch for your feature
2. Make your changes
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## Known Issues & TODO

- [ ] Consolidate redundant monitor implementations
- [ ] Expand test coverage to 70%+
- [ ] Migrate hardcoded paths to environment variables
- [ ] Separate Scraper data from code
- [ ] Add comprehensive end-to-end tests
- [ ] Improve performance profiling

See **DEVELOPMENT_PLAN.md** for detailed improvement roadmap.

## Performance

Current baseline metrics:
- **Classification**: ~50 items/minute (single processor)
- **Cross-referencing**: ~30 PDFs/minute with validation
- **Scraping**: ~10 PDFs/minute with concurrent connections

## Support

For issues or questions:
1. Check the documentation files (CLASSIFY_ANALYSIS.md, DEVELOPMENT_PLAN.md)
2. Review the MODULE_OVERVIEW.md for component details
3. Check existing issues in the repository

## License

[Add your license here]

## Author

Kren Castro (castrokren@gmail.com)

## Version

Current version: 1.0.0

Last updated: May 5, 2026
