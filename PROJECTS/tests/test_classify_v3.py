#!/usr/bin/env python3
"""Classifier rules, each one a bug we actually hit.
Run: python tests/test_classify_v3.py
"""
import importlib.util
from pathlib import Path

_V3 = Path(__file__).resolve().parents[1] / "src" / "services" / "data-cleaning" / "column_filter_and_classify_v3.py"
spec = importlib.util.spec_from_file_location("classify_v3", _V3)
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)


def test_word_boundary():
    """Substring matching scored 'lysis' against 'anaLYSIS'. Whole words only."""
    hw = {"lysis", "ella", "contro", "multi", "microscope"}
    assert v3.classify_item("", "Standard Analysis package", hw, set(), set()) == "Unknown"
    assert v3.classify_item("", "noise CANCELLATION module", hw, set(), set()) == "Unknown"
    assert v3.classify_item("", "computer controlled", hw, set(), set()) == "Unknown"
    assert v3.classify_item("", "MULTICLAMP 700B", hw, set(), set()) == "Unknown"


def test_strong_vs_weak():
    hw = {"centrifuge", "microscope", "freezer", "analyzer", "meter"}
    ni = {"slider"}  # components live in Non-Instrument
    # One unambiguous term is enough.
    assert v3.classify_item("", "Eppendorf centrifuge 5810R", hw, set(), ni) == "Instrument"
    assert v3.classify_item("", "PHCBi UPRIGHT ULT -80c FREEZER", hw, set(), ni) == "Instrument"
    # A weak term alone is not ("Analyzer slider" was the real bug).
    assert v3.classify_item("", "Analyzer slider", hw, set(), ni) == "Non-Instrument"


def test_real_keyword_lists():
    """The shipped lists must classify the items Kren actually adjudicated."""
    hw, sw, ni = v3.load_and_clean_keywords()

    # Rig components are NOT instruments - they are parts of one. (Bare model
    # names match nothing and land in Unknown; either way they never reach the
    # scraper, which only takes Instrument/Software.)
    for component in (
        "MULTICLAMP 700B SYSTEM Includes: Microelectrode Amplifier, "
        "resistor-feedback, computer controlled",
        "MULTICLAMP 700B",
        "RHD 512-channel Recording Controller",
    ):
        assert v3.classify_item("", component, hw, sw, ni) != "Instrument", component

    # Real instruments still classify.
    assert v3.classify_item("", "Confocal microscope with 50X objective", hw, sw, ni) == "Instrument"
    assert v3.classify_item("", "Eppendorf centrifuge 5810R", hw, sw, ni) == "Instrument"
    assert v3.classify_item("", "PHCBi UPRIGHT ULT -80c FREEZER 25.7 CU FT", hw, sw, ni) == "Instrument"

    # Junk keywords are gone from the lists.
    for junk in ("multi", "contro", "ella", "lysis", "buyout", "quote#", "total"):
        assert junk not in hw, f"{junk!r} still in instrument keywords"
    # Part numbers harvested by learning_mode are gone.
    for pn in ("a28568", "l23119", "fb4209", "x50i", "bx43fw"):
        assert pn not in hw, f"{pn!r} still in instrument keywords"
    # But real punctuated terms survive.
    for real in ("gc-ms", "icp-ms", "-80", "co2"):
        assert real in hw, f"{real!r} was wrongly purged"


def test_riders_and_price_gate():
    assert v3._is_rider("SHIPPING/HANDLING")
    assert v3._is_rider("Power Cord 110V (US)")
    assert v3._is_rider("Simulator Trade-In Program Value")
    assert v3._is_rider("NC2682403 VLBL00GD2 2Y WARR SMST EACH")
    assert not v3._is_rider("PHILIPS AFFINITI ULTRASOUND SYSTEM")
    # Word-boundary: instruments containing fee/tax substrings are NOT riders.
    assert not v3._is_rider("PENTAX video endoscope")
    assert not v3._is_rider("Stereotaxic frame, mouse")
    assert v3._RULE_B_MIN_PRICE == 1000


def test_software_classification():
    """Verify scientific software still classifies after cleanup (Phase 2 assertion)."""
    hw, sw, ni = v3.load_and_clean_keywords()

    # pCLAMP is scientific software, must still classify as Software
    assert v3.classify_item("", "PCLAMP 11 SOFTWARE FOR WINDOWS", hw, sw, ni) == "Software"
    # INCUCYTE with software/module descriptor
    assert v3.classify_item("", "9600-0012 INCUCYTE SCRATCH WOUND SOFTWARE MODULE", hw, sw, ni) == "Software"


if __name__ == "__main__":
    test_word_boundary()
    test_strong_vs_weak()
    test_real_keyword_lists()
    test_riders_and_price_gate()
    test_software_classification()
    print("OK - word boundaries, strong/weak terms, components excluded, "
          "junk purged, scientific software still classifies")
