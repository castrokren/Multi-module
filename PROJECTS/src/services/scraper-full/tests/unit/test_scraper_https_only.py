"""HTTPS-only egress enforcement.

Covers the https_upgrade_attempt + allow_http_hosts behaviour added in
2026-08-18: plain http:// is rejected by default, excepted hosts may still
use it, and http:// PDF links are rewritten to https:// before download.

Run with: python -m pytest src/services/scraper-full/tests/unit/test_scraper_https_only.py -v -m unit
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scraper_engine import (
    _validate_url, _StateDB, ScraperEngine, DEFAULT_SITE_CONFIG,
)


PAYLOAD = b"%PDF-1.4 " + b"x" * 600


def _make_engine(**kw):
    kw.setdefault("use_relevance_filter", False)
    kw.setdefault("use_keyword_filter", False)
    kw.setdefault("min_pdf_size_bytes", 4)
    kw.setdefault("malware_scan_enabled", False)
    return ScraperEngine(**kw)


def _make_session(upgraded_url: str = "https://acme.com/doc.pdf"):
    session = MagicMock()
    resp = MagicMock()
    resp.headers = {"content-type": "application/pdf"}
    resp.url = upgraded_url
    resp.history = []
    resp.iter_content.return_value = iter([PAYLOAD])
    session.get.return_value = resp
    session.head.return_value = MagicMock(headers={})
    return session


def _download(e, pdf_url, tmp_path, session):
    db = _StateDB(str(tmp_path / "state.db"))
    cfg = dict(DEFAULT_SITE_CONFIG, delay=0)
    e._download_pdf(pdf_url, str(tmp_path), "ACME", "", "acme.com", session, db, cfg)
    db.close()


class TestValidateUrlHttpsOnly:
    def test_https_url_always_allowed(self):
        assert _validate_url("https://vendor.com/x.pdf") is True
        assert _validate_url("https://sub.vendor.com/x.pdf") is True
        assert _validate_url("https://vendor.com:8443/x.pdf") is True

    def test_http_url_blocked_by_default(self):
        assert _validate_url("http://vendor.com/x.pdf") is False
        assert _validate_url("http://vendor.com") is False

    def test_http_url_allowed_with_exception(self):
        assert _validate_url(
            "http://vendor.com/x.pdf",
            allow_http_hosts=frozenset({"vendor.com"}),
        ) is True

    def test_localhost_and_ip_still_blocked(self):
        assert _validate_url("http://localhost/x.pdf") is False
        assert _validate_url("http://127.0.0.1/x.pdf") is False
        assert _validate_url("https://localhost/x.pdf") is False
        assert _validate_url("https://127.0.0.1/x.pdf") is False
        assert _validate_url(
            "http://localhost/x.pdf",
            allow_http_hosts=frozenset({"localhost"}),
        ) is False


class TestHttpsUpgrade:
    def test_https_upgrade_rewrites_url(self, tmp_path):
        e = _make_engine()
        session = _make_session()
        _download(e, "http://acme.com/doc.pdf", tmp_path, session)
        got = [c.args[0] for c in session.get.call_args_list]
        assert got == ["https://acme.com/doc.pdf"]
        assert session.head.call_args_list[0].args[0] == "https://acme.com/doc.pdf"

    def test_https_upgrade_disabled_blocks_outright(self, tmp_path):
        e = _make_engine(https_upgrade_attempt=False)
        session = _make_session()
        _download(e, "http://acme.com/doc.pdf", tmp_path, session)
        assert not session.get.called
        assert not session.head.called
        db = _StateDB(str(tmp_path / "state.db"))
        row = db._conn().execute(
            "SELECT status FROM seen_urls WHERE url=?",
            ("http://acme.com/doc.pdf",)).fetchone()
        db.close()
        assert row is not None and row[0] == "blocked_insecure_scheme"

    def test_http_exception_skips_upgrade(self, tmp_path):
        e = _make_engine(allow_http_hosts={"acme.com"})
        session = _make_session()
        _download(e, "http://acme.com/doc.pdf", tmp_path, session)
        got = [c.args[0] for c in session.get.call_args_list]
        assert got == ["http://acme.com/doc.pdf"]
        assert (tmp_path / "doc.pdf").exists()