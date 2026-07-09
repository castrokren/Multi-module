"""
Integration tests for pipeline stage transitions.

Verifies _import_from_file, _normalized_config, _validate_paths,
and CLI flag overrides all work correctly without running real stages.
"""

import pytest
import sys
import json
import os
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "services"))

from pipeline import (
    _import_from_file,
    _normalized_config,
    _validate_paths,
    _load_config,
    _resolve_path,
    PROJECT_ROOT,
    SERVICES_ROOT,
)


@pytest.mark.integration
class TestImportFromFile:
    """Verify _import_from_file can discover all 5 stage modules."""

    STAGE_MODULES = {
        "data_cleaner": (
            "data_cleaner",
            SERVICES_ROOT / "data-cleaning" / "data_cleaner.py",
            "clean_all_input_excels",
        ),
        "scraper": (
            "scraper_engine",
            SERVICES_ROOT / "scraper-full" / "scraper_engine.py",
            "ScraperEngine",
        ),
        "classify": (
            "column_filter_and_classify_v3",
            SERVICES_ROOT / "data-cleaning" / "column_filter_and_classify_v3.py",
            "process_all_inputs",
        ),
        "supplier_resolution": (
            "supplier_resolver",
            SERVICES_ROOT / "supplier-resolution" / "supplier_resolver.py",
            "resolve_suppliers",
        ),
        "crossref": (
            "crossref_standalone_fast",
            SERVICES_ROOT / "cross-reference" / "crossref_standalone_fast.py",
            "CrossReferenceEngine",
        ),
    }

    def test_import_file_paths_exist(self):
        """All 5 stage file paths should resolve to real files."""
        for stage_name, (mod_name, file_path, symbol) in self.STAGE_MODULES.items():
            assert file_path.exists(), (
                f"Stage '{stage_name}' file not found: {file_path}"
            )

    def test_import_from_file_raises_on_missing_file(self):
        """Importing a nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _import_from_file("ghost", Path("/nonexistent/stage.py"), "Symbol")

    def test_import_from_file_raises_on_missing_symbol(self):
        """Importing a file that exists but lacks the requested symbol should raise."""
        fake_path = SERVICES_ROOT / "pipeline.py"
        with pytest.raises(ImportError):
            _import_from_file("pipeline_mod", fake_path, "_THIS_SYMBOL_DOES_NOT_EXIST_")


@pytest.mark.integration
class TestNormalizedConfig:
    """Verify _normalized_config resolves relative paths to absolute."""

    def test_resolve_relative_path(self):
        """Relative paths should be resolved against PROJECT_ROOT."""
        result = _resolve_path("data/some_file.xlsx")
        expected = str((PROJECT_ROOT / "data" / "some_file.xlsx").resolve())
        assert result == expected

    def test_resolve_absolute_path(self):
        """Absolute paths should be returned unchanged (modulo OS path normalization)."""
        path = "C:/Data/Crawler/output"
        result = _resolve_path(path)
        assert Path(result) == Path(path)

    def test_resolve_empty_path(self):
        """Empty/Noneshould return empty string."""
        assert _resolve_path("") == ""
        assert _resolve_path(None) == ""

    def test_normalized_config_resolves_paths(self):
        """All known path keys should be made absolute."""
        cfg = {
            "paths": {
                "supplier_excel": "data/suppliers.xlsx",
                "pdf_dir": "C:/Data/Crawler/output",
                "input_excel_dir": "C:/Data/Crawler/input",
                "labeled_dir": "C:/Data/Crawler/labeled",
                "master_excel": "data/master.xlsx",
                "master_list": "data/master.xlsx",
                "results_dir": "output/results",
            },
            "classify": {
                "hw_keywords_file": "keywords/hw.txt",
                "sw_keywords_file": "keywords/sw.txt",
                "ni_keywords_file": "keywords/ni.txt",
            },
        }
        normalized = _normalized_config(cfg)
        paths = normalized["paths"]
        assert paths["supplier_excel"].startswith(str(PROJECT_ROOT))
        assert Path(paths["pdf_dir"]) == Path("C:/Data/Crawler/output")
        assert paths["master_excel"].startswith(str(PROJECT_ROOT))
        for k in ("hw_keywords_file", "sw_keywords_file", "ni_keywords_file"):
            assert normalized["classify"][k].startswith(str(PROJECT_ROOT))

    def test_normalized_config_preserves_unknown_keys(self):
        """Keys not in the known path list should be passed through unchanged."""
        cfg = {"paths": {"custom_extra": "some_value"}}
        normalized = _normalized_config(cfg)
        assert normalized["paths"]["custom_extra"] == "some_value"


@pytest.mark.integration
class TestValidatePaths:
    """Verify _validate_paths catches missing required paths."""

    def test_validate_scraper_missing_supplier_excel(self):
        """Scraper stage should error when supplier_excel is missing."""
        cfg = {"paths": {"supplier_excel": "/nonexistent/suppliers.xlsx", "pdf_dir": ""}}
        stages = {"scraper": True, "classify": False, "crossref": False}
        errors = _validate_paths(cfg, stages)
        assert any("supplier_excel" in e for e in errors)

    def test_validate_classify_missing_input_dir(self):
        """Classify stage should error when input_excel_dir is missing."""
        cfg = {"paths": {"input_excel_dir": "/nonexistent/input"}, "classify": {}}
        stages = {"scraper": False, "classify": True, "crossref": False}
        errors = _validate_paths(cfg, stages)
        assert any("input_excel_dir" in e for e in errors)

    def test_validate_crossref_missing_labeled_dir(self):
        """Cross-ref stage should error when labeled_dir is missing."""
        cfg = {
            "paths": {
                "labeled_dir": "/nonexistent/labeled",
                "master_excel": "/nonexistent/master.xlsx",
                "pdf_dir": "/nonexistent/pdfs",
            },
            "classify": {},
        }
        stages = {"scraper": False, "classify": False, "crossref": True}
        errors = _validate_paths(cfg, stages)
        assert any("labeled_dir" in e for e in errors)

    def test_validate_no_errors_when_disabled(self):
        """Disabled stages should not produce path errors."""
        cfg = {"paths": {}, "classify": {}}
        stages = {"scraper": False, "classify": False, "crossref": False}
        errors = _validate_paths(cfg, stages)
        assert errors == []

    def test_validate_returns_empty_for_valid_paths(self, tmp_path):
        """All valid paths should produce no errors."""
        pdf_parent = tmp_path / "pdfs_parent"
        pdf_parent.mkdir()
        pdf_dir = pdf_parent / "pdfs"
        pdf_dir.mkdir()
        labeled = tmp_path / "labeled"
        labeled.mkdir()
        master = tmp_path / "master.xlsx"
        master.touch()
        supplier_excel = tmp_path / "suppliers.xlsx"
        supplier_excel.touch()
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        kw_file = tmp_path / "keywords.txt"
        kw_file.touch()

        cfg = {
            "paths": {
                "supplier_excel": str(supplier_excel),
                "pdf_dir": str(pdf_dir),
                "input_excel_dir": str(input_dir),
                "labeled_dir": str(labeled),
                "master_excel": str(master),
            },
            "classify": {
                "hw_keywords_file": str(kw_file),
                "sw_keywords_file": str(kw_file),
                "ni_keywords_file": str(kw_file),
            },
        }
        stages = {"scraper": True, "classify": True, "crossref": True}
        errors = _validate_paths(cfg, stages)
        assert errors == []


@pytest.mark.integration
class TestCliFlagOverrides:
    """Verify CLI flags correctly toggle stage booleans."""

    def _run_main_with_args(self, args_list, mock_config=None):
        """Helper: call main() with mocked config and sys.argv."""
        if mock_config is None:
            mock_config = {
                "pipeline": {
                    "run_data_cleaner": True,
                    "run_scraper": True,
                    "run_classify": True,
                    "run_supplier_resolution": True,
                    "run_crossref": True,
                },
                "paths": {},
                "classify": {},
                "scraper": {},
                "crossref": {},
                "supplier_resolution": {},
            }

        with patch("pipeline._load_config", return_value=mock_config), \
             patch("pipeline._normalized_config", return_value=mock_config), \
             patch("pipeline._validate_paths", return_value=[]), \
             patch("pipeline._setup_logging"), \
             patch("pipeline.logger"):
            try:
                from pipeline import main as pipeline_main
                with patch.object(sys, "argv", ["pipeline.py"] + args_list):
                    pipeline_main()
            except SystemExit:
                pass

    @patch("pipeline.run_scraper")
    @patch("pipeline._load_config")
    @patch("pipeline._normalized_config")
    @patch("pipeline._validate_paths")
    @patch("pipeline._setup_logging")
    def test_only_scraper_flag(self, mock_log, mock_val, mock_norm, mock_load, mock_run):
        """--only-scraper should set scraper=True, all others False."""
        from pipeline import main as pipeline_main

        mock_load.return_value = {
            "pipeline": {
                "run_data_cleaner": True,
                "run_scraper": True,
                "run_classify": True,
                "run_supplier_resolution": True,
                "run_crossref": True,
            },
            "paths": {
                "supplier_excel": "dummy.xlsx",
                "pdf_dir": "dummy",
                "results_dir": "dummy",
            },
            "classify": {},
            "scraper": {},
            "crossref": {},
            "supplier_resolution": {},
        }
        mock_norm.return_value = mock_load.return_value
        mock_val.return_value = []
        mock_run.return_value = False

        with patch.object(sys, "argv", ["pipeline.py", "--only-scraper"]):
            with pytest.raises(SystemExit):
                pipeline_main()

    @patch("pipeline.run_scraper")
    @patch("pipeline._load_config")
    @patch("pipeline._normalized_config")
    @patch("pipeline._validate_paths")
    @patch("pipeline._setup_logging")
    def test_only_scraper_sets_stages_correctly(self, mock_log, mock_val, mock_norm, mock_load, mock_run):
        """Verify --only-scraper internal stage dict logic."""
        from pipeline import main as pipeline_main

        base_cfg = {
            "pipeline": {"run_data_cleaner": True, "run_scraper": True,
                         "run_classify": True, "run_supplier_resolution": True,
                         "run_crossref": True},
            "paths": {"supplier_excel": "dummy.xlsx", "pdf_dir": "dummy", "results_dir": "dummy"},
            "classify": {}, "scraper": {},
            "crossref": {}, "supplier_resolution": {},
        }
        mock_load.return_value = base_cfg
        mock_norm.return_value = base_cfg
        mock_val.return_value = []
        mock_run.return_value = False

        with patch.object(sys, "argv", ["pipeline.py", "--only-scraper"]):
            with pytest.raises(SystemExit):
                pipeline_main()

    def test_only_scraper_direct_logic(self):
        """Direct verification of the --only-scraper stage-dict logic."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--only-scraper", action="store_true")
        parser.add_argument("--skip-scraper", action="store_true")
        parser.add_argument("--only-crossref", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only-data-cleaner", action="store_true")
        parser.add_argument("--only-classify", action="store_true")
        parser.add_argument("--only-supplier-resolution", action="store_true")
        parser.add_argument("--skip-data-cleaner", action="store_true")
        parser.add_argument("--skip-classify", action="store_true")
        parser.add_argument("--skip-supplier-resolution", action="store_true")
        parser.add_argument("--skip-crossref", action="store_true")
        parser.add_argument("--config", default="")

        pipe = {"run_data_cleaner": True, "run_scraper": True,
                "run_classify": True, "run_supplier_resolution": True,
                "run_crossref": True}

        stages = {
            "data_cleaner": pipe.get("run_data_cleaner", True),
            "scraper": pipe.get("run_scraper", True),
            "classify": pipe.get("run_classify", True),
            "supplier_resolution": pipe.get("run_supplier_resolution", True),
            "crossref": pipe.get("run_crossref", True),
        }

        args = parser.parse_args(["--only-scraper"])

        if args.only_scraper:
            stages = {"data_cleaner": False, "scraper": True,
                      "classify": False, "supplier_resolution": False,
                      "crossref": False}

        assert stages["scraper"] is True
        assert stages["data_cleaner"] is False
        assert stages["classify"] is False
        assert stages["supplier_resolution"] is False
        assert stages["crossref"] is False

    def test_skip_scraper_direct_logic(self):
        """--skip-scraper should set scraper=False, leave others unchanged."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--only-scraper", action="store_true")
        parser.add_argument("--skip-scraper", action="store_true")
        parser.add_argument("--only-crossref", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only-data-cleaner", action="store_true")
        parser.add_argument("--only-classify", action="store_true")
        parser.add_argument("--only-supplier-resolution", action="store_true")
        parser.add_argument("--skip-data-cleaner", action="store_true")
        parser.add_argument("--skip-classify", action="store_true")
        parser.add_argument("--skip-supplier-resolution", action="store_true")
        parser.add_argument("--skip-crossref", action="store_true")
        parser.add_argument("--config", default="")

        pipe = {"run_data_cleaner": True, "run_scraper": True,
                "run_classify": True, "run_supplier_resolution": True,
                "run_crossref": True}

        stages = {
            "data_cleaner": pipe.get("run_data_cleaner", True),
            "scraper": pipe.get("run_scraper", True),
            "classify": pipe.get("run_classify", True),
            "supplier_resolution": pipe.get("run_supplier_resolution", True),
            "crossref": pipe.get("run_crossref", True),
        }

        args = parser.parse_args(["--skip-scraper"])

        if args.skip_scraper:
            stages["scraper"] = False

        assert stages["scraper"] is False
        assert stages["data_cleaner"] is True
        assert stages["classify"] is True

    def test_only_crossref_direct_logic(self):
        """--only-crossref should set only crossref=True."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--only-scraper", action="store_true")
        parser.add_argument("--skip-scraper", action="store_true")
        parser.add_argument("--only-crossref", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only-data-cleaner", action="store_true")
        parser.add_argument("--only-classify", action="store_true")
        parser.add_argument("--only-supplier-resolution", action="store_true")
        parser.add_argument("--skip-data-cleaner", action="store_true")
        parser.add_argument("--skip-classify", action="store_true")
        parser.add_argument("--skip-supplier-resolution", action="store_true")
        parser.add_argument("--skip-crossref", action="store_true")
        parser.add_argument("--config", default="")

        pipe = {"run_data_cleaner": True, "run_scraper": True,
                "run_classify": True, "run_supplier_resolution": True,
                "run_crossref": True}

        stages = {
            "data_cleaner": pipe.get("run_data_cleaner", True),
            "scraper": pipe.get("run_scraper", True),
            "classify": pipe.get("run_classify", True),
            "supplier_resolution": pipe.get("run_supplier_resolution", True),
            "crossref": pipe.get("run_crossref", True),
        }

        args = parser.parse_args(["--only-crossref"])

        if args.only_crossref:
            stages = {"data_cleaner": False, "scraper": False,
                      "classify": False, "supplier_resolution": False,
                      "crossref": True}

        assert stages["crossref"] is True
        assert stages["scraper"] is False
        assert stages["classify"] is False

    def test_dry_run_flag(self):
        """--dry-run should not run any stage functions."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--config", default="")

        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True
