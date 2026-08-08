import unittest
from io import StringIO
from unittest.mock import patch

from arista_sim import Session
from arista_sim.terminal import _read_windows_command, read_command


class TerminalTests(unittest.TestCase):
    @patch("builtins.input", return_value="enable")
    def test_non_windows_or_redirected_input_uses_standard_input(self, mocked):
        session = Session()
        self.assertEqual(read_command(session), "enable")
        mocked.assert_called_once_with("switch> ")

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
