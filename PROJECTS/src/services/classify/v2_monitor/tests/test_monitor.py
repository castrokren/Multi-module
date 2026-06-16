"""
Unit tests for FileMonitor
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor import FileMonitor, ExcelFileHandler


class TestFileMonitorShouldProcess:
    """Test FileMonitor.should_process() file validation."""

    def test_process_xlsx_file(self):
        """Should process .xlsx files."""
        assert FileMonitor.should_process("data.xlsx") is True

    def test_process_xls_file(self):
        """Should process .xls files."""
        assert FileMonitor.should_process("data.xls") is True

    def test_skip_temp_excel_file(self):
        """Should skip Excel temp files starting with ~$."""
        assert FileMonitor.should_process("~$data.xlsx") is False

    def test_skip_processed_file(self):
        """Should skip already-processed files ending with _labeled."""
        assert FileMonitor.should_process("data_labeled.xlsx") is False

    def test_skip_non_excel_file(self):
        """Should skip non-Excel files."""
        assert FileMonitor.should_process("readme.txt") is False
        assert FileMonitor.should_process("image.jpg") is False
        assert FileMonitor.should_process("document.pdf") is False

    def test_skip_directory(self):
        """Should skip directory paths."""
        assert FileMonitor.should_process("/path/to/dir/") is False

    def test_case_insensitive_extension(self):
        """Should handle case-insensitive file extensions."""
        assert FileMonitor.should_process("data.XLSX") is True
        assert FileMonitor.should_process("data.XlS") is True

    def test_excel_temp_and_processed(self):
        """Should skip file with both temp and processed markers."""
        assert FileMonitor.should_process("~$data_labeled.xlsx") is False


class TestFileMonitorInitialization:
    """Test FileMonitor initialization."""

    def test_init_with_paths(self):
        """Should initialize with watch and output directories."""
        config = {'output_dir': 'output'}
        monitor = FileMonitor('input', 'output', config)

        assert monitor.watch_dir == Path('input')
        assert monitor.output_dir == Path('output')
        assert monitor.processor is None
        assert monitor.observer is None
        assert monitor.running is False

    def test_init_with_processor_config(self):
        """Should store processor configuration."""
        config = {
            'hw_keywords_file': 'hw.txt',
            'sw_keywords_file': 'sw.txt',
            'output_dir': 'output'
        }
        monitor = FileMonitor('input', 'output', config)

        assert monitor.processor_config == config

    def test_init_with_custom_logger(self):
        """Should accept custom logger."""
        custom_logger = Mock()
        monitor = FileMonitor('input', 'output', {}, logger=custom_logger)

        assert monitor.logger is custom_logger

    def test_init_creates_logger(self):
        """Should create default logger if not provided."""
        monitor = FileMonitor('input', 'output', {})

        assert monitor.logger is not None


class TestFileMonitorProcessorInitialization:
    """Test lazy processor initialization."""

    @patch('monitor.AdaptiveExcelProcessor')
    def test_processor_not_initialized_on_creation(self, mock_processor_class):
        """Processor should not be initialized until needed."""
        monitor = FileMonitor('input', 'output', {})
        assert monitor.processor is None
        mock_processor_class.assert_not_called()

    @patch('monitor.AdaptiveExcelProcessor')
    def test_processor_initialized_on_first_use(self, mock_processor_class):
        """Processor should be initialized on first use."""
        mock_instance = Mock()
        mock_processor_class.return_value = mock_instance

        config = {'hw_keywords_file': 'hw.txt'}
        monitor = FileMonitor('input', 'output', config)

        monitor._initialize_processor()

        assert monitor.processor is mock_instance
        mock_processor_class.assert_called_once_with(**config)

    @patch('monitor.AdaptiveExcelProcessor')
    def test_processor_not_reinitialized(self, mock_processor_class):
        """Processor should only be initialized once."""
        mock_instance = Mock()
        mock_processor_class.return_value = mock_instance

        monitor = FileMonitor('input', 'output', {})

        monitor._initialize_processor()
        monitor._initialize_processor()

        mock_processor_class.assert_called_once()


class TestFileMonitorProcessFile:
    """Test file processing."""

    @patch('monitor.AdaptiveExcelProcessor')
    def test_process_file_success(self, mock_processor_class):
        """Should log success when file processes successfully."""
        mock_instance = Mock()
        mock_instance.process_file.return_value = True
        mock_processor_class.return_value = mock_instance

        mock_logger = Mock()
        monitor = FileMonitor('input', 'output', {}, logger=mock_logger)

        result = monitor._process_file('test.xlsx')

        assert result is True
        mock_instance.process_file.assert_called_once_with('test.xlsx')
        assert any('Success' in str(call) for call in mock_logger.info.call_args_list)

    @patch('monitor.AdaptiveExcelProcessor')
    def test_process_file_failure(self, mock_processor_class):
        """Should log failure when file processing fails."""
        mock_instance = Mock()
        mock_instance.process_file.return_value = False
        mock_processor_class.return_value = mock_instance

        mock_logger = Mock()
        monitor = FileMonitor('input', 'output', {}, logger=mock_logger)

        result = monitor._process_file('test.xlsx')

        assert result is False
        assert any('Failed' in str(call) for call in mock_logger.warning.call_args_list)

    @patch('monitor.AdaptiveExcelProcessor')
    def test_process_file_exception(self, mock_processor_class):
        """Should handle exceptions gracefully."""
        mock_instance = Mock()
        mock_instance.process_file.side_effect = Exception("Test error")
        mock_processor_class.return_value = mock_instance

        mock_logger = Mock()
        monitor = FileMonitor('input', 'output', {}, logger=mock_logger)

        result = monitor._process_file('test.xlsx')

        assert result is False
        assert any('Exception' in str(call) for call in mock_logger.error.call_args_list)


class TestExcelFileHandler:
    """Test ExcelFileHandler event handling."""

    def test_handler_initialization(self):
        """Should initialize with callbacks."""
        process_cb = Mock()
        validate_cb = Mock()

        handler = ExcelFileHandler(process_cb, validate_cb)

        assert handler.process_callback is process_cb
        assert handler.should_process is validate_cb

    def test_on_created_valid_file(self):
        """Should process valid file on creation."""
        process_cb = Mock()
        validate_cb = Mock(return_value=True)

        handler = ExcelFileHandler(process_cb, validate_cb)

        event = Mock(is_directory=False, src_path='test.xlsx')

        with patch('time.sleep'):
            handler.on_created(event)

        validate_cb.assert_called_once_with('test.xlsx')
        process_cb.assert_called_once_with('test.xlsx')

    def test_on_created_skip_directory(self):
        """Should skip directory events."""
        process_cb = Mock()
        validate_cb = Mock()

        handler = ExcelFileHandler(process_cb, validate_cb)

        event = Mock(is_directory=True)

        handler.on_created(event)

        validate_cb.assert_not_called()
        process_cb.assert_not_called()

    def test_on_created_invalid_file(self):
        """Should skip invalid files."""
        process_cb = Mock()
        validate_cb = Mock(return_value=False)

        handler = ExcelFileHandler(process_cb, validate_cb)

        event = Mock(is_directory=False, src_path='test.txt')

        handler.on_created(event)

        validate_cb.assert_called_once_with('test.txt')
        process_cb.assert_not_called()

    def test_on_modified_valid_file(self):
        """Should process valid file on modification."""
        process_cb = Mock()
        validate_cb = Mock(return_value=True)

        handler = ExcelFileHandler(process_cb, validate_cb)

        event = Mock(is_directory=False, src_path='test.xlsx')

        with patch('time.sleep'):
            handler.on_modified(event)

        validate_cb.assert_called_once_with('test.xlsx')
        process_cb.assert_called_once_with('test.xlsx')


class TestFileMonitorStop:
    """Test graceful shutdown."""

    def test_stop_sets_running_false(self):
        """Should set running flag to False on stop."""
        monitor = FileMonitor('input', 'output', {})
        monitor.running = True

        monitor.stop()

        assert monitor.running is False

    def test_stop_stops_observer(self):
        """Should stop observer if it exists."""
        monitor = FileMonitor('input', 'output', {})
        monitor.observer = Mock()

        monitor.stop()

        monitor.observer.stop.assert_called_once()
        monitor.observer.join.assert_called_once()

    def test_stop_safe_without_observer(self):
        """Should handle stop gracefully without observer."""
        monitor = FileMonitor('input', 'output', {})
        monitor.observer = None

        # Should not raise
        monitor.stop()

        assert monitor.running is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
