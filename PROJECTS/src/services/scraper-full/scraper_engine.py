"""
Headless Scraper Engine
=======================
Contains the core crawling logic extracted from pdf_crawler_gui_2.py so it
can be driven programmatically (e.g. from pipeline.py) without a GUI.

The public API is intentionally small:

    engine = ScraperEngine(config)
    engine.run(supplier_excel, output_dir)   # blocks until done / stopped
    engine.stop()                            # signal early stop from another thread

All user-visible output goes through the standard ``logging`` module.
"""

import os
import sys
import re
import time
import threading
import logging
import hashlib
import gc
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security helpers (mirrors the GUI module)
# ---------------------------------------------------------------------------

def _validate_url(url: str) -> bool:
    """Return True only for safe http/https URLs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        if "localhost" in parsed.netloc or "127.0.0.1" in parsed.netloc:
            return False
        return True
    except Exception:
        return False


def _sanitize_path(path: str) -> str:
    """Remove path-traversal and dangerous characters from a filename."""
    path = path.replace("..", "").replace("/", "_").replace("\\", "_")
    for ch in '<>:"|?*':
        path = path.replace(ch, "_")
    return path


def _file_hash(file_path: str) -> str | None:
    """SHA-256 hash of a file, or None on error."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Rate-limited HTTP adapter
# ---------------------------------------------------------------------------

class _RateLimitedAdapter(HTTPAdapter):
    def __init__(self, request_delay: float = 2.0, **kwargs):
        self._min_interval = request_delay
        self._last_request = 0.0
        super().__init__(**kwargs)

    def send(self, request, **kwargs):
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()
        return super().send(request, **kwargs)


# ---------------------------------------------------------------------------
# ScraperEngine
# ---------------------------------------------------------------------------

class ScraperEngine:
    """
    Headless crawler.  Reads a supplier list from an Excel file, crawls each
    supplier's website, and downloads PDFs to ``output_dir/<Supplier Name>/``.

    Parameters
    ----------
    max_concurrent : int
        Maximum simultaneous crawl threads.
    request_delay : float
        Minimum seconds between HTTP requests (politeness).
    page_timeout : int
        HTTP request timeout in seconds.
    max_pages_per_site : int
        Hard cap on pages visited per supplier.
    max_pdf_size_mb : int
        PDFs larger than this are skipped.
    min_pdf_size_bytes : int
        PDFs smaller than this are deleted after download.
    strict_content_validation : bool
        When True, skip URLs whose Content-Type does not contain 'pdf'.
    verbose : bool
        Log every page visit (noisy but useful for debugging).
    batch_size : int
        Number of suppliers processed per batch before gc.collect().
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        request_delay: float = 2.0,
        page_timeout: int = 15,
        max_pages_per_site: int = 50,
        max_pdf_size_mb: int = 100,
        min_pdf_size_bytes: int = 512,
        strict_content_validation: bool = False,
        verbose: bool = False,
        batch_size: int = 10,
    ):
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self.page_timeout = page_timeout
        self.max_pages_per_site = max_pages_per_site
        self.max_pdf_size_mb = max_pdf_size_mb
        self.min_pdf_size_bytes = min_pdf_size_bytes
        self.strict_content_validation = strict_content_validation
        self.verbose = verbose
        self.batch_size = batch_size

        self._stop_event = threading.Event()
        self.page_count = 0
        self.pdf_count = 0
        self.session = self._create_session()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def stop(self):
        """Signal the engine to stop after the current download finishes."""
        self._stop_event.set()

    @property
    def running(self) -> bool:
        return not self._stop_event.is_set()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, supplier_excel: str, output_dir: str) -> dict:
        """
        Crawl all suppliers listed in *supplier_excel* and save PDFs to
        *output_dir*.

        The Excel file must have at minimum two columns:
            - ``Supplier Name``
            - ``Website``

        Returns a summary dict with keys ``pages``, ``pdfs``, ``suppliers``.
        """
        self._stop_event.clear()
        self.page_count = 0
        self.pdf_count = 0

        output_dir = str(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Load supplier list
        pairs = self._load_supplier_pairs(supplier_excel)
        if not pairs:
            logger.warning("No suppliers with valid websites found in %s", supplier_excel)
            return {"pages": 0, "pdfs": 0, "suppliers": 0}

        logger.info("Starting crawl: %d suppliers, batch_size=%d, max_concurrent=%d",
                    len(pairs), self.batch_size, self.max_concurrent)

        completed = 0
        _lock = threading.Lock()

        for batch_start in range(0, len(pairs), self.batch_size):
            if not self.running:
                break

            batch = pairs[batch_start : batch_start + self.batch_size]
            batch_num = batch_start // self.batch_size + 1
            total_batches = (len(pairs) + self.batch_size - 1) // self.batch_size
            logger.info("Batch %d/%d — suppliers %d-%d",
                        batch_num, total_batches,
                        batch_start + 1, batch_start + len(batch))

            semaphore = threading.Semaphore(self.max_concurrent)
            threads = []

            def _crawl(supplier, url):
                try:
                    semaphore.acquire()
                    self.crawl_site(supplier, url, output_dir)
                except Exception as exc:
                    logger.error("Unexpected error crawling %s: %s", supplier, exc)
                finally:
                    semaphore.release()
                    nonlocal completed
                    with _lock:
                        completed += 1
                    logger.info("Progress: %d/%d suppliers done", completed, len(pairs))

            for supplier, url in batch:
                if not self.running:
                    break
                t = threading.Thread(target=_crawl, args=(supplier, url), daemon=True)
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=300)
                if t.is_alive():
                    logger.warning("Thread timeout — a supplier in this batch is still running")

            if self.running:
                logger.info("Batch %d/%d complete", batch_num, total_batches)
            gc.collect()

        summary = {"pages": self.page_count, "pdfs": self.pdf_count, "suppliers": completed}
        logger.info("Crawl finished — pages=%d  pdfs=%d  suppliers=%d",
                    summary["pages"], summary["pdfs"], summary["suppliers"])
        return summary

    # ------------------------------------------------------------------
    # Crawling methods (adapted from PDFCrawlerEnhancedApp)
    # ------------------------------------------------------------------

    def crawl_site(self, supplier: str, url: str, output_dir: str):
        """Crawl a single vendor site, downloading all PDFs found."""
        if not self.running:
            return

        logger.info("Starting crawl: %s  %s", supplier, url)
        vendor_folder = os.path.join(output_dir, supplier)
        os.makedirs(vendor_folder, exist_ok=True)

        supplier_visited: set[str] = set()

        try:
            success = self._intelligent_crawling(url, supplier, vendor_folder, supplier_visited)
            if not success:
                logger.info("Falling back to recursive crawl for %s", supplier)
                self.crawl_url_recursive(url, vendor_folder, supplier, visited_set=supplier_visited)

            logger.info("Finished %s — %d pages visited", supplier, len(supplier_visited))
        except Exception as exc:
            logger.error("Failed to crawl %s: %s", supplier, exc)

    def _intelligent_crawling(
        self, url: str, supplier: str, vendor_folder: str, supplier_visited: set
    ) -> bool:
        """Try robots.txt / sitemap crawling first; return True if it produced PDFs."""
        try:
            robots_url = urljoin(url, "/robots.txt")
            logger.debug("Checking robots.txt for %s", supplier)
            try:
                resp = self.session.get(robots_url, timeout=10)
                if resp.status_code == 200:
                    sitemap_urls = self._extract_sitemap_urls(resp.text, url)
                    if sitemap_urls:
                        logger.info("Found %d sitemap(s) for %s", len(sitemap_urls), supplier)
                        return self._crawl_via_sitemap(sitemap_urls, supplier, vendor_folder, supplier_visited)
            except Exception as exc:
                logger.debug("Could not read robots.txt for %s: %s", supplier, exc)

            return False
        except Exception as exc:
            logger.warning("Intelligent crawling failed for %s: %s", supplier, exc)
            return False

    def _extract_sitemap_urls(self, robots_content: str, base_url: str) -> list[str]:
        """Pull Sitemap: lines out of robots.txt."""
        urls = []
        for line in robots_content.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                urls.append(urljoin(base_url, sitemap_url))
        return urls

    def _crawl_via_sitemap(
        self, sitemap_urls: list, supplier: str, vendor_folder: str, supplier_visited: set
    ) -> bool:
        """Download all PDFs referenced in the sitemaps; return True if any found."""
        pdf_urls = []
        for sitemap_url in sitemap_urls:
            if not self.running:
                break
            try:
                resp = self.session.get(sitemap_url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, "xml")
                for loc in soup.find_all("loc"):
                    href = (loc.text or "").strip()
                    if href.lower().endswith(".pdf"):
                        pdf_urls.append(href)
                    elif len(supplier_visited) < self.max_pages_per_site:
                        supplier_visited.add(href)
                logger.debug("Sitemap %s — %d PDF(s) found", sitemap_url, len(pdf_urls))
            except Exception as exc:
                logger.warning("Failed to read sitemap %s: %s", sitemap_url, exc)

        for pdf_url in pdf_urls:
            if not self.running:
                break
            self.download_pdf(pdf_url, vendor_folder, supplier)

        if pdf_urls:
            logger.info("Sitemap crawl: %d PDF(s) for %s", len(pdf_urls), supplier)
            return True
        return False

    def crawl_url_recursive(
        self,
        url: str,
        vendor_folder: str,
        supplier: str,
        visited_set: set | None = None,
        depth: int = 0,
        max_depth: int = 2,
    ):
        """Recursively follow links, downloading any PDFs encountered."""
        if visited_set is None:
            visited_set = set()

        if not self.running or depth > max_depth or url in visited_set:
            return
        if not _validate_url(url):
            logger.warning("Blocked unsafe URL: %s", url)
            return
        if len(visited_set) >= self.max_pages_per_site:
            logger.warning("Page limit reached for %s, stopping", supplier)
            return

        visited_set.add(url)
        self.page_count += 1

        try:
            time.sleep(self.request_delay)
            if self.verbose:
                logger.debug("Visiting: %s (depth %d)", url, depth)

            resp = self.session.get(url, timeout=self.page_timeout)
            resp.raise_for_status()

            if url.lower().endswith(".pdf"):
                self.download_pdf(url, vendor_folder, supplier)
                return

            soup = BeautifulSoup(resp.content, "html.parser")
            pdf_links, other_links = [], []

            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                if not href or href.startswith(("#", "mailto:", "tel:")):
                    continue
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc != urlparse(url).netloc:
                    continue
                if full_url.lower().endswith(".pdf"):
                    pdf_links.append(full_url)
                elif depth < max_depth and full_url not in visited_set:
                    other_links.append(full_url)

            for pdf_url in pdf_links:
                if not self.running:
                    return
                self.download_pdf(pdf_url, vendor_folder, supplier)

            for link_url in other_links[:10]:
                if not self.running:
                    return
                self.crawl_url_recursive(link_url, vendor_folder, supplier, visited_set, depth + 1, max_depth)

        except requests.exceptions.Timeout:
            logger.warning("Timeout crawling %s", url)
        except requests.exceptions.RequestException as exc:
            logger.warning("Request failed for %s: %s", url, exc)
        except Exception as exc:
            logger.error("Error crawling %s: %s", url, exc)

    def download_pdf(self, pdf_url: str, vendor_folder: str, supplier: str):
        """Download one PDF, enforcing size limits and integrity checks."""
        if not self.running:
            return
        if not _validate_url(pdf_url):
            logger.warning("Blocked unsafe PDF URL: %s", pdf_url)
            return

        filename = _sanitize_path(os.path.basename(urlparse(pdf_url).path))
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        if not filename or len(filename) < 5:
            filename = f"document_{int(time.time())}.pdf"

        file_path = os.path.join(vendor_folder, filename)
        if os.path.exists(file_path):
            if self.verbose:
                logger.debug("Already downloaded: %s", filename)
            return

        try:
            resp = self.session.get(pdf_url, timeout=self.page_timeout, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            content_length = resp.headers.get("content-length")
            max_bytes = self.max_pdf_size_mb * 1024 * 1024

            if content_length and int(content_length) > max_bytes:
                logger.warning("Skipping oversized PDF (%.1f MB): %s",
                               int(content_length) / (1024 * 1024), pdf_url)
                return
            if self.strict_content_validation and "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
                logger.warning("Skipping non-PDF content-type: %s", pdf_url)
                return

            downloaded = 0
            with open(file_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if not self.running:
                        fh.close()
                        os.remove(file_path)
                        return
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        fh.close()
                        os.remove(file_path)
                        logger.warning("Removed oversized download: %s", pdf_url)
                        return
                    fh.write(chunk)

            if os.path.getsize(file_path) < self.min_pdf_size_bytes:
                os.remove(file_path)
                logger.warning("Removed undersized PDF (%d bytes): %s",
                               os.path.getsize(file_path) if os.path.exists(file_path) else 0, filename)
                return

            self.pdf_count += 1
            logger.info("Downloaded: %s/%s (%.1f MB)",
                        supplier, filename, os.path.getsize(file_path) / (1024 * 1024))

        except requests.exceptions.Timeout:
            logger.warning("Timeout downloading %s", pdf_url)
        except requests.exceptions.RequestException as exc:
            logger.warning("Download failed for %s: %s", pdf_url, exc)
        except Exception as exc:
            logger.error("Error downloading %s: %s", pdf_url, exc)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_session(self) -> requests.Session:
        """Build a polite, retry-equipped requests session."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504, 522, 524],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = _RateLimitedAdapter(
            request_delay=self.request_delay,
            max_retries=retry,
            pool_connections=20,
            pool_maxsize=20,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.verify = True
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
        })
        return session

    def _load_supplier_pairs(self, supplier_excel: str) -> list[tuple[str, str]]:
        """Read supplier name + website pairs from an Excel file."""
        try:
            df = pd.read_excel(supplier_excel)
        except Exception as exc:
            logger.error("Cannot read supplier list %s: %s", supplier_excel, exc)
            return []

        # Flexible column detection
        name_col = next((c for c in df.columns if "supplier" in c.lower() and "name" in c.lower()), None)
        url_col  = next((c for c in df.columns if c.lower() in ("website", "url", "web", "site")), None)

        if not name_col or not url_col:
            logger.error("Supplier Excel must have 'Supplier Name' and 'Website' columns. Found: %s",
                         list(df.columns))
            return []

        pairs = []
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            url  = str(row[url_col]).strip()
            if name and url and url.lower() not in ("nan", "none", ""):
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                if _validate_url(url):
                    pairs.append((name, url))
                else:
                    logger.warning("Invalid URL skipped for %s: %s", name, url)

        logger.info("Loaded %d valid supplier(s) from %s", len(pairs), supplier_excel)
        return pairs
