"""
Unit tests for the service-installer credential exposure fix.

Covers Updated_Monitor_UI._execute_command() changes:
- _redact_cmd() masks password values in the displayed command line
- password is moved from argv to --password-stdin + subprocess stdin
- pass_var is cleared after the command runs
- live service scripts translate --password-stdin by reading stdin
"""

import sys
import types
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

CLASSIFY_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(CLASSIFY_DIR))

from Updated_Monitor_UI import _redact_cmd, ServiceGUI


class FakeVar:
    """Minimal stand-in for tk.StringVar used by the GUI."""

    def __init__(self, value=''):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def make_gui_instance(password='hunter2'):
    """Build a ServiceGUI-like object without creating a real Tk window."""
    app = object.__new__(ServiceGUI)
    app.service_path_var = FakeVar('svc.py')
    app.user_var = FakeVar('domain\\user')
    app.pass_var = FakeVar(password)
    app.startup_var = FakeVar('auto')
    app.interactive_var = FakeVar(False)
    app.log_text = Mock()
    app.status_var = FakeVar()
    app.after = Mock()
    app._log_message = Mock()
    return app


def test_redact_cmd_masks_password_value():
    result = _redact_cmd(['python', 'svc.py', '--username', 'x', '--password', 'hunter2', 'install'])
    assert 'hunter2' not in result
    assert result[result.index('--password') + 1] == '********'


def test_redact_cmd_no_password_present():
    cmd = ['python', 'svc.py', 'install']
    result = _redact_cmd(cmd)
    assert result == cmd


def test_redact_cmd_leaves_password_stdin_token_alone():
    cmd = ['python', 'svc.py', '--password-stdin', 'install']
    assert _redact_cmd(cmd) == cmd


def test_execute_command_never_puts_password_in_argv():
    app = make_gui_instance(password='hunter2')

    with patch('Updated_Monitor_UI.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='ok', stderr='', returncode=0)
        app._execute_command('install')

    mock_run.assert_called_once()
    cmd = mock_run.call_args.args[0]
    assert '--password' not in cmd
    assert '--password-stdin' in cmd
    assert 'hunter2' not in cmd
    assert mock_run.call_args.kwargs.get('input') == 'hunter2\n'


def test_execute_command_clears_pass_var_after_run():
    app = make_gui_instance(password='hunter2')

    with patch('Updated_Monitor_UI.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='ok', stderr='', returncode=0)
        app._execute_command('install')

    assert app.pass_var.get() == ''


def test_execute_command_no_stdin_when_password_empty():
    app = make_gui_instance(password='')

    with patch('Updated_Monitor_UI.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='ok', stderr='', returncode=0)
        app._execute_command('install')

    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs.get('input') is None


def _stub_service_deps():
    """Inject fake modules so simple_W_service.py can be imported in CI."""
    for name in ['watchdog', 'watchdog.observers', 'watchdog.events',
                 'win32serviceutil', 'win32service', 'win32event',
                 'servicemanager']:
        if name not in sys.modules:
            sys.modules[name] = MagicMock()


def test_simple_W_service_password_stdin_reads_from_stdin():
    _stub_service_deps()

    with patch('sys.stdin') as mock_stdin:
        mock_stdin.readline.return_value = 'hunter2\n'
        import simple_W_service
        argv = simple_W_service._resolve_password_from_stdin(
            ['py', '--username', 'u', '--password-stdin', 'install'])
        assert '--password' in argv
        assert '--password-stdin' not in argv
        assert argv[argv.index('--password') + 1] == 'hunter2'


def test_simple_W_service_no_password_stdin_unchanged():
    _stub_service_deps()

    import simple_W_service
    argv = simple_W_service._resolve_password_from_stdin(['py', 'install'])
    assert argv == ['py', 'install']