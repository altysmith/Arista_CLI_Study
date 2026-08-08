import unittest
from unittest.mock import patch

from arista_sim import Session
from arista_sim.terminal import read_command


class TerminalTests(unittest.TestCase):
    @patch("builtins.input", return_value="enable")
    def test_non_windows_or_redirected_input_uses_standard_input(self, mocked):
        session = Session()
        self.assertEqual(read_command(session), "enable")
        mocked.assert_called_once_with("switch> ")


if __name__ == "__main__":
    unittest.main()
