# HTTPS-Only Enforcement — Implementation Plan
**Date:** 2026-08-18
**Branch:** suggest `feature/https-only-egress`
**Closes gap:** Q5 of the 2026-08-18 Egress Control Audit — "`_validate_url()` accepts scheme `http` as well as `https`; certificate validation is on by default but never required, since plain HTTP is never rejected up front."
**Audience:** implementing agent — self-contained, no other conversation context assumed.

---

## Pre-flight — audit before changing behavior (do not skip)

Flipping to HTTPS-only blind risks silently losing PDFs from vendors whose sites are only linked over `http://`. Measure first:

```powershell
cd <repo>\src\services\scraper-full
# Search recent pipeline logs for http:// URLs that were actually fetched
Select-String -Path "..\cross-reference\results\pipeline_*.log" -Pattern "http://" | Select-Object -First 50
```

Also check `.scraper_dedup.db`'s `seen_urls` table (if it stores the raw URL) for the proportion of `http://` vs `https://` entries. Report the count of distinct **domains** (not URLs) that are http-only — that's the number of vendors this change could break, and it's the number that determines whether Task 2's exception list is a formality or a real list to populate before merging.

---

## Task 1 — Reject plain HTTP by default

**File:** `PROJECTS/src/services/scraper-full/scraper_engine.py`, `_validate_url()` (currently ~lines 207–219).

```python
def _validate_url(url: str, allow_http_hosts: frozenset[str] = frozenset()) -> bool:
    try:
        p = urlparse(url)
        host = p.netloc.split(":")[0].lower()
        if p.scheme == "http" and host not in allow_http_hosts:
            return False
        return (
            p.scheme in ("http", "https")
            and bool(host)
            and "." in host
            and "localhost" not in host
            and "127.0.0.1" not in host
        )
    except Exception:
        return False
```

`allow_http_hosts` comes from `pipeline_config.json`'s new `security.allow_http_hosts` list (see Task 2) — same shape and same sign-off bar as the existing per-vendor `allowed_hosts` domain override, so it's an explicit, reviewable exception list rather than a silent global downgrade.

Every call site of `_validate_url()` needs the new parameter threaded through — grep for all call sites before assuming `_download_pdf` is the only one:

```powershell
Select-String -Path scraper_engine.py -Pattern "_validate_url\("
```

Blocked URLs should get a new status string, `blocked_insecure_scheme`, consistent with the existing convention (`blocked_off_domain`, `skipped_size`, etc.).

## Task 2 — Config-gated exception list

**File:** `PROJECTS/src/services/pipeline_config.json`

```json
{
  "security": {
    "allow_http_hosts": [],
    "https_upgrade_attempt": true
  }
}
```

- `allow_http_hosts`: hostnames explicitly permitted to be fetched over plain HTTP. Starts empty. Only populate it with entries the Pre-flight audit found to be genuinely HTTPS-incapable (confirm with a manual `curl -I https://<host>` — many "http-only" links are just authored lazily and the site actually serves HTTPS fine). Each addition here is a real exception and should get the same sign-off as flipping `malware_scan_enabled` off — document who approved it and why, in `docs/RUNBOOK.md`.
- `https_upgrade_attempt`: default `true`. See Task 3.

## Task 3 — Try HTTPS before giving up on an http:// link

Many `http://` URLs discovered on a vendor's page will happily serve over HTTPS even though the link wasn't authored that way. Rather than blocking every one (and inflating the exception list unnecessarily), attempt the upgrade first:

**File:** `scraper_engine.py`, in `_download_pdf`, right where `_validate_url` currently gates (line ~1089):

```python
if not _validate_url(pdf_url, allow_http_hosts):
    if pdf_url.lower().startswith("http://") and cfg.get("https_upgrade_attempt", True):
        upgraded = "https://" + pdf_url[len("http://"):]
        if _validate_url(upgraded, allow_http_hosts):
            logger.info("[%s] Upgraded insecure link to HTTPS: %s", supplier, upgraded)
            pdf_url = upgraded
        else:
            logger.warning("[%s] Blocked insecure URL (no HTTPS upgrade available): %s", supplier, pdf_url)
            state_db.mark_seen(pdf_url, "blocked_insecure_scheme")
            return
    else:
        logger.warning("[%s] Blocked insecure URL: %s", supplier, pdf_url)
        state_db.mark_seen(pdf_url, "blocked_insecure_scheme")
        return
```

This is a URL-string upgrade only, not a live probe — no plaintext request is ever made to test reachability, so the "upgrade attempt" itself never completes a transfer over HTTP. If the upgraded HTTPS URL is unreachable, it fails downstream the same way any other unreachable HTTPS URL does (connection error, logged, skipped) — no fallback to plaintext.

## Task 4 — Unit tests

`src/services/scraper-full/tests/unit/test_scraper_https_only.py`:

- `test_https_url_always_allowed` — baseline, no regression.
- `test_http_url_blocked_by_default` — `_validate_url("http://vendor.com/x.pdf")` → `False`.
- `test_http_url_allowed_with_exception` — host in `allow_http_hosts` → `True`.
- `test_https_upgrade_rewrites_url` — `_download_pdf` given an `http://` URL for a host not in the exception list, with `https_upgrade_attempt: true`, actually issues the request against the `https://` variant (mock the session, assert the URL passed to `session.get`).
- `test_https_upgrade_disabled_blocks_outright` — `https_upgrade_attempt: false` → insecure URL blocked, no upgrade attempted, no request issued at all.
- `test_localhost_and_ip_still_blocked` — confirm Task 1's rewrite didn't loosen the existing `localhost`/`127.0.0.1` checks.

## Task 5 — Rollout

1. Run the Pre-flight audit against the real supplier list before merging. If it finds zero http-only vendors, this is a clean cutover — merge with `allow_http_hosts: []`.
2. If it finds some, populate `allow_http_hosts` with sign-off per entry, or contact those vendors' sites directly to confirm they have no HTTPS endpoint before accepting the exception.
3. Confirm the full existing test suite still passes (136 tests + new suite here), same acceptance bar as the malware-scan-gate work.
4. Update `docs/RUNBOOK.md`: HTTPS-only is now the default, how `allow_http_hosts` works, and that additions require sign-off — mirror the existing "Malware scanning control" section's tone and format.
