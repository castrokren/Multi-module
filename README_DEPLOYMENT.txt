================================================================================
CRAWLER PIPELINE - AUTOMATED DEPLOYMENT SYSTEM
================================================================================

QUICK START: Read this file first, then follow the 3 steps below.

================================================================================
WHAT IS THIS?
================================================================================

This is an automated deployment system for the Crawler PDF processing pipeline.
It enables:
  - Zero-downtime updates via GitHub
  - Automatic daily checks for new code
  - Instant rollback if something breaks
  - Minimal manual intervention

Two critical fixes are included:
  1. CrossRef module import fix (Stage 3 now works)
  2. 7-day smart detection (10 minutes instead of 2 hours on subsequent runs)

================================================================================
WHERE TO FIND THINGS
================================================================================

DOCUMENTATION:
  Location: C:\Projects\Crawler\PROJECTS\

  Quick reference (start here):
    DEPLOYMENT_QUICK_START.txt (2 pages, covers most common tasks)

  Full guide:
    DEPLOYMENT.md (comprehensive, 400+ lines)

  Technical report:
    DEPLOYMENT_REPORT.md (detailed architecture)

PROJECT CONTEXT:
  C:\Projects\Crawler\PROJECTS\CLAUDE.md (updated with deployment info)

DEPLOYMENT OVERVIEW:
  C:\Projects\Crawler\DEPLOYMENT_SYSTEM_SUMMARY.txt (complete overview)
  C:\Projects\Crawler\DELIVERABLES.txt (all deliverables checklist)

SCRIPTS:
  Location: C:\Projects\Crawler\PROJECTS\

  Auto-updater:
    update.bat (daily check & deploy)

  Setup automation:
    setup_deployment.ps1 (Task Scheduler setup)

  Remote deployment:
    deploy_to_remote.bat (deploy to other machines)

================================================================================
3 STEPS TO GET STARTED (Total: ~20 minutes)
================================================================================

STEP 1: PUSH TO GITHUB (5 minutes)
===================================
Run this in Command Prompt or PowerShell:

  cd C:\Projects\Crawler
  git push origin main

What it does:
  - Sends the commit to GitHub
  - Makes code available to remote machines
  - Required before automation can work

If it fails with "authentication failed":
  - Use GitHub Personal Access Token (https://github.com/settings/tokens)
  - Or set up SSH keys (https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

STEP 2: SET UP AUTOMATION (2 minutes)
====================================
Run this PowerShell command AS ADMINISTRATOR:

  C:\Projects\Crawler\PROJECTS\setup_deployment.ps1

What it does:
  - Creates directories for logs and backups
  - Registers daily 6:00 AM update job
  - Verifies everything works

STEP 3: TEST (10 minutes)
=========================
Verify it works by running manually:

  C:\Projects\Crawler\PROJECTS\update.bat

Check the result:
  Get-Content C:\Projects\Crawler\logs\deployment.log -Tail 30

Expected output:
  [timestamp] [SUCCESS] Update completed successfully
  (or "Already on latest commit - no update needed" if no changes)

Verify Task Scheduler:
  Get-ScheduledTask -TaskName "Crawler-Pipeline-Update" | Select State, NextRunTime

  Should show:
    State: Ready
    NextRunTime: Tomorrow at 6:00 AM

================================================================================
HOW IT WORKS (AFTER SETUP)
================================================================================

AUTOMATIC SCHEDULE:
  Time: Every day at 6:00 AM
  Action: Runs update.bat automatically

WHAT HAPPENS:
  1. Checks GitHub for new commits
  2. If no changes: exits quietly
  3. If changes found:
     a. Backs up your current code (backup_<timestamp>.zip)
     b. Downloads new code from GitHub
     c. Validates that critical files exist
     d. Logs everything to logs/deployment.log

RESULT:
  - Your code is always up-to-date
  - Old code is backed up (can restore if needed)
  - All changes are logged

MONITORING:
  - Check logs: C:\Projects\Crawler\logs\deployment.log
  - View backups: C:\Projects\Crawler\backups\
  - Watch Task Scheduler: taskschd.msc

================================================================================
FEATURES INCLUDED
================================================================================

FEATURE 1: CROSSREF MODULE IMPORT FIX
Status: Verified working on remote machine (May 14, 2026)
What it does: Fixes pipeline Stage 3 errors
Impact: Pipeline can now complete without import failures

FEATURE 2: 7-DAY SMART DETECTION
Status: 16 unit tests passing
What it does: Skips re-scraping suppliers from the last 7 days
Impact: Pipeline runs in 2 hours first time, then 10 minutes on subsequent runs

Configuration (in PROJECTS/src/services/pipeline_config.json):
  "skip_recent_sites": true    # Enable/disable this feature
  "days_before_rescrape": 7    # Days between re-scrape (adjustable)

How to disable temporarily:
  Edit pipeline_config.json, change "skip_recent_sites" to false

================================================================================
RUNTIME IMPACT
================================================================================

BEFORE DEPLOYMENT:
  Pipeline run: ~2 hours every time

AFTER DEPLOYMENT (WITH SMART DETECTION):
  First run: ~2 hours (full scrape required)
  Subsequent runs (< 7 days): ~10 minutes (skip scraper)
  Subsequent runs (>= 7 days): ~2 hours (re-scrape)

EXAMPLE:
  Monday: Run 1 (~2 hours, full scrape)
  Tuesday-Sunday: Runs 2-7 (~10 minutes each, skip scraper)
  Next Monday: Run 8 (~2 hours again, >= 7 days, re-scrape)

================================================================================
WHAT GETS BACKED UP & RESTORED
================================================================================

BEFORE EACH DEPLOYMENT:
  Automatic backup of: PROJECTS/ directory
  Location: C:\Projects\Crawler\backups\backup_<timestamp>.zip
  Size: ~50-100 MB
  Kept: Last 5 backups (older ones auto-deleted)

TO RESTORE A BACKUP:
  1. Find the backup: ls C:\Projects\Crawler\backups\
  2. Restore it:
     Expand-Archive C:\Projects\Crawler\backups\backup_<timestamp>.zip -DestinationPath C:\Projects\Crawler\PROJECTS -Force

================================================================================
COMMON TASKS
================================================================================

Q: How do I manually trigger an update?
A: Run: C:\Projects\Crawler\PROJECTS\update.bat

Q: How do I check if an update already ran?
A: View: Get-Content C:\Projects\Crawler\logs\deployment.log -Tail 50

Q: How do I change the update time from 6:00 AM?
A: Open Task Scheduler (taskschd.msc)
   Right-click "Crawler-Pipeline-Update"
   Properties > Triggers > Edit
   Change time as needed

Q: How do I disable the 7-day smart detection?
A: Edit: C:\Projects\Crawler\PROJECTS\src\services\pipeline_config.json
   Change: "skip_recent_sites": false

Q: How do I deploy to another machine?
A: Run: C:\Projects\Crawler\PROJECTS\deploy_to_remote.bat "PATH"
   Example: deploy_to_remote.bat "C:\Users\castrk05_adm\Desktop\Multi-module"

Q: How do I restore to an old version?
A: 1. Find backup: ls C:\Projects\Crawler\backups\
   2. Restore: Expand-Archive backup_<timestamp>.zip -DestinationPath PROJECTS -Force
   3. Run pipeline.py to verify

Q: Why is update.bat taking a long time?
A: It's creating a backup. This is normal and good (protects your code).
   Backups typically take 1-2 minutes.

Q: What if git push fails at Step 1?
A: Common causes:
     - Wrong GitHub credentials
     - SSH key not set up
     - Personal Access Token expired
   See: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

================================================================================
TROUBLESHOOTING
================================================================================

ISSUE: Git push fails with "authentication failed"
FIX: 1. Use GitHub Personal Access Token (better than password)
     2. Or set up SSH keys (most secure)
     3. See DEPLOYMENT.md "Troubleshooting" section

ISSUE: Task Scheduler job doesn't run at 6:00 AM
FIX: 1. Verify task exists: Get-ScheduledTask Crawler-Pipeline-Update
     2. Check if enabled: (Get-ScheduledTask).State should be "Ready"
     3. Manually test: C:\Projects\Crawler\PROJECTS\update.bat

ISSUE: Pipeline still takes 2 hours (smart detection not working)
FIX: 1. Check config: grep "skip_recent_sites" pipeline_config.json
     2. Should show: "skip_recent_sites": true
     3. Verify update succeeded: Check logs\deployment.log

ISSUE: Backup space is growing
FIX: Backups are auto-cleaned (keeps last 5)
     Manual cleanup: Delete old files from C:\Projects\Crawler\backups\

For more help, see:
  - DEPLOYMENT_QUICK_START.txt (quick reference)
  - DEPLOYMENT.md (full guide with troubleshooting)
  - DEPLOYMENT_REPORT.md (technical details)

================================================================================
KEY FILES YOU'LL WORK WITH
================================================================================

LOGS (check these to see what happened):
  C:\Projects\Crawler\logs\deployment.log

BACKUPS (restore from here if needed):
  C:\Projects\Crawler\backups\backup_<timestamp>.zip

CONFIGURATION (adjust settings here):
  C:\Projects\Crawler\PROJECTS\src\services\pipeline_config.json

SCRIPTS (run these manually if needed):
  C:\Projects\Crawler\PROJECTS\update.bat
  C:\Projects\Crawler\PROJECTS\setup_deployment.ps1

================================================================================
SUPPORT & DOCUMENTATION
================================================================================

QUICK REFERENCE (Start here):
  File: DEPLOYMENT_QUICK_START.txt
  Location: C:\Projects\Crawler\PROJECTS\

COMPREHENSIVE GUIDE (Full details):
  File: DEPLOYMENT.md
  Location: C:\Projects\Crawler\PROJECTS\

TECHNICAL REPORT (Architecture & details):
  File: DEPLOYMENT_REPORT.md
  Location: C:\Projects\Crawler\PROJECTS\

EMAIL SUPPORT:
  castrokren@gmail.com

================================================================================
SYSTEM STATUS
================================================================================

DEPLOYMENT SYSTEM: Ready
FEATURES: Complete
DOCUMENTATION: Comprehensive
GIT COMMIT: Done (awaiting push)
TASK SCHEDULER: Ready to setup

WHAT'S NEXT:
  1. Push to GitHub (git push origin main)
  2. Set up Task Scheduler (setup_deployment.ps1)
  3. Test (run update.bat)

Estimated total time: ~20 minutes

================================================================================
REMEMBER
================================================================================

- All code changes are backed up automatically
- You can restore any previous version anytime
- Logs show exactly what happened and when
- Smart detection reduces pipeline time 10x (optional, can disable)
- Updates happen automatically every day at 6:00 AM

Questions? See DEPLOYMENT.md or contact castrokren@gmail.com

================================================================================
