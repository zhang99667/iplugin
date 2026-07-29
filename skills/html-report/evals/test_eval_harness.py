#!/usr/bin/env python3
"""回归测试 html-report eval runner 的隔离、校验、评分和汇总链路。"""

from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


EVALS_DIR = Path(__file__).resolve().parent
RUNNER = EVALS_DIR / "run_evals.py"


class EvalHarnessTest(unittest.TestCase):
    def test_prepare_hides_rubric_and_preserves_nested_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            prepared = subprocess.run(
                ["python3", str(RUNNER), "prepare", "--eval-id", "7", "--run-dir", str(run_dir)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)
            task = json.loads((run_dir / "agent" / "task.json").read_text(encoding="utf-8"))
            self.assertNotIn("expectations", task)
            self.assertFalse((run_dir / "grader").exists())
            self.assertTrue(
                (run_dir / "agent" / "inputs" / "review_workspace_sources" / "CheckoutGate.baseline.kt").is_file()
            )
            self.assertTrue((run_dir / "agent" / task["skill_entrypoint"]).is_file())

    def test_verify_rejects_invalid_report_and_records_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            subprocess.run(
                ["python3", str(RUNNER), "prepare", "--eval-id", "6", "--run-dir", str(run_dir)],
                check=True,
                capture_output=True,
            )
            (run_dir / "submission" / "report.html").write_text("<html></html>", encoding="utf-8")
            (run_dir / "submission" / "trace.md").write_text("validator failed\n", encoding="utf-8")
            verified = subprocess.run(
                ["python3", str(RUNNER), "verify", "--run-dir", str(run_dir)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, verified.returncode)
            checks = json.loads(
                (run_dir / "grader" / "automated-checks.json").read_text(encoding="utf-8")
            )
            self.assertFalse(checks["passed"])
            self.assertFalse(next(item for item in checks["checks"] if item["id"] == "html-validator")["passed"])

    def test_run_uses_separate_agent_and_grader_then_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            run_dir = temporary / "run"
            fake_codex = temporary / "fake-codex"
            # 假执行器只模拟 Codex CLI 的文件契约，避免单元测试消耗真实模型调用。
            fake_codex.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import shutil
                    import sys
                    from pathlib import Path

                    args = sys.argv[1:]
                    workdir = Path(args[args.index("-C") + 1])
                    output = Path(args[args.index("-o") + 1])
                    if "--output-schema" in args:
                        template = json.loads((workdir / "grader" / "assessment-template.json").read_text(encoding="utf-8"))
                        for item in template["expectations"]:
                            item["passed"] = True
                            item["evidence"] = ["submission/trace.md:1"]
                            item["reason"] = "fixture evidence"
                        output.write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
                    else:
                        submission = workdir.parent / "submission"
                        shutil.copy2(workdir / "inputs" / "annotation_source_report.html", submission / "report.html")
                        (submission / "trace.md").write_text("validated\\n", encoding="utf-8")
                        output.write_text("done\\n", encoding="utf-8")
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            completed = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "run",
                    "--eval-id",
                    "6",
                    "--run-dir",
                    str(run_dir),
                    "--codex-bin",
                    str(fake_codex),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            result = json.loads((run_dir / "grader" / "result.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", result["status"])
            self.assertEqual(1.0, result["expectation_pass_rate"])

            summary = subprocess.run(
                ["python3", str(RUNNER), "summary", "--runs-dir", str(temporary)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, summary.returncode, summary.stderr)
            summary_data = json.loads(summary.stdout)
            self.assertEqual(1, summary_data["run_count"])
            self.assertEqual(1.0, summary_data["run_pass_rate"])


if __name__ == "__main__":
    unittest.main()
