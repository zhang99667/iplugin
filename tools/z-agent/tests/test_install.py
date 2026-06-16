"""验证 install 只生成 hook 配置，不接管真实 Agent 命令。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.install import build_install_plan


class InstallTest(unittest.TestCase):
    def test_install_plan_does_not_shadow_agent_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"Z_AGENT_INSTALL_ROOT": tmp}, clear=False):
                plan = build_install_plan("codex")

        paths = sorted(plan)
        self.assertEqual(
            paths,
            [
                str(Path(tmp) / "codex" / "config" / "hooks" / "codex-hook-ingest.sh"),
                str(Path(tmp) / "codex" / "config" / "hooks" / "codex-native-hooks.json"),
            ],
        )
        self.assertNotIn("/bin/codex", "\n".join(paths))
        self.assertNotIn("codex.zsh", "\n".join(paths))

    def test_hook_ingest_script_points_back_to_zagent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"Z_AGENT_INSTALL_ROOT": tmp}, clear=False):
                plan = build_install_plan("claude")

        hook_path = str(Path(tmp) / "claude" / "config" / "hooks" / "claude-hook-ingest.sh")
        self.assertIn("hook ingest --agent claude --json", plan[hook_path])


if __name__ == "__main__":
    unittest.main()
