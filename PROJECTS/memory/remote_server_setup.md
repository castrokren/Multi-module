---
name: Remote Server Deployment Setup
description: Path and configuration for remote server deployment
type: project
---

# Remote Server Deployment Configuration

**Remote Server Path:** `C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS`

**Key Files:**
- Main repo: `C:\Users\castrk05_adm\Desktop\Multi-module`
- Backups: `C:\Users\castrk05_adm\Desktop\Multi-module\backups`
- Logs: `C:\Users\castrk05_adm\Desktop\Multi-module\logs`

## Important: Path Differences

Local machine (Kren's computer):
- Path: `C:\Projects\Crawler\PROJECTS`
- Uses: `update.bat` and deployment scripts

Remote server:
- Path: `C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS`
- Does NOT have `C:\Projects\Crawler` directory
- **All deployment scripts must reference the remote path, not C:\Projects\Crawler**

## Update.bat Configuration

The `update.bat` script has hardcoded paths. When updating it:
1. Local version uses: `C:\Projects\Crawler`
2. Remote version must use: `C:\Users\castrk05_adm\Desktop\Multi-module`

**Lines to update in update.bat:**
```batch
set REPO_DIR=C:\Users\castrk05_adm\Desktop\Multi-module
set BACKUP_DIR=C:\Users\castrk05_adm\Desktop\Multi-module\backups
set LOG_DIR=C:\Users\castrk05_adm\Desktop\Multi-module\logs
```

## Deployment Process

1. Make changes locally at: `C:\Projects\Crawler\PROJECTS`
2. Commit and push to GitHub
3. On remote server, run: `git pull origin main` from `C:\Users\castrk05_adm\Desktop\Multi-module`
4. Test pipeline from remote location

## Testing Updates on Remote

```powershell
cd "C:\Users\castrk05_adm\Desktop\Multi-module"
.\update.bat
```

Check logs at: `C:\Users\castrk05_adm\Desktop\Multi-module\logs\deployment.log`
