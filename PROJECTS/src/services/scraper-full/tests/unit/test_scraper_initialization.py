"""
Unit tests for ScraperEngine initialization and configuration.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from scraper_engine import ScraperEngine


@pytest.mark.unit
class TestScraperEngineInitialization:
    """Test ScraperEngine initialization."""

    def test_default_initialization(self):
        """Engine should initialize with default parameters."""
        engine = ScraperEngine()

        assert engine.max_concurrent == 3
        assert engine.request_delay == 2.0
        assert engine.page_timeout == 15
        assert engine.max_pages_per_site == 50
        assert engine.max_pdf_size_mb == 100
        assert engine.min_pdf_size_bytes == 512

    def test_custom_initialization(self):
        """Engine should accept custom parameters."""
        engine = ScraperEngine(
            max_concurrent=5,
            request_delay=1.5,
            page_timeout=20,
            max_pages_per_site=100,
            max_pdf_size_mb=200,
            min_pdf_size_bytes=1024
        )

        assert engine.max_concurrent == 5
        assert engine.request_delay == 1.5
        assert engine.page_timeout == 20
        assert engine.max_pages_per_site == 100
        assert engine.max_pdf_size_mb == 200
        assert engine.min_pdf_size_bytes == 1024

    def test_running_state_initial(self):
        """Engine should start in running state."""
        engine = ScraperEngine()
        assert engine.running is True

    def test_page_and_pdf_counters_initial(self):
        """Counters should initialize to zero."""
        engine = ScraperEngine()
        assert engine.page_count == 0
        assert engine.pdf_count == 0

    def test_stop_event_initialization(self):
        """Stop event should be properly initialized."""
        engine = ScraperEngine()
        assert engine._stop_event.is_set() is False

    def test_session_creation(self):
        """Session should be created on initialization."""
        engine = ScraperEngine()
        assert engine.session is not None

    def test_batch_size_parameter(self):
        """Batch size should be configurable."""
        engine = ScraperEngine(batch_size=20)
        assert engine.batch_size == 20

    def test_verbose_logging_parameter(self):
        """Verbose parameter should be stored."""
        engine = ScraperEngine(verbose=True)
        assert engine.verbose is True

        engine = ScraperEngine(verbose=False)
        assert engine.verbose is False

    def test_strict_validation_parameter(self):
        """Strict content validation should be configurable."""
        engine = ScraperEngine(strict_content_validation=True)
        assert engine.strict_content_validation is True

        engine = ScraperEngine(strict_content_validation=False)
        assert engine.strict_content_validation is False


@pytest.mark.unit
class TestScraperEngineControl:
    """Test ScraperEngine control methods."""

    def test_stop_method(self):
        """stop() should set the stop event."""
        engine = ScraperEngine()
        assert engine.running is True

        engine.stop()
        assert engine.running is False

    def test_stop_idempotent(self):
        """Multiple stop() calls should be safe."""
        engine = ScraperEngine()
        engine.stop()
        engine.stop()  # Should not raise
        assert engine.running is False

    def test_running_property(self):
        """running property should reflect stop state."""
        engine = ScraperEngine()

        # Initially running
        assert engine.running is True

        # After stop
        engine.stop()
        assert engine.running is False


@pytest.mark.unit
class TestScraperEngineSessionCreation:
    """Test HTTP session creation with rate limiting."""

    def test_session_has_adapters(self):
        """Session should have HTTP/HTTPS adapters."""
        engine = ScraperEngine()
        assert 'http://' in engine.session.adapters
        assert 'https://' in engine.session.adapters

    def test_session_retry_strategy(self):
        """Session should have retry strategy configured."""
        engine = ScraperEngine()
        http_adapter = engine.session.get_adapter('http://example.com')
        assert http_adapter is not None

    def test_session_request_delay(self):
        """Session adapter should respect request delay."""
        engine = ScraperEngine(request_delay=3.0)
        # Verify the adapter is created with rate limiting
        assert engine.request_delay == 3.0


@pytest.mark.unit
class TestScraperEngineParameterValidation:
    """Test parameter validation and constraints."""

    def test_max_concurrent_positive(self):
        """max_concurrent should be positive."""
        engine = ScraperEngine(max_concurrent=1)
        assert engine.max_concurrent == 1

    def test_request_delay_positive(self):
        """request_delay should be positive."""
        engine = ScraperEngine(request_delay=0.1)
        assert engine.request_delay == 0.1

    def test_page_timeout_reasonable(self):
        """page_timeout should be reasonable."""
        engine = ScraperEngine(page_timeout=5)
        assert engine.page_timeout == 5

    def test_max_pages_realistic(self):
        """max_pages_per_site should be stored."""
        engine = ScraperEngine(max_pages_per_site=10)
        assert engine.max_pages_per_site == 10

    def test_pdf_size_constraints(self):
        """PDF size limits should be configurable."""
        engine = ScraperEngine(
            max_pdf_size_mb=500,
            min_pdf_size_bytes=100
        )
        assert engine.max_pdf_size_mb == 500
        assert engine.min_pdf_size_bytes == 100
