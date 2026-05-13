"""
Unit Tests for Data Cleaner Module

Tests all cleaning functions, pattern detection, and file operations.
Run with: pytest src/services/data-cleaning/tests/unit/test_data_cleaner.py -v
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parents[2]))
from data_cleaner import (
    clean_supplier_name,
    detect_corrupted_names,
    clean_excel_file,
    CLEANUP_PATTERNS,
)


class TestCleanSupplierName:
    """Test individual name cleaning function"""

    def test_clean_use_code_suffix(self):
        """Remove ***USE V#*** patterns"""
        assert clean_supplier_name("PHILIPS HEALTHCARE***USE V#79***") == "PHILIPS HEALTHCARE"
        assert clean_supplier_name("VWR INTERNATIONAL LLC***USE V#8026***") == "VWR INTERNATIONAL LLC"

    def test_clean_use_code_parens(self):
        """Remove (USE ...) patterns"""
        assert clean_supplier_name("COMPANY (USE CODE 123)") == "COMPANY"
        assert clean_supplier_name("ABC (USE 456)") == "ABC"

    def test_clean_trailing_asterisks(self):
        """Remove trailing asterisks"""
        assert clean_supplier_name("COMPANY***") == "COMPANY"
        assert clean_supplier_name("NAME**") == "NAME"
        assert clean_supplier_name("TEST*") == "TEST"

    def test_clean_leading_asterisks(self):
        """Remove leading asterisks"""
        assert clean_supplier_name("***COMPANY") == "COMPANY"
        assert clean_supplier_name("**NAME") == "NAME"
        assert clean_supplier_name("*TEST") == "TEST"

    def test_clean_multiple_spaces(self):
        """Normalize multiple spaces to single space"""
        assert clean_supplier_name("COMPANY  NAME") == "COMPANY NAME"
        assert clean_supplier_name("A   B   C") == "A B C"
        assert clean_supplier_name("TEST    CORP") == "TEST CORP"

    def test_clean_whitespace_trim(self):
        """Trim leading/trailing whitespace"""
        assert clean_supplier_name("  COMPANY  ") == "COMPANY"
        assert clean_supplier_name("\tNAME\t") == "NAME"
        assert clean_supplier_name(" \n TEST \n ") == "TEST"

    def test_clean_combined_issues(self):
        """Clean multiple issues in one name"""
        assert clean_supplier_name("  ***COMPANY***USE V#1***  ") == "COMPANY"
        assert clean_supplier_name("NAME  (USE 123)***") == "NAME"

    def test_clean_already_clean(self):
        """Names with no issues remain unchanged"""
        assert clean_supplier_name("CLEAN COMPANY NAME") == "CLEAN COMPANY NAME"
        assert clean_supplier_name("SIMPLE INC") == "SIMPLE INC"

    def test_clean_nan_values(self):
        """Handle NaN/None values gracefully"""
        assert pd.isna(clean_supplier_name(None))
        assert pd.isna(clean_supplier_name(float('nan')))

    def test_clean_empty_string(self):
        """Handle empty strings"""
        assert clean_supplier_name("") == ""
        assert clean_supplier_name("   ") == ""

    def test_clean_numeric_only(self):
        """Handle numeric names with cleaning patterns"""
        assert clean_supplier_name("***789***") == "789"
        assert clean_supplier_name("123***USE V#1***") == "123"

    def test_clean_special_chars_preserved(self):
        """Preserve valid special characters"""
        assert clean_supplier_name("COMPANY & CO") == "COMPANY & CO"
        assert clean_supplier_name("O'REILLY MEDIA") == "O'REILLY MEDIA"
        assert clean_supplier_name("AT&T INC") == "AT&T INC"

    def test_clean_case_preserved(self):
        """Preserve case"""
        assert clean_supplier_name("MiXeD CaSe***USE V#1***") == "MiXeD CaSe"
        assert clean_supplier_name("lowercase name") == "lowercase name"


class TestDetectCorruptedNames:
    """Test corruption detection"""

    def test_detect_use_code_suffix(self):
        """Detect ***USE V#*** patterns"""
        df = pd.DataFrame({
            "Supplier Name": ["PHILIPS***USE V#79***", "CLEAN NAME"]
        })
        issues = detect_corrupted_names(df, "Supplier Name")
        assert len(issues) == 1
        assert "use_code_suffix" in issues.iloc[0]["issues"]

    def test_detect_trailing_asterisks(self):
        """Detect trailing asterisks"""
        df = pd.DataFrame({
            "Supplier Name": ["NAME***", "CLEAN"]
        })
        issues = detect_corrupted_names(df, "Supplier Name")
        assert len(issues) == 1

    def test_detect_multiple_issues_same_row(self):
        """Detect multiple issues in same row"""
        df = pd.DataFrame({
            "Supplier Name": ["***NAME***USE V#1***"]
        })
        issues = detect_corrupted_names(df, "Supplier Name")
        assert len(issues) == 1
        assert len(issues.iloc[0]["issues"]) > 1

    def test_detect_no_issues(self):
        """Return empty when no issues"""
        df = pd.DataFrame({
            "Supplier Name": ["CLEAN NAME", "ANOTHER CLEAN", "THIRD CLEAN"]
        })
        issues = detect_corrupted_names(df, "Supplier Name")
        assert len(issues) == 0

    def test_detect_with_nan(self):
        """Handle NaN values gracefully"""
        df = pd.DataFrame({
            "Supplier Name": [None, "NAME***", pd.NA, "CLEAN"]
        })
        issues = detect_corrupted_names(df, "Supplier Name")
        assert len(issues) == 1  # Only the "NAME***" row

    def test_detect_wrong_column_raises(self):
        """Raise error if column doesn't exist"""
        df = pd.DataFrame({"Wrong Column": ["test"]})
        with pytest.raises(ValueError):
            detect_corrupted_names(df, "Supplier Name")


class TestCleanExcelFile:
    """Test Excel file cleaning"""

    def test_clean_single_file(self):
        """Clean a single Excel file"""
        # Create test Excel
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")
            df = pd.DataFrame({
                "Supplier Name": ["COMPANY***USE V#1***", "CLEAN NAME"],
                "Website": ["https://example.com", "https://test.com"]
            })
            df.to_excel(test_file, index=False)

            # Clean it
            result = clean_excel_file(test_file, dry_run=False)

            # Verify
            assert result["status"] == "success"
            assert result["rows_cleaned"] == 1
            assert result["rows_total"] == 2

            # Verify file was updated
            df_cleaned = pd.read_excel(test_file)
            assert df_cleaned.iloc[0]["Supplier Name"] == "COMPANY"

    def test_clean_dry_run(self):
        """Dry run doesn't modify file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")
            df = pd.DataFrame({
                "Supplier Name": ["COMPANY***USE V#1***"]
            })
            df.to_excel(test_file, index=False)

            # Dry run
            result = clean_excel_file(test_file, dry_run=True)

            # Verify
            assert result["status"] == "dry_run_complete"
            assert result["rows_cleaned"] == 1

            # Verify file is unchanged
            df_original = pd.read_excel(test_file)
            assert df_original.iloc[0]["Supplier Name"] == "COMPANY***USE V#1***"

    def test_clean_preserves_other_columns(self):
        """Cleaning only affects supplier column"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")
            df = pd.DataFrame({
                "Supplier Name": ["COMPANY***"],
                "Website": ["https://example.com"],
                "Contact": ["john@example.com"],
                "Phone": ["555-1234"]
            })
            df.to_excel(test_file, index=False)

            clean_excel_file(test_file, dry_run=False)

            df_cleaned = pd.read_excel(test_file)
            assert df_cleaned.iloc[0]["Website"] == "https://example.com"
            assert df_cleaned.iloc[0]["Contact"] == "john@example.com"
            assert df_cleaned.iloc[0]["Phone"] == "555-1234"

    def test_clean_missing_file_raises(self):
        """Raise error if file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            clean_excel_file("/nonexistent/file.xlsx")

    def test_clean_wrong_column_raises(self):
        """Raise error if supplier column missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")
            df = pd.DataFrame({"Wrong Column": ["data"]})
            df.to_excel(test_file, index=False)

            with pytest.raises(ValueError):
                clean_excel_file(test_file)

    def test_clean_large_file(self):
        """Clean large file (1000+ rows)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")

            # Create 1000-row file with 10% corruption
            data = {
                "Supplier Name": [
                    f"COMPANY{i}***USE V#{i}***" if i % 10 == 0 else f"CLEAN NAME {i}"
                    for i in range(1000)
                ]
            }
            df = pd.DataFrame(data)
            df.to_excel(test_file, index=False)

            result = clean_excel_file(test_file, dry_run=False)

            assert result["rows_total"] == 1000
            assert result["rows_cleaned"] == 100

    def test_clean_no_issues(self):
        """Clean file with no issues"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.xlsx")
            df = pd.DataFrame({
                "Supplier Name": ["CLEAN NAME 1", "CLEAN NAME 2", "CLEAN NAME 3"]
            })
            df.to_excel(test_file, index=False)

            result = clean_excel_file(test_file, dry_run=False)

            assert result["rows_cleaned"] == 0


class TestPatternDefinitions:
    """Test pattern definitions are valid"""

    def test_all_patterns_are_valid_regex(self):
        """All patterns should be valid regex"""
        import re
        for name, pattern in CLEANUP_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Pattern '{name}' is invalid regex: {e}")

    def test_patterns_not_empty(self):
        """Pattern dict should have patterns"""
        assert len(CLEANUP_PATTERNS) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unicode_characters(self):
        """Handle Unicode characters"""
        assert clean_supplier_name("BJÖRK ÅSTRÖM***USE V#1***") == "BJÖRK ÅSTRÖM"
        assert clean_supplier_name("中文公司***") == "中文公司"

    def test_very_long_name(self):
        """Handle very long supplier names"""
        long_name = "A" * 1000 + "***USE V#1***"
        result = clean_supplier_name(long_name)
        assert len(result) == 1000

    def test_only_asterisks(self):
        """Handle names that are only asterisks"""
        assert clean_supplier_name("***") == ""

    def test_nested_patterns(self):
        """Handle nested/overlapping patterns"""
        assert clean_supplier_name("***NAME***USE V#1***(USE 2)***") == "NAME"

    def test_case_insensitive_detection(self):
        """Pattern detection should be case-insensitive"""
        assert clean_supplier_name("company***use v#1***") == "company"
        assert clean_supplier_name("COMPANY***USE V#1***") == "COMPANY"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
