import unittest
from io import StringIO
from unittest.mock import patch

from arista_sim import Session
from arista_sim.terminal import _enable_readline, _read_windows_command, read_command


class TerminalTests(unittest.TestCase):
    @patch("builtins.input", return_value="enable")
    def test_non_windows_or_redirected_input_uses_standard_input(self, mocked):
        session = Session()
        self.assertEqual(read_command(session), "enable")
        mocked.assert_called_once_with("switch> ")

    @patch("arista_sim.terminal._enable_readline")
    @patch("arista_sim.terminal.os.name", "posix")
    @patch("arista_sim.terminal.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="show vlan")
    def test_posix_tty_enables_readline_history(
        self, mocked_input, _mocked_isatty, mocked_enable
    ):
        session = Session()
        self.assertEqual(read_command(session), "show vlan")
        mocked_enable.assert_called_once_with()
        mocked_input.assert_called_once_with("switch> ")

    @patch.dict("sys.modules", {"readline": object()})
    def test_readline_is_enabled_when_module_is_available(self):
        self.assertTrue(_enable_readline())

    @patch("builtins.__import__", side_effect=ImportError)
    def test_readline_falls_back_when_module_is_unavailable(self, _mocked_import):
        self.assertFalse(_enable_readline())

    def test_question_mark_displays_help_without_entering_it(self):
        session = Session()
        keys = iter(["e", "n", "?", "\r"])
        output = StringIO()
        command = _read_windows_command(session, lambda: next(keys), output)
        self.assertEqual(command, "en")
        self.assertIn("enable", output.getvalue())
        self.assertIn("switch> en", output.getvalue())

    def test_up_and_down_arrows_recall_history_and_restore_draft(self):
        session = Session()
        session.history.extend(["enable", "show vlan"])
        keys = iter(["x", "\xe0", "H", "\xe0", "H", "\xe0", "P", "\xe0", "P", "\r"])
        output = StringIO()
        command = _read_windows_command(session, lambda: next(keys), output)
        self.assertEqual(command, "x")


if __name__ == "__main__":
    unittest.main()
