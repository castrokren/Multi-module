#current project

##what are you building
We are working on 3 main modules that need to be improved and fully develop into one application. These are written in python.

each modules works well on its own and when used manually. The final goal will be to combine and automate as one workflow. 

## Your Three Main Modules

**1. CLASSIFY (Document Classification)**
- Monitors folders for new files and automatically classifies items (Hardware, Software, Non-Instrument)
- Uses keyword matching with self-learning capabilities to improve accuracy over time
- Provides a UI for real-time monitoring and manual adjustments
- **16 Python files** handling Excel processing, file watching, and classification logic

**2. CROSS-REFERENCE (PDF Linking)**
- Links PDFs to institutional records and creates cross-reference mappings
- Validates relationships and handles failures gracefully with recovery logic
- Tracks progress and generates reports of linked documents
- **15 Python files** for processing, validation, and CLI operations

**3. SCRAPER_FULL (Web Scraping)**
- Crawls websites to find and download PDF documents
- Uses concurrent connections for speed and intelligent retry logic for failures
- Organizes downloaded content and tracks statistics
- **24 Python files** (with 159 MB of cached data included)

## How They Work Together
The typical workflow is: **Scraper downloads PDFs** → **Classify categorizes metadata** → **Cross-reference links everything together** → **Result: organized, classified, cross-referenced documents**

##what good looks like
each modules works well on its own and when used manually. The final goal will be to combine and automate as one workflow. 

##what to avoid
If you edit code vefiry it works before moving on to something else. 

