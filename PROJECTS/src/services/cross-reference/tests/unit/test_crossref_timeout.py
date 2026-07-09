"""
Unit Tests for crossref_standalone_fast timeout & process management.

Covers:
- Duplicate timeout_handler (module-level vs class-scoped)
- emergency_stop() and GlobalStopManager.set_stop_flag
- Bare except: in terminate_all_processes and KeyboardInterrupt handling

Run with: python -m pytest src/services/cross-reference/tests/unit/test_crossref_timeout.py -v -m unit
"""

import sys
import os
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock


service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

from crossref_standalone_fast import (
    timeout_handler as module_timeout_handler,
    TimeoutException,
    TimeoutError,
    GlobalStopManager,
    emergency_stop,
)


# ============================================================================
# Duplicate timeout_handler
# ============================================================================


class TestDuplicateTimeoutHandler:
    @pytest.mark.unit
    def test_module_level_handler_raises_timeouterror(self):
        with pytest.raises(TimeoutError, match="PDF processing timed out"):
            module_timeout_handler(None, None)

    @pytest.mark.unit
    def test_timeoutexception_still_importable(self):
        assert issubclass(TimeoutException, Exception)

    @pytest.mark.unit
    def test_timeouterror_still_importable(self):
        assert issubclass(TimeoutError, Exception)

    @pytest.mark.unit
    def test_two_exception_types_are_distinct(self):
        assert TimeoutException is not TimeoutError
        assert not issubclass(TimeoutError, TimeoutException)
        assert not issubclass(TimeoutException, TimeoutError)

    @pytest.mark.unit
    def test_source_has_duplicate_timeout_handler_definitions(self):
        source = Path(__file__).parent.parent.parent / "crossref_standalone_fast.py"
        text = source.read_text(encoding="utf-8")
        count = text.count("def timeout_handler")
        assert count == 2, f"Expected 2 timeout_handler defs, found {count}"


# ============================================================================
# emergency_stop
# ============================================================================


class TestEmergencyStop:
    @pytest.mark.unit
    def test_sets_stop_flag(self):
        GlobalStopManager._stop_flag = False
        with patch("builtins.print"), \
             patch("os._exit") as mock_exit:
            emergency_stop()
        assert GlobalStopManager.should_stop() is True

    @pytest.mark.unit
    def test_calls_set_stop_flag_with_true(self):
        GlobalStopManager._stop_flag = False
        with patch.object(GlobalStopManager, "set_stop_flag") as mock_set, \
             patch("builtins.print"), \
             patch("os._exit"):
            emergency_stop()
            mock_set.assert_called_once_with(True)

    @pytest.mark.unit
    def test_calls_os_exit_with_one(self):
        GlobalStopManager._stop_flag = False
        with patch("builtins.print"), \
             patch("os._exit") as mock_exit:
            emergency_stop()
            mock_exit.assert_called_once_with(1)


# ============================================================================
# GlobalStopManager.terminate_all_processes / set_stop_flag
# ============================================================================


class TestGlobalStopManager:
    @pytest.mark.unit
    def test_set_stop_flag_triggers_terminate_all(self):
        with patch.object(GlobalStopManager, "terminate_all_processes") as mock_term:
            GlobalStopManager.set_stop_flag(True)
            mock_term.assert_called_once()

    @pytest.mark.unit
    def test_set_stop_flag_false_does_not_terminate(self):
        GlobalStopManager._processes.clear()
        with patch.object(GlobalStopManager, "terminate_all_processes") as mock_term:
            GlobalStopManager.set_stop_flag(False)
            mock_term.assert_not_called()

    @pytest.mark.unit
    def test_should_stop_returns_flag_value(self):
        GlobalStopManager._stop_flag = True
        assert GlobalStopManager.should_stop() is True
        GlobalStopManager._stop_flag = False
        assert GlobalStopManager.should_stop() is False

    @pytest.mark.unit
    def test_bare_except_swallows_keyboard_interrupt_bug(self):
        """KNOWN BUG: The bare except: in terminate_all_processes catches
        KeyboardInterrupt instead of letting it propagate.
        This test documents the current (broken) behavior."""
        mock_proc = MagicMock()
        mock_proc.is_alive.side_effect = KeyboardInterrupt()
        GlobalStopManager._processes.clear()
        GlobalStopManager._processes.append(mock_proc)
        GlobalStopManager.terminate_all_processes()

    @pytest.mark.unit
    def test_register_and_clear_processes(self):
        GlobalStopManager._processes.clear()
        mock_proc = MagicMock()
        GlobalStopManager.register_process(mock_proc)
        assert mock_proc in GlobalStopManager._processes
        GlobalStopManager._processes.clear()

    @pytest.mark.unit
    def test_terminate_all_clears_process_list(self):
        mock_proc = MagicMock()
        mock_proc.is_alive.return_value = True
        GlobalStopManager._processes.clear()
        GlobalStopManager._processes.append(mock_proc)
        GlobalStopManager.terminate_all_processes()
        assert len(GlobalStopManager._processes) == 0

    @pytest.mark.unit
    def test_terminate_calls_terminate_and_kill(self):
        mock_proc = MagicMock()
        mock_proc.is_alive.return_value = True
        GlobalStopManager._processes.clear()
        GlobalStopManager._processes.append(mock_proc)
        GlobalStopManager.terminate_all_processes()
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    @pytest.mark.unit
    def test_terminate_already_dead_process(self):
        mock_proc = MagicMock()
        mock_proc.is_alive.return_value = False
        GlobalStopManager._processes.clear()
        GlobalStopManager._processes.append(mock_proc)
        GlobalStopManager.terminate_all_processes()
        mock_proc.terminate.assert_not_called()
        mock_proc.kill.assert_not_called()


@pytest.fixture(autouse=True)
def reset_global_state():
    GlobalStopManager._stop_flag = False
    GlobalStopManager._processes.clear()
    yield
    GlobalStopManager._stop_flag = False
    GlobalStopManager._processes.clear()
