"""Egress proxy control tests for _make_session() and ScraperEngine.run()."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper_engine import ScraperEngine, _make_session

PROXY_URL = "http://proxy.corp.internal:8080"


class TestMakeSessionProxy:
    def test_no_proxy_configured_by_default(self):
        s = _make_session()
        assert s.proxies == {}

    def test_proxy_applied_when_configured(self):
        net = {"http_proxy": "http://proxy.http:8080", "https_proxy": PROXY_URL}
        s = _make_session(network_cfg=net)
        assert s.proxies["http"] == "http://proxy.http:8080"
        assert s.proxies["https"] == PROXY_URL

    def test_proxy_only_for_schemes_configured(self):
        s = _make_session(network_cfg={"https_proxy": PROXY_URL})
        assert s.proxies == {"https": PROXY_URL}

    def test_require_proxy_without_config_raises(self):
        with pytest.raises(RuntimeError):
            _make_session(network_cfg={"require_proxy": True})

    def test_require_proxy_with_config_passes(self):
        s = _make_session(network_cfg={"require_proxy": True, "https_proxy": PROXY_URL})
        assert s.proxies["https"] == PROXY_URL

    def test_trust_env_false_by_default(self):
        s = _make_session()
        assert s.trust_env is False

    def test_trust_env_false_ignores_env_proxy(self):
        with patch("requests.utils.getproxies", return_value={"https": PROXY_URL}):
            s = _make_session(network_cfg={})
            assert s.trust_env is False
            merged = s.merge_environment_settings(
                "https://example.com/doc.pdf", {}, None, None, None)
            assert merged["proxies"] == {}

    def test_trust_env_true_honors_env_proxy(self):
        with patch("requests.utils.getproxies", return_value={"https": PROXY_URL}):
            s = _make_session(network_cfg={"trust_env_proxy": True})
            assert s.trust_env is True
            merged = s.merge_environment_settings(
                "https://example.com/doc.pdf", {}, None, None, None)
            assert merged["proxies"]["https"] == PROXY_URL


class TestRunFailClosed:
    def test_require_proxy_without_config_refuses_to_run(self, tmp_path):
        e = ScraperEngine(network_cfg={"require_proxy": True})
        with pytest.raises(RuntimeError):
            e.run("missing_suppliers.xlsx", str(tmp_path))

    def test_require_proxy_with_config_runs_setup(self, tmp_path):
        e = ScraperEngine(network_cfg={"require_proxy": True, "https_proxy": PROXY_URL})
        # Reaches supplier loading (returns empty) rather than raising.
        summary = e.run("missing_suppliers.xlsx", str(tmp_path))
        assert summary["suppliers"] == 0