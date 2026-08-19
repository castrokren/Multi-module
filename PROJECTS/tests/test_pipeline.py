"""
Unit Tests for Pipeline Orchestrator (pipeline.py).

Tests config loading, path validation, import helpers, CLI parsing,
and main() stage dispatch logic.

Run with: python -m pytest tests/test_pipeline.py -v -m unit
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

_sec_dir = str(Path(__file__).resolve().parents[1] / "src" / "services" / "security")
if _sec_dir not in sys.path:
    sys.path.insert(0, _sec_dir)
from defender_scan import ScanResult, ScanVerdict  # noqa: E402

from pipeline import (
    _collect_matched_pdfs,
    _import_from_file,
    _normalized_config,
    _validate_paths,
    _resolve_path,
    PROJECT_ROOT,
)


# ============================================================================
# _import_from_file
# ============================================================================


class TestImportFromFile:
    @pytest.mark.unit
    def test_imports_existing_symbol(self, tmp_path):
        mod_file = tmp_path / "dummy_mod.py"
        mod_file.write_text("MY_CONST = 42\n")
        result = _import_from_file("dummy_mod", mod_file, "MY_CONST")
        assert result == 42

    @pytest.mark.unit
    def test_raises_on_missing_file(self):
        missing = Path("C:/does_not_exist/non_existent.py")
        with pytest.raises((ImportError, FileNotFoundError)):
            _import_from_file("bad", missing, "anything")

    @pytest.mark.unit
    def test_raises_import_error_on_missing_symbol(self, tmp_path):
        mod_file = tmp_path / "empty_mod.py"
        mod_file.write_text("")
        with pytest.raises(ImportError, match="does not define"):
            _import_from_file("empty_mod", mod_file, "NON_EXISTENT")

    @pytest.mark.unit
    def test_raises_when_spec_is_none(self):
        with patch("pipeline.importlib.util.spec_from_file_location", return_value=None):
            with pytest.raises(ImportError, match="Unable to load module spec"):
                _import_from_file("x", Path("x.py"), "y")


# ============================================================================
# _normalized_config
# ============================================================================


class TestNormalizedConfig:
    @pytest.mark.unit
    def test_resolves_path_fields(self):
        cfg = {
            "paths": {
                "supplier_excel": "data/input.xlsx",
                "pdf_dir": "output/pdfs",
                "input_excel_dir": "data/input",
                "labeled_dir": "data/labeled",
                "master_excel": "data/master.xlsx",
                "master_list": "data/master_list.xlsx",
                "results_dir": "data/results",
            },
            "classify": {
                "hw_keywords_file": "config/hw.txt",
                "sw_keywords_file": "config/sw.txt",
                "ni_keywords_file": "config/ni.txt",
            },
        }
        normalized = _normalized_config(cfg)
        for key in ("supplier_excel", "pdf_dir", "input_excel_dir", "labeled_dir",
                    "master_excel", "master_list", "results_dir"):
            resolved = normalized["paths"][key]
            assert resolved.startswith("C:") or resolved.startswith("/")
        for key in ("hw_keywords_file", "sw_keywords_file", "ni_keywords_file"):
            resolved = normalized["classify"][key]
            assert resolved.startswith("C:") or resolved.startswith("/")

    @pytest.mark.unit
    def test_handles_missing_paths_key(self):
        normalized = _normalized_config({})
        for key in ("supplier_excel", "pdf_dir", "input_excel_dir", "labeled_dir",
                    "master_excel", "master_list", "results_dir"):
            assert normalized["paths"][key] == ""

    @pytest.mark.unit
    def test_handles_missing_classify_key(self):
        cfg = {"paths": {}}
        normalized = _normalized_config(cfg)
        for key in ("hw_keywords_file", "sw_keywords_file", "ni_keywords_file"):
            assert normalized["classify"][key] == ""

    @pytest.mark.unit
    def test_handles_empty_path_values(self):
        cfg = {"paths": {"supplier_excel": "", "pdf_dir": None}}
        normalized = _normalized_config(cfg)
        assert normalized["paths"]["supplier_excel"] == ""
        assert normalized["paths"]["pdf_dir"] == ""

    @pytest.mark.unit
    def test_preserves_absolute_paths(self):
        cfg = {"paths": {"supplier_excel": "C:/Data/input.xlsx"}}
        normalized = _normalized_config(cfg)
        assert normalized["paths"]["supplier_excel"] == "C:\\Data\\input.xlsx"

    @pytest.mark.unit
    def test_unknown_pipeline_keys_preserved(self):
        cfg = {"pipeline": {"some_future_flag": True}, "paths": {}}
        normalized = _normalized_config(cfg)
        assert normalized["pipeline"]["some_future_flag"] is True


# ============================================================================
# _resolve_path
# ============================================================================


class TestResolvePath:
    @pytest.mark.unit
    def test_returns_empty_for_none(self):
        assert _resolve_path(None) == ""

    @pytest.mark.unit
    def test_returns_empty_for_empty(self):
        assert _resolve_path("") == ""

    @pytest.mark.unit
    def test_resolves_relative_path(self):
        resolved = _resolve_path("some/relative/path")
        assert (PROJECT_ROOT / "some/relative/path").resolve() == Path(resolved)

    @pytest.mark.unit
    def test_passes_through_absolute_path(self):
        abs_path = "C:/Projects/Crawler/PROJECTS/src/services/pipeline_config.json"
        assert _resolve_path(abs_path) == abs_path.replace("/", "\\")


# ============================================================================
# _validate_paths
# ============================================================================


class TestValidatePaths:
    @pytest.fixture
    def sample_cfg(self):
        return {
            "paths": {
                "supplier_excel": "C:/Data/input.xlsx",
                "pdf_dir": "C:/Data/pdfs",
                "input_excel_dir": "C:/Data/input",
                "labeled_dir": "C:/Data/labeled",
                "master_excel": "C:/Data/master.xlsx",
            },
            "classify": {
                "hw_keywords_file": "C:/config/hw.txt",
                "sw_keywords_file": "C:/config/sw.txt",
                "ni_keywords_file": "",
            },
        }

    @pytest.mark.unit
    def test_returns_errors_when_paths_missing(self, sample_cfg):
        stages = {"scraper": True, "classify": False, "crossref": False}
        with patch("os.path.exists", return_value=False):
            errors = _validate_paths(sample_cfg, stages)
            assert any("supplier_excel" in e for e in errors)

    @pytest.mark.unit
    def test_no_errors_when_all_paths_exist(self, sample_cfg):
        stages = {"scraper": True, "classify": True, "crossref": True}
        with patch("os.path.exists", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):
            errors = _validate_paths(sample_cfg, stages)
            assert errors == []

    @pytest.mark.unit
    def test_skips_disabled_stages(self, sample_cfg):
        stages = {"scraper": False, "classify": False, "crossref": False}
        with patch("os.path.exists", return_value=False):
            errors = _validate_paths(sample_cfg, stages)
            assert errors == []

    @pytest.mark.unit
    def test_reports_missing_keyword_file(self):
        cfg = {
            "paths": {"input_excel_dir": "C:/input"},
            "classify": {"hw_keywords_file": "C:/nonexistent.txt",
                         "sw_keywords_file": "", "ni_keywords_file": ""},
        }
        stages = {"scraper": False, "classify": True, "crossref": False}
        with patch("os.path.exists", return_value=True), \
             patch("pathlib.Path.exists", return_value=False):
            errors = _validate_paths(cfg, stages)
            assert any("keyword" in e for e in errors)

    @pytest.mark.unit
    def test_handles_missing_pdf_dir_parent(self, sample_cfg):
        stages = {"scraper": True, "classify": False, "crossref": False}
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "C:\\Data\\input.xlsx"
            errors = _validate_paths(sample_cfg, stages)
            assert any("parent directory" in e for e in errors)


# ============================================================================
# CLI argument parsing (main uses argparse)
# ============================================================================


class TestCLIParsing:
    @pytest.mark.unit
    def test_default_args(self):
        with patch("sys.argv", ["pipeline.py"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr, \
                 patch("pipeline.run_crossref") as m_cr:
                m_dc.return_value = True
                m_sc.return_value = True
                m_cl.return_value = True
                m_sr.return_value = True
                m_cr.return_value = True
                from pipeline import main
                main()
                m_dc.assert_called_once()
                m_sc.assert_called_once()
                m_cl.assert_called_once()
                m_sr.assert_called_once()
                m_cr.assert_called_once()

    @pytest.mark.unit
    def test_only_scraper_flag(self):
        with patch("sys.argv", ["pipeline.py", "--only-scraper"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr, \
                 patch("pipeline.run_crossref") as m_cr:
                m_sc.return_value = True
                from pipeline import main
                main()
                m_sc.assert_called_once()
                m_dc.assert_not_called()
                m_cl.assert_not_called()
                m_sr.assert_not_called()
                m_cr.assert_not_called()

    @pytest.mark.unit
    def test_skip_scraper_flag(self):
        with patch("sys.argv", ["pipeline.py", "--skip-scraper"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr, \
                 patch("pipeline.run_crossref") as m_cr:
                m_dc.return_value = True
                m_cl.return_value = True
                m_sr.return_value = True
                m_cr.return_value = True
                from pipeline import main
                main()
                m_sc.assert_not_called()
                m_dc.assert_called_once()

    @pytest.mark.unit
    def test_dry_run_does_not_run_stages(self):
        with patch("sys.argv", ["pipeline.py", "--dry-run"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr, \
                 patch("pipeline.run_crossref") as m_cr:
                from pipeline import main
                main()
                m_dc.assert_not_called()
                m_sc.assert_not_called()
                m_cl.assert_not_called()
                m_sr.assert_not_called()
                m_cr.assert_not_called()

    @pytest.mark.unit
    def test_config_path_respected(self):
        custom_cfg = "C:/custom/config.json"
        base_cfg = {
            "pipeline": {},
            "paths": {
                "supplier_excel": "C:/Data/input.xlsx",
                "pdf_dir": "C:/Data/pdfs",
                "input_excel_dir": "C:/Data/input",
                "labeled_dir": "C:/Data/labeled",
                "master_excel": "C:/Data/master.xlsx",
                "results_dir": "C:/logs",
            },
            "scraper": {},
            "classify": {},
            "crossref": {},
            "supplier_resolution": {"enabled": False},
        }
        with patch("sys.argv", ["pipeline.py", "--config", custom_cfg]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = base_cfg
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner", return_value=True), \
                 patch("pipeline.run_scraper", return_value=True), \
                 patch("pipeline.run_classify", return_value=True), \
                 patch("pipeline.run_supplier_resolution", return_value=True), \
                 patch("pipeline.run_crossref", return_value=True):
                from pipeline import main
                main()
                mock_load.assert_called_once_with(custom_cfg)

    @pytest.mark.unit
    def test_only_crossref_flag(self):
        with patch("sys.argv", ["pipeline.py", "--only-crossref"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_crossref") as m_cr, \
                 patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr:
                m_cr.return_value = True
                from pipeline import main
                main()
                m_cr.assert_called_once()
                m_dc.assert_not_called()
                m_sc.assert_not_called()
                m_cl.assert_not_called()
                m_sr.assert_not_called()

    @pytest.mark.unit
    def test_dry_run_with_errors_logs_and_returns(self):
        with patch("sys.argv", ["pipeline.py", "--dry-run"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=["some error"]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger") as mock_logger:
            mock_load.return_value = {"pipeline": {}, "paths": {"results_dir": "C:/logs"}}
            mock_norm.side_effect = lambda x: x
            from pipeline import main
            main()
            mock_logger.error.assert_any_call("Dry run - %d path error(s) found", 1)


# ============================================================================
# main() stage dispatch
# ============================================================================


class TestMainDispatch:
    @pytest.mark.unit
    def test_config_controls_default_flags(self):
        with patch("sys.argv", ["pipeline.py"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            pipe_cfg = {
                "pipeline": {
                    "run_data_cleaner": False,
                    "run_scraper": False,
                    "run_classify": True,
                    "run_supplier_resolution": False,
                    "run_crossref": True,
                },
                "paths": {"results_dir": "C:/logs"},
            }
            mock_load.return_value = pipe_cfg
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner") as m_dc, \
                 patch("pipeline.run_scraper") as m_sc, \
                 patch("pipeline.run_classify") as m_cl, \
                 patch("pipeline.run_supplier_resolution") as m_sr, \
                 patch("pipeline.run_crossref") as m_cr:
                m_cl.return_value = True
                m_cr.return_value = True
                from pipeline import main
                main()
                m_dc.assert_not_called()
                m_sc.assert_not_called()
                m_cl.assert_called_once()
                m_sr.assert_not_called()
                m_cr.assert_called_once()

    @pytest.mark.unit
    def test_stop_on_failure_aborts_pipeline(self):
        base_cfg = {
            "pipeline": {"stop_on_failure": True},
            "paths": {
                "supplier_excel": "C:/Data/input.xlsx",
                "pdf_dir": "C:/Data/pdfs",
                "input_excel_dir": "C:/Data/input",
                "labeled_dir": "C:/Data/labeled",
                "master_excel": "C:/Data/master.xlsx",
                "results_dir": "C:/logs",
            },
            "scraper": {},
            "classify": {},
            "crossref": {},
            "supplier_resolution": {"enabled": False},
        }
        with patch("sys.argv", ["pipeline.py"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"), \
             patch("pipeline.sys.exit", side_effect=SystemExit(1)) as mock_exit:
            mock_load.return_value = base_cfg
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner", return_value=False), \
                 patch("pipeline.run_scraper", return_value=True):
                from pipeline import main
                try:
                    main()
                except SystemExit:
                    pass
                mock_exit.assert_called_once_with(1)

    @pytest.mark.unit
    def test_continue_on_failure_when_stop_on_failure_false(self):
        base_cfg = {
            "pipeline": {"stop_on_failure": False},
            "paths": {
                "supplier_excel": "C:/Data/input.xlsx",
                "pdf_dir": "C:/Data/pdfs",
                "input_excel_dir": "C:/Data/input",
                "labeled_dir": "C:/Data/labeled",
                "master_excel": "C:/Data/master.xlsx",
                "results_dir": "C:/logs",
            },
            "scraper": {},
            "classify": {},
            "crossref": {},
            "supplier_resolution": {"enabled": False},
        }
        with patch("sys.argv", ["pipeline.py"]), \
             patch("pipeline._load_config") as mock_load, \
             patch("pipeline._normalized_config") as mock_norm, \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"), \
             patch("pipeline.sys.exit", side_effect=SystemExit(1)) as mock_exit:
            mock_load.return_value = base_cfg
            mock_norm.side_effect = lambda x: x
            with patch("pipeline.run_data_cleaner", return_value=False), \
                 patch("pipeline.run_scraper", return_value=False), \
                 patch("pipeline.run_classify", return_value=False), \
                 patch("pipeline.run_supplier_resolution", return_value=False), \
                 patch("pipeline.run_crossref", return_value=False):
                from pipeline import main
                try:
                    main()
                except SystemExit:
                    pass
                mock_exit.assert_called_once_with(1)


# ============================================================================
# _collect_matched_pdfs (Gate 3 - pre-transfer malware scan)
# ============================================================================


class TestCollectMatchedPdfsGate:
    @pytest.mark.unit
    def test_clean_pdf_copied(self, tmp_path):
        src = tmp_path / "supplier" / "catalog.pdf"
        src.parent.mkdir()
        src.write_bytes(b"%PDF")
        review = tmp_path / "review" / "20260101_000000"
        q = tmp_path / "quarantine"
        with patch("pipeline.scan_file",
                   return_value=ScanResult(ScanVerdict.CLEAN, "no_threats")):
            _collect_matched_pdfs([{"Matched PDF": str(src)}], review, str(q))
        assert (review / "catalog.pdf").exists()
        assert not list(q.rglob("*.pdf"))

    @pytest.mark.unit
    def test_infected_pdf_quarantined_not_copied(self, tmp_path):
        src = tmp_path / "supplier" / "bad.pdf"
        src.parent.mkdir()
        src.write_bytes(b"%PDF")
        review = tmp_path / "review" / "20260101_000000"
        q = tmp_path / "quarantine"
        with patch("pipeline.scan_file",
                   return_value=ScanResult(ScanVerdict.INFECTED, "Threat found")):
            _collect_matched_pdfs([{"Matched PDF": str(src)}], review, str(q))
        assert not (review / "bad.pdf").exists()
        assert not src.exists()
        assert list(q.rglob("*.pdf"))

    @pytest.mark.unit
    def test_missing_file_skipped(self, tmp_path):
        review = tmp_path / "review" / "20260101_000000"
        with patch("pipeline.scan_file") as fake_scan:
            _collect_matched_pdfs([{"Matched PDF": "C:/nope/missing.pdf"}],
                                  review, str(tmp_path / "q"))
        fake_scan.assert_not_called()
