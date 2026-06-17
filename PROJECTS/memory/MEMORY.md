# Memory Index

**Last Updated:** 2026-05-28

## Current Status
- **Deployment**: ✅ COMPLETE — One-click `setup.bat` is live on remote server. HTTPS dashboard at https://localhost. Auto-start on reboot configured via Windows Task Scheduler.
- **Cross-reference**: Path issues resolved (hardcoded paths removed, `sys.path` fixed in `crossref_standalone_fast.py`, state tracking added).
- **Pipeline**: Fully operational. Drop Excel file in `data\som-in\`, monitor detects in <10 sec, runs automatically (75–120 min), results saved to `crossref_results_*.xlsx`.

## Memory Files

- [Remote Server Setup](remote_server_setup.md) — **CRITICAL**: Remote path is `C:\Users\castrk05_adm\Desktop\Multi-module\PROJECTS`, NOT `C:\Projects\Crawler`. All deployment scripts must use remote path.
- [Deployment Workflow](deployment_workflow.md) — Complete setup: setup.bat, deploy-from-github.bat, services, file detection, HTTPS dashboard
- [Git & Branch Patterns](git_and_branch_patterns.md) — Worktree conflicts, force push, structure considerations, verification commands
- [User Profile](user_profile.md) — Solo developer, prefers simplicity, Windows/corporate constraints, working patterns

## Recent Changes (since May 18, 2026)
- `crossref_standalone_fast.py` — new fast cross-reference engine; `sys.path` and hardcoded path issues fixed
- `pipeline_config.json` — paths updated for remote server; merge conflict resolved
- `setup.bat` — path messages corrected for remote server context; pause added to show output
- Deployment declared complete; dashboard and folder monitor services verified running
