---
name: Git and Branch Management Patterns
description: Lessons from managing deployment branch and handling multiple worktrees
type: feedback
---

## Multiple Worktrees Issue

When working with multiple git worktrees, branch switching becomes complex.

**Problem:** When you have a worktree checked out for branch `X`, you cannot checkout that same branch in the main repository without deleting the worktree first.

**Error message:**
```
fatal: 'branch-name' is already used by worktree at 'path/.claude/worktrees/branch-name'
```

**Solution:**
- Use `git push origin <source-branch>:<destination-branch>` to push changes to a different branch without checking it out locally
- Or delete the worktree before switching: `git worktree remove path`
- When uncertain which branch you're on, **always check first** with `git status` before committing

**How to apply:** Before committing deployment changes, verify you're on the right branch. If you need to push to a different branch, use the push syntax to avoid worktree conflicts.

---

## File Not in Repository Despite Being "Tracked"

**Problem:** File showed up in `git ls-files` as tracked, but was not actually in remote repository commits.

**Root cause:** File existed locally and was listed as tracked, but was never actually committed to any branch.

**Verification steps:**
```bash
git ls-files | findstr "filename"           # Shows if tracked
git log --oneline -- path/filename          # Shows if in history
git log origin/branch -- path/filename      # Shows if on remote branch
```

**How to apply:** When unsure if a file is in GitHub, check the remote branch history, not just local tracking. Use `git log origin/branch-name` to verify files are actually committed to the deployment branch.

---

## Force Push on Deployment Branch

When development branches diverge from deployment branch, use force push carefully:

```bash
git push -f origin HEAD:deployment-branch
```

**Why needed:** Deployment branch may have commits that don't exist in current feature branch. Force push overwrites the remote branch with current HEAD.

**Risk:** Only acceptable on a dedicated deployment branch with a single developer. On shared branches, force push can destroy others' work.

**How to apply:** `claude/pedantic-hofstadter-313610` is a dedicated deployment branch, so force push is safe when consolidating changes from feature branches.

---

## Repository Structure Affects Deployment

**Lesson:** Repository structure matters to deployment scripts.

The Multi-module repo has:
```
Multi-module/
  ├── PROJECTS/          ← Contains setup.bat, ops/, src/
  ├── README.md
  └── <other files>
```

When cloning, scripts must account for the PROJECTS subfolder:
- deploy-from-github.bat must `cd PROJECTS` before running setup.bat
- Python scripts must adjust path logic to handle both:
  - Direct execution: `/path/to/PROJECTS/src/...`
  - Deployment execution: `/path/to/Multi-module/PROJECTS/src/...`

**How to apply:** When creating deployment scripts for repos with subfolders, test both:
1. Running from the subfolder directly (local development)
2. Running after cloning the whole repo (production deployment)

---

**Last Updated:** 2026-05-12  
**Session:** Crawler Pipeline one-click deployment project
