import json
import sys
import tempfile
import unittest
from pathlib import Path

# unittest discover 以 tests/ 作为起点时不会自动把 Skill 根目录加入导入路径；
# 显式加入根目录，确保测试命令与 Skill 实际运行方式使用同一份脚本。
SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from scripts.export_session import build_markdown, parse_rollout


class ExportSessionTest(unittest.TestCase):
    def write_jsonl(self, rows: list[dict]) -> Path:
        directory = Path(self.tmp.name)
        path = directory / "rollout-2026-08-18T00-00-00-11111111-1111-1111-1111-111111111111.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        return path

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_current_rollout_message_schema(self) -> None:
        path = self.write_jsonl(
            [
                {"type": "session_meta", "payload": {"id": "session-1", "cwd": "/tmp/project"}},
                {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "hidden"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "world"}]}},
                {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "input": "pwd", "call_id": "call-1"}},
                {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "call-1", "output": "/tmp/project"}},
            ]
        )

        data = parse_rollout(path, include_tools=True, max_tool_output=100)

        self.assertEqual(data["metadata"]["id"], "session-1")
        self.assertEqual([(role, text) for role, text, _ in data["transcript"]], [("User", "hello"), ("Codex", "world")])
        self.assertEqual(data["tools"][0]["name"], "exec")
        self.assertEqual(data["tools"][0]["output"], "/tmp/project")

    def test_legacy_event_message_schema(self) -> None:
        path = self.write_jsonl(
            [
                {"type": "event_msg", "payload": {"type": "user_message", "message": "hello"}},
                {"type": "event_msg", "payload": {"type": "agent_message", "message": "world", "phase": "final"}},
            ]
        )

        data = parse_rollout(path, include_tools=False, max_tool_output=100)

        self.assertEqual([(role, text) for role, text, _ in data["transcript"]], [("User", "hello"), ("Codex", "world")])

    def test_exec_json_events(self) -> None:
        path = self.write_jsonl(
            [
                {"type": "thread.started", "thread_id": "exec-session"},
                {"type": "item.completed", "item": {"type": "user_message", "text": "run the task"}},
                {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
                {"type": "item.completed", "item": {"type": "command_execution", "command": "pwd", "aggregated_output": "/tmp/project"}},
            ]
        )

        data = parse_rollout(path, include_tools=False, max_tool_output=100)
        markdown = build_markdown(data, "Codex Session exec-session", False, [])

        self.assertEqual(data["metadata"]["id"], "exec-session")
        self.assertEqual([(role, text) for role, text, _ in data["transcript"]], [("User", "run the task"), ("Codex", "done")])
        self.assertEqual(data["tools"][0]["name"], "command_execution")
        self.assertIn("done", markdown)


if __name__ == "__main__":
    unittest.main()
