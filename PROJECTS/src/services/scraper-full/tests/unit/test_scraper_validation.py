"""Unit tests for URL validation, path sanitisation, file hashing, and relevance filtering."""
import hashlib, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scraper_engine import _validate_url, _sanitize_path, _file_hash, _score_pdf_relevance, _same_site


class TestValidateUrl:
    def test_valid_https(self):
        assert _validate_url("https://www.example.com") is True
        assert _validate_url("https://example.com/path/file.pdf") is True

    def test_valid_http(self):
        assert _validate_url("http://example.com") is True

    def test_blocks_ftp(self):
        assert _validate_url("ftp://example.com") is False

    def test_blocks_file(self):
        assert _validate_url("file:///etc/passwd") is False

    def test_blocks_javascript(self):
        assert _validate_url("javascript:alert(1)") is False

    def test_blocks_localhost(self):
        assert _validate_url("http://localhost") is False
        assert _validate_url("http://localhost:8080") is False

    def test_blocks_loopback(self):
        assert _validate_url("http://127.0.0.1") is False

    def test_blocks_no_scheme(self):
        assert _validate_url("example.com") is False

    def test_blocks_empty(self):
        assert _validate_url("") is False

    def test_blocks_scheme_only(self):
        assert _validate_url("https://") is False


class TestSanitizePath:
    def test_removes_path_traversal(self):
        r = _sanitize_path("../../../etc/passwd")
        assert ".." not in r and "/" not in r

    def test_replaces_forward_slash(self):
        assert "/" not in _sanitize_path("path/to/file.pdf")

    def test_replaces_backslash(self):
        assert "\\" not in _sanitize_path("path\\to\\file.pdf")

    def test_replaces_dangerous_chars(self):
        for ch in '<>:"|?*':
            assert ch not in _sanitize_path(f"file{ch}name.pdf")

    def test_normal_filename_unchanged(self):
        name = "product-catalog_2024.pdf"
        assert _sanitize_path(name) == name


class TestFileHash:
    def test_correct_sha256(self, temp_output_dir):
        p = Path(temp_output_dir) / "t.bin"
        content = b"hello world"
        p.write_bytes(content)
        assert _file_hash(str(p)) == hashlib.sha256(content).hexdigest()

    def test_nonexistent_returns_none(self):
        assert _file_hash("/no/such/file.pdf") is None

    def test_empty_file(self, temp_output_dir):
        p = Path(temp_output_dir) / "empty.bin"
        p.write_bytes(b"")
        assert _file_hash(str(p)) == hashlib.sha256(b"").hexdigest()

    def test_consistent(self, temp_output_dir):
        p = Path(temp_output_dir) / "stable.bin"
        p.write_bytes(b"stable content")
        assert _file_hash(str(p)) == _file_hash(str(p))


class TestRelevanceFilter:
    @pytest.mark.parametrize("url", [
        "https://acme.com/terms-of-use.pdf",
        "https://acme.com/privacy_policy.pdf",
        "https://acme.com/cookie-policy.pdf",
        "https://acme.com/warranty.pdf",
        "https://acme.com/return_policy.pdf",
        "https://acme.com/invoice_2024.pdf",
        "https://acme.com/receipt_march.pdf",
        "https://acme.com/purchase_order.pdf",
        "https://acme.com/msds/chemical.pdf",
        "https://acme.com/sds-sheet.pdf",
        "https://acme.com/safety_data.pdf",
        "https://acme.com/annual-report-2023.pdf",
        "https://acme.com/nda.pdf",
        "https://acme.com/legal-disclaimer.pdf",
    ])
    def test_blocklist_url(self, url):
        ok, reason = _score_pdf_relevance(url)
        assert ok is False and reason == "blocklist_match"

    def test_blocklist_via_anchor(self):
        ok, _ = _score_pdf_relevance("https://acme.com/doc.pdf", "Terms of Service")
        assert ok is False

    @pytest.mark.parametrize("url", [
        "https://acme.com/product-catalog.pdf",
        "https://acme.com/datasheet-model-x.pdf",
        "https://acme.com/data_sheet.pdf",
        "https://acme.com/specifications.pdf",
        "https://acme.com/install-guide.pdf",
        "https://acme.com/user-manual.pdf",
        "https://acme.com/price-list-2024.pdf",
        "https://acme.com/parts-list.pdf",
        "https://acme.com/product-brochure.pdf",
        "https://acme.com/technical-bulletin.pdf",
        "https://acme.com/selection-guide.pdf",
    ])
    def test_allowlist_url(self, url):
        ok, reason = _score_pdf_relevance(url)
        assert ok is True and reason == "allowlist_match"

    def test_allowlist_via_anchor(self):
        ok, reason = _score_pdf_relevance("https://acme.com/doc123.pdf", "Download Datasheet")
        assert ok is True and reason == "allowlist_match"

    def test_default_allow_ambiguous(self):
        ok, reason = _score_pdf_relevance("https://acme.com/doc_12345.pdf", "")
        assert ok is True and reason == "default_allow"

    def test_blocklist_beats_allowlist_anchor(self):
        ok, _ = _score_pdf_relevance("https://acme.com/invoice.pdf", "product catalog")
        assert ok is False


class TestSameSite:
    def test_exact_host_match(self):
        assert _same_site("https://acme.com/doc.pdf", "acme.com") is True

    def test_subdomain_is_same_site(self):
        assert _same_site("https://cdn.acme.com/doc.pdf", "acme.com") is True
        assert _same_site("https://docs.assets.acme.com/doc.pdf", "acme.com") is True

    def test_www_prefix_ignored_both_directions(self):
        assert _same_site("https://www.acme.com/doc.pdf", "acme.com") is True
        assert _same_site("https://acme.com/doc.pdf", "www.acme.com") is True

    def test_rejects_unrelated_domain(self):
        assert _same_site("https://evil.com/doc.pdf", "acme.com") is False

    def test_rejects_domain_as_substring_only(self):
        # "acme.com" appears in the string but is not the actual host -
        # a naive `"acme.com" in url` check would wrongly allow this.
        assert _same_site("https://evil.com/acme.com/doc.pdf", "acme.com") is False
        assert _same_site("https://acme.com.evil.com/doc.pdf", "acme.com") is False

    def test_rejects_lookalike_suffix(self):
        # "notacme.com" ends with "acme.com" as a raw string but is a
        # different registrable domain.
        assert _same_site("https://notacme.com/doc.pdf", "acme.com") is False

    def test_allowed_hosts_override(self):
        assert _same_site("https://cdn.other-host.com/doc.pdf", "acme.com") is False
        assert _same_site(
            "https://cdn.other-host.com/doc.pdf", "acme.com",
            allowed_hosts=("cdn.other-host.com",),
        ) is True

    def test_invalid_url_rejected(self):
        assert _same_site("not a url", "acme.com") is False
