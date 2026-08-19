"""Scraper-full unit test fixtures."""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_robots_txt():
    return (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Sitemap: https://example.com/sitemap.xml\n"
        "Sitemap: https://example.com/sitemap-products.xml\n"
    )


@pytest.fixture
def sample_sitemap_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://example.com/page1</loc></url>"
        "<url><loc>https://example.com/downloads/product-catalog.pdf</loc></url>"
        "<url><loc>https://example.com/downloads/terms-of-use.pdf</loc></url>"
        "</urlset>"
    )


@pytest.fixture
def sample_html_with_pdf_links():
    return (
        "<html><body>"
        '<a href="https://example.com/downloads/datasheet.pdf">Product Datasheet</a>'
        '<a href="https://example.com/downloads/privacy-policy.pdf">Privacy Policy</a>'
        '<a href="https://example.com/downloads/catalog.pdf">Catalog</a>'
        '<a href="https://example.com/page">Regular Page</a>'
        "</body></html>"
    )


@pytest.fixture
def mock_pdf_response():
    r = MagicMock()
    r.status_code = 200
    r.headers = {"Content-Type": "application/pdf", "Content-Length": "10240"}
    r.history = []
    r.iter_content.return_value = [b"%PDF-1.4 mock content" * 100]
    return r
