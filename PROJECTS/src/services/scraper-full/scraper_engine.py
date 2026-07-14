"""
Headless Scraper Engine
=======================
Crawls ~50 supplier websites and downloads product PDFs.

Architecture
------------
- Per-domain queues: one worker thread per domain, serialising requests
  within a domain while all domains crawl concurrently.  This respects
  each site's rate limit without throttling unrelated sites.
- Sitemap-first discovery: robots.txt -> /sitemap.xml fallbacks before
  any link-walking.  Many suppliers list their PDFs directly.
- Search-based fallback: ``site:<domain> filetype:pdf`` via DuckDuckGo /
  Bing HTML interface - never touches the target site's own search box.
- Dedup + resume: SQLite tracks seen URLs and downloaded files so a
  restart skips completed work.
- Per-site config: optional JSON file lets you tune delay, max pages,
  or disable recursive crawl on a per-domain basis without code changes.
- Relevance filtering: blocklist skips obviously irrelevant PDFs (terms,
  invoices, SDS sheets, etc.).  Allowlist-only mode restricts to
  product docs (catalog, datasheet, spec, manual...).

Scope: Stage 1 (discovery + fetch) only.
       Classification (Stage 2) and cross-reference (Stage 3) are untouched.

Public API
----------
    engine = ScraperEngine(config)
    engine.run(supplier_excel, output_dir)   # blocks until done / stopped
    engine.stop()                            # signal early stop
"""

import gc
import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional web_searcher (search-based PDF discovery)
# ---------------------------------------------------------------------------
try:
    import sys as _sys, os as _os
    _sys.path.insert(
        0,
        _os.path.join(_os.path.dirname(os.path.abspath(__file__)), "..", "supplier-resolution"),
    )
    from web_searcher import search_duckduckgo, search_bing
    _HAS_WEB_SEARCHER = True
except ImportError:
    _HAS_WEB_SEARCHER = False

# ---------------------------------------------------------------------------
# Keyword-based filtering + Camofox integration
# ---------------------------------------------------------------------------
_HARDWARE_KEYWORDS_FILE = r"C:\Data\Crawler\labeled\hardware_keywords_ACTIVE.txt"
_SOFTWARE_KEYWORDS_FILE = r"C:\Data\Crawler\labeled\software_keywords_ACTIVE.txt"
_CAMOFOX_API = "http://localhost:8000"  # Local camofox server (default port)
_HAS_CAMOFOX = False
_KEYWORDS_ACTIVE = set()


def _load_keywords() -> set:
    """Load hardware + software keywords from files."""
    keywords = set()
    for fpath in [_HARDWARE_KEYWORDS_FILE, _SOFTWARE_KEYWORDS_FILE]:
        if os.path.exists(fpath):
            try:
                with open(fpath, encoding="utf-8") as f:
                    for line in f:
                        kw = line.strip()
                        if kw and not kw.startswith("#"):
                            keywords.add(kw.lower())
            except Exception as exc:
                logger.warning("Could not load keywords from %s: %s", fpath, exc)
    logger.info("Loaded %d keywords for supplier filtering", len(keywords))
    return keywords


def _check_page_keywords(url: str, keywords: set, timeout: int = 15) -> bool:
    """
    Use camofox to load the page and check if it contains any keywords.
    Returns True if ≥1 keyword found, False otherwise.
    """
    if not keywords:
        return True  # No filter = allow all
    try:
        resp = requests.post(
            f"{_CAMOFOX_API}/api/browse",
            json={"url": url},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            snapshot = data.get("snapshot", "").lower()
            found = [kw for kw in keywords if kw in snapshot]
            if found:
                logger.info("[%s] Found keywords: %s", urlparse(url).netloc, ", ".join(found[:3]))
                return True
            else:
                logger.info("[%s] No relevant keywords on page", urlparse(url).netloc)
                return False
        else:
            logger.warning("Camofox returned %d for %s", resp.status_code, url)
            return True  # Fallback: allow if camofox fails
    except requests.exceptions.ConnectionError:
        logger.warning("Camofox not running at %s - skipping keyword filter", _CAMOFOX_API)
        return True  # Fallback: allow if camofox unavailable
    except Exception as exc:
        logger.warning("Camofox error for %s: %s", url, exc)
        return True  # Fallback: allow on error

# ---------------------------------------------------------------------------
# PDF relevance filtering
# ---------------------------------------------------------------------------

_PDF_BLOCKLIST = re.compile(
    r"(terms[_\-\s]?of[_\-\s]?(use|service)|privacy[_\-\s]?policy|cookie[_\-\s]?policy"
    r"|warranty|return[_\-\s]?policy|refund|invoice|receipt|purchase[_\-\s]?order"
    r"|msds|sds|safety[_\-\s]?data|material[_\-\s]?safety"
    r"|annual[_\-\s]?report|financial[_\-\s]?report|10\-?k|10\-?q"
    r"|press[_\-\s]?release|newsletter|whitepaper|case[_\-\s]?study"
    r"|compliance|regulatory|iso[_\-\s]?cert|certificate[_\-\s]?of"
    r"|nda|agreement|contract|legal|disclaimer"
    r"|map|directions|parking|exhibit[_\-\s]?hall"
    # HR / corporate: these carry the vendor's brand and words like "guide"
    # or "brochure", so the allowlist waves them through otherwise.
    r"|career|careers|candidate|recruit|job[_\-\s]?(description|posting)"
    r"|working[_\-\s]?at|employee|benefits[_\-\s]?(guide|summary)"
    r"|onboarding|code[_\-\s]?of[_\-\s]?conduct|esg|sustainability"
    r"|investor|annual[_\-\s]?meeting|proxy"
    r"|irs|tax|form[_\-\s]?(w2|1040|1099|941|940|990|k1|ct[_\-]?1)"
    r"|w\-?2|1099|941|940|990|k\-?1|ct[_\-]?1"
    r"|earnings|payroll|deduction|withhold|federal|state[_\-\s]?tax)",
    re.IGNORECASE,
)

_PDF_ALLOWLIST = re.compile(
    r"(catalog|catalogue|datasheet|data[_\-]?sheet|spec(ification)?s?"
    r"|product[_\-]?(guide|list|range|brochure|sheet|info|overview)"
    r"|price[_\-]?list|pricelist|part[_\-]?list|parts[_\-]?list"
    r"|technical|install(ation)?|manual|guide|brochure|ifu|instructions?"
    r"|accessory|accessories|selection[_\-]?guide"
    r"|flyer|bulletin|literature|resource|quickstart|quick[_\-]?start"
    r"|user[_\-]?guide|reference[_\-]?guide|operator[_\-]?manual"
    r"|service[_\-]?manual|maintenance|setup|configuration"
    r"|protocol|application[_\-]?note|app[_\-]?note|tech[_\-]?note)",
    re.IGNORECASE,
)


def _score_pdf_relevance(url: str, anchor_text: str = "") -> tuple[bool, str]:
    """Return (should_download, reason). Checked before any network request."""
    combined = f"{url} {anchor_text}".lower()
    if _PDF_BLOCKLIST.search(combined):
        return False, "blocklist_match"
    if _PDF_ALLOWLIST.search(combined):
        return True, "allowlist_match"
    return True, "default_allow"


def _keywords_match(keywords, text: str) -> bool:
    """True if any keyword hits ``text`` (pre-normalized, space-separated).

    ponytail: short tokens ("kit", "lab", "1064") need exact-word match;
    substring only for 5+ chars ("microscope" matches "microscopes").
    """
    words = set(text.split())
    return any((kw in text) if len(kw) >= 5 else (kw in words) for kw in keywords)


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

def _validate_url(url: str) -> bool:
    try:
        p = urlparse(url)
        host = p.netloc.split(":")[0]  # strip port if present
        return (
            p.scheme in ("http", "https")
            and bool(host)
            and "." in host          # require at least one dot (real domain)
            and "localhost" not in host
            and "127.0.0.1" not in host
        )
    except Exception:
        return False


def _sanitize_path(path: str) -> str:
    path = path.replace("..", "").replace("/", "_").replace("\\", "_")
    for ch in '<>:"|?*':
        path = path.replace(ch, "_")
    return path


def _file_hash(file_path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-domain rate limiter
# ---------------------------------------------------------------------------

class _DomainRateLimiter:
    """Thread-safe per-domain delay enforcement."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}

    def wait(self, domain: str, delay: float) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last.get(domain, 0.0)
            gap = delay - elapsed
        if gap > 0:
            time.sleep(gap)
        with self._lock:
            self._last[domain] = time.monotonic()


# ---------------------------------------------------------------------------
# State DB (dedup + resume)
# ---------------------------------------------------------------------------

class _StateDB:
    """
    SQLite-backed dedup and resume store.

    Tables:
      seen_urls  (url TEXT PRIMARY KEY, status TEXT, ts TEXT)
      downloaded (path TEXT PRIMARY KEY, url TEXT, supplier TEXT, ts TEXT)
    """

    def __init__(self, db_path: str):
        self._path = db_path
        self._local = threading.local()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_schema(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS seen_urls (
                url     TEXT PRIMARY KEY,
                status  TEXT,
                ts      TEXT
            );
            CREATE TABLE IF NOT EXISTS downloaded (
                path     TEXT PRIMARY KEY,
                url      TEXT,
                supplier TEXT,
                ts       TEXT
            );
            CREATE TABLE IF NOT EXISTS hashes (
                hash TEXT PRIMARY KEY
            );
        """)
        c.commit()

    def is_seen(self, url: str) -> bool:
        row = self._conn().execute(
            "SELECT 1 FROM seen_urls WHERE url=?", (url,)
        ).fetchone()
        return row is not None

    def mark_seen(self, url: str, status: str = "queued"):
        try:
            self._conn().execute(
                "INSERT OR IGNORE INTO seen_urls(url,status,ts) VALUES(?,?,?)",
                (url, status, datetime.utcnow().isoformat()),
            )
            self._conn().commit()
        except Exception:
            pass

    def update_status(self, url: str, status: str):
        try:
            self._conn().execute(
                "UPDATE seen_urls SET status=?,ts=? WHERE url=?",
                (status, datetime.utcnow().isoformat(), url),
            )
            self._conn().commit()
        except Exception:
            pass

    def is_downloaded(self, path: str) -> bool:
        row = self._conn().execute(
            "SELECT 1 FROM downloaded WHERE path=?", (path,)
        ).fetchone()
        return row is not None

    def mark_downloaded(self, path: str, url: str, supplier: str):
        try:
            self._conn().execute(
                "INSERT OR REPLACE INTO downloaded(path,url,supplier,ts) VALUES(?,?,?,?)",
                (path, url, supplier, datetime.utcnow().isoformat()),
            )
            self._conn().commit()
        except Exception:
            pass

    def is_hash_seen(self, file_hash: str) -> bool:
        row = self._conn().execute(
            "SELECT 1 FROM hashes WHERE hash=?", (file_hash,)
        ).fetchone()
        return row is not None

    def mark_hash(self, file_hash: str):
        try:
            self._conn().execute(
                "INSERT OR IGNORE INTO hashes(hash) VALUES(?)", (file_hash,)
            )
            self._conn().commit()
        except Exception:
            pass

    def close(self):
        if hasattr(self._local, "conn"):
            self._local.conn.close()


# ---------------------------------------------------------------------------
# Per-site config
# ---------------------------------------------------------------------------

DEFAULT_SITE_CONFIG = {
    "delay": 2.0,           # seconds between requests to this domain
    "max_pages": 50,        # hard cap on link-walk pages
    "max_pdfs_per_supplier": 50,  # hard cap on downloads per supplier; a run
                                  # past this means a generic keyword slipped
                                  # through, not 50+ relevant docs
    "use_sitemap": True,    # attempt sitemap discovery
    "use_search": True,     # attempt filetype:pdf search discovery
    "use_recursive": True,  # fall back to recursive link-walking
    "max_depth": 2,         # recursive crawl depth
}


def _load_site_configs(config_path: str | None) -> dict[str, dict]:
    """
    Load per-site overrides from a JSON file.  Example:

        {
          "example.com": {"delay": 5.0, "use_recursive": false},
          "slow-site.net": {"delay": 10.0, "max_pages": 20}
        }

    Any missing key falls back to DEFAULT_SITE_CONFIG.
    """
    if not config_path or not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not load site config %s: %s", config_path, exc)
        return {}


def _site_cfg(domain: str, overrides: dict[str, dict]) -> dict:
    """Merge per-site overrides onto the defaults."""
    base = dict(DEFAULT_SITE_CONFIG)
    base.update(overrides.get(domain, {}))
    return base


# ---------------------------------------------------------------------------
# HTTP session factory
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _make_session(timeout: int = 15) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# ---------------------------------------------------------------------------
# ScraperEngine
# ---------------------------------------------------------------------------

class ScraperEngine:
    """
    Parameters
    ----------
    page_timeout : int
        Per-request HTTP timeout (seconds).
    max_pdf_size_mb : int
        Skip PDFs larger than this.
    min_pdf_size_bytes : int
        Delete downloaded files smaller than this.
    strict_content_validation : bool
        Reject responses whose Content-Type is not PDF.
    verbose : bool
        Log every URL visited.
    skip_recent_sites : bool
        Skip suppliers crawled within days_before_rescrape days.
    days_before_rescrape : int
        Freshness window (default 7).
    use_relevance_filter : bool
        Apply blocklist filter before each download.
    allowlist_only : bool
        Only download PDFs matching the product-doc allowlist.
    site_config_path : str | None
        Path to per-domain JSON config (optional).
    """

    def __init__(
        self,
        page_timeout: int = 15,
        max_pdf_size_mb: int = 100,
        min_pdf_size_bytes: int = 512,
        strict_content_validation: bool = False,
        verbose: bool = False,
        skip_recent_sites: bool = True,
        days_before_rescrape: int = 7,
        use_relevance_filter: bool = True,
        allowlist_only: bool = False,
        site_config_path: str | None = None,
        use_keyword_filter: bool = True,
        supplier_keywords: dict[str, list[str]] | None = None,
    ):
        self.page_timeout = page_timeout
        self.max_pdf_size_mb = max_pdf_size_mb
        self.min_pdf_size_bytes = min_pdf_size_bytes
        self.strict_content_validation = strict_content_validation
        self.verbose = verbose
        self.skip_recent_sites = skip_recent_sites
        self.days_before_rescrape = days_before_rescrape
        self.use_relevance_filter = use_relevance_filter
        self.allowlist_only = allowlist_only
        self.use_keyword_filter = use_keyword_filter
        self.supplier_keywords = supplier_keywords or {}
        self._site_overrides = _load_site_configs(site_config_path)
        self.keywords = _load_keywords() if use_keyword_filter else set()

        self._stop_event = threading.Event()
        self._rate_limiter = _DomainRateLimiter()
        self.page_count = 0
        self.pdf_count = 0
        self._count_lock = threading.Lock()
        self._supplier_pdf_counts: Counter = Counter()
        self._warned_no_kw: set[str] = set()
        self._warned_pdf_cap: set[str] = set()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def stop(self):
        self._stop_event.set()

    @property
    def running(self) -> bool:
        return not self._stop_event.is_set()

    # ------------------------------------------------------------------
    # 7-day state (JSON, same as before)
    # ------------------------------------------------------------------

    def _scrape_state_path(self, output_dir: str) -> str:
        return os.path.join(output_dir, ".scraper_state.json")

    def _load_scrape_state(self, output_dir: str) -> dict:
        p = self._scrape_state_path(output_dir)
        if not os.path.exists(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_scrape_state(self, state: dict, output_dir: str):
        p = self._scrape_state_path(output_dir)
        tmp = p + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            if os.path.exists(p):
                os.remove(p)
            os.rename(tmp, p)
        except Exception as exc:
            logger.error("Could not save scrape state: %s", exc)

    def _is_due(self, name: str, state: dict) -> bool:
        if name not in state:
            return True
        try:
            last = datetime.fromisoformat(state[name])
            return (datetime.utcnow() - last).days >= self.days_before_rescrape
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Supplier loading
    # ------------------------------------------------------------------

    def _load_supplier_pairs(self, supplier_excel: str) -> list[tuple[str, str]]:
        try:
            df = pd.read_excel(supplier_excel, engine="openpyxl")
        except Exception as exc:
            logger.error("Cannot read %s: %s", supplier_excel, exc)
            return []

        df.columns = [str(c).strip() for c in df.columns]
        name_col = next(
            (c for c in df.columns if "supplier" in c.lower() and "name" in c.lower()),
            next((c for c in df.columns if "supplier" in c.lower()), None),
        )
        url_col = next(
            (c for c in df.columns if "website" in c.lower() or "url" in c.lower()),
            None,
        )
        if not name_col or not url_col:
            logger.error("Cannot find Supplier Name / Website columns in %s", supplier_excel)
            return []

        pairs = []
        for _, row in df.iterrows():
            name = str(row.get(name_col, "")).strip()
            url = str(row.get(url_col, "")).strip()
            if not name or name.lower() in ("nan", "", "none") or not url or url.lower() in ("nan", "", "none"):
                continue
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            if _validate_url(url):
                pairs.append((name, url))
            else:
                logger.warning("Invalid URL for %s: %s - skipping", name, url)

        logger.info("Loaded %d suppliers from %s", len(pairs), supplier_excel)
        return pairs

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, supplier_excel: str, output_dir: str) -> dict:
        """
        Crawl all suppliers.  Per-domain workers run concurrently; requests
        within each domain are serialised with the configured delay.
        """
        self._stop_event.clear()
        self.page_count = 0
        self.pdf_count = 0
        self._supplier_pdf_counts.clear()
        self._warned_pdf_cap.clear()

        output_dir = str(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        pairs = self._load_supplier_pairs(supplier_excel)
        if not pairs:
            logger.warning("No suppliers found in %s", supplier_excel)
            return {"pages": 0, "pdfs": 0, "suppliers": 0}

        # Guardrail: only crawl vendors that appear in the input CSVs.
        # No requisition rows = no keywords = nothing relevant to download.
        if self.supplier_keywords:
            dropped = sorted(n for n, _ in pairs if n.lower() not in self.supplier_keywords)
            if dropped:
                pairs = [(n, u) for n, u in pairs if n.lower() in self.supplier_keywords]
                logger.warning(
                    "Skipping %d supplier(s) with no rows in input CSVs: %s",
                    len(dropped), ", ".join(dropped),
                )
            if not pairs:
                logger.warning("No suppliers match input CSV vendors - nothing to crawl")
                return {"pages": 0, "pdfs": 0, "suppliers": 0}

        # 7-day freshness filter
        scrape_state = self._load_scrape_state(output_dir)
        original_count = len(pairs)
        if self.skip_recent_sites:
            pairs = [(n, u) for n, u in pairs if self._is_due(n, scrape_state)]
            skipped = original_count - len(pairs)
            if skipped:
                logger.info("Skipping %d supplier(s) scraped within %d days", skipped, self.days_before_rescrape)

        if not pairs:
            logger.info("All suppliers are up to date - nothing to crawl")
            return {"pages": 0, "pdfs": 0, "suppliers": 0}

        # Open shared dedup DB
        db_path = os.path.join(output_dir, ".scraper_dedup.db")
        state_db = _StateDB(db_path)

        logger.info(
            "Starting crawl: %d suppliers | relevance_filter=%s | allowlist_only=%s | web_searcher=%s",
            len(pairs), self.use_relevance_filter, self.allowlist_only, _HAS_WEB_SEARCHER,
        )

        # Group suppliers by domain so we build one worker per domain
        domain_map: dict[str, list[tuple[str, str]]] = {}
        for name, url in pairs:
            domain = urlparse(url).netloc
            domain_map.setdefault(domain, []).append((name, url))

        completed = 0
        completed_lock = threading.Lock()
        threads = []

        for domain, domain_pairs in domain_map.items():
            if not self.running:
                break
            cfg = _site_cfg(domain, self._site_overrides)
            t = threading.Thread(
                target=self._domain_worker,
                args=(domain, domain_pairs, output_dir, scrape_state, state_db, cfg,
                      completed_lock, lambda: None),
                daemon=True,
                name=f"worker-{domain}",
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=600)
            if t.is_alive():
                logger.warning("Domain worker %s timed out", t.name)
            with completed_lock:
                completed += 1
            logger.info("Progress: %d/%d domains done", completed, len(domain_map))

        # Save freshness state
        self._save_scrape_state(scrape_state, output_dir)
        state_db.close()

        summary = {"pages": self.page_count, "pdfs": self.pdf_count, "suppliers": len(pairs)}
        logger.info("Crawl finished - pages=%d  pdfs=%d  suppliers=%d",
                    summary["pages"], summary["pdfs"], summary["suppliers"])
        return summary

    # ------------------------------------------------------------------
    # Domain worker - serialises all requests for one domain
    # ------------------------------------------------------------------

    def _domain_worker(
        self,
        domain: str,
        pairs: list[tuple[str, str]],
        output_dir: str,
        scrape_state: dict,
        state_db: _StateDB,
        cfg: dict,
        completed_lock: threading.Lock,
        on_done,
    ):
        """One thread per domain.  Processes all suppliers on that domain in sequence."""
        session = _make_session(self.page_timeout)
        for supplier, url in pairs:
            if not self.running:
                break
            vendor_folder = os.path.join(output_dir, supplier)
            os.makedirs(vendor_folder, exist_ok=True)
            try:
                self._crawl_supplier(supplier, url, domain, vendor_folder,
                                     session, state_db, cfg)
                scrape_state[supplier] = datetime.utcnow().isoformat()
            except Exception as exc:
                logger.error("Unhandled error crawling %s: %s", supplier, exc)

    # ------------------------------------------------------------------
    # Per-supplier discovery chain
    # ------------------------------------------------------------------

    def _crawl_supplier(
        self,
        supplier: str,
        url: str,
        domain: str,
        vendor_folder: str,
        session: requests.Session,
        state_db: _StateDB,
        cfg: dict,
    ):
        """
        Discovery order (stops as soon as PDFs are found):
        1. robots.txt -> sitemap
        2. /sitemap.xml, /sitemap_index.xml (direct fallbacks)
        3. filetype:pdf search via DuckDuckGo / Bing
        4. Recursive link-walk (last resort)
        """
        logger.info("[%s] Starting - %s", supplier, url)

        # Keyword filter: check if page contains relevant keywords before crawling
        if self.use_keyword_filter and self.keywords:
            if not _check_page_keywords(url, self.keywords, self.page_timeout):
                logger.info("[%s] Skipping - no relevant keywords found", supplier)
                return

        found_any = False

        # 1 + 2 - sitemap
        if cfg["use_sitemap"]:
            pdf_urls = self._discover_via_sitemap(url, domain, session, cfg)
            if pdf_urls:
                for pdf_url in pdf_urls:
                    if not self.running:
                        return
                    self._download_pdf(pdf_url, vendor_folder, supplier, "",
                                       domain, session, state_db, cfg)
                found_any = True

        # 3 - search
        if not found_any and cfg["use_search"] and _HAS_WEB_SEARCHER:
            pdf_urls = self._discover_via_search(domain, supplier)
            if pdf_urls:
                for pdf_url in pdf_urls:
                    if not self.running:
                        return
                    self._download_pdf(pdf_url, vendor_folder, supplier, "",
                                       domain, session, state_db, cfg)
                found_any = True

        # 4 - recursive link-walk
        if not found_any and cfg["use_recursive"]:
            logger.info("[%s] Falling back to recursive crawl", supplier)
            visited: set[str] = set()
            self._crawl_recursive(url, vendor_folder, supplier, domain,
                                  session, state_db, cfg, visited, depth=0)

        logger.info("[%s] Done - total PDFs so far: %d", supplier, self.pdf_count)

    # ------------------------------------------------------------------
    # Discovery: sitemap
    # ------------------------------------------------------------------

    def _discover_via_sitemap(
        self, base_url: str, domain: str, session: requests.Session, cfg: dict
    ) -> list[str]:
        """
        Try robots.txt first, then common sitemap paths.
        Returns a flat list of PDF URLs found across all sitemaps.
        """
        sitemap_urls: list[str] = []

        # robots.txt
        try:
            self._rate_limiter.wait(domain, cfg["delay"])
            resp = session.get(urljoin(base_url, "/robots.txt"), timeout=10)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("sitemap:"):
                        sitemap_urls.append(line.split(":", 1)[1].strip())
        except Exception as exc:
            logger.debug("[%s] robots.txt: %s", domain, exc)

        # Common paths if robots.txt had none
        if not sitemap_urls:
            for path in ("/sitemap.xml", "/sitemap_index.xml"):
                try:
                    candidate = urljoin(base_url, path)
                    self._rate_limiter.wait(domain, cfg["delay"])
                    resp = session.get(candidate, timeout=10)
                    if resp.status_code == 200 and b"<loc>" in resp.content:
                        sitemap_urls.append(candidate)
                        logger.debug("[%s] Found sitemap at %s", domain, path)
                        break
                except Exception as exc:
                    logger.debug("[%s] No sitemap at %s: %s", domain, path, exc)

        if not sitemap_urls:
            return []

        pdf_urls: list[str] = []
        for sitemap_url in sitemap_urls:
            if not self.running:
                break
            try:
                self._rate_limiter.wait(domain, cfg["delay"])
                resp = session.get(sitemap_url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, "xml")
                for loc in soup.find_all("loc"):
                    href = (loc.text or "").strip()
                    if href.lower().endswith(".pdf"):
                        pdf_urls.append(href)
                logger.info("[%s] Sitemap %s -> %d PDF(s)", domain, sitemap_url, len(pdf_urls))
            except Exception as exc:
                logger.warning("[%s] Failed to parse sitemap %s: %s", domain, sitemap_url, exc)

        return pdf_urls

    # ------------------------------------------------------------------
    # Discovery: search engine
    # ------------------------------------------------------------------

    def _discover_via_search(self, domain: str, supplier: str) -> list[str]:
        """
        Query ``site:<domain> filetype:pdf`` via DuckDuckGo then Bing.
        Never touches the supplier's own site or search box.
        """
        query = f"site:{domain} filetype:pdf"
        pdf_urls: list[str] = []

        try:
            results = search_duckduckgo(query, timeout=10, max_results=30)
            pdf_urls = [r for r in results if r.lower().endswith(".pdf") and domain in r]
            logger.debug("[%s] DuckDuckGo: %d PDF(s)", supplier, len(pdf_urls))
        except Exception as exc:
            logger.debug("[%s] DuckDuckGo failed: %s", supplier, exc)

        if not pdf_urls:
            try:
                results = search_bing(query, timeout=10, max_results=30)
                pdf_urls = [r for r in results if r.lower().endswith(".pdf") and domain in r]
                logger.debug("[%s] Bing: %d PDF(s)", supplier, len(pdf_urls))
            except Exception as exc:
                logger.debug("[%s] Bing failed: %s", supplier, exc)

        return pdf_urls

    # ------------------------------------------------------------------
    # Discovery: recursive link-walk (last resort)
    # ------------------------------------------------------------------

    def _crawl_recursive(
        self,
        url: str,
        vendor_folder: str,
        supplier: str,
        domain: str,
        session: requests.Session,
        state_db: _StateDB,
        cfg: dict,
        visited: set,
        depth: int,
    ):
        max_depth = cfg["max_depth"]
        max_pages = cfg["max_pages"]

        if not self.running or depth > max_depth or url in visited:
            return
        if not _validate_url(url):
            return
        if len(visited) >= max_pages:
            logger.warning("[%s] Page limit (%d) reached", supplier, max_pages)
            return

        visited.add(url)
        with self._count_lock:
            self.page_count += 1

        if self.verbose:
            logger.debug("[%s] Visiting (depth %d): %s", supplier, depth, url)

        try:
            self._rate_limiter.wait(domain, cfg["delay"])
            resp = session.get(url, timeout=self.page_timeout)
            resp.raise_for_status()

            if url.lower().endswith(".pdf"):
                self._download_pdf(url, vendor_folder, supplier, "",
                                   domain, session, state_db, cfg)
                return

            soup = BeautifulSoup(resp.content, "html.parser")
            pdf_links: list[tuple[str, str]] = []
            page_links: list[str] = []

            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                if not href or href.startswith(("#", "mailto:", "tel:")):
                    continue
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc != domain:
                    continue
                if full_url.lower().endswith(".pdf"):
                    pdf_links.append((full_url, tag.get_text(strip=True)))
                elif depth < max_depth and full_url not in visited:
                    page_links.append(full_url)

            for pdf_url, anchor in pdf_links:
                if not self.running:
                    return
                self._download_pdf(pdf_url, vendor_folder, supplier, anchor,
                                   domain, session, state_db, cfg)

            for link in page_links[:10]:
                if not self.running:
                    return
                self._crawl_recursive(link, vendor_folder, supplier, domain,
                                      session, state_db, cfg, visited, depth + 1)

        except requests.exceptions.Timeout:
            logger.warning("[%s] Timeout: %s", supplier, url)
        except requests.exceptions.RequestException as exc:
            logger.warning("[%s] Request failed: %s - %s", supplier, url, exc)
        except Exception as exc:
            logger.error("[%s] Error crawling %s: %s", supplier, url, exc)

    # ------------------------------------------------------------------
    # Relevance filter
    # ------------------------------------------------------------------

    def _should_download(self, pdf_url: str, anchor: str, supplier: str = "") -> tuple[bool, str]:
        if not self.use_relevance_filter:
            return True, "filter_disabled"
        allowed, reason = _score_pdf_relevance(pdf_url, anchor)
        if not allowed:
            return False, reason
        if self.allowlist_only and reason == "default_allow":
            return False, "no_allowlist_match"

        # Supplier keyword filter: only download if PDF filename matches
        # at least one keyword from the supplier's item descriptions.

        if self.supplier_keywords and supplier:
            supplier_lower = supplier.lower()

            if supplier_lower not in self.supplier_keywords:
                # Fail closed: keyword filtering is on but this supplier has no
                # item descriptions, so nothing can be judged relevant.
                if supplier_lower not in self._warned_no_kw:
                    self._warned_no_kw.add(supplier_lower)
                    logger.warning("[%s] No supplier keywords loaded - skipping all PDFs", supplier)
                return False, "no_supplier_keywords"

            # Match against the full URL path + link text, not just the
            # filename - product identity often lives in the folder path
            # ("/products/mx-500/datasheet.pdf") or the anchor text.
            path = urlparse(pdf_url).path
            if '.' in path.rsplit('/', 1)[-1]:
                path = path.rsplit('.', 1)[0]

            # Normalize: lowercase, separators to spaces
            search_text = f"{path} {anchor}".lower()
            for sep in ('/', '-', '_'):
                search_text = search_text.replace(sep, ' ')

            if not _keywords_match(self.supplier_keywords[supplier_lower], search_text):
                return False, "no_keyword_match"

        return True, reason

    def _content_relevant(self, file_path: str, supplier: str) -> bool:
        """First-page text check: at least one supplier keyword must appear.

        Fails open when keywords, pdfplumber, or a text layer are missing -
        scanned PDFs and extraction errors are judged later by cross-reference.
        """
        keywords = self.supplier_keywords.get(supplier.lower())
        if not keywords:
            return True
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
        except Exception:
            return True
        if not text.strip():
            return True  # no text layer (scanned PDF) - cannot judge here
        text = text.lower().replace('-', ' ').replace('_', ' ')
        return _keywords_match(keywords, text)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _download_pdf(
        self,
        pdf_url: str,
        vendor_folder: str,
        supplier: str,
        anchor: str,
        domain: str,
        session: requests.Session,
        state_db: _StateDB,
        cfg: dict,
    ):
        if not self.running:
            return
        if self._supplier_pdf_counts[supplier] >= cfg["max_pdfs_per_supplier"]:
            if supplier not in self._warned_pdf_cap:
                self._warned_pdf_cap.add(supplier)
                logger.warning("[%s] Per-supplier PDF cap (%d) reached - skipping "
                               "further downloads (generic keyword slipping through?)",
                               supplier, cfg["max_pdfs_per_supplier"])
            return
        if not _validate_url(pdf_url):
            logger.warning("[%s] Blocked unsafe URL: %s", supplier, pdf_url)
            return

        # Relevance - no network cost
        ok, reason = self._should_download(pdf_url, anchor, supplier)
        if not ok:
            logger.debug("[%s] Skipping (%s): %s", supplier, reason, pdf_url)
            return

        # Dedup - skip if already seen
        if state_db.is_seen(pdf_url):
            logger.debug("[%s] Already processed: %s", supplier, pdf_url)
            return
        state_db.mark_seen(pdf_url, "queued")

        filename = _sanitize_path(os.path.basename(urlparse(pdf_url).path))
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        if len(filename) < 5:
            filename = f"document_{int(time.time())}.pdf"

        file_path = os.path.join(vendor_folder, filename)

        # Dedup by path
        if state_db.is_downloaded(file_path) or os.path.exists(file_path):
            logger.debug("[%s] Already downloaded: %s", supplier, filename)
            state_db.update_status(pdf_url, "exists")
            return

        try:
            max_bytes = self.max_pdf_size_mb * 1024 * 1024

            # HEAD pre-check before streaming
            try:
                self._rate_limiter.wait(domain, cfg["delay"])
                head = session.head(pdf_url, timeout=10, allow_redirects=True)
                cl = head.headers.get("content-length")
                ct = head.headers.get("content-type", "").lower()

                if cl and int(cl) > max_bytes:
                    logger.warning("[%s] Too large (HEAD): %.1f MB - %s",
                                   supplier, int(cl) / 1024 / 1024, pdf_url)
                    state_db.update_status(pdf_url, "skipped_size")
                    return

                if self.strict_content_validation and "pdf" not in ct and not pdf_url.lower().endswith(".pdf"):
                    logger.warning("[%s] Non-PDF content-type (HEAD): %s", supplier, ct)
                    state_db.update_status(pdf_url, "skipped_type")
                    return
            except Exception as exc:
                logger.debug("[%s] HEAD failed for %s: %s - proceeding with GET", supplier, pdf_url, exc)

            # Full download
            self._rate_limiter.wait(domain, cfg["delay"])
            resp = session.get(pdf_url, timeout=self.page_timeout, stream=True)
            resp.raise_for_status()

            ct = resp.headers.get("content-type", "").lower()
            cl = resp.headers.get("content-length")

            if cl and int(cl) > max_bytes:
                logger.warning("[%s] Too large: %.1f MB - %s",
                               supplier, int(cl) / 1024 / 1024, pdf_url)
                state_db.update_status(pdf_url, "skipped_size")
                return

            if self.strict_content_validation and "pdf" not in ct and not pdf_url.lower().endswith(".pdf"):
                state_db.update_status(pdf_url, "skipped_type")
                return

            # Peek at the first chunk: reject HTML error/login pages served
            # at .pdf URLs before anything touches disk. PDF spec allows the
            # magic bytes anywhere in the first 1024 bytes.
            stream = resp.iter_content(chunk_size=8192)
            first = next(stream, b"")
            if b"%PDF" not in first[:1024]:
                logger.warning("[%s] Not a PDF payload - skipped: %s", supplier, pdf_url)
                state_db.update_status(pdf_url, "rejected_not_pdf")
                return

            downloaded = len(first)
            with open(file_path, "wb") as f:
                f.write(first)
                for chunk in stream:
                    if not self.running:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                        return
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                        logger.warning("[%s] Exceeded size mid-download - removed: %s", supplier, filename)
                        state_db.update_status(pdf_url, "skipped_size")
                        return
                    f.write(chunk)

            actual = os.path.getsize(file_path)
            if actual < self.min_pdf_size_bytes:
                os.remove(file_path)
                logger.warning("[%s] File too small (%d bytes) - removed: %s", supplier, actual, filename)
                state_db.update_status(pdf_url, "skipped_small")
                return

            # Same catalog PDF often served at several URLs - keep one copy
            file_hash = _file_hash(file_path)
            if file_hash and state_db.is_hash_seen(file_hash):
                os.remove(file_path)
                logger.info("[%s] Duplicate content - removed: %s", supplier, filename)
                state_db.update_status(pdf_url, "duplicate")
                return

            if not self._content_relevant(file_path, supplier):
                os.remove(file_path)
                logger.info("[%s] First page has no supplier keywords - removed: %s",
                            supplier, filename)
                state_db.update_status(pdf_url, "rejected_content")
                return

            state_db.mark_downloaded(file_path, pdf_url, supplier)
            if file_hash:
                state_db.mark_hash(file_hash)
            state_db.update_status(pdf_url, "downloaded")
            with self._count_lock:
                self.pdf_count += 1
                self._supplier_pdf_counts[supplier] += 1
            logger.info("[%s] Downloaded: %s (%.1f MB) [%s]",
                        supplier, filename, actual / 1024 / 1024, reason)

        except requests.exceptions.Timeout:
            logger.warning("[%s] Timeout downloading %s", supplier, pdf_url)
            state_db.update_status(pdf_url, "timeout")
        except requests.exceptions.RequestException as exc:
            logger.warning("[%s] Download failed %s: %s", supplier, pdf_url, exc)
            state_db.update_status(pdf_url, "error")
        except Exception as exc:
            logger.error("[%s] Unexpected error %s: %s", supplier, pdf_url, exc)
            state_db.update_status(pdf_url, "error")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
