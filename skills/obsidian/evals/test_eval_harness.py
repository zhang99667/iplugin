#!/usr/bin/env python3
"""回归测试 Obsidian 行为 eval 的任务隔离、输入哈希和评分归档。"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parent / "run_evals.py"


class EvalHarnessTest(unittest.TestCase):
    def test_prepare_and_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            prepared = subprocess.run(
                ["python3", str(RUNNER), "prepare", "--eval-id", "8", "--run-dir", str(run_dir)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)
            task = json.loads((run_dir / "agent" / "task.json").read_text(encoding="utf-8"))
            rubric = json.loads((run_dir / "grader" / "rubric.json").read_text(encoding="utf-8"))
            self.assertNotIn("expectations", task)
            self.assertEqual(task["input_sha256"], rubric["input_sha256"])
            self.assertEqual(task["skill_sha256"], rubric["skill_sha256"])
            self.assertTrue((run_dir / "agent" / task["skill_entrypoint"]).is_file())
            self.assertTrue((run_dir / "agent" / "skill" / "scripts" / "validate_note.py").is_file())

            (run_dir / "submission" / "final.md").write_text("final", encoding="utf-8")
            (run_dir / "submission" / "trace.md").write_text("trace", encoding="utf-8")
            assessment = json.loads(
                (run_dir / "grader" / "assessment-template.json").read_text(encoding="utf-8")
            )
            for item in assessment["expectations"]:
                item["passed"] = True
                item["evidence"] = ["submission/trace.md:1"]
            assessment_path = run_dir / "grader" / "assessment.json"
            assessment_path.write_text(json.dumps(assessment, ensure_ascii=False), encoding="utf-8")

            finalized = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "finalize",
                    "--run-dir",
                    str(run_dir),
                    "--assessment",
                    str(assessment_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, finalized.returncode, finalized.stderr)
            result = json.loads((run_dir / "grader" / "result.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", result["status"])

    def test_finalize_rejects_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            subprocess.run(
                ["python3", str(RUNNER), "prepare", "--eval-id", "9", "--run-dir", str(run_dir)],
                check=True,
                capture_output=True,
            )
            assessment_path = run_dir / "grader" / "assessment-template.json"
            finalized = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "finalize",
                    "--run-dir",
                    str(run_dir),
                    "--assessment",
                    str(assessment_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, finalized.returncode)
            self.assertIn("缺少非空评测产物", finalized.stderr)

    def test_finalize_rejects_evidence_outside_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            subprocess.run(
                ["python3", str(RUNNER), "prepare", "--eval-id", "9", "--run-dir", str(run_dir)],
                check=True,
                capture_output=True,
            )
            (run_dir / "submission" / "final.md").write_text("final", encoding="utf-8")
            (run_dir / "submission" / "trace.md").write_text("trace", encoding="utf-8")
            assessment = json.loads(
                (run_dir / "grader" / "assessment-template.json").read_text(encoding="utf-8")
            )
            for item in assessment["expectations"]:
                item["passed"] = True
                item["evidence"] = ["grader/rubric.json:1"]
            assessment_path = run_dir / "grader" / "assessment.json"
            assessment_path.write_text(json.dumps(assessment, ensure_ascii=False), encoding="utf-8")

            finalized = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "finalize",
                    "--run-dir",
                    str(run_dir),
                    "--assessment",
                    str(assessment_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, finalized.returncode)
            self.assertIn("必须位于 submission", finalized.stderr)


if __name__ == "__main__":
    unittest.main()
