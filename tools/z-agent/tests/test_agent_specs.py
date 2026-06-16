"""验证 AgentSpec 生成的 resume 命令符合各 Agent 契约。"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.agent_specs import get_agent_spec


class AgentSpecsTest(unittest.TestCase):
    def test_codex_resume_argv(self):
        restore = get_agent_spec("codex").build_resume("abc-123")

        self.assertEqual(restore["argv"], ["codex", "resume", "abc-123"])
        self.assertEqual(restore["display"], "codex resume abc-123")

    def test_claude_resume_argv(self):
        restore = get_agent_spec("claude").build_resume("abc-123")

        self.assertEqual(restore["argv"], ["claude", "--resume", "abc-123"])
        self.assertEqual(restore["display"], "claude --resume abc-123")

    def test_unknown_agent(self):
        with self.assertRaises(ValueError):
            get_agent_spec("missing")


if __name__ == "__main__":
    unittest.main()
