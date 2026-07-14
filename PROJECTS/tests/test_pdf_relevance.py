#!/usr/bin/env python3
"""PDF relevance filter: product docs in, corporate/HR docs out.
Run: python tests/test_pdf_relevance.py
"""
import importlib.util
from pathlib import Path

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "services" / "scraper-full" / "scraper_engine.py"
spec = importlib.util.spec_from_file_location("scraper_engine", _ENGINE)
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)


def test_relevance():
    # Real product docs from the last run: keep.
    for url in (
        "https://x.com/Sonosite_LX_UG_ENG_P28669-08C_e.pdf",
        "https://x.com/multiclamp-700b-microelectrode-amplifier.pdf",
        "https://x.com/manual-quickstartguide-octet-bli-hardware.pdf",
        "https://x.com/Intan_Recording_Controller_user_guide.pdf",
    ):
        ok, reason = eng._score_pdf_relevance(url)
        assert ok, f"should keep {url} ({reason})"

    # Corporate/HR: the careers brochure that slipped through on the word
    # "guide" plus the vendor's own brand name.
    for url in (
        "https://x.com/working-at-sartorius-candidate-guide-202114.pdf",
        "https://x.com/careers-brochure.pdf",
        "https://x.com/2025-sustainability-report.pdf",
        "https://x.com/investor-presentation.pdf",
    ):
        ok, reason = eng._score_pdf_relevance(url)
        assert not ok, f"should block {url} ({reason})"

    print("OK - product docs kept, corporate/HR docs blocked")


if __name__ == "__main__":
    test_relevance()
