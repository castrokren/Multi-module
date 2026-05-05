# Git Repository Setup Guide

Due to a filesystem issue with the mounted directory, the Git repository needs to be initialized directly on your machine. This guide provides step-by-step instructions.

## Quick Start

### On Windows

1. **Open Command Prompt or PowerShell**
   - Navigate to your project: `cd C:\Projects\Crawler`

2. **Run the initialization script**
   ```bash
   INIT_GIT_REPO.bat
   ```
   - This will initialize the repository, stage all files, and create the initial commit
   - The script will show you the results when complete

### On Mac/Linux

1. **Open Terminal**
   - Navigate to your project: `cd ~/Projects/Crawler` (or your path)

2. **Run the initialization script**
   ```bash
   bash INIT_GIT_REPO.sh
   ```
   - This will initialize the repository, stage all files, and create the initial commit
   - The script will show you the results when complete

## Manual Setup (if scripts don't work)

If the scripts don't work for some reason, you can initialize Git manually:

```bash
# Navigate to project directory
cd C:\Projects\Crawler

# Initialize git
git init --initial-branch=main

# Configure user
git config user.email "castrokren@gmail.com"
git config user.name "Kren Castro"

# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: Multi-module PDF Crawler System"

# Verify
git log
git status
```

## Repository Structure

After initialization, your repository will have:

```
Crawler/
├── .git/                      # Git internal directory
├── README.md                  # Project overview
├── .gitignore                 # Git ignore configuration
├── PROJECTS/
│   ├── Classify/             # Classification module
│   ├── Cross-reference/      # Cross-reference module
│   └── Scraper_full/         # Web scraping module
├── MODULE_OVERVIEW.md        # Module documentation
├── CLASSIFY_ANALYSIS.md      # Classification analysis
├── DEVELOPMENT_PLAN.md       # Development roadmap
└── PROJECT_COMPARISON.md     # Comparison with GitHub version
```

## Working with Git

### Basic Commands

**Check status**
```bash
git status
```

**Create a new branch**
```bash
git checkout -b feature/your-feature-name
```

**Make changes and commit**
```bash
git add .                           # Stage all changes
git commit -m "Description of changes"
```

**View commit history**
```bash
git log --oneline              # Short view
git log -10                    # Last 10 commits
git log --graph --all          # Visual branch history
```

**Switch branches**
```bash
git checkout main              # Switch to main
git checkout feature/your-feature
```

### Important Files

**README.md**
- Start here for project overview
- Contains quick start instructions
- Documents how to run each module

**MODULE_OVERVIEW.md**
- Detailed description of all three modules
- Shows how modules work together
- Lists current issues and TODOs

**.gitignore**
- Prevents syncing large files (venv/, logs, PDFs, etc.)
- You shouldn't need to edit this
- Data files won't be committed

## Common Tasks

### Initialize a new branch for improvements

```bash
# Create and switch to a new branch
git checkout -b improvement/consolidate-classify

# Make your changes
# ... edit files ...

# Commit your changes
git add .
git commit -m "Consolidate monitor implementations

- Merged simple_monitor.py and simple_W_service.py
- Removed redundant code
- Updated UI imports"

# View changes
git log --oneline
```

### Review what's changed

```bash
# See all modified files
git status

# See specific changes in a file
git diff PROJECTS/Classify/config.py

# Compare commits
git log --oneline main..improvement/your-branch
```

### Undo changes

```bash
# Undo uncommitted changes to a file
git checkout PROJECTS/Classify/config.py

# Undo all uncommitted changes
git reset --hard

# Revert a committed change
git revert <commit-hash>
```

## Setting up Remote (GitHub/GitLab)

If you want to push to GitHub:

```bash
# Create a new repository on GitHub (https://github.com/new)

# Add remote
git remote add origin https://github.com/castrokren/Crawler.git

# Push to GitHub
git push -u origin main

# After initial push, you can just use:
git push
```

## Troubleshooting

### "fatal: not a git repository"
- Make sure you're in the Crawler directory
- Run `git init` if .git directory is missing

### "error: bad signature"
- Remove corrupted .git: `rm -rf .git`
- Run the initialization script again

### Files not showing in commits
- Check .gitignore rules
- Verify files aren't in ignored directories
- Use `git add -f filename` to force add

### Permission denied on script
- Windows: Run Command Prompt as Administrator
- Mac/Linux: Use `chmod +x INIT_GIT_REPO.sh`

## Next Steps After Setup

1. **Update Configuration**
   - Edit `config.ini` with your paths
   - Update `monitor_config.json` if needed

2. **Create Feature Branches**
   - Use the development plan in `DEVELOPMENT_PLAN.md`
   - Create branches for improvements

3. **Make Improvements**
   - Consolidate module code
   - Add tests
   - Improve documentation

4. **Commit Regularly**
   - Make small, focused commits
   - Write clear commit messages

5. **Collaborate** (Optional)
   - Push to GitHub
   - Create pull requests for review
   - Track issues

## Reference

- [Git Documentation](https://git-scm.com/doc)
- [Git Cheat Sheet](https://github.github.com/training-kit/downloads/github-git-cheat-sheet.pdf)
- [GitHub Hello World](https://guides.github.com/activities/hello-world/)

## Questions?

Refer to:
- `README.md` - Project overview
- `MODULE_OVERVIEW.md` - Module details
- `DEVELOPMENT_PLAN.md` - Improvement roadmap
- `CLASSIFY_ANALYSIS.md` - Detailed analysis
