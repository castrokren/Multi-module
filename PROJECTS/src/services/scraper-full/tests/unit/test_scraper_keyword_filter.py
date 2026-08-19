"""Unit tests for the supplier keyword filter in _should_download.

Regression tests for the over-download bug: junk numeric tokens and
missing supplier entries used to fail open and download everything.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parents[4] / "services"))

from scraper_engine import ScraperEngine
from pipeline import _extract_keyword_tokens


def _engine(**kw):
    kw.setdefault("use_keyword_filter", False)  # skip keyword file loading
    return ScraperEngine(**kw)


class TestSupplierKeywordFilter:
    URL = "https://example.com/docs/confocal-microscope-datasheet.pdf"

    def test_keyword_match_allows(self):
        e = _engine(supplier_keywords={"acme": ["microscope"]})
        ok, reason = e._should_download(self.URL, "", "ACME")
        assert ok

    def test_no_keyword_match_blocks(self):
        e = _engine(supplier_keywords={"acme": ["centrifuge"]})
        ok, reason = e._should_download(self.URL, "", "ACME")
        assert not ok and reason == "no_keyword_match"

    def test_missing_supplier_fails_closed(self):
        e = _engine(supplier_keywords={"other supplier": ["microscope"]})
        ok, reason = e._should_download(self.URL, "", "ACME")
        assert not ok and reason == "no_supplier_keywords"

    def test_short_token_needs_whole_word(self):
        # "lab" must not substring-match "collaboration"
        e = _engine(supplier_keywords={"acme": ["lab"]})
        ok, _ = e._should_download("https://example.com/collaboration-datasheet.pdf", "", "ACME")
        assert not ok
        ok, _ = e._should_download("https://example.com/lab-equipment-datasheet.pdf", "", "ACME")
        assert ok

    def test_long_token_substring_matches(self):
        e = _engine(supplier_keywords={"acme": ["microscope"]})
        ok, _ = e._should_download("https://example.com/microscopes-catalog.pdf", "", "ACME")
        assert ok

    def test_empty_keyword_dict_skips_filter(self):
        # No keywords loaded at all -> filter not applied (GUI / standalone use)
        e = _engine(supplier_keywords={})
        ok, _ = e._should_download(self.URL, "", "ACME")
        assert ok


class TestPathAndAnchorMatching:
    def test_keyword_in_folder_path_matches(self):
        # generic filename, product name in the path
        e = _engine(supplier_keywords={"acme": ["microscope"]})
        ok, _ = e._should_download(
            "https://example.com/products/confocal-microscope/datasheet.pdf", "", "ACME")
        assert ok

    def test_keyword_in_anchor_matches(self):
        e = _engine(supplier_keywords={"acme": ["mx500"]})
        ok, _ = e._should_download(
            "https://example.com/files/dl.php-datasheet.pdf", "MX500 Spec Sheet", "ACME")
        assert ok

    def test_no_match_anywhere_blocks(self):
        e = _engine(supplier_keywords={"acme": ["centrifuge"]})
        ok, reason = e._should_download(
            "https://example.com/products/microscope/datasheet.pdf", "Datasheet", "ACME")
        assert not ok and reason == "no_keyword_match"


class TestContentRelevance:
    def test_fails_open_without_keywords(self, tmp_path):
        e = _engine(supplier_keywords={})
        assert e._content_relevant(str(tmp_path / "missing.pdf"), "ACME")

    def test_fails_open_on_unreadable_file(self, tmp_path):
        e = _engine(supplier_keywords={"acme": ["microscope"]})
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a real pdf")
        assert e._content_relevant(str(bad), "ACME")


class TestHashDedup:
    def test_hash_roundtrip(self, tmp_path):
        from scraper_engine import _StateDB
        db = _StateDB(str(tmp_path / "state.db"))
        assert not db.is_hash_seen("abc123")
        db.mark_hash("abc123")
        assert db.is_hash_seen("abc123")
        db.close()


class TestMagicBytes:
    def test_html_payload_rejected(self, tmp_path):
        from unittest.mock import MagicMock
        from scraper_engine import _StateDB, DEFAULT_SITE_CONFIG
        e = _engine(use_relevance_filter=False)
        session = MagicMock()
        resp = MagicMock()
        resp.headers = {"content-type": "application/pdf"}
        resp.history = []
        resp.iter_content.return_value = iter([b"<html><body>Login required</body></html>"])
        session.get.return_value = resp
        session.head.return_value = MagicMock(headers={})
        db = _StateDB(str(tmp_path / "state.db"))
        cfg = dict(DEFAULT_SITE_CONFIG, delay=0)
        e._download_pdf("https://example.com/doc.pdf", str(tmp_path), "ACME",
                        "", "example.com", session, db, cfg)
        assert not (tmp_path / "doc.pdf").exists()
        row = db._conn().execute(
            "SELECT status FROM seen_urls WHERE url=?",
            ("https://example.com/doc.pdf",)).fetchone()
        assert row[0] == "rejected_not_pdf"
        db.close()

    def test_pdf_payload_accepted(self, tmp_path):
        from unittest.mock import MagicMock
        from scraper_engine import _StateDB, DEFAULT_SITE_CONFIG
        # malware_scan_enabled=False: these tests exercise magic-byte/dedup,
        # not the scan gate (covered by the security suite, which needs a
        # host with Defender active).
        e = _engine(use_relevance_filter=False, min_pdf_size_bytes=4,
                    malware_scan_enabled=False)
        session = MagicMock()
        resp = MagicMock()
        resp.headers = {"content-type": "application/pdf"}
        resp.history = []
        resp.iter_content.return_value = iter([b"%PDF-1.4 " + b"x" * 600])
        session.get.return_value = resp
        session.head.return_value = MagicMock(headers={})
        db = _StateDB(str(tmp_path / "state.db"))
        cfg = dict(DEFAULT_SITE_CONFIG, delay=0)
        e._download_pdf("https://example.com/doc.pdf", str(tmp_path), "ACME",
                        "", "example.com", session, db, cfg)
        assert (tmp_path / "doc.pdf").exists()
        db.close()

    def test_duplicate_content_removed(self, tmp_path):
        from unittest.mock import MagicMock
        from scraper_engine import _StateDB, DEFAULT_SITE_CONFIG
        e = _engine(use_relevance_filter=False, min_pdf_size_bytes=4,
                    malware_scan_enabled=False)
        db = _StateDB(str(tmp_path / "state.db"))
        cfg = dict(DEFAULT_SITE_CONFIG, delay=0)
        payload = b"%PDF-1.4 " + b"x" * 600
        for name in ("a.pdf", "b.pdf"):
            session = MagicMock()
            resp = MagicMock()
            resp.headers = {"content-type": "application/pdf"}
            resp.history = []
            resp.iter_content.return_value = iter([payload])
            session.get.return_value = resp
            session.head.return_value = MagicMock(headers={})
            e._download_pdf(f"https://example.com/{name}", str(tmp_path), "ACME",
                            "", "example.com", session, db, cfg)
        assert (tmp_path / "a.pdf").exists()
        assert not (tmp_path / "b.pdf").exists()  # same bytes, second copy dropped
        db.close()


class TestCsvVendorGuardrail:
    def _run_with(self, tmp_path, keywords):
        import pandas as pd
        from unittest.mock import patch
        excel = tmp_path / "suppliers.xlsx"
        pd.DataFrame({
            "Supplier Name": ["ACME", "GHOST VENDOR"],
            "Website": ["https://acme.example.com", "https://ghost.example.com"],
        }).to_excel(excel, index=False)
        e = _engine(supplier_keywords=keywords, skip_recent_sites=False)
        with patch.object(e, "_domain_worker") as worker:
            e.run(str(excel), str(tmp_path))
            crawled = {name for call in worker.call_args_list
                       for name, _ in call.args[1]}
        return crawled

    def test_vendor_not_in_csv_is_not_crawled(self, tmp_path):
        crawled = self._run_with(tmp_path, {"acme": ["microscope"]})
        assert crawled == {"ACME"}

    def test_no_keywords_loaded_crawls_all(self, tmp_path):
        # standalone use without CSV keywords: guardrail off
        crawled = self._run_with(tmp_path, {})
        assert crawled == {"ACME", "GHOST VENDOR"}


class TestKeywordTokenizer:
    def test_drops_bare_short_numbers(self):
        tokens = _extract_keyword_tokens("2 ML TUBE RACK MODEL 10")
        assert "2" not in tokens and "10" not in tokens
        assert "tube" in tokens and "rack" in tokens

    def test_keeps_real_part_numbers(self):
        tokens = _extract_keyword_tokens("Laser 920-2 controller")
        assert "9202" in tokens  # hyphen-stripped variant, 4+ digits
        assert "laser" in tokens

    def test_drops_short_alpha(self):
        assert "ml" not in _extract_keyword_tokens("50 ml conical")
