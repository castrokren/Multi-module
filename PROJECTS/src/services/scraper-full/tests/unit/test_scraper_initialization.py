"""Unit tests for ScraperEngine initialization, DomainRateLimiter, StateDB, and site config."""
import sys, os, time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scraper_engine import ScraperEngine, _DomainRateLimiter, _StateDB, _site_cfg, DEFAULT_SITE_CONFIG


class TestScraperEngineInitialization:
    def test_default_params(self):
        e = ScraperEngine()
        assert e.page_timeout == 15
        assert e.max_pdf_size_mb == 100
        assert e.min_pdf_size_bytes == 512
        assert e.use_relevance_filter is True
        assert e.allowlist_only is False
        assert e.skip_recent_sites is True
        assert e.days_before_rescrape == 7

    def test_custom_params(self):
        e = ScraperEngine(page_timeout=30, max_pdf_size_mb=50, min_pdf_size_bytes=1024,
                          use_relevance_filter=False, allowlist_only=True, days_before_rescrape=14)
        assert e.page_timeout == 30
        assert e.max_pdf_size_mb == 50
        assert e.min_pdf_size_bytes == 1024
        assert e.use_relevance_filter is False
        assert e.allowlist_only is True
        assert e.days_before_rescrape == 14

    def test_starts_running(self):
        e = ScraperEngine()
        assert e.running is True

    def test_counters_zero(self):
        e = ScraperEngine()
        assert e.page_count == 0
        assert e.pdf_count == 0

    def test_stop(self):
        e = ScraperEngine()
        e.stop()
        assert e.running is False

    def test_stop_idempotent(self):
        e = ScraperEngine()
        e.stop(); e.stop()
        assert e.running is False

    def test_rate_limiter_created(self):
        e = ScraperEngine()
        assert isinstance(e._rate_limiter, _DomainRateLimiter)

    def test_no_legacy_session_attr(self):
        # session is now per-domain-worker, not on engine
        e = ScraperEngine()
        assert not hasattr(e, "session")


class TestDomainRateLimiter:
    def test_enforces_delay(self):
        rl = _DomainRateLimiter()
        rl.wait("a.com", 0.05)
        t0 = time.monotonic()
        rl.wait("a.com", 0.05)
        assert time.monotonic() - t0 >= 0.04

    def test_independent_domains(self):
        rl = _DomainRateLimiter()
        rl.wait("a.com", 0.2)
        t0 = time.monotonic()
        rl.wait("b.com", 0.2)   # b.com never seen — no wait
        assert time.monotonic() - t0 < 0.15


class TestStateDB:
    def test_seen_url(self, temp_output_dir):
        db = _StateDB(os.path.join(temp_output_dir, "t.db"))
        url = "https://example.com/a.pdf"
        assert db.is_seen(url) is False
        db.mark_seen(url, "queued")
        assert db.is_seen(url) is True
        db.close()

    def test_update_status_no_raise(self, temp_output_dir):
        db = _StateDB(os.path.join(temp_output_dir, "t.db"))
        db.mark_seen("https://x.com/b.pdf")
        db.update_status("https://x.com/b.pdf", "downloaded")
        db.close()

    def test_downloaded_path(self, temp_output_dir):
        db = _StateDB(os.path.join(temp_output_dir, "t.db"))
        p = "/tmp/file.pdf"
        assert db.is_downloaded(p) is False
        db.mark_downloaded(p, "https://x.com/file.pdf", "Acme")
        assert db.is_downloaded(p) is True
        db.close()

    def test_dedup_same_url(self, temp_output_dir):
        db = _StateDB(os.path.join(temp_output_dir, "t.db"))
        db.mark_seen("https://x.com/dup.pdf")
        db.mark_seen("https://x.com/dup.pdf")  # must not raise
        db.close()


class TestSiteConfig:
    def test_defaults(self):
        assert _site_cfg("unknown.com", {}) == DEFAULT_SITE_CONFIG

    def test_delay_override(self):
        cfg = _site_cfg("slow.com", {"slow.com": {"delay": 10.0}})
        assert cfg["delay"] == 10.0
        assert cfg["max_pages"] == DEFAULT_SITE_CONFIG["max_pages"]

    def test_disable_recursive(self):
        cfg = _site_cfg("sm.com", {"sm.com": {"use_recursive": False}})
        assert cfg["use_recursive"] is False
        assert cfg["use_sitemap"] is True

    def test_unknown_domain_gets_defaults(self):
        cfg = _site_cfg("other.com", {"only.com": {"delay": 5.0}})
        assert cfg["delay"] == DEFAULT_SITE_CONFIG["delay"]
