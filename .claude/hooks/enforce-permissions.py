#!/usr/bin/env python3
"""PreToolUse hook: autonomy with guardrails. Auto-approves Bash except a
dangerous denylist; scopes file writes to project roots."""
import json, sys, os

def decide(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,      # "allow" | "deny" | "ask"
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)

# Writes allowed only under these roots (lowercase, backslash form)
ALLOWED_ROOTS = [
    r"c:\projects\arcvault2.0",
    r"c:\brain\arcvault2.0",
]

# Bash commands containing any of these are always blocked
DENY_SUBSTRINGS = [
    "rm -rf", "rm -fr", ":(){",        # recursive delete / fork bomb
    "mkfs", "dd if=", "> /dev/sd",     # disk destruction
    "git push --force", "git push -f", # history rewrites
    "shutdown", "reg delete",
    "del /f /s /q", "rmdir /s",        # Windows recursive delete
]

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # can't parse -> fall through to normal flow (fail safe)

tool = data.get("tool_name", "")
ti = data.get("tool_input", {}) or {}

if tool == "Bash":
    cmd = (ti.get("command") or "").lower()
    for bad in DENY_SUBSTRINGS:
        if bad in cmd:
            decide("deny", f"Blocked dangerous pattern: {bad!r}")
    decide("allow", "Approved by ArcVault project policy")

if tool in ("Edit", "Write", "MultiEdit"):
    path = ti.get("file_path") or ti.get("path") or ""
    if path:
        np = os.path.normpath(path).replace("/", "\\").lower()
        if any(np.startswith(root) for root in ALLOWED_ROOTS):
            decide("allow", "Write within allowed project root")
        decide("ask", f"Path outside allowed roots: {path}")

sys.exit(0)  # anything else: don't interfere