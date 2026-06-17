---
name: User Profile - Kren
description: Working style, preferences, and technical context for Crawler Projects
type: user
---

## Role and Context

- **Project:** Crawler Pipeline - document scraping, classification, and cross-reference matching system
- **Scope:** Solo developer managing multi-stage pipeline on Windows servers
- **Environment:** Corporate network with restrictions (no relay servers for email, port 443 required)

## Working Style

**Preference for simplicity:**
- Prefers "ultra-simple" one-click deployments over complex multi-step processes
- Values working end-to-end quickly rather than perfect architecture upfront
- Pragmatic about technical decisions (e.g., "use self-signed certs, it's fine")

**Testing and iteration:**
- Tests locally first, then on remote deployment
- Values seeing concrete results (file detection, pipeline running) over theoretical correctness
- Patient with incremental fixes when issues arise

**Communication:**
- Direct and concise in messages
- Asks clarifying questions ("do this locally or on remote PC?") rather than making assumptions
- Provides context about constraints upfront (network restrictions, ports, no email)

## Technical Environment

**Local Development:**
- Windows machine with Python 3.13+
- Visual Studio Code
- Git with multiple worktrees
- Project structure: `C:\Projects\Crawler\PROJECTS\`

**Remote Deployment:**
- Windows Server
- No internet relay access
- Port 443 open, port 5000 not available
- Fresh deployments via GitHub branch clone

**Constraints:**
- Cannot use email relays → dashboard-only status monitoring
- Must use port 443 → HTTPS with self-signed certificates
- GitHub-based deployment required

## Known Working Patterns

**Deployment strategy:**
- One-click setup.bat for local and remote deployment
- GitHub branch (`claude/pedantic-hofstadter-313610`) as single source of truth
- deploy-from-github.bat for fresh deployments on remote machines

**File handling:**
- Excel files as primary input (`data/som-in/`)
- Auto-detection via polling monitor (not watchdog - more reliable on Windows)
- Status tracked in JSON files (status.json, run_history.json)

**Script language preference:**
- Batch files for Windows deployment (not PowerShell) 
- Python for service logic
- Dashboard as Flask web app

## Things That Have Worked

- Removing watchdog in favor of polling-based file detection
- Copying source files from PROJECTS subfolder to parent for deployment compatibility
- Using goto labels instead of nested if/else in batch files
- Keeping service windows visible (not backgrounded) for error debugging
- Self-signed HTTPS certificates for corporate network

## Things to Avoid

- Multi-line nested if/else blocks with parentheses in batch files
- Backgrounding services with `/B` flag when debugging
- Complex email integration in absence of relay server
- Assuming file paths are the same in development and deployed environments

---

**Last Updated:** 2026-05-12  
**Project Focus:** One-click deployment for Windows Server, GitHub-based installation
