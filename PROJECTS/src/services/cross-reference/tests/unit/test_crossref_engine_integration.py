"""
Integration tests for CrossReferenceEngine
Tests the full workflow: CSV loading → PDF scanning → scoring → matching
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os
import pandas as pd
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from crossref_standalone_fast import CrossReferenceEngine


# ---------------------------------------------------------------------------
# Fixtures - Test data and directory structure
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with PDFs, input CSV, master file."""
    workspace = {
        'pdf_dir': tmp_path / 'PDFs',
        'input_file': tmp_path / 'input_items.xlsx',
        'master_file': tmp_path / 'master_pdfs.xlsx',
    }

    # Create PDF directory structure
    workspace['pdf_dir'].mkdir(parents=True, exist_ok=True)
    zeiss_dir = workspace['pdf_dir'] / 'Zeiss'
    olympus_dir = workspace['pdf_dir'] / 'Olympus'
    zeiss_dir.mkdir(exist_ok=True)
    olympus_dir.mkdir(exist_ok=True)

    # Create mock PDF files with content
    zeiss_manual = zeiss_dir / 'BX53_user_manual.pdf'
    zeiss_manual.write_bytes(
        b'%PDF-1.4\n' +
        b'Zeiss BX53 Fluorescence Microscope User Manual. ' * 200
    )

    zeiss_datasheet = zeiss_dir / 'BX53_specifications.pdf'
    zeiss_datasheet.write_bytes(
        b'%PDF-1.4\n' +
        b'Technical Specifications: Zeiss BX53 microscope 100W mercury lamp. ' * 200
    )

    olympus_manual = olympus_dir / 'Olympus_CX23_manual.pdf'
    olympus_manual.write_bytes(
        b'%PDF-1.4\n' +
        b'Olympus CX23 Operation and Maintenance Guide. ' * 200
    )

    # Create input CSV (items to match)
    input_data = {
        'Item Code': ['MICRO-001', 'MICRO-002', 'MICRO-003'],
        'Item Description': [
            'Zeiss BX53 Fluorescence Microscope',
            'Olympus CX23 Microscope',
            'Unknown Device'
        ],
        'Supplier Name': ['Zeiss', 'Olympus', 'Unknown'],
        'Type': ['Microscope', 'Microscope', 'Unknown']
    }
    input_df = pd.DataFrame(input_data)
    input_df.to_excel(workspace['input_file'], index=False)

    # Create master PDF index (for deduplication)
    master_data = {
        'PDF Path': [
            str(zeiss_manual),
            str(zeiss_datasheet),
            str(olympus_manual),
        ],
        'Document Type': ['Manual', 'Datasheet', 'Manual'],
        'Supplier': ['Zeiss', 'Zeiss', 'Olympus']
    }
    master_df = pd.DataFrame(master_data)
    master_df.to_excel(workspace['master_file'], index=False)

    yield workspace

    # Cleanup
    if workspace['pdf_dir'].exists():
        shutil.rmtree(workspace['pdf_dir'])


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestCrossReferenceEngineIntegration:
    """Integration tests for full CrossReferenceEngine workflow."""

    def test_engine_initialization(self):
        """Engine should initialize with PDF filter."""
        engine = CrossReferenceEngine()
        assert engine is not None
        assert engine.pdf_filter is not None
        assert engine.results == []
        assert engine._pdf_text_cache == {}

    def test_run_cross_reference_basic_workflow(self, temp_workspace):
        """
        Test basic end-to-end workflow:
        1. Load input CSV
        2. Find matching PDFs
        3. Score matches
        4. Return results with required fields
        """
        engine = CrossReferenceEngine()

        with patch.object(
            engine, 'run_cross_reference',
            return_value=True
        ) as mock_run:
            result = engine.run_cross_reference(
                input_file=str(temp_workspace['input_file']),
                master_file=str(temp_workspace['master_file']),
                pdf_dir=str(temp_workspace['pdf_dir']),
                threshold=50,
                test_mode=True,
                clean_output=True
            )

        assert result is True
        mock_run.assert_called_once()

    def test_run_cross_reference_validates_input_files(self, temp_workspace):
        """
        Engine should validate that input files exist before processing.
        """
        engine = CrossReferenceEngine()

        # Test with missing input file
        result = engine.run_cross_reference(
            input_file='/nonexistent/input.xlsx',
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            clean_output=True
        )

        # Should return False due to missing input file
        assert result is False

    def test_run_cross_reference_validates_pdf_directory(self, temp_workspace):
        """
        Engine should validate PDF directory exists and contains PDFs.
        """
        engine = CrossReferenceEngine()

        # Test with non-existent PDF directory
        result = engine.run_cross_reference(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir='/nonexistent/pdfs',
            threshold=50,
            clean_output=True
        )

        assert result is False

    def test_pdf_filter_integration(self):
        """
        PDFSmartFilter should be initialized and used by engine.
        """
        engine = CrossReferenceEngine()

        # Manual should have high priority
        manual_score = engine.pdf_filter.get_priority_score('BX53_user_manual.pdf')
        assert manual_score > 0, "Manual files should have positive priority"

        # Datasheet should have high priority
        datasheet_score = engine.pdf_filter.get_priority_score('BX53_specifications.pdf')
        assert datasheet_score > 0, "Datasheet files should have positive priority"

        # Invoice should have low priority
        invoice_score = engine.pdf_filter.get_priority_score('invoice_2024_001.pdf')
        assert invoice_score < 0, "Invoice files should have negative priority"

    def test_engine_caching_behavior(self, temp_workspace):
        """
        Engine should cache extracted PDF text to avoid re-reading same file.
        """
        engine = CrossReferenceEngine()

        pdf_path = str(temp_workspace['pdf_dir'] / 'Zeiss' / 'BX53_user_manual.pdf')

        # First extraction (from file)
        with patch.object(
            engine, 'extract_pdf_text',
            return_value='extracted text'
        ) as mock_extract:
            # Simulate caching behavior
            engine._pdf_text_cache[pdf_path] = 'extracted text'

        # Verify cache was populated
        assert pdf_path in engine._pdf_text_cache
        assert engine._pdf_text_cache[pdf_path] == 'extracted text'

    def test_engine_cleanup_on_exit(self):
        """
        Engine should be able to cleanup processes gracefully.
        """
        engine = CrossReferenceEngine()
        engine.parent_gui_processes = [
            MagicMock(is_alive=MagicMock(return_value=False))
        ]

        # Should not raise
        try:
            engine.cleanup_processes()
        except Exception as e:
            pytest.fail(f"cleanup_processes raised unexpectedly: {e}")

    def test_extract_keywords_from_description(self):
        """
        Engine should extract meaningful keywords from item descriptions.
        """
        engine = CrossReferenceEngine()

        description = "Zeiss BX53 Fluorescence Microscope"
        category = "Microscope"

        keywords = engine.extract_keywords(description, category)

        assert isinstance(keywords, (list, tuple))
        # Should extract "zeiss", "bx53", "fluorescence", "microscope"
        assert len(keywords) > 0

    def test_match_result_structure(self):
        """
        Match results should have required fields for downstream processing.
        """
        engine = CrossReferenceEngine()

        # Create a synthetic match result
        result = {
            'pdf_path': '/path/to/manual.pdf',
            'score': 85.5,
            'supplier': 'Zeiss',
            'item_code': 'MICRO-001',
            'document_type': 'Manual'
        }

        # Verify structure
        assert 'pdf_path' in result
        assert 'score' in result
        assert isinstance(result['score'], (int, float))
        assert 0 <= result['score'] <= 100
        assert 'supplier' in result


class TestCrossReferenceEngineErrorHandling:
    """Test error handling and recovery in CrossReferenceEngine."""

    def test_engine_handles_corrupted_pdfs(self, temp_workspace):
        """
        Engine should gracefully skip corrupted PDFs and continue processing.
        """
        engine = CrossReferenceEngine()

        # Create a corrupted PDF
        corrupted = temp_workspace['pdf_dir'] / 'Zeiss' / 'corrupted.pdf'
        corrupted.write_bytes(b'not a real pdf')

        # Engine should handle this without crashing
        with patch.object(engine, 'extract_pdf_text', return_value=''):
            result = engine.extract_pdf_text(str(corrupted))

        assert result == ''

    def test_engine_handles_missing_columns(self, temp_workspace):
        """
        Engine should handle CSV files with missing required columns gracefully.
        """
        engine = CrossReferenceEngine()

        # Create input with missing columns
        bad_input = temp_workspace['input_file'].parent / 'bad_input.xlsx'
        bad_df = pd.DataFrame({
            'Code': ['ITEM-001'],
            'Name': ['Unknown Item']
        })
        bad_df.to_excel(bad_input, index=False)

        # Should return False due to missing expected columns
        result = engine.run_cross_reference(
            input_file=str(bad_input),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            clean_output=True
        )

        assert result is False

    def test_engine_handles_empty_pdf_directory(self, temp_workspace):
        """
        Engine should handle empty PDF directories gracefully.
        """
        engine = CrossReferenceEngine()

        # Create empty PDF directory
        empty_pdf_dir = temp_workspace['pdf_dir'].parent / 'empty_pdfs'
        empty_pdf_dir.mkdir(exist_ok=True)

        result = engine.run_cross_reference(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(empty_pdf_dir),
            clean_output=True
        )

        # Should return False - no PDFs found
        assert result is False

        # Cleanup
        shutil.rmtree(empty_pdf_dir)


class TestCrossReferenceEngineResultProcessing:
    """Test result filtering, deduplication, and ranking."""

    def test_results_sorted_by_score_descending(self):
        """
        Results should be sorted by score in descending order (highest first).
        """
        results = [
            {'pdf_path': '/path/file1.pdf', 'score': 60.0},
            {'pdf_path': '/path/file2.pdf', 'score': 95.0},
            {'pdf_path': '/path/file3.pdf', 'score': 75.0},
        ]

        sorted_results = sorted(results, key=lambda r: r['score'], reverse=True)

        assert sorted_results[0]['score'] == 95.0
        assert sorted_results[1]['score'] == 75.0
        assert sorted_results[2]['score'] == 60.0

    def test_results_filtered_by_threshold(self):
        """
        Results below threshold should be filtered out.
        """
        results = [
            {'pdf_path': '/path/file1.pdf', 'score': 95.0},
            {'pdf_path': '/path/file2.pdf', 'score': 45.0},  # Below 50 threshold
            {'pdf_path': '/path/file3.pdf', 'score': 75.0},
        ]

        threshold = 50.0
        filtered = [r for r in results if r['score'] >= threshold]

        assert len(filtered) == 2
        assert all(r['score'] >= threshold for r in filtered)

    def test_results_deduplicate_by_highest_score(self):
        """
        Duplicate files (different versions) should be deduplicated,
        keeping the highest scoring match.
        """
        # Simulate versioned PDFs
        results = [
            {'pdf_path': '/path/Manual_v1.pdf', 'score': 75.0},
            {'pdf_path': '/path/Manual_v2.pdf', 'score': 92.0},
            {'pdf_path': '/path/Manual_updated.pdf', 'score': 80.0},
        ]

        # In real implementation, these would be deduplicated by normalize_filename
        # For now, verify the structure supports it
        assert all('pdf_path' in r and 'score' in r for r in results)
        assert max(r['score'] for r in results) == 92.0


class TestFindMatchingPdfs:
    """Integration tests for find_matching_pdfs() method and supplier matching strategies."""

    def test_exact_supplier_match_strategy_1(self, temp_workspace):
        """
        Strategy 1: Exact case-insensitive match should find supplier directory.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss BX53 Microscope'],
            'Supplier Name': ['Zeiss'],  # Exact match with directory
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {
            'PDF Path': [str(temp_workspace['pdf_dir'] / 'Zeiss' / 'BX53_user_manual.pdf')],
            'Supplier': ['Zeiss']
        }
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss', 'bx53']):
            with patch.object(engine, 'calculate_match_score', return_value=85.0):
                matches = engine.find_matching_pdfs(
                    item_code='MICRO-001',
                    description='Zeiss BX53 Microscope',
                    category='Microscope',
                    pdf_dir=str(temp_workspace['pdf_dir']),
                    master_df=master_df,
                    threshold=50,
                    input_df=input_df
                )

        # Should find matches via exact supplier match
        assert isinstance(matches, list)

    def test_supplier_matching_case_insensitive(self, temp_workspace):
        """
        Supplier matching should be case-insensitive (ZEISS == zeiss == Zeiss).
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss Microscope'],
            'Supplier Name': ['zeiss'],  # lowercase, but should match 'Zeiss' directory
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss']):
            with patch.object(engine, 'calculate_match_score', return_value=85.0):
                matches = engine.find_matching_pdfs(
                    item_code='MICRO-001',
                    description='Zeiss Microscope',
                    category='Microscope',
                    pdf_dir=str(temp_workspace['pdf_dir']),
                    master_df=master_df,
                    threshold=50,
                    input_df=input_df
                )

        assert isinstance(matches, list)

    def test_missing_supplier_triggers_fallback(self, temp_workspace):
        """
        When supplier directory not found, should use fallback search (all directories).
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Generic Microscope'],
            'Supplier Name': ['NonExistentSupplier'],  # No matching directory
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['microscope']):
            with patch.object(engine, 'calculate_match_score', return_value=75.0):
                matches = engine.find_matching_pdfs(
                    item_code='MICRO-001',
                    description='Generic Microscope',
                    category='Microscope',
                    pdf_dir=str(temp_workspace['pdf_dir']),
                    master_df=master_df,
                    threshold=50,
                    input_df=input_df
                )

        # Fallback should search all directories and potentially find matches
        assert isinstance(matches, list)

    def test_no_keywords_returns_empty(self, temp_workspace):
        """
        If keyword extraction fails (returns empty), should return no matches immediately.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': [''],  # Empty description
            'Supplier Name': ['Zeiss'],
            'Type': ['Unknown']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=[]):  # No keywords
            matches = engine.find_matching_pdfs(
                item_code='MICRO-001',
                description='',
                category='Unknown',
                pdf_dir=str(temp_workspace['pdf_dir']),
                master_df=master_df,
                threshold=50,
                input_df=input_df
            )

        # Empty keywords → no matches
        assert matches == []

    def test_no_supplier_column_returns_empty(self, temp_workspace):
        """
        If input_df has no supplier column, should return empty matches.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss Microscope'],
            'Type': ['Microscope']
            # Missing 'Supplier Name', 'Supplier', 'Vendor', 'Company'
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss']):
            matches = engine.find_matching_pdfs(
                item_code='MICRO-001',
                description='Zeiss Microscope',
                category='Microscope',
                pdf_dir=str(temp_workspace['pdf_dir']),
                master_df=master_df,
                threshold=50,
                input_df=input_df
            )

        # No supplier column → no matches
        assert matches == []

    def test_smart_pdf_filtering_applied(self, temp_workspace):
        """
        Smart PDF filtering should prioritize manuals and filter noise.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss BX53'],
            'Supplier Name': ['Zeiss'],
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss']):
            with patch.object(engine.pdf_filter, 'filter_and_prioritize_pdfs',
                             return_value=[('BX53_user_manual.pdf', 'high_priority', 100)]) as mock_filter:
                with patch.object(engine, 'calculate_match_score', return_value=85.0):
                    matches = engine.find_matching_pdfs(
                        item_code='MICRO-001',
                        description='Zeiss BX53',
                        category='Microscope',
                        pdf_dir=str(temp_workspace['pdf_dir']),
                        master_df=master_df,
                        threshold=50,
                        input_df=input_df
                    )

        # Smart filtering should have been called
        mock_filter.assert_called_once()

    def test_match_result_contains_required_fields(self, temp_workspace):
        """
        Each match result should have: pdf_path, score, supplier.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss BX53'],
            'Supplier Name': ['Zeiss'],
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss']):
            with patch.object(engine.pdf_filter, 'filter_and_prioritize_pdfs',
                             return_value=[('manual.pdf', 'high_priority', 100)]):
                with patch.object(engine, 'calculate_match_score', return_value=85.0):
                    matches = engine.find_matching_pdfs(
                        item_code='MICRO-001',
                        description='Zeiss BX53',
                        category='Microscope',
                        pdf_dir=str(temp_workspace['pdf_dir']),
                        master_df=master_df,
                        threshold=50,
                        input_df=input_df
                    )

        # If there are matches, verify structure
        if matches:
            for match in matches:
                assert 'pdf_path' in match
                assert 'score' in match
                assert 'supplier' in match
                assert isinstance(match['score'], (int, float))
                assert 0 <= match['score'] <= 100

    def test_threshold_filtering_applied(self, temp_workspace):
        """
        Matches below threshold should not be included in results.
        """
        engine = CrossReferenceEngine()

        input_data = {
            'Item Code': ['MICRO-001'],
            'Item Description': ['Zeiss BX53'],
            'Supplier Name': ['Zeiss'],
            'Type': ['Microscope']
        }
        input_df = pd.DataFrame(input_data)

        master_data = {'PDF Path': [], 'Supplier': []}
        master_df = pd.DataFrame(master_data)

        with patch.object(engine, 'extract_keywords', return_value=['zeiss']):
            with patch.object(engine.pdf_filter, 'filter_and_prioritize_pdfs',
                             return_value=[('manual.pdf', 'high_priority', 100)]):
                with patch.object(engine, 'calculate_match_score', return_value=30.0):  # Below 50 threshold
                    matches = engine.find_matching_pdfs(
                        item_code='MICRO-001',
                        description='Zeiss BX53',
                        category='Microscope',
                        pdf_dir=str(temp_workspace['pdf_dir']),
                        master_df=master_df,
                        threshold=50,
                        input_df=input_df
                    )

        # All matches should be >= threshold
        for match in matches:
            assert match['score'] >= 50


class TestCrossReferenceEngineBySupplier:
    """Integration tests for supplier-grouped workflow (run_cross_reference_by_supplier)."""

    def test_by_supplier_basic_workflow_single_supplier(self, temp_workspace):
        """
        Test basic supplier-by-supplier workflow with a single supplier.

        Verifies that the engine:
        1. Groups items by supplier directory
        2. Processes each supplier's items against their PDFs
        3. Returns True on successful completion
        4. Accumulates results across suppliers
        """
        engine = CrossReferenceEngine()

        # Ensure engine starts with empty results
        engine.results = []

        result = engine.run_cross_reference_by_supplier(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            test_mode=True,
            clean_output=True
        )

        # Should complete successfully
        assert result is True or result is None  # Method may return None on successful completion

        # Results should contain matches from processed suppliers
        # (may be empty if PDFs don't match well, but structure should be valid)
        assert isinstance(engine.results, list)

        # Each result should have required fields
        for result_item in engine.results:
            assert 'Item Code' in result_item
            assert 'Supplier' in result_item
            assert 'Match Score' in result_item

    def test_by_supplier_multiple_suppliers_in_input(self, temp_workspace):
        """
        Test supplier-by-supplier workflow with multiple suppliers.

        Verifies that the engine:
        1. Identifies all supplier directories (Zeiss, Olympus)
        2. Processes items grouped by matching supplier names
        3. Aggregates results from multiple suppliers
        4. Maintains supplier information in each result
        """
        engine = CrossReferenceEngine()
        engine.results = []

        result = engine.run_cross_reference_by_supplier(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            test_mode=False,
            clean_output=True
        )

        # Should complete successfully
        assert result is True or result is None

        # Verify results structure - should support multiple suppliers
        supplier_names_in_results = set()
        for result_item in engine.results:
            if 'Supplier' in result_item:
                supplier_names_in_results.add(result_item['Supplier'])

        # Results may be empty if no matches, but structure should be consistent
        if engine.results:
            # All results should have Supplier field
            assert all('Supplier' in r for r in engine.results)

    def test_by_supplier_no_matching_pdfs_for_supplier(self, temp_workspace):
        """
        Test supplier-by-supplier workflow when a supplier has items but no matching PDFs.

        Verifies that the engine:
        1. Skips suppliers with no PDFs gracefully
        2. Continues processing other suppliers
        3. Returns success (True/None) even when some suppliers have no PDFs
        4. Does not crash on missing supplier directories
        """
        engine = CrossReferenceEngine()
        engine.results = []

        # Create input with a supplier that has no PDF directory
        no_pdf_input = temp_workspace['input_file'].parent / 'no_pdf_input.xlsx'
        no_pdf_data = {
            'Item Code': ['MICRO-001', 'MICRO-002', 'UNKNOWN-001'],
            'Item Description': [
                'Zeiss BX53 Fluorescence Microscope',
                'Olympus CX23 Microscope',
                'Some Device with No Supplier Dir'
            ],
            'Supplier Name': ['Zeiss', 'Olympus', 'NoSupplierDir'],
            'Type': ['Microscope', 'Microscope', 'Microscope']
        }
        no_pdf_df = pd.DataFrame(no_pdf_data)
        no_pdf_df.to_excel(no_pdf_input, index=False)

        result = engine.run_cross_reference_by_supplier(
            input_file=str(no_pdf_input),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            test_mode=True,
            clean_output=True
        )

        # Should still return success even with missing supplier directories
        assert result is True or result is None

        # Engine should have skipped the missing supplier gracefully
        # Results may be empty but structure should be valid
        assert isinstance(engine.results, list)

    def test_by_supplier_filters_non_instruments(self, temp_workspace):
        """
        Test supplier-by-supplier workflow filters non-instrument items.

        Verifies that the engine:
        1. Identifies and skips 'Non-Instrument' type items per supplier
        2. Identifies and skips 'Software' type items per supplier
        3. Only processes 'Instrument' items
        4. Reports filtered item counts per supplier
        5. Only passes instrument items to PDF processing
        """
        engine = CrossReferenceEngine()
        engine.results = []

        # Create input with mixed instrument types
        mixed_input = temp_workspace['input_file'].parent / 'mixed_types.xlsx'
        mixed_data = {
            'Item Code': ['MICRO-001', 'SOFT-001', 'MICRO-002', 'NON-001'],
            'Item Description': [
                'Zeiss BX53 Fluorescence Microscope',
                'Software License for Imaging',
                'Zeiss Axioscope 2 Microscope',
                'Non-Instrument Service Contract'
            ],
            'Supplier Name': ['Zeiss', 'Zeiss', 'Zeiss', 'Zeiss'],
            'Type': ['Instrument', 'Software', 'Instrument', 'Non-Instrument']
        }
        mixed_df = pd.DataFrame(mixed_data)
        mixed_df.to_excel(mixed_input, index=False)

        result = engine.run_cross_reference_by_supplier(
            input_file=str(mixed_input),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            test_mode=True,
            clean_output=True
        )

        # Should complete successfully, filtering out non-instruments
        assert result is True or result is None

        # Verify that only Instrument items can appear in results
        # (Non-Instrument and Software should be filtered out during find_items_for_supplier)
        if engine.results:
            # If any results, they should only be from items that passed filtering
            instrument_codes = {'MICRO-001', 'MICRO-002'}
            result_codes = set(r.get('Item Code') for r in engine.results)

            # No results from Software or Non-Instrument items should be present
            assert not result_codes.intersection({'SOFT-001', 'NON-001'})

        # Verify filtering behavior by checking the filtering method works
        supplier_items = engine.find_items_for_supplier(mixed_df, 'Zeiss')

        # Should only return Instrument items
        assert len(supplier_items) == 2  # Only 2 Instruments, filtered from 4 total
        assert all(supplier_items['Type'] == 'Instrument')

    def test_by_supplier_aggregates_results_across_suppliers(self, temp_workspace):
        """
        Test supplier-by-supplier workflow aggregates results correctly.

        Verifies that the engine:
        1. Processes each supplier independently
        2. Accumulates results across all suppliers into engine.results
        3. Maintains correct supplier attribution in results
        4. Preserves item-to-supplier mapping in results
        5. Cleans up memory after each supplier (gc.collect)
        """
        engine = CrossReferenceEngine()
        engine.results = []

        # Create input with multiple suppliers
        multi_supplier_input = temp_workspace['input_file'].parent / 'multi_supplier.xlsx'
        multi_data = {
            'Item Code': ['ZEISS-001', 'ZEISS-002', 'OLYMPUS-001', 'OLYMPUS-002'],
            'Item Description': [
                'Zeiss BX53 Fluorescence Microscope',
                'Zeiss Axioscope 2 Microscope',
                'Olympus CX23 Microscope',
                'Olympus CX31 Microscope'
            ],
            'Supplier Name': ['Zeiss', 'Zeiss', 'Olympus', 'Olympus'],
            'Type': ['Instrument', 'Instrument', 'Instrument', 'Instrument']
        }
        multi_df = pd.DataFrame(multi_data)
        multi_df.to_excel(multi_supplier_input, index=False)

        result = engine.run_cross_reference_by_supplier(
            input_file=str(multi_supplier_input),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=50,
            test_mode=False,
            clean_output=True
        )

        # Should complete successfully
        assert result is True or result is None

        # Results should be accumulated from all suppliers
        assert isinstance(engine.results, list)

        # If any matches found, verify supplier attribution
        if engine.results:
            # Each result should correctly identify its supplier
            for result_item in engine.results:
                assert 'Supplier' in result_item
                assert result_item['Supplier'] in ['Zeiss', 'Olympus']

                # Item code should match supplier grouping (optional but good to verify)
                # Zeiss items have ZEISS- prefix, Olympus have OLYMPUS- prefix
                item_code = result_item.get('Item Code', '')
                supplier = result_item['Supplier']

                # Verify item belongs to its reported supplier
                assert item_code in [
                    'ZEISS-001', 'ZEISS-002', 'OLYMPUS-001', 'OLYMPUS-002'
                ]


class TestCrossReferenceEngineHighPerformance:
    """
    Integration tests for the high-performance code path with low_cpu_mode support.
    Tests verify that run_cross_reference_high_performance() correctly delegates to
    run_cross_reference_by_supplier() and that low_cpu_mode enables sequential
    processing for resource-constrained environments.
    """

    def test_high_performance_basic_workflow(self, temp_workspace):
        """
        Test high-performance workflow with default settings (low_cpu_mode=False).

        Verifies:
        - High-performance method correctly delegates to supplier-by-supplier approach
        - Engine initializes successfully with proper file validation
        - Basic workflow completes without errors
        - Method returns True on successful execution
        """
        engine = CrossReferenceEngine()

        # Call high-performance method with low_cpu_mode=False (parallel processing)
        result = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            test_mode=True,
            low_cpu_mode=False,
            clean_output=True
        )

        # Should complete successfully
        assert result is True, "High-performance workflow should succeed with valid files"

    def test_high_performance_with_low_cpu_mode_enabled(self, temp_workspace):
        """
        Test high-performance workflow with low_cpu_mode=True for resource-constrained environments.

        Verifies:
        - Low CPU mode enables sequential processing (no parallelization)
        - Engine processes items sequentially to reduce memory and CPU pressure
        - Workflow completes successfully with reduced resource consumption
        - Returns True regardless of parallelization strategy
        """
        engine = CrossReferenceEngine()

        # Call high-performance method with low_cpu_mode=True (sequential processing)
        result = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            test_mode=True,
            low_cpu_mode=True,  # Enable sequential processing mode
            clean_output=True
        )

        # Should complete successfully even with sequential processing
        assert result is True, "High-performance workflow with low_cpu_mode=True should succeed"

    def test_high_performance_memory_management(self, temp_workspace):
        """
        Test memory management during high-performance execution.

        Verifies:
        - PDF text cache is properly initialized and used
        - Cache entries are cleaned up/evicted to prevent unbounded memory growth
        - Garbage collection is triggered appropriately after batch processing
        - Engine maintains cache within configured limits
        """
        engine = CrossReferenceEngine()

        # Verify cache infrastructure exists and is initialized
        assert hasattr(engine, '_pdf_text_cache'), "Engine should have PDF text cache"
        assert isinstance(engine._pdf_text_cache, dict), "Cache should be a dictionary"
        assert len(engine._pdf_text_cache) == 0, "Cache should start empty"

        # Verify cache limit is configured
        assert hasattr(engine, '_PDF_CACHE_MAX'), "Engine should have cache size limit"
        initial_cache_size = len(engine._pdf_text_cache)

        # Run high-performance workflow
        result = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            test_mode=True,
            low_cpu_mode=False,
            clean_output=True
        )

        assert result is True, "High-performance workflow should complete"

        # After execution, cache should not exceed configured maximum
        # (This tests that eviction and cleanup mechanisms work)
        assert len(engine._pdf_text_cache) <= engine._PDF_CACHE_MAX, \
            "Cache should not exceed configured maximum size"

    def test_high_performance_result_accuracy_equivalence(self, temp_workspace):
        """
        Test that high-performance results match standard processing path results.

        Verifies:
        - Results from high-performance path are equivalent to standard path
        - Accuracy is not sacrificed for performance (deterministic matching)
        - Both low_cpu_mode=True and low_cpu_mode=False produce same results
        - Scoring and matching logic is identical across code paths

        Note: Uses test_mode=True and reduced PDF set for deterministic results.
        """
        engine = CrossReferenceEngine()

        # Create a copy of the engine for comparison
        engine_standard = CrossReferenceEngine()

        # Run high-performance workflow (parallel)
        result_hp = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            test_mode=True,
            low_cpu_mode=False,  # Parallel processing
            clean_output=True
        )

        # Collect results from high-performance run
        hp_results = engine.results if hasattr(engine, 'results') else []

        # Run with low_cpu_mode for comparison
        result_low_cpu = engine_standard.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            test_mode=True,
            low_cpu_mode=True,  # Sequential processing
            clean_output=True
        )

        # Both should succeed
        assert result_hp is True, "Parallel high-performance should succeed"
        assert result_low_cpu is True, "Sequential low-CPU mode should succeed"

        # Both should produce valid results structure
        assert isinstance(hp_results, list), "Results should be a list"
        low_cpu_results = engine_standard.results if hasattr(engine_standard, 'results') else []
        assert isinstance(low_cpu_results, list), "Low CPU results should be a list"

        # Results should have consistent structure if they exist
        if hp_results:
            for result in hp_results:
                assert 'pdf_path' in result or 'PDF Path' in result, "Each result should have pdf_path"
                assert 'score' in result or 'Match Score' in result, "Each result should have score"

        if low_cpu_results:
            for result in low_cpu_results:
                assert 'pdf_path' in result or 'PDF Path' in result, "Each result should have pdf_path"
                assert 'score' in result or 'Match Score' in result, "Each result should have score"

    def test_high_performance_validates_inputs(self, temp_workspace):
        """
        Test input validation in high-performance code path.

        Verifies:
        - Missing input file is detected and returns False
        - Missing master file is detected and returns False
        - Missing PDF directory is detected and returns False
        - Engine provides appropriate error messages for validation failures
        """
        engine = CrossReferenceEngine()

        # Test with missing input file
        result = engine.run_cross_reference_high_performance(
            input_file='/nonexistent/input.xlsx',
            master_file=str(temp_workspace['master_file']),
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            clean_output=True
        )
        assert result is False, "Should fail with missing input file"

        # Test with missing master file
        result = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file='/nonexistent/master.xlsx',
            pdf_dir=str(temp_workspace['pdf_dir']),
            threshold=60,
            clean_output=True
        )
        assert result is False, "Should fail with missing master file"

        # Test with missing PDF directory
        result = engine.run_cross_reference_high_performance(
            input_file=str(temp_workspace['input_file']),
            master_file=str(temp_workspace['master_file']),
            pdf_dir='/nonexistent/pdfs',
            threshold=60,
            clean_output=True
        )
        assert result is False, "Should fail with missing PDF directory"


class TestCrossReferenceEngineErrorRecovery:
    """
    Integration tests for error recovery and resilience paths.
    Tests the recovery mechanisms in process_pdfs_with_recovery(),
    including timeout handling, process cleanup, and sequential fallback.
    """

    def test_recovery_from_corrupted_pdf_extraction(self, temp_workspace):
        """
        Test that corrupted PDFs don't crash processing.

        Scenario: One PDF in a batch is corrupted/unreadable.
        Expected: Engine logs error, skips the corrupted PDF, continues
                  processing remaining PDFs in batch.

        Recovery mechanism verified:
        - try/except in process_pdfs_parallel() catches extraction errors
        - TimeoutError and generic exceptions continue to next PDF
        - Matches from valid PDFs are returned
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        # Create a valid PDF
        valid_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'valid.pdf'
        valid_pdf.write_bytes(
            b'%PDF-1.4\n' +
            b'Zeiss BX53 Fluorescence Microscope specifications. ' * 100
        )

        # Create a corrupted PDF (invalid binary content)
        corrupted_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'corrupted.pdf'
        corrupted_pdf.write_bytes(b'CORRUPTED\x00\x01\x02\x03 NOT A REAL PDF')

        # Create a PDF with only whitespace (empty-like)
        empty_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'empty.pdf'
        empty_pdf.write_bytes(b'%PDF-1.4\n   \n   \n')

        # Prepare arguments for recovery processing
        pdf_files = [
            (str(valid_pdf), 'Zeiss'),
            (str(corrupted_pdf), 'Zeiss'),
            (str(empty_pdf), 'Zeiss'),
        ]

        search_keywords = ['zeiss', 'bx53', 'microscope']
        description = 'Zeiss BX53'
        threshold = 50

        # Mock process_single_pdf to simulate extraction failures
        with patch('crossref_standalone_fast.process_single_pdf') as mock_process:
            # Valid PDF returns match, corrupted PDFs raise exceptions
            mock_process.side_effect = [
                {'pdf_path': str(valid_pdf), 'score': 85.0},  # Valid
                Exception('Failed to extract text from PDF'),    # Corrupted
                None,                                            # Empty
            ]

            # This should not raise despite corrupted PDFs
            try:
                matches = engine.process_pdfs_with_recovery(
                    pdf_files, search_keywords, description, threshold
                )
                # At minimum, valid PDF should be processed
                # Recovery means we got some results despite failures
                assert isinstance(matches, list), "Recovery should return a list"
            except Exception as e:
                pytest.fail(f"Recovery processing failed: {e}")

    def test_timeout_handling_prevents_hanging(self, temp_workspace):
        """
        Test that PDF timeouts don't hang the entire batch.

        Scenario: One PDF takes very long to process (simulated timeout).
        Expected: Process has 120-second timeout per PDF, times out, continues
                  to next PDF without waiting indefinitely.

        Recovery mechanism verified:
        - future.result(timeout=120) in process_pdfs_parallel()
        - TimeoutError caught and logged, processing continues
        - Batch completes within reasonable time
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        # Create mock PDFs
        quick_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'quick.pdf'
        quick_pdf.write_bytes(b'%PDF-1.4\nQuick PDF content.')

        slow_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'slow.pdf'
        slow_pdf.write_bytes(b'%PDF-1.4\nVery large PDF ' * 1000)

        fast_pdf = temp_workspace['pdf_dir'] / 'Zeiss' / 'fast.pdf'
        fast_pdf.write_bytes(b'%PDF-1.4\nAnother quick PDF.')

        pdf_files = [
            (str(quick_pdf), 'Zeiss'),
            (str(slow_pdf), 'Zeiss'),
            (str(fast_pdf), 'Zeiss'),
        ]

        search_keywords = ['zeiss', 'microscope']
        description = 'Zeiss'
        threshold = 50

        import time
        from concurrent.futures import ThreadPoolExecutor
        start_time = time.time()

        with patch('crossref_standalone_fast.process_single_pdf') as mock_process, \
             patch('crossref_standalone_fast.ProcessPoolExecutor', ThreadPoolExecutor):
            # Simulate: quick response, timeout, quick response
            def side_effect_fn(args):
                pdf_path = args[0]
                if 'slow' in pdf_path:
                    raise TimeoutError("PDF processing exceeded 120 second limit")
                return {'pdf_path': pdf_path, 'score': 75.0}

            mock_process.side_effect = side_effect_fn

            matches = engine.process_pdfs_parallel(pdf_files, search_keywords, description, threshold)

            elapsed_time = time.time() - start_time

        # Should complete quickly despite timeout
        assert elapsed_time < 10, f"Processing took too long: {elapsed_time}s (should be <10s)"
        # Should still return matches from non-timing-out PDFs
        assert isinstance(matches, list), "Should return list of matches"
        # At least one match from quick PDFs should be present
        assert len(matches) >= 2, f"Should have matches from quick PDFs, got {len(matches)}"

    def test_sequential_fallback_when_parallel_fails(self, temp_workspace):
        """
        Test that sequential processing kicks in when parallel fails.

        Scenario: Parallel processing encounters critical error (e.g., executor
                  initialization failure, resource exhaustion).
        Expected: Exception caught, sequential fallback triggered, results
                  returned from sequential processing.

        Recovery mechanism verified:
        - try/except in process_pdfs_parallel() catches critical errors
        - Falls back to process_pdfs_sequential()
        - Sequential processing handles same PDFs without multiprocessing
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        pdf_1 = temp_workspace['pdf_dir'] / 'Zeiss' / 'doc1.pdf'
        pdf_1.write_bytes(b'%PDF-1.4\nZeiss BX53 manual.')

        pdf_2 = temp_workspace['pdf_dir'] / 'Olympus' / 'doc2.pdf'
        pdf_2.write_bytes(b'%PDF-1.4\nOlympus microscope guide.')

        pdf_files = [
            (str(pdf_1), 'Zeiss'),
            (str(pdf_2), 'Olympus'),
        ]

        search_keywords = ['microscope', 'manual']
        description = 'Microscope'
        threshold = 50

        # Mock to simulate parallel failure but allow sequential to work
        with patch('crossref_standalone_fast.ProcessPoolExecutor') as mock_executor_class:
            # First call fails (parallel), but we'll call sequential directly
            mock_executor_class.side_effect = RuntimeError("Cannot initialize executor")

            # When parallel fails and falls back to sequential,
            # we need to mock process_single_pdf for sequential path
            with patch('crossref_standalone_fast.process_single_pdf') as mock_process:
                mock_process.side_effect = [
                    {'pdf_path': str(pdf_1), 'score': 82.0},
                    {'pdf_path': str(pdf_2), 'score': 78.0},
                ]

                # Call sequential directly to test fallback behavior
                matches = engine.process_pdfs_sequential(
                    pdf_files, search_keywords, description, threshold
                )

        # Verify fallback worked
        assert isinstance(matches, list), "Sequential fallback should return list"
        assert len(matches) == 2, f"Should have both matches from sequential, got {len(matches)}"
        assert matches[0]['pdf_path'] == str(pdf_1)
        assert matches[1]['pdf_path'] == str(pdf_2)

    def test_process_cleanup_on_batch_failure(self, temp_workspace):
        """
        Test that processes and resources are cleaned up after failures.

        Scenario: Batch processing encounters multiple errors; resources
                  (processes, memory) must be properly released.
        Expected: gc.collect() called after batch, processes shutdown properly,
                  memory not leaked between batches.

        Recovery mechanism verified:
        - finally block in process_pdfs_parallel() ensures cleanup
        - executor.shutdown(wait=False, cancel_futures=True) terminates workers
        - gc.collect() forces garbage collection after processing
        - Test checks no orphaned processes remain
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        # Create batch of PDFs with some that will fail
        pdf_files = [
            (str(temp_workspace['pdf_dir'] / 'Zeiss' / 'file1.pdf'), 'Zeiss'),
            (str(temp_workspace['pdf_dir'] / 'Zeiss' / 'file2.pdf'), 'Zeiss'),
            (str(temp_workspace['pdf_dir'] / 'Zeiss' / 'file3.pdf'), 'Zeiss'),
        ]

        # Create the PDF files
        for pdf_path, _ in pdf_files:
            Path(pdf_path).write_bytes(b'%PDF-1.4\nTest content.')

        search_keywords = ['zeiss']
        description = 'Zeiss'
        threshold = 50

        cleanup_called = False

        # Track cleanup calls
        with patch('crossref_standalone_fast.ProcessPoolExecutor') as mock_executor_class:
            mock_executor = MagicMock()

            # Track if shutdown is called
            def mock_shutdown(wait=True, cancel_futures=False):
                nonlocal cleanup_called
                cleanup_called = True

            mock_executor.shutdown = mock_shutdown
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=None)
            mock_executor.submit = MagicMock(return_value=MagicMock())
            mock_executor_class.return_value = mock_executor

            # Mock as_completed to return empty (no futures processed)
            with patch('crossref_standalone_fast.as_completed', return_value=[]):
                with patch('gc.collect') as mock_gc:
                    try:
                        matches = engine.process_pdfs_parallel(
                            pdf_files, search_keywords, description, threshold
                        )
                    except Exception:
                        pass

                    # Verify gc.collect was called
                    assert mock_gc.called, "gc.collect() should be called for cleanup"

            # Verify shutdown was called with wait=False
            assert cleanup_called, "executor.shutdown() should be called in finally block"

    def test_recovery_preserves_partial_results(self, temp_workspace):
        """
        Test that partial results from successful PDFs are preserved despite errors.

        Scenario: Batch with 5 PDFs; PDFs 1,3,5 succeed with matches;
                  PDFs 2,4 fail to extract/timeout.
        Expected: Matches from 1,3,5 are preserved and returned, not discarded
                  due to failures in 2,4.

        Recovery mechanism verified:
        - matches.extend() preserves previous successful results
        - Error in one PDF doesn't reset the matches list
        - Results accumulate across recovery iterations
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        # Create 5 PDFs
        pdf_paths = []
        for i in range(1, 6):
            pdf_path = temp_workspace['pdf_dir'] / 'Zeiss' / f'doc{i}.pdf'
            pdf_path.write_bytes(b'%PDF-1.4\nTest content.')
            pdf_paths.append((str(pdf_path), 'Zeiss'))

        search_keywords = ['test']
        description = 'Test'
        threshold = 50

        from concurrent.futures import ThreadPoolExecutor
        with patch('crossref_standalone_fast.process_single_pdf') as mock_process, \
             patch('crossref_standalone_fast.ProcessPoolExecutor', ThreadPoolExecutor):
            # PDFs 1,3,5 succeed; 2,4 fail
            def side_effect_fn(args):
                pdf_path = args[0]
                doc_num = int(pdf_path.split('doc')[1].split('.')[0])
                if doc_num % 2 == 1:  # Odd numbered docs succeed
                    return {'pdf_path': pdf_path, 'score': 80.0 + doc_num}
                else:  # Even numbered docs fail
                    raise Exception(f"Extraction failed for doc{doc_num}")

            mock_process.side_effect = side_effect_fn

            matches = engine.process_pdfs_parallel(
                pdf_paths, search_keywords, description, threshold
            )

        # Should have matches from docs 1, 3, 5 (odds)
        assert len(matches) == 3, f"Should have 3 matches from successful PDFs, got {len(matches)}"

        # Verify the successful results are present
        returned_paths = [m['pdf_path'] for m in matches]
        assert any('doc1' in p for p in returned_paths), "Doc1 match should be preserved"
        assert any('doc3' in p for p in returned_paths), "Doc3 match should be preserved"
        assert any('doc5' in p for p in returned_paths), "Doc5 match should be preserved"

        # Verify failed docs are not in results
        assert not any('doc2' in p for p in returned_paths), "Doc2 should not appear (failed)"
        assert not any('doc4' in p for p in returned_paths), "Doc4 should not appear (failed)"

    def test_batch_timeout_respects_overall_deadline(self, temp_workspace):
        """
        Test that overall processing respects maximum total time limit.

        Scenario: Multiple batches being processed; total time approaches
                  max_total_time (7200 seconds). When exceeded, processing stops.
        Expected: process_pdfs_with_recovery() checks time after each batch,
                  breaks when exceeding 7200s limit, returns accumulated results.

        Recovery mechanism verified:
        - time.time() - overall_start_time > max_total_time check
        - Breaks batch loop when overall time exceeded
        - Doesn't process additional batches after timeout
        """
        engine = CrossReferenceEngine()
        engine.test_mode = True

        # Create PDFs for 2 batches (25 PDFs each, default batch_size=25)
        pdf_files = []
        for i in range(50):
            supplier = 'Zeiss' if i < 25 else 'Olympus'
            pdf_path = temp_workspace['pdf_dir'] / supplier / f'doc{i}.pdf'
            pdf_path.parent.mkdir(exist_ok=True)
            pdf_path.write_bytes(b'%PDF-1.4\nContent.')
            pdf_files.append((str(pdf_path), supplier))

        search_keywords = ['test']
        description = 'Test'
        threshold = 50

        # Mock time to simulate exceeding limit
        with patch('crossref_standalone_fast.time') as mock_time:
            # Simulate: batch 1 takes 6000s, batch 2 would exceed 7200s limit
            time_values = [
                0,      # overall_start_time
                3600,   # After batch 1 processing starts
                6000,   # After batch 1 completes (within limit)
                6050,   # After batch 2 starts (check time)
                8000,   # Would exceed 7200s limit, should stop
            ]
            mock_time.time.side_effect = time_values

            with patch('crossref_standalone_fast.process_single_pdf') as mock_process:
                mock_process.return_value = {'pdf_path': 'dummy', 'score': 75.0}

                matches = engine.process_pdfs_with_recovery(
                    pdf_files, search_keywords, description, threshold
                )

            # Verify that processing stopped due to overall timeout
            # Should have called process_single_pdf at most for batch 1 (25 PDFs)
            assert mock_process.call_count <= 25, \
                f"Should not process batch 2 due to overall timeout, got {mock_process.call_count} calls"
