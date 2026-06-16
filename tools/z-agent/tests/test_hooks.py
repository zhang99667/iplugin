"""验证 hook ingest 只提取恢复元数据并正确写入状态。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent.hooks import HookIngestError, extract_session_metadata, ingest_hook_event
from z_agent.state import load_state


class HooksTest(unittest.TestCase):
    def test_extracts_explicit_session_id(self):
        session_id, session_file = extract_session_metadata(
            {"event": {"session_id": "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"}}
        )

        self.assertEqual(session_id, "019e9d90-07e9-79c3-93c3-a5b6952aaf4f")
        self.assertIsNone(session_file)

    def test_derives_session_id_from_transcript_path(self):
        session_id, session_file = extract_session_metadata(
            {"transcript_path": "/tmp/rollout-019e9d90-07e9-79c3-93c3-a5b6952aaf4f.jsonl"}
        )

        self.assertEqual(session_id, "019e9d90-07e9-79c3-93c3-a5b6952aaf4f")
        self.assertEqual(
            session_file,
            "/tmp/rollout-019e9d90-07e9-79c3-93c3-a5b6952aaf4f.jsonl",
        )

    def test_ingest_updates_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "Z_AGENT_STATE_DIR": tmp,
                "Z_AGENT_TERMINAL_KEY": "za_terminal_a1b2c3d4",
                "Z_AGENT_CWD": "/repo",
                "Z_AGENT_RUN_ID": "za_run_abc12345",
            }
            with patch.dict(os.environ, env, clear=False):
                patch_data = ingest_hook_event(
                    "codex",
                    {"session_id": "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"},
                    env=env,
                )
                state = load_state(Path(tmp))

            self.assertTrue(patch_data["resumable"])
            active = state["active_terminals"]["za_terminal_a1b2c3d4"]
            self.assertEqual(active["agent"], "codex")
            self.assertEqual(
                active["restore"]["argv"],
                ["codex", "resume", "019e9d90-07e9-79c3-93c3-a5b6952aaf4f"],
            )

    def test_missing_terminal_key_fails(self):
        with self.assertRaises(HookIngestError):
            ingest_hook_event("codex", {"session_id": "abc"}, env={})


if __name__ == "__main__":
    unittest.main()
