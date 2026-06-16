"""验证 Ghostty AppleScript 生成逻辑，不触发真实 GUI 自动化。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.ghostty import build_restore_script


class GhosttyScriptTest(unittest.TestCase):
    def test_restore_script_contains_safe_resume_command(self):
        workspace = {
            "windows": [
                {
                    "window_index": 1,
                    "tabs": [
                        {
                            "tab_index": 1,
                            "split_tree": {
                                "cwd": "/repo",
                                "agent": "codex",
                                "session_id": "019e9d90",
                                "binding_confidence": "high",
                                "restore": {
                                    "agent": "codex",
                                    "argv": ["codex", "resume", "019e9d90"],
                                    "display": "codex resume 019e9d90",
                                    "kind": "agent_resume",
                                },
                                "restore_cmd": "codex resume 019e9d90",
                            },
                        }
                    ],
                }
            ]
        }

        script = build_restore_script(workspace)

        self.assertIn('tell application "Ghostty"', script)
        self.assertIn('initial working directory:"/repo"', script)
        self.assertIn('input text "codex resume 019e9d90\n"', script)


if __name__ == "__main__":
    unittest.main()
