"""Unit tests for 7-day freshness / skip-recent logic."""
import json, os, shutil, tempfile, sys
from datetime import datetime, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scraper_engine import ScraperEngine


class TestScrapeState:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _e(self, **kw):
        return ScraperEngine(**kw)

    def test_state_file_path(self):
        e = self._e()
        assert e._scrape_state_path(self.tmp) == os.path.join(self.tmp, ".scraper_state.json")

    def test_load_missing_returns_empty(self):
        assert self._e()._load_scrape_state(self.tmp) == {}

    def test_load_valid_file(self):
        e = self._e()
        data = {"Acme": "2026-05-10T10:00:00"}
        with open(e._scrape_state_path(self.tmp), "w") as f:
            json.dump(data, f)
        assert e._load_scrape_state(self.tmp) == data

    def test_load_corrupted_returns_empty(self):
        e = self._e()
        with open(e._scrape_state_path(self.tmp), "w") as f:
            f.write("not json {{{")
        assert e._load_scrape_state(self.tmp) == {}

    def test_save_and_reload(self):
        e = self._e()
        state = {"Acme": datetime.utcnow().isoformat()}
        e._save_scrape_state(state, self.tmp)
        assert e._load_scrape_state(self.tmp) == state

    def test_save_no_tmp_leftover(self):
        e = self._e()
        e._save_scrape_state({"X": "2026-01-01T00:00:00"}, self.tmp)
        assert not os.path.exists(e._scrape_state_path(self.tmp) + ".tmp")

    def test_unknown_supplier_is_due(self):
        assert self._e(days_before_rescrape=7)._is_due("New", {}) is True

    def test_recent_supplier_skipped(self):
        recent = (datetime.utcnow() - timedelta(days=3)).isoformat()
        assert self._e(days_before_rescrape=7)._is_due("Acme", {"Acme": recent}) is False

    def test_stale_supplier_is_due(self):
        old = (datetime.utcnow() - timedelta(days=8)).isoformat()
        assert self._e(days_before_rescrape=7)._is_due("Acme", {"Acme": old}) is True

    def test_exactly_at_boundary_is_due(self):
        boundary = (datetime.utcnow() - timedelta(days=7)).isoformat()
        assert self._e(days_before_rescrape=7)._is_due("Acme", {"Acme": boundary}) is True

    def test_corrupt_timestamp_treated_as_due(self):
        assert self._e()._is_due("Acme", {"Acme": "not-a-date"}) is True

    def test_custom_days_window(self):
        e = self._e(days_before_rescrape=30)
        recent = (datetime.utcnow() - timedelta(days=20)).isoformat()
        assert e._is_due("Acme", {"Acme": recent}) is False
        old = (datetime.utcnow() - timedelta(days=31)).isoformat()
        assert e._is_due("Acme", {"Acme": old}) is True
