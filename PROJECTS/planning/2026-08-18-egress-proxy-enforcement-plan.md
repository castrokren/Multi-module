# Egress Proxy Enforcement — Implementation Plan
**Date:** 2026-08-18
**Status (2026-08-19): TABLED.** IT security has deferred a network-level proxy/allowlist control for now rather than committing to it — it isn't confirmed as feasible with current tooling. Do not start implementation. Kept here as a ready-to-go plan for whenever it's revisited, plus a "Future enhancement" note below on the dynamic-allowlist requirement that came up in review.
**Status (2026-08-19, updated): IMPLEMENTED (Tasks 1, 2, 4, 6) by agent per explicit user request.** Fail-open defaults deployed (`require_proxy: false`, empty proxy URLs) per Pre-flight Q1 = direct egress acceptable.

## Outstanding (not done — blocked/deferred, do before treating this plan as complete)

- **Task 3 — Proxy authentication.** IT has NOT confirmed whether the corporate proxy requires credentials. Until confirmed: no credentials added, no plaintext allowed in `pipeline_config.json`. If/when creds are confirmed, follow the env-var/secret-store pattern documented in `docs/RUNBOOK.md` §8b (runtime interpolation from `os.environ["CRAWLER_PROXY_URL"]` set via Windows Credential Manager / existing ops secret store); escalate if no secret-store convention exists.
- **Task 5 — Validation on the target server.** Requires IT/proxy access + the production data tree (`C:\Data\Crawler\`), not available on the dev box. When IT provides a proxy:
  1. With `require_proxy: false` and no proxy configured, confirm a real crawl run still succeeds unchanged (no regression).
  2. Point `https_proxy` at the real corporate proxy, run a crawl, confirm requests transit it (proxy-side access logs / source IP).
  3. Set `require_proxy: true` and point the proxy URL at an unreachable host — confirm the pipeline refuses to start with a clear error (fail-closed acceptance test). Locally equivalent checks already pass: `--dry-run` reports the error, and `_make_session()`/`run()` raise `RuntimeError`.
**Branch:** suggest `feature/egress-proxy-controls` off `feature/malware-scan-gate` (or off `main` once that merges)
**Closes gap:** Q4 of the 2026-08-18 Egress Control Audit — "no proxy controls; `requests` silently inherits `HTTP_PROXY`/`HTTPS_PROXY` from the host environment if set, but nothing in code requires, verifies, or configures one."
**Audience:** implementing agent — self-contained, no other conversation context assumed.

---

## Pre-flight (answer before writing code)

This plan cannot be finished blind — get answers from IT security / network team first:

1. **Is a corporate egress proxy actually mandated** for this host, or is direct internet egress acceptable? If direct egress is fine, the correct fix may be "explicitly document and pin that decision" rather than adding proxy plumbing nobody will configure.
2. If mandated: proxy host, port, scheme (`http://` vs authenticated `https://`), and whether it differs for HTTP vs HTTPS targets.
3. Does the proxy require credentials, and if so, where are they stored today (env var, Windows Credential Manager, none)? This determines whether Task 3 is needed.

Do not guess these values into the default config — an unreachable placeholder proxy would silently break every crawl run.

---

## Task 1 — Explicit proxy config surface

**File:** `PROJECTS/src/services/pipeline_config.json`

Add a `network` block:

```json
{
  "network": {
    "https_proxy": "",
    "http_proxy": "",
    "require_proxy": false,
    "trust_env_proxy": false
  }
}
```

- `https_proxy` / `http_proxy`: explicit proxy URLs (e.g. `http://proxy.corp.internal:8080`). Empty string = no proxy for that scheme.
- `require_proxy`: hard fail-closed switch — if `true` and the resolved proxy config is empty, the pipeline must refuse to start (mirrors the `malware_scan_enabled` kill-switch precedent in `defender_scan.py`).
- `trust_env_proxy`: default `false`. When `false`, the session must ignore `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` env vars entirely, so behavior is fully determined by this config file, not whatever happens to be set in the host's environment. Only flip to `true` if IT security explicitly wants env-var-managed proxying (e.g. centrally pushed via GPO) instead of file-based config.

Update `PROJECTS/docs/ARCHITECTURE.md` the same way `review_dir`/`quarantine_dir` were documented, so the config surface stays current.

## Task 2 — Wire into the session factory

**File:** `PROJECTS/src/services/scraper-full/scraper_engine.py`, `_make_session()` (currently ~line 447).

```python
def _make_session(timeout: int = 15, network_cfg: dict | None = None) -> requests.Session:
    network_cfg = network_cfg or {}
    s = requests.Session()
    s.headers.update({"User-Agent": _USER_AGENT})

    s.trust_env = bool(network_cfg.get("trust_env_proxy", False))

    proxies = {}
    if network_cfg.get("http_proxy"):
        proxies["http"] = network_cfg["http_proxy"]
    if network_cfg.get("https_proxy"):
        proxies["https"] = network_cfg["https_proxy"]

    if network_cfg.get("require_proxy") and not proxies:
        raise RuntimeError(
            "network.require_proxy is true but no http_proxy/https_proxy "
            "configured in pipeline_config.json - refusing to start "
            "unproxied egress."
        )

    if proxies:
        s.proxies.update(proxies)

    retry = Retry(...)  # unchanged
    ...
    return s
```

Thread `network_cfg` (the `network` block from `pipeline_config.json`) into every call site of `_make_session()` — check both the pipeline path and the GUI path (`pdf_crawler_gui_2.py`) so the GUI can't bypass the control by constructing a session without it.

`s.trust_env = False` is the important line even when no proxy is configured: it stops `requests` from silently picking up an unaudited env-based proxy (or an unaudited absence of one) and makes the config file the single source of truth.

## Task 3 — Proxy authentication (only if Pre-flight says the proxy needs credentials)

If the corporate proxy requires auth, do **not** embed a plaintext username/password in `pipeline_config.json`. Two acceptable patterns, in order of preference:

1. Embed credentials in the proxy URL only via an environment variable resolved at runtime (`network_cfg["https_proxy"]` interpolated from `os.environ["CRAWLER_PROXY_URL"]`, itself set through Windows Credential Manager / a secrets store the ops team already uses — check `docs/RUNBOOK.md` for whatever pattern is already used for other secrets in this deployment, if any, and match it rather than inventing a new one).
2. If no secrets-management convention exists yet in this repo, escalate — do not add the first plaintext credential to `pipeline_config.json` without a decision from IT security on where it should actually live.

## Task 4 — Unit tests

`src/services/scraper-full/tests/unit/test_scraper_proxy.py`:

- `test_no_proxy_configured_by_default` — empty `network` block → `session.proxies == {}`.
- `test_proxy_applied_when_configured` — `http_proxy`/`https_proxy` set → `session.proxies` matches.
- `test_require_proxy_without_config_raises` — `require_proxy: true`, no proxy URLs → `_make_session()` raises `RuntimeError`.
- `test_trust_env_false_ignores_env_proxy` — monkeypatch `HTTPS_PROXY` env var, confirm `session.trust_env is False` and the env var has no effect on `session.proxies` when config is empty.
- `test_trust_env_true_honors_env_proxy` — same, but `trust_env_proxy: true` in config → env var applies (only if Task 3/Pre-flight decides this mode is needed).

## Task 5 — Validation on the target server

1. With `require_proxy: false` and no proxy configured, confirm a real crawl run still succeeds unchanged (no regression).
2. If a proxy is mandated: point `https_proxy` at the real corporate proxy, run a crawl, confirm requests actually transit it (check proxy-side access logs for the crawler's User-Agent / source IP).
3. Set `require_proxy: true` and point the proxy URL at an unreachable host — confirm the pipeline fails to start with a clear error, rather than silently falling back to direct egress. This is the fail-closed check and the most important one, mirroring the Defender fail-closed acceptance test in the malware-scan-gate plan.

## Task 6 — Documentation

Add a short section to `docs/RUNBOOK.md` (after the existing "Malware scanning control" section, same style): what `network.*` config does, how to point it at the corporate proxy, and that `require_proxy: true` is the recommended production setting once a proxy is confirmed mandatory.

---

## Future enhancement (not part of this plan) — dynamic domain allowlist

Raised during the 2026-08-18/19 security review, tabled 2026-08-19 pending confirmation of available tooling. Capturing the idea so it isn't lost:

The vendor domain list changes over time as suppliers are added/removed, so a network-level allowlist would need to stay in sync automatically rather than being a static rule someone maintains by hand. If this is picked back up, the mechanism sketched during review was:

- Regenerate a plain-text domain list from the master vendor spreadsheet (the same source `_same_site()` already trusts at the app layer) on every pipeline run, written to a fixed file location.
- Point the enforcement point at that file. This only works cleanly with a **domain-aware** proxy or next-gen firewall that supports reloading a rule list from a file/URL — a traditional IP-based firewall rule will not hold up, since most vendor sites sit behind CDNs with rotating IPs.
- Log every diff (domains added/removed) each time the list regenerates, so there's an audit trail of authorization changes, not just a current snapshot.
- Fail closed on a bad read: if the vendor spreadsheet is ever missing/unreadable, keep the last known-good list rather than wiping it out.

**Before resuming this:** confirm with the network team (a) whether a domain-aware proxy or FQDN-capable firewall is actually in place, (b) whether it supports automated/scheduled reloads or only manual rule changes, and (c) whether org policy permits an automated push to security infrastructure at all, or requires human review per change. The answer to those determines whether this becomes a fully automated sync, a scripted-diff-with-manual-approval workflow, or gets dropped in favor of detective controls (egress logging/alerting) instead of a preventive allowlist.
