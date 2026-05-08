import sys
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from supplier_resolver import _extract_suppliers


class TestExtractSuppliers:
    def _make_excel(self, data: dict, path: str) -> str:
        pd.DataFrame(data).to_excel(path, index=False)
        return path

    def test_extracts_unique_suppliers(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "Supplier Name": ["Zeiss", "Zeiss", "Olympus", "Beckman", "Beckman",
                              "Zeiss", "Olympus", "Beckman", "Olympus", "Zeiss"],
            "Item Code": list(range(10)),
        }, excel)
        result = _extract_suppliers(excel)
        assert len(result) == 3
        assert set(result) == {"ZEISS", "OLYMPUS", "BECKMAN"}

    def test_normalizes_to_uppercase(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "Supplier Name": ["ancare corp", "Beckman Coulter", "ZEISS"],
        }, excel)
        result = _extract_suppliers(excel)
        assert all(s == s.upper() for s in result)

    def test_skips_null_values(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "Supplier Name": ["Zeiss", None, "Olympus", None, "Zeiss"],
        }, excel)
        result = _extract_suppliers(excel)
        assert None not in result
        assert len(result) == 2

    def test_missing_supplier_column_raises(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "Item Code": ["A001", "A002"],
            "Description": ["Microscope", "Centrifuge"],
        }, excel)
        with pytest.raises(ValueError, match="No supplier column found"):
            _extract_suppliers(excel)

    def test_finds_supplier_column_case_insensitive(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "SUPPLIER NAME": ["Zeiss", "Olympus"],
        }, excel)
        result = _extract_suppliers(excel)
        assert set(result) == {"ZEISS", "OLYMPUS"}

    def test_strips_whitespace(self, tmp_path):
        excel = str(tmp_path / "test.xlsx")
        self._make_excel({
            "Supplier Name": ["  Zeiss  ", "Olympus ", " Beckman"],
        }, excel)
        result = _extract_suppliers(excel)
        assert "ZEISS" in result
        assert "OLYMPUS" in result
        assert "BECKMAN" in result
