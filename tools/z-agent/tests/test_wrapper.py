"""验证 wrapper 构造的环境变量和 terminal 身份。"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.wrapper import prepare_wrapper_context


class WrapperTest(unittest.TestCase):
    def test_context_injects_z_agent_environment(self):
        with patch("os.getcwd", return_value="/repo"):
            context = prepare_wrapper_context(
                "codex",
                ["--model", "gpt-5"],
                explicit_binary="/bin/echo",
                env={},
            )

        self.assertEqual(context.binary, "/bin/echo")
        self.assertEqual(context.args, ["--model", "gpt-5"])
        self.assertTrue(context.terminal_key.startswith("za_terminal_"))
        self.assertTrue(context.run_id.startswith("za_run_"))
        self.assertEqual(context.env["Z_AGENT_CWD"], "/repo")
        self.assertEqual(context.env["Z_AGENT_AGENT"], "codex")

    def test_context_reuses_existing_terminal_key(self):
        with patch("os.getcwd", return_value="/repo"):
            context = prepare_wrapper_context(
                "claude",
                [],
                explicit_binary="/bin/echo",
                env={"Z_AGENT_TERMINAL_KEY": "za_terminal_existing"},
            )

        self.assertEqual(context.terminal_key, "za_terminal_existing")
        self.assertEqual(context.env["Z_AGENT_TERMINAL_KEY"], "za_terminal_existing")


if __name__ == "__main__":
    unittest.main()
