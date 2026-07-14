#!/usr/bin/env python3
"""
Phase 1: Triage all Software and Non-Instrument keywords.
Buckets each term into STOPWORD | FRAGMENT | IT_JARGON | BRAND | KEEP.
No judgment calls - mechanical categorization only.
"""

import sys
from pathlib import Path

# Add PROJECTS dir to path
proj_dir = Path(__file__).parent.parent
sys.path.insert(0, str(proj_dir))

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("classify_v3",
    proj_dir / "src" / "services" / "data-cleaning" / "column_filter_and_classify_v3.py")
classify_v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classify_v3)
load_and_clean_keywords = classify_v3.load_and_clean_keywords

# Common English stopwords that add noise to classification
STOPWORDS = {
    # articles, pronouns, prepositions
    "a", "an", "the", "i", "me", "my", "we", "you", "he", "she", "it", "this", "that",
    "to", "of", "in", "on", "at", "by", "for", "with", "from", "about", "as", "is", "are",
    "am", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    # vague adjectives
    "great", "ideal", "good", "bad", "small", "large", "big", "heavy", "light", "full", "empty",
    "new", "old", "high", "low", "fast", "slow", "strong", "weak", "easy", "hard",
    # numbers spelled out
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    # other noise
    "above", "below", "only", "once", "over", "under", "next", "last", "first", "second",
    "need", "want", "will", "can", "could", "should", "may", "might", "must", "able",
    "comes", "come", "go", "goes", "came", "went", "more", "less", "kind", "way",
    "place", "thing", "time", "price", "cost", "list", "item", "way", "away",
    "before", "after", "during", "through", "between", "among", "until", "since",
}

# IT/DevOps/Enterprise vocabulary - never appears in equipment requisitions
IT_JARGON = {
    "agile", "scrum", "jira", "docker", "kubernetes", "saas", "paas", "iaas",
    "gdpr", "hipaa", "itil", "cobit", "mtbf", "mttr", "ci/cd", "devops",
    "azure", "aws", "slack", "teams", "webex", "skype", "zoom", "redis", "mysql",
    "json", "yaml", "toml", "soap", "xml", "rest api", "api", "sdk",
    "unix", "linux", "macos", "windows", "virtual", "vmware", "hyperv",
    "jenkins", "github", "gitlab", "bitbucket", "monitoring", "logging",
    "prometheus", "grafana", "elasticsearch", "splunk", "datadog",
    "sql server", "oracle", "mongodb", "postgresql", "hadoop", "spark",
    "java", "python", "nodejs", "golang", "rust", "csharp", "cpp",
    "docker", "container", "orchestration", "microservices",
}

# Known brand/vendor names (not product categories)
BRANDS = {
    # Software brands not scientific software
    "dell", "cisco", "adobe", "microsoft", "oracle", "salesforce", "sap",
    "google", "amazon", "apple", "ibm", "hp", "canon", "brother",
    # Hardware/telecom brands
    "sony", "panasonic", "lg", "samsung", "philips", "siemens", "ge",
    "bosch", "liebherr", "bofa", "barco", "zebra", "capsa",
    # In non_instrument specifically
    "axon",  # (Molecular Devices; deliberate non-instrument per plan)
    "nomad", "joel", "jess", "york", "rice",
}

def is_fragment(kw: str) -> bool:
    """True if this looks like a word fragment, not a real word."""
    # Length <= 5, alphabetic only
    if len(kw) > 5 or not kw.isalpha():
        return False
    # Known abbreviations/acronyms that are valid
    if kw in {"pcr", "nmr", "gc", "lc", "rna", "dna", "atm", "rpm", "ppb", "ppm",
              "hplc", "gcms", "lcms", "icpms", "isobar", "co2", "n2", "ar", "he"}:
        return False
    # Known domain terms that are short but real
    if kw in {"cell", "tube", "dish", "vial", "tape", "wire", "pump", "motor", "rotor"}:
        return False
    return True

def triage_keyword(kw: str, category: str) -> str:
    """Categorize a single keyword."""
    kw_lower = kw.lower().strip()

    if kw_lower in STOPWORDS:
        return "STOPWORD"
    if is_fragment(kw_lower):
        return "FRAGMENT"
    if kw_lower in IT_JARGON:
        return "IT_JARGON"
    if kw_lower in BRANDS:
        return "BRAND"
    return "KEEP"

def main():
    # Load cleaned keywords
    hw_kw, sw_kw, ni_kw = load_and_clean_keywords()

    print("\n" + "="*80)
    print("PHASE 1: KEYWORD TRIAGE")
    print("="*80)

    # Triage Software
    print("\n[SOFTWARE] Categorizing {} terms...".format(len(sw_kw)))
    sw_buckets = {"STOPWORD": set(), "FRAGMENT": set(), "IT_JARGON": set(),
                  "BRAND": set(), "KEEP": set()}
    for kw in sw_kw:
        bucket = triage_keyword(kw, "software")
        sw_buckets[bucket].add(kw)

    print("\nSOFTWARE KEYWORD BUCKETS:")
    print(f"  STOPWORD:   {len(sw_buckets['STOPWORD']):3d}  {sorted(list(sw_buckets['STOPWORD'])[:10])}")
    print(f"  FRAGMENT:   {len(sw_buckets['FRAGMENT']):3d}  {sorted(list(sw_buckets['FRAGMENT'])[:10])}")
    print(f"  IT_JARGON:  {len(sw_buckets['IT_JARGON']):3d}  {sorted(list(sw_buckets['IT_JARGON'])[:10])}")
    print(f"  BRAND:      {len(sw_buckets['BRAND']):3d}  {sorted(list(sw_buckets['BRAND'])[:10])}")
    print(f"  KEEP:       {len(sw_buckets['KEEP']):3d}  (largest bucket)")
    print(f"  TOTAL:      {sum(len(v) for v in sw_buckets.values())}")

    # Triage Non-Instrument
    print("\n[NON-INSTRUMENT] Categorizing {} terms...".format(len(ni_kw)))
    ni_buckets = {"STOPWORD": set(), "FRAGMENT": set(), "IT_JARGON": set(),
                  "BRAND": set(), "KEEP": set()}
    for kw in ni_kw:
        bucket = triage_keyword(kw, "non_instrument")
        ni_buckets[bucket].add(kw)

    print("\nNON-INSTRUMENT KEYWORD BUCKETS:")
    print(f"  STOPWORD:   {len(ni_buckets['STOPWORD']):3d}  {sorted(list(ni_buckets['STOPWORD'])[:10])}")
    print(f"  FRAGMENT:   {len(ni_buckets['FRAGMENT']):3d}  {sorted(list(ni_buckets['FRAGMENT'])[:10])}")
    print(f"  IT_JARGON:  {len(ni_buckets['IT_JARGON']):3d}  {sorted(list(ni_buckets['IT_JARGON'])[:10])}")
    print(f"  BRAND:      {len(ni_buckets['BRAND']):3d}  {sorted(list(ni_buckets['BRAND'])[:10])}")
    print(f"  KEEP:       {len(ni_buckets['KEEP']):3d}  (largest bucket)")
    print(f"  TOTAL:      {sum(len(v) for v in ni_buckets.values())}")

    # Detailed output for review
    print("\n" + "="*80)
    print("DETAILED BUCKETS FOR REVIEW")
    print("="*80)

    print("\n[SOFTWARE] STOPWORDS TO REMOVE:")
    for kw in sorted(sw_buckets["STOPWORD"]):
        print(f"  {kw}")

    print("\n[SOFTWARE] FRAGMENTS TO REMOVE:")
    for kw in sorted(sw_buckets["FRAGMENT"]):
        print(f"  {kw}")

    print("\n[SOFTWARE] IT_JARGON TO REMOVE:")
    for kw in sorted(sw_buckets["IT_JARGON"]):
        print(f"  {kw}")

    print("\n[SOFTWARE] BRANDS (check plan for disposition):")
    for kw in sorted(sw_buckets["BRAND"]):
        print(f"  {kw}")

    print("\n[NON-INSTRUMENT] STOPWORDS TO REMOVE:")
    for kw in sorted(ni_buckets["STOPWORD"]):
        print(f"  {kw}")

    print("\n[NON-INSTRUMENT] FRAGMENTS TO REMOVE:")
    for kw in sorted(ni_buckets["FRAGMENT"]):
        print(f"  {kw}")

    print("\n[NON-INSTRUMENT] IT_JARGON TO REMOVE:")
    for kw in sorted(ni_buckets["IT_JARGON"]):
        print(f"  {kw}")

    print("\n[NON-INSTRUMENT] BRANDS (check plan for disposition):")
    for kw in sorted(ni_buckets["BRAND"]):
        print(f"  {kw}")

    print("\n" + "="*80)
    print("END PHASE 1 TRIAGE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
