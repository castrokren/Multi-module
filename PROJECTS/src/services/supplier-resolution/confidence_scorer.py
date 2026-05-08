from urllib.parse import urlparse
import re

DIRECTORY_BLOCKLIST = [
    "amazon", "alibaba", "linkedin", "yellowpages", "thomasnet",
    "globalspec", "grainger", "fishersci", "directindustry", "kompass",
    "selectscience", "labcompare", "capterra", "g2", "yelp"
]


def extract_domain(url: str) -> str:
    """Extract bare domain from URL e.g. https://www.ancare.com/ -> ancare.com"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain
    except Exception:
        return ""


def domain_matches_supplier(domain: str, supplier_name: str) -> bool:
    """Check if domain contains meaningful words from supplier name."""
    name = supplier_name.lower()
    for suffix in [" inc", " llc", " corp", " ltd", " co", " gmbh",
                   " usa", " us", " na", " north america", " corporation",
                   " company", " technologies", " scientific", " medical"]:
        name = name.replace(suffix, "")
    words = [w for w in re.split(r'\s+|-', name) if len(w) > 2]
    return any(word in domain for word in words)


def is_directory(domain: str) -> bool:
    return any(blocked in domain for blocked in DIRECTORY_BLOCKLIST)


def score_url(url: str, supplier_name: str, ddg_urls: list,
              bing_urls: list) -> int:
    """Score a candidate URL for a supplier. Returns 0-130."""
    if not url:
        return 0

    score = 0
    domain = extract_domain(url)
    if not domain:
        return 0

    # Both engines agree on top result
    ddg_domains = [extract_domain(u) for u in ddg_urls[:1]]
    bing_domains = [extract_domain(u) for u in bing_urls[:1]]
    if ddg_domains and bing_domains and ddg_domains[0] == bing_domains[0]:
        score += 40
    elif ddg_domains or bing_domains:
        score += 10

    # Domain contains supplier name words
    if domain_matches_supplier(domain, supplier_name):
        score += 25

    # HTTPS
    if url.startswith("https://"):
        score += 15

    # TLD
    tld = domain.split(".")[-1] if "." in domain else ""
    if tld in ("com", "org", "us", "edu"):
        score += 10

    # Not a directory/marketplace
    if not is_directory(domain):
        score += 20

    return score


def pick_best_url(ddg_urls: list, bing_urls: list,
                  supplier_name: str) -> tuple:
    """
    Pick the best URL from combined search results.
    Returns (url, score). Returns ("", 0) if nothing found.
    """
    candidates = []
    seen = set()
    for url in (ddg_urls[:3] + bing_urls[:3]):
        domain = extract_domain(url)
        if domain and domain not in seen:
            seen.add(domain)
            candidates.append(url)

    if not candidates:
        return "", 0

    scored = [
        (url, score_url(url, supplier_name, ddg_urls, bing_urls))
        for url in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0]
