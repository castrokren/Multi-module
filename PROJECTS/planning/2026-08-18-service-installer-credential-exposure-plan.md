# Service-Installer Credential Exposure — Fix Plan
**Date:** 2026-08-18
**Branch:** suggest `fix/service-installer-credential-exposure`
**Closes gap:** the legacy-subsystem finding from the 2026-08-18 Egress Control Audit (Q6) — `classify/Updated_Monitor_UI.py` passes a Windows service account password as a plaintext CLI argument, and echoes the full command (password included) into the on-screen log.
**Scope note:** this is unrelated to the crawler's network egress and to `feature/malware-scan-gate` — it's a separate, pre-existing tool (`src/services/classify/`) that installs a Windows Service for the classify/monitor pipeline. Fix independently; do not bundle into the egress-control branches.
**Audience:** implementing agent — self-contained, no other conversation context assumed.

---

## Confirmed exposure (read before starting)

`PROJECTS/src/services/classify/Updated_Monitor_UI.py`, `_execute_command()` (lines 745–791):

```python
opts += ['--username', self.user_var.get().strip()]
opts += ['--password', self.pass_var.get().strip()]
...
cmd = [sys.executable, svc] + opts + [action]
...
self._log_message(f"Running: {' '.join(cmd)}")   # line 766 - password visible on screen
...
result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)  # line 773 - password visible in argv
```

Two separate exposure points, both need fixing:

1. **On-screen log** (`self.log_text`, an in-memory Tk widget — confirmed not written to a log file, so this is a screen/screen-share exposure, not a data-at-rest one).
2. **Process argument list** — the password is a plain `argv` entry for the lifetime of the `subprocess.run` call, visible to anything with permission to enumerate process command lines on that host (Task Manager "Command line" column, `Get-CimInstance Win32_Process`, etc.).

The password is confirmed **not** persisted to either on-disk config file (`_save_config`, lines 608–634, only writes `service_path`/`startup_type`/`interactive`), so there is no data-at-rest exposure to fix — only in-flight exposure.

`svc` (`self.service_path_var`) is a user-browsable path to an arbitrary script (`_browse_service`), so the fix must not assume a fixed target script — it has to work generically for whatever install script the operator points the GUI at, which is why Task 2 below is stdin-based rather than an in-process pywin32 call (an in-process call would require rewriting whichever target script is selected, which this GUI does not control).

---

## Task 1 — Stop echoing the password to the log widget

**File:** `Updated_Monitor_UI.py`, `_execute_command()`, line 766.

Build a redacted copy for display only; the real `cmd` (used at line 773) is unchanged:

```python
def _redact_cmd(cmd: list[str]) -> list[str]:
    display = list(cmd)
    for i, tok in enumerate(display):
        if tok == '--password' and i + 1 < len(display):
            display[i + 1] = '********'
    return display

...
self._log_message(f"Running: {' '.join(_redact_cmd(cmd))}")
```

This is the cheap, immediate fix — do it even if Task 2 takes longer, since it closes the more casually-triggered exposure (anyone glancing at the screen or a screenshot/screen-share) first.

## Task 2 — Move the password off argv onto stdin

**File:** `Updated_Monitor_UI.py`, `_execute_command()`.

Stop putting `--password <value>` in `opts`. Instead, signal the child script to read the password from stdin, and supply it via `subprocess.run(..., input=...)`:

```python
opts = []
if action in ('install', 'update'):
    if self.user_var.get().strip():
        opts += ['--username', self.user_var.get().strip()]
    password = self.pass_var.get().strip()
    if password:
        opts += ['--password-stdin']
    if self.startup_var.get():
        opts += ['--startup', self.startup_var.get()]
    if self.interactive_var.get():
        opts += ['--interactive']

cmd = [sys.executable, svc] + opts + [action]
...
result = subprocess.run(
    cmd,
    input=(password + "\n") if password else None,
    capture_output=True,
    text=True,
    check=True,
    timeout=30,
)
```

`--password-stdin` never appears with a value attached, so the redaction in Task 1 has nothing left to redact for this field — the value simply never enters `argv`.

**Corresponding change required in the target service scripts.** Identify which scripts `service_path_var` actually points to in current use (check `src/services/classify/run_monitor_service.py` and `src/services/classify/simple_W_service.py` — there are also `archive/` copies of both; confirm with the user or `git log`/`git blame` which is the live one before touching anything under `archive/`, since that folder name suggests it's already retired). Whichever is live needs its argument parser updated to accept `--password-stdin` and, when present, read the password from `sys.stdin.readline().rstrip("\n")` instead of (or in addition to, for backward compatibility during rollout) a `--password` flag.

## Task 3 — Clear the password from memory after use

**File:** `Updated_Monitor_UI.py`, `_execute_command()`, in the `finally` block (~line 790).

```python
finally:
    self.pass_var.set('')
    self.after(3000, lambda: self.status_var.set("Ready"))
```

This doesn't prevent the exposure window during the call (Tasks 1–2 do that) but shortens how long the plaintext value sits in the widget/variable afterward. Note this is defense-in-depth, not the primary fix — Tkinter `StringVar` values aren't securely wiped from process memory regardless, so don't oversell this step in documentation.

## Task 4 — Unit tests

`src/services/classify/tests/unit/test_service_installer_credentials.py` (create the `tests/unit/` folder if `classify/` doesn't already have one — check first):

- `test_redact_cmd_masks_password_value` — `_redact_cmd(['python','svc.py','--username','x','--password','hunter2','install'])` → the password value is replaced, `'hunter2'` does not appear anywhere in the result.
- `test_redact_cmd_no_password_present` — no `--password` token → list returned unchanged.
- `test_execute_command_never_puts_password_in_argv` — build `cmd`/`opts` for an `install` action with a password set, assert `'--password'` (the flag itself) is absent from `cmd`, `'--password-stdin'` is present, and the password string only appears in the value passed as `input=` to the mocked `subprocess.run` call.
- `test_execute_command_clears_pass_var_after_run` — mock `subprocess.run`, run an install, assert `self.pass_var.get() == ''` afterward.

If the target service script(s) from Task 2 are also being modified in this same PR, add a matching test there: `--password-stdin` reads from stdin correctly and a plain `--password` (if kept for backward compat) still works during transition.

## Task 5 — Manual validation on the target machine

1. Launch `Updated_Monitor_UI.py`, fill in a test service path, username, and password, click Install.
2. Confirm the on-screen log never shows the plaintext password (Task 1).
3. While the install is running (or immediately after, from `.log` history if the OS retains it briefly), check `Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | Select-Object CommandLine` (or Process Explorer) — confirm no `--password` value appears in any captured command line (Task 2).
4. Confirm the install still succeeds end-to-end with the new stdin path.
5. Confirm `self.pass_var` is empty after the run completes (Task 3) — e.g. temporarily log its length during manual testing, don't ship that log line.

## Task 6 — Documentation

Update `SERVICE_INSTALLATION_GUIDE.md` (`src/services/classify/`): note that credentials are supplied via stdin at install/update time, not via command-line flags, and that the on-screen log intentionally redacts the password.
