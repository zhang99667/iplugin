"""验证 restore planner 的白名单和低置信绑定保护。"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.planner import RestorePlanError, assert_plan_executable, build_restore_plan, validate_restore


def _workspace(confidence="high", restore=None):
    restore = restore or {
        "kind": "agent_resume",
        "agent": "codex",
        "argv": ["codex", "resume", "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"],
        "display": "codex resume 019e9d90-07e9-79c3-93c3-a5b6952aaf4f",
    }
    return {
        "snapshot_id": "ws_test",
        "captured_at": "2026-06-13T14:30:15+08:00",
        "terminal_app": "Ghostty",
        "windows": [
            {
                "window_index": 1,
                "tabs": [
                    {
                        "tab_index": 1,
                        "split_tree": {
                            "direction": "unknown",
                            "children": [
                                {
                                    "cwd": "/repo",
                                    "agent": "codex",
                                    "session_id": "019e9d90-07e9-79c3-93c3-a5b6952aaf4f",
                                    "binding_confidence": confidence,
                                    "restore": restore,
                                    "restore_cmd": restore["display"],
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


class PlannerTest(unittest.TestCase):
    def test_validates_codex_resume(self):
        ok, reason = validate_restore(
            {"agent": "codex", "argv": ["codex", "resume", "019e9d90-07e9"], "display": ""}
        )

        self.assertTrue(ok)
        self.assertEqual(reason, "通过")

    def test_rejects_non_whitelisted_command(self):
        ok, reason = validate_restore({"agent": "codex", "argv": ["sh", "-c", "echo nope"]})

        self.assertFalse(ok)
        self.assertIn("白名单", reason)

    def test_high_confidence_plan_is_executable(self):
        plan = build_restore_plan(_workspace())

        self.assertTrue(plan["items"][0]["allowed"])
        assert_plan_executable(plan)

    def test_low_confidence_plan_is_not_executable(self):
        plan = build_restore_plan(_workspace(confidence="low"))

        self.assertFalse(plan["items"][0]["allowed"])
        with self.assertRaises(RestorePlanError):
            assert_plan_executable(plan)

    def test_legacy_string_restore_cmd_is_not_executable(self):
        workspace = _workspace()
        pane = workspace["windows"][0]["tabs"][0]["split_tree"]["children"][0]
        pane["restore"] = None

        plan = build_restore_plan(workspace)

        self.assertFalse(plan["items"][0]["allowed"])
        with self.assertRaises(RestorePlanError):
            assert_plan_executable(plan)


if __name__ == "__main__":
    unittest.main()
