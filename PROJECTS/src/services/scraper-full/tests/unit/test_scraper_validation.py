"""
Unit tests for scraper_engine validation functions.
Tests security and input validation logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(service_dir))

from scraper_engine import _validate_url, _sanitize_path, _file_hash


@pytest.mark.unit
class TestValidateUrl:
    """Test URL validation security function."""

    def test_valid_https_url(self):
        """Valid HTTPS URLs should pass."""
        assert _validate_url('https://www.example.com') is True
        assert _validate_url('https://example.com/path') is True
        assert _validate_url('https://subdomain.example.com:8080/resource') is True

    def test_valid_http_url(self):
        """Valid HTTP URLs should pass."""
        assert _validate_url('http://www.example.com') is True
        assert _validate_url('http://example.com/path') is True

    def test_invalid_protocol(self):
        """Non-HTTP(S) protocols should fail."""
        assert _validate_url('ftp://example.com') is False
        assert _validate_url('file:///etc/passwd') is False
        assert _validate_url('javascript:alert(1)') is False

    def test_localhost_blocked(self):
        """Localhost URLs should be blocked."""
        assert _validate_url('http://localhost') is False
        assert _validate_url('http://localhost:8080') is False
        assert _validate_url('http://127.0.0.1') is False

    def test_missing_scheme(self):
        """URLs without scheme should fail."""
        assert _validate_url('example.com') is False
        assert _validate_url('www.example.com') is False

    def test_empty_netloc(self):
        """URLs with empty network location should fail."""
        assert _validate_url('https://') is False

    def test_malformed_url(self):
        """Malformed URLs should fail gracefully."""
        assert _validate_url('not-a-url') is False
        assert _validate_url('') is False
        assert _validate_url('http://') is False


@pytest.mark.unit
class TestSanitizePath:
    """Test filename sanitization function."""

    def test_remove_path_traversal(self):
        """Path traversal sequences should be removed."""
        result = _sanitize_path('../../../etc/passwd')
        assert '..' not in result
        assert '/' not in result

    def test_remove_dangerous_chars(self):
        """Dangerous characters should be replaced."""
        result = _sanitize_path('file<name>test|.pdf')
        assert '<' not in result
        assert '>' not in result
        assert '|' not in result

    def test_replace_slashes(self):
        """Forward and backslashes should be replaced."""
        result = _sanitize_path('path/to/file.pdf')
        assert '/' not in result

        result = _sanitize_path('path\\to\\file.pdf')
        assert '\\' not in result

    def test_colon_replacement(self):
        """Colons should be replaced (Windows compatibility)."""
        result = _sanitize_path('file:name')
        assert ':' not in result

    def test_quote_replacement(self):
        """Quotes should be replaced."""
        result = _sanitize_path('file"name\'test')
        assert '"' not in result
        assert "'" not in result

    def test_normal_filename(self):
        """Normal filenames should be largely unchanged."""
        filename = 'document_2024-01-15.pdf'
        result = _sanitize_path(filename)
        assert result == filename

    def test_wildcard_removal(self):
        """Wildcards should be replaced."""
        result = _sanitize_path('file*.pdf')
        assert '*' not in result

        result = _sanitize_path('file?.pdf')
        assert '?' not in result


@pytest.mark.unit
class TestFileHash:
    """Test file hashing function."""

    def test_hash_existing_file(self, temp_output_dir):
        """Hash should compute correctly for existing files."""
        import hashlib
        from pathlib import Path

        # Create test file
        test_file = Path(temp_output_dir) / 'test.txt'
        content = b'test content for hashing'
        test_file.write_bytes(content)

        # Compute hash
        result = _file_hash(str(test_file))

        # Verify
        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_large_file(self, temp_output_dir):
        """Hash should handle large files correctly."""
        import hashlib
        from pathlib import Path

        test_file = Path(temp_output_dir) / 'large.bin'

        # Create a large file (5MB)
        chunk_size = 1024 * 1024  # 1MB
        chunk = b'x' * chunk_size
        with open(test_file, 'wb') as f:
            for _ in range(5):
                f.write(chunk)

        # Hash should complete without error
        result = _file_hash(str(test_file))
        assert result is not None
        assert len(result) == 64  # SHA-256 hex length

    def test_hash_nonexistent_file(self):
        """Nonexistent file should return None."""
        result = _file_hash('/nonexistent/path/file.txt')
        assert result is None

    def test_hash_empty_file(self, temp_output_dir):
        """Empty file should return valid hash."""
        import hashlib
        from pathlib import Path

        test_file = Path(temp_output_dir) / 'empty.txt'
        test_file.write_text('')

        result = _file_hash(str(test_file))
        expected = hashlib.sha256(b'').hexdigest()
        assert result == expected

    def test_hash_consistency(self, temp_output_dir):
        """Same file should produce consistent hash."""
        from pathlib import Path

        test_file = Path(temp_output_dir) / 'consistent.txt'
        test_file.write_text('consistent content')

        hash1 = _file_hash(str(test_file))
        hash2 = _file_hash(str(test_file))

        assert hash1 == hash2
