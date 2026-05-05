#!/bin/bash
# Git Repository Initialization Script
# This script sets up the git repository for the Crawler project
#
# INSTRUCTIONS:
# 1. On Windows: Use Git Bash or WSL to run this script
# 2. On Mac/Linux: Run directly in terminal
# 3. Run from the project root (C:\Projects\Crawler or equivalent)

# Clean up any corrupted git state
if [ -d .git ]; then
    echo "⚠️  Existing .git directory found. Backing up to .git.bak"
    mv .git .git.bak
fi

echo "📦 Initializing Git repository..."

# Initialize with main branch
git init --initial-branch=main

# Configure git user
git config user.email "castrokren@gmail.com"
git config user.name "Kren Castro"

echo "📋 Staging files..."

# Stage all files
git add .

echo "✅ Creating initial commit..."

# Create initial commit with detailed message
git commit -m "Initial commit: Multi-module PDF Crawler System

Project Overview:
This is a production-ready system for processing and managing PDF documents
with classification and cross-referencing capabilities.

Modules:
1. CLASSIFY
   - Monitors folders for new documents
   - Automatically classifies items (Hardware/Software/Non-Instrument)
   - Self-learning system with confidence scoring
   - Includes GUI for monitoring and manual adjustments

2. CROSS-REFERENCE
   - Links PDFs to institutional records
   - Creates cross-reference mappings
   - Validates relationships with error recovery
   - Tracks progress and generates reports

3. SCRAPER_FULL
   - Web scraping for PDF resources
   - Concurrent downloads with intelligent retry logic
   - Manages and organizes downloaded content
   - Progress tracking and statistics

Documentation:
- README.md: Quick start and project overview
- MODULE_OVERVIEW.md: Detailed module documentation
- CLASSIFY_ANALYSIS.md: In-depth classification analysis
- DEVELOPMENT_PLAN.md: Improvement roadmap
- PROJECT_COMPARISON.md: Comparison with GitHub version

Configuration:
- .gitignore: Excludes venv, logs, data files
- config.ini: Main project configuration
- monitor_config.json: Monitoring settings"

# Show results
echo ""
echo "✨ Repository initialized successfully!"
echo ""
echo "=== Commit Information ==="
git log --oneline
echo ""
echo "=== Current Status ==="
git status

echo ""
echo "📝 Next steps:"
echo "1. Update config.ini with your specific paths"
echo "2. Review README.md for usage instructions"
echo "3. Create additional branches as needed:"
echo "   - git checkout -b feature/your-feature"
echo "   - git checkout -b bugfix/your-bugfix"
echo "4. Make your first changes and commit:"
echo "   - git add <files>"
echo "   - git commit -m 'Your message'"
echo "5. (Optional) Add remote repository:"
echo "   - git remote add origin <github-url>"
echo "   - git push -u origin main"
