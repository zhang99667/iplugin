"""验证 workspace_state.json 的读写、备份和快照轮转。"""

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.state import load_state, save_latest_workspace, update_active_terminal


class StateTest(unittest.TestCase):
    def test_missing_state_returns_empty_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing-dir"
            state = load_state(root)

            self.assertEqual(state["schema"], 1)
            self.assertFalse(root.exists())

    def test_update_active_terminal_preserves_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update_active_terminal("za_terminal_a1b2c3d4", {"agent": "codex"}, root=root)
            update_active_terminal("za_terminal_a1b2c3d4", {"cwd": "/repo"}, root=root)
            state = load_state(root)

            active = state["active_terminals"]["za_terminal_a1b2c3d4"]
            self.assertEqual(active["agent"], "codex")
            self.assertEqual(active["cwd"], "/repo")

    def test_save_latest_workspace_moves_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_latest_workspace({"snapshot_id": "one", "windows": []}, root=root)
            save_latest_workspace({"snapshot_id": "two", "windows": []}, root=root)
            state = load_state(root)

            self.assertEqual(state["latest_workspace"]["snapshot_id"], "two")
            self.assertEqual(state["previous_workspace"]["snapshot_id"], "one")

    def test_broken_state_is_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "workspace_state.json"
            path.write_text("{broken", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                state = load_state(root)

            self.assertEqual(state["schema"], 1)
            backups = list(root.glob("workspace_state.json.broken.*"))
            self.assertEqual(len(backups), 1)
            json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
