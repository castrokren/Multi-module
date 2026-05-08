import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def search_duckduckgo(query: str, timeout: int = 10,
                      max_results: int = 3) -> list:
    """Search DuckDuckGo HTML interface. Returns list of result URLs."""
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        resp = requests.post(url, data=params, headers=HEADERS,
                             timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select("a.result__url"):
            href = a.get("href", "")
            if href.startswith("http"):
                results.append(href)
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def search_bing(query: str, timeout: int = 10,
                max_results: int = 3) -> list:
    """Search Bing HTML interface. Returns list of result URLs."""
    try:
        url = "https://www.bing.com/search"
        params = {"q": query}
        resp = requests.get(url, params=params, headers=HEADERS,
                            timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for cite in soup.select("cite"):
            text = cite.get_text(strip=True)
            if text.startswith("http"):
                results.append(text)
            elif "." in text:
                results.append("https://" + text)
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def find_supplier_url(supplier_name: str, delay: float = 1.5,
                      timeout: int = 10) -> tuple:
    """
    Search both engines for a supplier.
    Returns (ddg_urls, bing_urls).
    Applies delay between requests to avoid rate limiting.
    """
    query = f'"{supplier_name}" official website'
    ddg_urls = search_duckduckgo(query, timeout=timeout)
    time.sleep(delay)
    bing_urls = search_bing(query, timeout=timeout)
    time.sleep(delay)
    return ddg_urls, bing_urls
