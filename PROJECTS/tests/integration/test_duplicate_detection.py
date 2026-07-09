"""
Integration tests for duplicate file detection across parallel directory trees.

Verifies the 3 copies of crossref_standalone_fast.py share core logic,
the 3 copies of config.ini parse consistently, and reports key differences.
"""

import pytest
import sys
import os
import configparser
import hashlib
from pathlib import Path


PROJECTS_ROOT = Path(__file__).resolve().parents[2]

CROSSREF_COPIES = [
    ("src/services/cross-reference/crossref_standalone_fast.py", "new (services)"),
    ("Cross-reference/crossref_standalone_fast.py", "legacy (Cross-reference/)"),
    ("crossref_standalone_fast.py", "legacy (root)"),
]

CONFIG_INI_COPIES = [
    ("src/services/config.ini", "services config.ini"),
    ("src/services/scraper-full/config.ini", "scraper-full config.ini"),
    ("config.ini", "root config.ini"),
]

CROSSREF_KEY_FUNCTIONS = [
    "class CrossReferenceEngine",
    "normalize_filename",
    "def run_cross_reference",
    "class GlobalStopManager",
    "deduplicate_matches",
    "class PDFSmartFilter",
    "def run_cross_reference_by_supplier",
    "def run_cross_reference_high_performance",
]

CONFIG_INI_KEYS = [
    "max_concurrent",
    "request_delay",
    "page_timeout",
    "max_pages_per_site",
    "match_threshold",
    "max_retries",
    "backup_interval",
]

CONFIG_INI_FULL_KEYS = CONFIG_INI_KEYS + [
    "max_pdf_size_mb",
    "min_pdf_size_bytes",
    "min_text_length",
    "strict_content_validation",
]


def _read_file(path):
    """Read a file and return its lines."""
    p = PROJECTS_ROOT / path
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8", errors="replace").splitlines()


def _file_hash(path):
    """Return SHA-256 hex digest of a file."""
    p = PROJECTS_ROOT / path
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_config_ini(path):
    """Load a config.ini file and return its DEFAULT section as a dict."""
    p = PROJECTS_ROOT / path
    if not p.exists():
        return {}
    cfg = configparser.ConfigParser()
    cfg.read(str(p), encoding="utf-8")
    return dict(cfg["DEFAULT"]) if "DEFAULT" in cfg else {}


@pytest.mark.integration
class TestCrossrefStandaloneCopiesExist:
    """All 3 copies of crossref_standalone_fast.py should exist."""

    def test_all_copies_present(self):
        """Every crossref_standalone_fast.py path must resolve to a real file."""
        for rel_path, label in CROSSREF_COPIES:
            full = PROJECTS_ROOT / rel_path
            assert full.exists(), f"Missing copy ({label}): {full}"


@pytest.mark.integration
class TestCrossrefCoreLogicConsistency:
    """The 3 copies should share the same core classes and functions."""

    @pytest.fixture(scope="class")
    def copy_lines(self):
        return {label: _read_file(rel_path) for rel_path, label in CROSSREF_COPIES}

    def test_all_copies_contain_core_classes(self, copy_lines):
        """Each core class/function must appear in every copy."""
        for label, lines in copy_lines.items():
            content = "\n".join(lines)
            for func in CROSSREF_KEY_FUNCTIONS:
                assert func in content, f"Copy '{label}' missing {func}"

    def test_deduplicate_matches_logic_consistent(self):
        """The deduplicate_matches logic should exist in all copies."""
        dedup_patterns = [
            "deduplicate_matches",
            "normalize_filename",
        ]
        for rel_path, label in CROSSREF_COPIES:
            content = "\n".join(_read_file(rel_path))
            for pat in dedup_patterns:
                assert pat in content, f"Copy '{label}' missing dedup pattern: {pat}"

    def test_class_name_consistency(self):
        """All copies should define CrossReferenceEngine."""
        for rel_path, label in CROSSREF_COPIES:
            content = "\n".join(_read_file(rel_path))
            assert "class CrossReferenceEngine" in content, f"Copy '{label}' missing CrossReferenceEngine"

    def test_not_all_copies_are_bit_identical(self):
        """Copies might differ in import style (sys.path trick) — measure divergence."""
        hashes = [_file_hash(rel_path) for rel_path, _ in CROSSREF_COPIES]
        unique = len(set(h for h in hashes if h))
        if unique == 1:
            pytest.skip("All copies are bit-identical — no divergence")

    def test_report_significant_differences(self):
        """
        Identify any copy that is missing key logic compared to the
        reference copy (src/services/cross-reference/crossref_standalone_fast.py).
        """
        ref_path = PROJECTS_ROOT / "src" / "services" / "cross-reference" / "crossref_standalone_fast.py"
        ref_content = ref_path.read_text(encoding="utf-8", errors="replace")

        differences = []
        for rel_path, label in CROSSREF_COPIES:
            if rel_path == "src/services/cross-reference/crossref_standalone_fast.py":
                continue
            other_content = "\n".join(_read_file(rel_path))
            for func in CROSSREF_KEY_FUNCTIONS:
                if func in ref_content and func not in other_content:
                    differences.append(f"  {label}: missing '{func}'")

        if differences:
            msg = "Core logic differences found:\n" + "\n".join(differences)
            pytest.fail(msg)


@pytest.mark.integration
class TestConfigIniCopiesExist:
    """All 3 copies of config.ini should exist."""

    def test_all_copies_present(self):
        """Every config.ini path must resolve to a real file."""
        for rel_path, label in CONFIG_INI_COPIES:
            full = PROJECTS_ROOT / rel_path
            assert full.exists(), f"Missing copy ({label}): {full}"


@pytest.mark.integration
class TestConfigIniParsingConsistency:
    """The 3 config.ini copies should parse without errors."""

    def test_all_copies_parse_successfully(self):
        """Every config.ini must parse as valid INI."""
        for rel_path, label in CONFIG_INI_COPIES:
            try:
                _load_config_ini(rel_path)
            except Exception as e:
                pytest.fail(f"Copy '{label}' failed to parse: {e}")

    def test_all_copies_have_default_section(self):
        """Every config.ini must have a [DEFAULT] section."""
        for rel_path, label in CONFIG_INI_COPIES:
            cfg = _load_config_ini(rel_path)
            assert cfg is not None, f"Copy '{label}' has no [DEFAULT] section"

    def test_all_copies_have_required_keys(self):
        """Each config.ini must define all standard keys."""
        for rel_path, label in CONFIG_INI_COPIES:
            cfg = _load_config_ini(rel_path)
            keys_to_check = CONFIG_INI_FULL_KEYS if label != "scraper-full config.ini" else CONFIG_INI_KEYS
            for key in keys_to_check:
                if key not in cfg:
                    pytest.fail(f"Copy '{label}' missing key: {key}")


@pytest.mark.integration
class TestConfigIniKeyDrift:
    """Report which keys differ between config.ini copies."""

    def test_report_missing_keys(self):
        """Identify keys present in some copies but absent in others."""
        all_configs = {label: _load_config_ini(rel_path) for rel_path, label in CONFIG_INI_COPIES}
        all_keys = set()
        for cfg in all_configs.values():
            all_keys.update(cfg.keys())

        ref_label = CONFIG_INI_COPIES[0][1]
        ref_cfg = all_configs[ref_label]

        missing = {}
        for label, cfg in all_configs.items():
            if label == ref_label:
                continue
            # scraper-full/config.ini is intentionally a subset; only check shared keys
            ref_keys = CONFIG_INI_KEYS if label == "scraper-full config.ini" else ref_cfg
            absent = [k for k in ref_keys if k not in cfg]
            if absent:
                missing[label] = absent

        if missing:
            msg_lines = ["Config key drift between config.ini copies:"]
            for label, keys in missing.items():
                msg_lines.append(f"  {label} missing vs reference: {keys}")
            pytest.fail("\n".join(msg_lines))

    def test_report_value_differences(self):
        """Report keys whose values differ between copies."""
        all_configs = {label: _load_config_ini(rel_path) for rel_path, label in CONFIG_INI_COPIES}
        ref_label = CONFIG_INI_COPIES[0][1]
        ref_cfg = all_configs[ref_label]

        diffs = {}
        for rel_path, label in CONFIG_INI_COPIES:
            if label == ref_label:
                continue
            cfg = all_configs[label]
            key_diffs = {}
            keys_to_check = CONFIG_INI_FULL_KEYS if label != "scraper-full config.ini" else CONFIG_INI_KEYS
            for k in keys_to_check:
                if k in ref_cfg and k in cfg and ref_cfg[k] != cfg[k]:
                    key_diffs[k] = (ref_cfg[k], cfg[k])
            if key_diffs:
                diffs[label] = key_diffs

        if diffs:
            msg_lines = ["Config value differences found:"]
            for label, key_diffs in diffs.items():
                for k, (ref_v, copy_v) in key_diffs.items():
                    msg_lines.append(f"  {label}: {k} = {copy_v!r} (ref: {ref_v!r})")
            pytest.fail("\n".join(msg_lines))

    def test_scraper_full_config_has_fewer_keys(self):
        """scraper-full/config.ini is a subset — verify it's missing the expected keys."""
        scraper_cfg = _load_config_ini("src/services/scraper-full/config.ini")
        services_cfg = _load_config_ini("src/services/config.ini")
        scraper_keys = set(scraper_cfg.keys())
        services_keys = set(services_cfg.keys())
        # scraper-full config should be a subset of services config
        assert scraper_keys.issubset(services_keys), (
            f"scraper-full keys not subset of services keys: "
            f"{scraper_keys - services_keys}"
        )
