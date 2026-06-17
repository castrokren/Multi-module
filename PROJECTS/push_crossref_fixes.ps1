#!/usr/bin/env powershell
# Commit and push CrossRef fixes to GitHub

param([switch]$Force = $false)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
if (-not $scriptDir) { $scriptDir = Get-Location }

Write-Host "📁 Working directory: $scriptDir" -ForegroundColor Cyan
Write-Host ""

# Check git
Write-Host "Checking for git..." -ForegroundColor Cyan
$gitVersion = & git --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Git not found. Please install Git." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Git found: $gitVersion" -ForegroundColor Green
Write-Host ""

# Change directory
Set-Location $scriptDir
Write-Host "📂 Current location: $(Get-Location)" -ForegroundColor Cyan
Write-Host ""

# Verify correct directory
if (-not (Test-Path "src/services/pipeline_config.json")) {
    Write-Host "❌ Error: Not in PROJECTS directory" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Correct directory confirmed" -ForegroundColor Green
Write-Host ""

# Check git status
Write-Host "📋 Current git status:" -ForegroundColor Cyan
& git status
Write-Host ""

# Stage files
Write-Host "📝 Staging modified files..." -ForegroundColor Cyan
& git add "src/services/pipeline_config.json"
& git add "Cross-reference/crossref_standalone_fast.py"
& git add "CROSSREF_DEBUGGING_REPORT.md"
& git add "test_crossref_fixes.py"
Write-Host ""

Write-Host "✅ Staged files:" -ForegroundColor Green
& git diff --cached --name-only
Write-Host ""

# Check if anything is staged
$stagedChanges = & git diff --cached --name-only
if (-not $stagedChanges) {
    Write-Host "❌ No files staged for commit" -ForegroundColor Red
    exit 1
}

# Create commit message file
$tempMessage = [System.IO.Path]::GetTempFileName()
@"
fix(crossref): Fix hardcoded paths, remove duplicates, add state tracking

Critical fixes for CrossRef failures:

1. Updated pipeline_config.json with relative paths instead of hardcoded ones
   - Fixes FileNotFoundError on every pipeline run
   - Makes configuration portable across machines

2. Removed duplicate find_matching_pdfs() stub methods
   - Eliminated unused legacy code that returned empty results

3. Added state tracking to prevent rescanning directories
   - New methods: _load_state(), _save_state(), _mark_supplier_scanned()
   - Saves .crossref_state.json with processed supplier list
   - FALLBACK logic now skips already-scanned suppliers

4. Added CROSSREF_DEBUGGING_REPORT.md
   - Complete root cause analysis and documentation

Verified: All fixes tested and working correctly
"@ | Set-Content $tempMessage

# Commit
Write-Host "💾 Creating commit..." -ForegroundColor Cyan
& git commit -F $tempMessage
$commitStatus = $LASTEXITCODE

Remove-Item $tempMessage -Force

if ($commitStatus -ne 0) {
    Write-Host "⚠️ Commit failed or no changes to commit" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Commit successful!" -ForegroundColor Green
Write-Host ""

# Push to GitHub
Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Cyan
$branch = & git rev-parse --abbrev-ref HEAD
Write-Host "📌 Current branch: $branch" -ForegroundColor Cyan
Write-Host ""

& git push origin $branch
$pushStatus = $LASTEXITCODE

if ($pushStatus -eq 0) {
    Write-Host ""
    Write-Host "✅✅✅ Push successful! ✅✅✅" -ForegroundColor Green
    Write-Host ""
    Write-Host "✨ CrossRef fixes have been pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Run deployment: .\update.bat" -ForegroundColor White
    Write-Host "   2. Test pipeline: python pipeline.py --only-crossref" -ForegroundColor White
    Write-Host "   3. Verify .crossref_state.json is created" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Push failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Troubleshooting:" -ForegroundColor Cyan
    Write-Host "   1. Check network connection" -ForegroundColor White
    Write-Host "   2. Verify GitHub credentials: git config --list" -ForegroundColor White
    Write-Host "   3. Check remote: git remote -v" -ForegroundColor White
    exit 1
}

Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
