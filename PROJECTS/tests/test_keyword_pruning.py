#!/usr/bin/env python3
"""Keyword pruning: the guard that stops one requisition from pulling a
vendor's whole catalogue. Run: python tests/test_keyword_pruning.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "services"))

from pipeline import load_supplier_keywords, prune_generic_keywords


def test_prune():
    # "server" appears for only ONE vendor - the cross-vendor count can't
    # catch it, the category-noun list must. That single word used to pull
    # Broadax's entire 500+ PDF catalogue.
    kw_sets = {
        "broadax systems inc": {"server", "specifications", "gigabyte", "r263z30"},
        "other reseller inc": {"workstation", "specifications", "supermicro", "x11dpi"},
        "molecular devices llc": {"system", "software", "digidata", "1550b1"},
        "acme instruments": {"system", "software", "widget"},
        "generic only inc": {"system", "manual"},
    }
    pruned = prune_generic_keywords(kw_sets)

    # Document-type word: gone everywhere, even though only 2 vendors used it.
    assert not any("specifications" in v for v in pruned.values())
    assert not any("manual" in v for v in pruned.values())

    # Category nouns: gone, even when unique to a single vendor.
    assert not any("server" in v for v in pruned.values())
    assert not any("workstation" in v for v in pruned.values())
    assert not any("system" in v for v in pruned.values())
    assert not any("software" in v for v in pruned.values())

    # Distinctive product identity: kept.
    assert pruned["broadax systems inc"] == {"gigabyte", "r263z30"}
    assert pruned["molecular devices llc"] == {"digidata", "1550b1"}
    assert pruned["acme instruments"] == {"widget"}

    # Nothing distinctive left -> vendor dropped, so the scraper skips the site.
    assert "generic only inc" not in pruned

    print("OK - generic keywords pruned, distinctive ones kept")


def test_type_gate():
    # Only rows sorted Instrument/Software may feed the scraper.
    import tempfile
    import pandas as pd

    with tempfile.TemporaryDirectory() as d:
        pd.DataFrame({
            "Supplier Name": ["Broadax Systems Inc", "USA Shred", "Soft Co"],
            "Item Description": ["Gigabyte R263-Z30 rack server",
                                 "onsite document shredding",
                                 "FlowJo v10 analysis package"],
            "Type": ["Instrument", "Non-Instrument", "Software"],
        }).to_excel(Path(d) / "req_classified_v3.xlsx", index=False)

        kws = load_supplier_keywords(d)

    assert set(kws) == {"broadax systems inc", "soft co"}, kws
    assert "r263z30" in kws["broadax systems inc"]
    assert "flowjo" in kws["soft co"]
    # Non-Instrument vendor never reaches the scraper.
    assert "usa shred" not in kws

    print("OK - only Instrument/Software rows feed the scraper")


if __name__ == "__main__":
    test_prune()
    test_type_gate()
