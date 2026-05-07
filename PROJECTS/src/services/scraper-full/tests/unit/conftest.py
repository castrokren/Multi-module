"""
Scraper-full service specific fixtures.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

# Add parent service directory to path
service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))


@pytest.fixture
def scraper_config():
    """Base configuration for ScraperEngine."""
    return {
        'max_concurrent': 2,
        'request_delay': 1.0,
        'page_timeout': 10,
        'max_pages_per_site': 20,
        'max_pdf_size_mb': 50,
        'min_pdf_size_bytes': 256,
        'strict_content_validation': False,
        'verbose': False,
        'batch_size': 5
    }


@pytest.fixture
def sample_robots_txt():
    """Sample robots.txt content."""
    return """User-agent: *
Disallow: /admin/
Disallow: /private/
Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-products.xml
"""


@pytest.fixture
def sample_sitemap_xml():
    """Sample XML sitemap content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
        <lastmod>2024-01-15</lastmod>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
        <lastmod>2024-01-14</lastmod>
    </url>
    <url>
        <loc>https://example.com/downloads/product.pdf</loc>
        <lastmod>2024-01-13</lastmod>
    </url>
</urlset>
"""


@pytest.fixture
def sample_html_with_pdf_links():
    """Sample HTML page with PDF download links."""
    return """
    <html>
    <body>
        <h1>Product Resources</h1>
        <ul>
            <li><a href="https://example.com/downloads/product-sheet.pdf">Product Sheet</a></li>
            <li><a href="https://example.com/downloads/manual.pdf">User Manual</a></li>
            <li><a href="https://example.com/downloads/specifications.pdf">Specifications</a></li>
            <li><a href="https://example.com/page">Regular Page</a></li>
        </ul>
    </body>
    </html>
    """


@pytest.fixture
def mock_pdf_response():
    """Mock response object for PDF downloads."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {'Content-Type': 'application/pdf', 'Content-Length': '1024000'}
    response.content = b'%PDF-1.4\n%mock pdf content'
    response.url = 'https://example.com/document.pdf'
    return response
