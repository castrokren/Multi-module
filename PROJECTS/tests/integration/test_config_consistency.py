"""
Integration tests for config consistency between pipeline_config.json and config.ini.

Verifies both files can be loaded, parsed, and that overlapping keys
have consistent values. Reports drift warnings.
"""

import pytest
import json
import configparser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_CONFIG = PROJECT_ROOT / "src" / "services" / "pipeline_config.json"
CONFIG_INI = PROJECT_ROOT / "src" / "services" / "config.ini"


def load_pipeline_json(path=None):
    """Load and return pipeline_config.json as a dict."""
    p = path or PIPELINE_CONFIG
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_config_ini(path=None):
    """Load and return config.ini as a dict of {section: {key: value}}."""
    p = path or CONFIG_INI
    cfg = configparser.ConfigParser()
    cfg.read(p, encoding="utf-8")
    result = {s: dict(cfg[s]) for s in cfg.sections()}
    if cfg.defaults():
        result["DEFAULT"] = dict(cfg.defaults())
    return result


# ---------------------------------------------------------------------------
# Overlapping keys between the two config files
# ---------------------------------------------------------------------------
OVERLAPPING_KEYS = {
    "max_concurrent": {"json_path": ["scraper", "max_concurrent"], "ini_section": "DEFAULT", "ini_key": "max_concurrent", "type_cast": int},
    "request_delay": {"json_path": ["scraper", "request_delay"], "ini_section": "DEFAULT", "ini_key": "request_delay", "type_cast": float},
    "page_timeout": {"json_path": ["scraper", "page_timeout"], "ini_section": "DEFAULT", "ini_key": "page_timeout", "type_cast": int},
    "max_pages_per_site": {"json_path": ["scraper", "max_pages_per_site"], "ini_section": "DEFAULT", "ini_key": "max_pages_per_site", "type_cast": int},
    "match_threshold": {"json_path": ["crossref", "threshold"], "ini_section": "DEFAULT", "ini_key": "match_threshold", "type_cast": int},
    "max_pdf_size_mb": {"json_path": ["scraper", "max_pdf_size_mb"], "ini_section": "DEFAULT", "ini_key": "max_pdf_size_mb", "type_cast": int},
    "min_pdf_size_bytes": {"json_path": ["scraper", "min_pdf_size_bytes"], "ini_section": "DEFAULT", "ini_key": "min_pdf_size_bytes", "type_cast": int},
    "strict_content_validation": {"json_path": ["scraper", "strict_content_validation"], "ini_section": "DEFAULT", "ini_key": "strict_content_validation", "type_cast": lambda x: x == "True"},
}


def _json_get(d, path):
    """Traverse a nested dict following *path* keys."""
    for key in path:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return None
    return d


def _compare_overlapping_keys(json_cfg, ini_cfg):
    """
    Compare overlapping keys and return a list of (key, json_val, ini_val)
    tuples where values differ.
    """
    diffs = []
    ini_defaults = ini_cfg.get("DEFAULT", {})
    for key, spec in OVERLAPPING_KEYS.items():
        json_val = _json_get(json_cfg, spec["json_path"])
        ini_val = ini_defaults.get(spec["ini_key"])
        if json_val is None and ini_val is None:
            continue
        cast = spec["type_cast"]
        try:
            json_cast = cast(json_val) if json_val is not None else None
            ini_cast = cast(ini_val) if ini_val is not None else None
        except (ValueError, TypeError):
            diffs.append((key, json_val, ini_val, "type_cast_error"))
            continue
        if json_cast != ini_cast:
            diffs.append((key, json_val, ini_val))
    return diffs


@pytest.mark.integration
class TestConfigFilesExist:
    """Both config files should exist and be readable."""

    def test_pipeline_config_json_exists(self):
        """pipeline_config.json must exist."""
        assert PIPELINE_CONFIG.exists(), f"Missing: {PIPELINE_CONFIG}"

    def test_config_ini_exists(self):
        """config.ini must exist."""
        assert CONFIG_INI.exists(), f"Missing: {CONFIG_INI}"


@pytest.mark.integration
class TestPipelineConfigJson:
    """pipeline_config.json should parse correctly."""

    def test_load_and_parse(self):
        """Loading pipeline_config.json should not raise."""
        cfg = load_pipeline_json()
        assert isinstance(cfg, dict)

    def test_has_required_sections(self):
        """pipeline_config.json must have paths, pipeline, scraper, classify, crossref sections."""
        cfg = load_pipeline_json()
        for section in ("paths", "pipeline", "scraper", "classify", "crossref"):
            assert section in cfg, f"Missing section: {section}"

    def test_required_paths_present(self):
        """paths section must have all known path keys."""
        cfg = load_pipeline_json()
        paths = cfg.get("paths", {})
        for key in ("supplier_excel", "pdf_dir", "input_excel_dir", "labeled_dir", "master_excel"):
            assert key in paths, f"Missing path key: {key}"

    def test_threshold_is_int(self):
        """crossref.threshold must be an integer."""
        cfg = load_pipeline_json()
        threshold = cfg.get("crossref", {}).get("threshold")
        assert isinstance(threshold, int), f"threshold is {type(threshold).__name__}, expected int"


@pytest.mark.integration
class TestConfigIni:
    """config.ini should parse correctly."""

    def test_load_and_parse(self):
        """Loading config.ini should not raise."""
        cfg = load_config_ini()
        assert isinstance(cfg, dict)
        assert "DEFAULT" in cfg

    def test_default_section_has_required_keys(self):
        """DEFAULT section must have all required keys."""
        cfg = load_config_ini()
        defaults = cfg.get("DEFAULT", {})
        for key in ("max_concurrent", "request_delay", "page_timeout",
                     "max_pages_per_site", "match_threshold", "max_pdf_size_mb",
                     "min_pdf_size_bytes", "strict_content_validation"):
            assert key in defaults, f"Missing key in config.ini DEFAULT: {key}"

    def test_values_are_parseable(self):
        """All values in config.ini DEFAULT must be parseable to their expected types."""
        cfg = load_config_ini()
        defaults = cfg.get("DEFAULT", {})
        for key, spec in OVERLAPPING_KEYS.items():
            val = defaults.get(spec["ini_key"])
            assert val is not None, f"Missing ini key: {spec['ini_key']}"
            try:
                spec["type_cast"](val)
            except (ValueError, TypeError) as e:
                pytest.fail(f"Cannot parse {spec['ini_key']}={val!r}: {e}")


@pytest.mark.integration
class TestConfigConsistency:
    """Detect drift between pipeline_config.json and config.ini."""

    def test_overlapping_keys_coverage(self):
        """All overlapping keys should be loadable from both configs."""
        json_cfg = load_pipeline_json()
        ini_cfg = load_config_ini()
        ini_defaults = ini_cfg.get("DEFAULT", {})

        for key, spec in OVERLAPPING_KEYS.items():
            json_val = _json_get(json_cfg, spec["json_path"])
            ini_val = ini_defaults.get(spec["ini_key"])
            assert json_val is not None, f"JSON missing key: {'.'.join(spec['json_path'])}"
            assert ini_val is not None, f"INI missing key: {spec['ini_key']}"

    def test_no_drift_in_overlapping_keys(self):
        """
        Overlapping keys between pipeline_config.json and config.ini
        should have consistent values.
        """
        json_cfg = load_pipeline_json()
        ini_cfg = load_config_ini()
        diffs = _compare_overlapping_keys(json_cfg, ini_cfg)

        if diffs:
            msg = ["Config drift detected between pipeline_config.json and config.ini:"]
            for key, jv, iv in diffs:
                msg.append(f"  {key}: JSON={jv!r}  INI={iv!r}")
            pytest.fail("\n".join(msg))

    def test_drift_report_format(self):
        """The diff report should be a list of 3-tuples."""
        json_cfg = load_pipeline_json()
        ini_cfg = load_config_ini()
        diffs = _compare_overlapping_keys(json_cfg, ini_cfg)
        for d in diffs:
            assert len(d) == 3 or (len(d) == 4 and d[3] == "type_cast_error")
