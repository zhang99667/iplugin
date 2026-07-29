#!/usr/bin/env python3
"""运行 html-report 隔离评测，并归档确定性校验与逐项评分结果。"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVALS_DIR = Path(__file__).resolve().parent
SKILL_DIR = EVALS_DIR.parent
EVALS_FILE = EVALS_DIR / "evals.json"
FIXTURES_DIR = EVALS_DIR / "fixtures"


def load_json(path: Path) -> Any:
    """读取 JSON，并把底层异常转换成适合命令行展示的错误。"""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    """稳定写入 UTF-8 JSON，保证评测产物便于 diff 和归档。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_evals() -> list[dict[str, Any]]:
    data = load_json(EVALS_FILE)
    evals = data.get("evals") if isinstance(data, dict) else None
    if not isinstance(evals, list) or not evals:
        raise ValueError(f"{EVALS_FILE} 缺少非空 evals 数组")
    return evals


def find_eval(eval_id: int) -> dict[str, Any]:
    for item in load_evals():
        if item.get("id") == eval_id:
            return item
    raise ValueError(f"不存在 eval id: {eval_id}")


def stable_digest(parts: list[tuple[str, bytes]]) -> str:
    """同时哈希相对路径和内容，避免同内容换路径后仍被误判为同一输入。"""

    digest = hashlib.sha256()
    for label, content in sorted(parts):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def definition_digest(item: dict[str, Any]) -> str:
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fixture_source(file_ref: str) -> Path:
    """解析 fixture 引用，并阻止路径越出当前 skill。"""

    source = (SKILL_DIR / file_ref).resolve()
    try:
        source.relative_to(SKILL_DIR.resolve())
    except ValueError as exc:
        raise ValueError(f"fixture 路径越出 html-report skill: {file_ref}") from exc
    if not source.is_file():
        raise ValueError(f"fixture 不存在: {file_ref}")
    return source


def input_digest(item: dict[str, Any]) -> str:
    parts = [("prompt", item["prompt"].encode("utf-8"))]
    for file_ref in item.get("files", []):
        parts.append((file_ref, fixture_source(file_ref).read_bytes()))
    return stable_digest(parts)


def skill_files(root: Path = SKILL_DIR) -> list[Path]:
    """收集任务 Agent 需要的 skill 快照，不包含 eval rubric 和缓存文件。"""

    files = [root / "SKILL.md"]
    for relative_dir in ("references", "assets", "scripts"):
        directory = root / relative_dir
        if directory.is_dir():
            files.extend(
                path
                for path in directory.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    return sorted(files)


def tree_digest(root: Path, files: list[Path] | None = None) -> str:
    selected = files if files is not None else skill_files(root)
    return stable_digest(
        [(path.relative_to(root).as_posix(), path.read_bytes()) for path in selected]
    )


def copied_fixture_path(file_ref: str) -> Path:
    """保留 fixtures 下的目录结构，使 Workspace spec 的相对源码路径继续有效。"""

    source = fixture_source(file_ref)
    try:
        relative = source.relative_to(FIXTURES_DIR.resolve())
    except ValueError as exc:
        raise ValueError(f"eval 输入必须位于 evals/fixtures/: {file_ref}") from exc
    return Path("inputs") / relative


def build_task_prompt(task: dict[str, Any]) -> str:
    file_lines = "\n".join(f"- `{file_ref}`" for file_ref in task["files"])
    return f"""# html-report 隔离评测任务

从 `skill/SKILL.md` 开始读取并严格使用该 skill，完成下面的用户请求：

{task["prompt"]}

输入文件：
{file_lines or "- 无"}

评测输出契约优先于用户请求中的默认桌面路径：

1. 最终单文件报告必须写到 `../submission/report.html`。
2. 执行过的关键脚本、校验命令和结果摘要写到 `../submission/trace.md`。
3. 图片或视频等附属证据只能写到 `../submission/assets/`，并从报告使用相对路径引用。
4. 完成前必须运行快照中的 `skill/scripts/check_html_report.py` 校验最终报告。
5. 只读取当前 `agent/` 工作区提供的 skill 和 inputs；不要寻找评测标准或预期答案。
"""


def prepare(eval_id: int, run_dir: Path) -> None:
    """创建不含 rubric 的任务包，保护 forward test 的评分完整性。"""

    item = find_eval(eval_id)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"运行目录必须为空：{run_dir}")

    agent_dir = run_dir / "agent"
    snapshot_dir = agent_dir / "skill"
    submission_dir = run_dir / "submission"
    agent_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for file_ref in item.get("files", []):
        source = fixture_source(file_ref)
        relative = copied_fixture_path(file_ref)
        destination = agent_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_files.append(relative.as_posix())

    snapshot_files = skill_files()
    for source in snapshot_files:
        destination = snapshot_dir / source.relative_to(SKILL_DIR)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    metadata = {
        "schema_version": 1,
        "eval_id": eval_id,
        "name": item.get("name"),
        "definition_sha256": definition_digest(item),
        "input_sha256": input_digest(item),
        "skill_sha256": tree_digest(SKILL_DIR, snapshot_files),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    task = {
        "eval_id": eval_id,
        "name": item.get("name"),
        "prompt": item["prompt"],
        "files": copied_files,
        "skill_entrypoint": "skill/SKILL.md",
        "submission_contract": {
            "report": "../submission/report.html",
            "trace": "../submission/trace.md",
            "assets_dir": "../submission/assets",
        },
        "input_sha256": metadata["input_sha256"],
        "skill_sha256": metadata["skill_sha256"],
    }
    write_json(run_dir / "run.json", metadata)
    write_json(agent_dir / "task.json", task)
    (agent_dir / "TASK.md").write_text(build_task_prompt(task), encoding="utf-8")

    print(f"Prepared eval {eval_id}: {run_dir}")
    print(f"Agent task: {agent_dir / 'TASK.md'}")
    print("Rubric is intentionally withheld until verify.")


def snapshot_input_digest(agent_dir: Path, task: dict[str, Any]) -> str:
    parts = [("prompt", task["prompt"].encode("utf-8"))]
    item = find_eval(task["eval_id"])
    source_refs = item.get("files", [])
    copied_refs = task.get("files", [])
    if len(source_refs) != len(copied_refs):
        raise ValueError("task.json 的输入文件数量与 eval 定义不一致")
    for source_ref, copied_ref in zip(source_refs, copied_refs, strict=True):
        candidate = (agent_dir / copied_ref).resolve()
        try:
            candidate.relative_to(agent_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"任务输入路径越出 agent 目录: {copied_ref}") from exc
        if not candidate.is_file():
            raise ValueError(f"任务输入不存在: {copied_ref}")
        parts.append((source_ref, candidate.read_bytes()))
    return stable_digest(parts)


def submission_digest(submission_dir: Path) -> str:
    """绑定最终 HTML、trace 和附件，防止评分后替换提交物。"""

    files = sorted(path for path in submission_dir.rglob("*") if path.is_file())
    return stable_digest(
        [(path.relative_to(submission_dir).as_posix(), path.read_bytes()) for path in files]
    )


def create_grader_files(run_dir: Path, item: dict[str, Any], artifact_sha256: str) -> None:
    """任务结束后才落盘 rubric，确保任务 Agent 无法提前读取 expectations。"""

    metadata = load_json(run_dir / "run.json")
    grader_dir = run_dir / "grader"
    expectations = [
        {"id": f"{item['id']}.{index}", "text": text}
        for index, text in enumerate(item["expectations"], start=1)
    ]
    rubric = {
        "eval_id": item["id"],
        "name": item.get("name"),
        "expected_output": item["expected_output"],
        "expectations": expectations,
        "input_sha256": metadata["input_sha256"],
        "skill_sha256": metadata["skill_sha256"],
        "submission_sha256": artifact_sha256,
    }
    write_json(grader_dir / "rubric.json", rubric)
    write_json(
        grader_dir / "assessment-template.json",
        {
            "eval_id": item["id"],
            "input_sha256": metadata["input_sha256"],
            "skill_sha256": metadata["skill_sha256"],
            "submission_sha256": artifact_sha256,
            "expectations": [
                {"id": expectation["id"], "passed": None, "evidence": [], "reason": ""}
                for expectation in expectations
            ],
            "notes": "",
        },
    )
    write_json(grader_dir / "assessment.schema.json", assessment_schema(rubric))


def assessment_schema(rubric: dict[str, Any]) -> dict[str, Any]:
    """约束自动 grader 只返回可归档字段，具体 expectation 顺序由 finalize 二次校验。"""

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "eval_id",
            "input_sha256",
            "skill_sha256",
            "submission_sha256",
            "expectations",
            "notes",
        ],
        "properties": {
            "eval_id": {"type": "integer", "const": rubric["eval_id"]},
            "input_sha256": {"type": "string", "const": rubric["input_sha256"]},
            "skill_sha256": {"type": "string", "const": rubric["skill_sha256"]},
            "submission_sha256": {"type": "string", "const": rubric["submission_sha256"]},
            "expectations": {
                "type": "array",
                "minItems": len(rubric["expectations"]),
                "maxItems": len(rubric["expectations"]),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "passed", "evidence", "reason"],
                    "properties": {
                        "id": {"type": "string"},
                        "passed": {"type": "boolean"},
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
            "notes": {"type": "string"},
        },
    }


def verify(run_dir: Path) -> bool:
    """验证任务快照未被污染，并运行报告的确定性结构校验。"""

    metadata = load_json(run_dir / "run.json")
    task = load_json(run_dir / "agent" / "task.json")
    item = find_eval(metadata["eval_id"])
    if definition_digest(item) != metadata["definition_sha256"]:
        raise ValueError("eval 定义在 prepare 后发生变化，请重新准备运行目录")
    if task.get("eval_id") != metadata["eval_id"]:
        raise ValueError("task.json 的 eval_id 与 run.json 不一致")
    if snapshot_input_digest(run_dir / "agent", task) != metadata["input_sha256"]:
        raise ValueError("任务 prompt 或输入 fixture 在执行期间被修改")
    if tree_digest(run_dir / "agent" / "skill") != metadata["skill_sha256"]:
        raise ValueError("任务使用的 skill 快照在执行期间被修改")

    submission_dir = run_dir / "submission"
    report_path = submission_dir / "report.html"
    trace_path = submission_dir / "trace.md"
    checks = [
        {
            "id": "report-exists",
            "passed": report_path.is_file() and bool(report_path.stat().st_size),
            "detail": str(report_path),
        },
        {
            "id": "trace-exists",
            "passed": trace_path.is_file() and bool(trace_path.read_text(encoding="utf-8").strip()),
            "detail": str(trace_path),
        },
    ]

    validator_stdout = ""
    validator_stderr = ""
    if checks[0]["passed"]:
        validator = run_dir / "agent" / "skill" / "scripts" / "check_html_report.py"
        completed = subprocess.run(
            [sys.executable, str(validator), str(report_path)],
            text=True,
            capture_output=True,
            check=False,
        )
        validator_stdout = completed.stdout
        validator_stderr = completed.stderr
        checks.append(
            {
                "id": "html-validator",
                "passed": completed.returncode == 0,
                "detail": (completed.stdout + completed.stderr).strip(),
            }
        )
    else:
        checks.append({"id": "html-validator", "passed": False, "detail": "report.html 不存在"})

    artifact_sha256 = submission_digest(submission_dir)
    create_grader_files(run_dir, item, artifact_sha256)
    automated = {
        "eval_id": item["id"],
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "validator_stdout": validator_stdout,
        "validator_stderr": validator_stderr,
        "submission_sha256": artifact_sha256,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_dir / "grader" / "automated-checks.json", automated)
    print(f"Automated checks {'passed' if automated['passed'] else 'failed'}: {run_dir}")
    return automated["passed"]


def evidence_path(run_dir: Path, citation: str) -> tuple[Path, int]:
    """校验证据引用仅指向当前 submission 中真实存在的 UTF-8 行。"""

    path_text, separator, line_text = citation.rpartition(":")
    if not separator or not line_text.isdigit() or int(line_text) < 1:
        raise ValueError(f"证据必须使用 submission/path:line 格式：{citation}")
    candidate = (run_dir / path_text).resolve()
    submission_dir = (run_dir / "submission").resolve()
    try:
        candidate.relative_to(submission_dir)
    except ValueError as exc:
        raise ValueError(f"证据路径必须位于 submission/：{citation}") from exc
    if not candidate.is_file():
        raise ValueError(f"证据文件不存在：{citation}")
    try:
        line_count = len(candidate.read_text(encoding="utf-8").splitlines())
    except UnicodeDecodeError as exc:
        raise ValueError(f"证据必须引用可按行审查的 UTF-8 文本：{citation}") from exc
    if int(line_text) > line_count:
        raise ValueError(f"证据行号越界：{citation}，文件共 {line_count} 行")
    return candidate, int(line_text)


def finalize(run_dir: Path, assessment_path: Path) -> dict[str, Any]:
    """校验 grader 结果和证据，计算 expectation 通过率并持久化。"""

    rubric = load_json(run_dir / "grader" / "rubric.json")
    automated = load_json(run_dir / "grader" / "automated-checks.json")
    assessment = load_json(assessment_path)
    for field in ("eval_id", "input_sha256", "skill_sha256", "submission_sha256"):
        if assessment.get(field) != rubric.get(field):
            raise ValueError(f"assessment 的 {field} 与 rubric 不一致")
    if submission_digest(run_dir / "submission") != rubric["submission_sha256"]:
        raise ValueError("submission 在 verify 后发生变化，请重新执行 verify 和评分")

    expected_ids = [item["id"] for item in rubric["expectations"]]
    scored = assessment.get("expectations")
    if not isinstance(scored, list) or [item.get("id") for item in scored] != expected_ids:
        raise ValueError("assessment 必须按 rubric 顺序覆盖全部 expectation id")
    for item in scored:
        if not isinstance(item.get("passed"), bool):
            raise ValueError(f"{item.get('id')} 的 passed 必须是 boolean")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{item['id']} 必须提供至少一条证据")
        for citation in evidence:
            if not isinstance(citation, str) or not citation.strip():
                raise ValueError(f"{item['id']} 包含无效证据引用")
            evidence_path(run_dir, citation)
        if not isinstance(item.get("reason"), str):
            raise ValueError(f"{item['id']} 的 reason 必须是字符串")

    passed_count = sum(1 for item in scored if item["passed"])
    total = len(scored)
    passed = bool(automated.get("passed")) and passed_count == total
    result = {
        **assessment,
        "status": "passed" if passed else "failed",
        "automated_checks_passed": bool(automated.get("passed")),
        "expectation_passed": passed_count,
        "expectation_total": total,
        "expectation_pass_rate": round(passed_count / total, 4),
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    }
    result_path = run_dir / "grader" / "result.json"
    write_json(result_path, result)
    print(
        f"Eval {rubric['eval_id']} {result['status']}: "
        f"{passed_count}/{total} expectations, {result_path}"
    )
    return result


def build_agent_command(codex_bin: str, run_dir: Path, model: str | None) -> list[str]:
    command = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--color",
        "never",
        "--sandbox",
        "workspace-write",
        "-C",
        str(run_dir / "agent"),
        "--add-dir",
        str(run_dir / "submission"),
        "-o",
        str(run_dir / "submission" / "agent-response.md"),
    ]
    if model:
        command.extend(("--model", model))
    command.append("-")
    return command


def build_grader_command(codex_bin: str, run_dir: Path, model: str | None) -> list[str]:
    command = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--color",
        "never",
        "--sandbox",
        "read-only",
        "-C",
        str(run_dir),
        "--output-schema",
        str(run_dir / "grader" / "assessment.schema.json"),
        "-o",
        str(run_dir / "grader" / "assessment.json"),
    ]
    if model:
        command.extend(("--model", model))
    command.append("-")
    return command


def run_command(command: list[str], prompt: str, timeout: int, log_prefix: Path) -> None:
    """无 shell 执行 Codex，保留 stdout/stderr 以便复盘失败原因。"""

    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        log_prefix.with_suffix(".stdout.log").write_text(exc.stdout or "", encoding="utf-8")
        log_prefix.with_suffix(".stderr.log").write_text(exc.stderr or "", encoding="utf-8")
        raise ValueError(f"Codex 执行超过 {timeout} 秒") from exc
    log_prefix.with_suffix(".stdout.log").write_text(completed.stdout, encoding="utf-8")
    log_prefix.with_suffix(".stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise ValueError(
            f"Codex 执行失败，退出码 {completed.returncode}；查看 {log_prefix.with_suffix('.stderr.log')}"
        )


def grader_prompt() -> str:
    return """你是独立的 html-report eval grader。

只读取 `grader/rubric.json`、`grader/automated-checks.json` 和 `submission/` 中的最终产物。
按 rubric 顺序逐项判断，每项都提供 `submission/path:line` 证据和简短 reason。
不得修改 submission，不得读取 `agent/` 推断执行者意图。最终只输出符合
`grader/assessment.schema.json` 的 JSON；哈希字段原样复制 rubric。
"""


def record_automated_failure(run_dir: Path) -> dict[str, Any]:
    """确定性校验失败时仍生成可汇总结果，但不伪造语义评分。"""

    rubric = load_json(run_dir / "grader" / "rubric.json")
    result = {
        "eval_id": rubric["eval_id"],
        "input_sha256": rubric["input_sha256"],
        "skill_sha256": rubric["skill_sha256"],
        "submission_sha256": rubric["submission_sha256"],
        "status": "failed",
        "automated_checks_passed": False,
        "expectations": [],
        "expectation_passed": 0,
        "expectation_total": len(rubric["expectations"]),
        "expectation_pass_rate": None,
        "notes": "确定性 HTML 校验失败，未运行语义 grader。",
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_dir / "grader" / "result.json", result)
    return result


def run_eval(
    eval_id: int,
    run_dir: Path,
    codex_bin: str,
    model: str | None,
    grader_model: str | None,
    timeout: int,
) -> dict[str, Any]:
    """用互不共享会话的任务 Agent 和 grader 完成一次端到端评测。"""

    prepare(eval_id, run_dir)
    task_prompt = (run_dir / "agent" / "TASK.md").read_text(encoding="utf-8")
    run_command(
        build_agent_command(codex_bin, run_dir, model),
        task_prompt,
        timeout,
        run_dir / "submission" / "agent",
    )
    if not verify(run_dir):
        return record_automated_failure(run_dir)

    run_command(
        build_grader_command(codex_bin, run_dir, grader_model or model),
        grader_prompt(),
        timeout,
        run_dir / "grader" / "grader",
    )
    return finalize(run_dir, run_dir / "grader" / "assessment.json")


def summarize(runs_dir: Path, output: Path | None = None) -> dict[str, Any]:
    """汇总多个独立 run 的结果，分别报告运行通过率和已评分 expectation 通过率。"""

    result_paths = sorted(runs_dir.rglob("grader/result.json"))
    if not result_paths:
        raise ValueError(f"未找到 grader/result.json：{runs_dir}")
    results = [load_json(path) for path in result_paths]
    passed_runs = sum(1 for result in results if result.get("status") == "passed")
    graded = [item for result in results for item in result.get("expectations", [])]
    passed_expectations = sum(1 for item in graded if item.get("passed") is True)
    summary = {
        "run_count": len(results),
        "passed_runs": passed_runs,
        "run_pass_rate": round(passed_runs / len(results), 4),
        "graded_expectations": len(graded),
        "passed_expectations": passed_expectations,
        "expectation_pass_rate": (
            round(passed_expectations / len(graded), 4) if graded else None
        ),
        "evals": [
            {
                "eval_id": result.get("eval_id"),
                "status": result.get("status"),
                "expectation_pass_rate": result.get("expectation_pass_rate"),
            }
            for result in results
        ],
        "summarized_at": datetime.now(timezone.utc).isoformat(),
    }
    if output:
        write_json(output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行并归档 html-report 隔离评测。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="准备不含 rubric 的隔离任务包")
    prepare_parser.add_argument("--eval-id", type=int, required=True)
    prepare_parser.add_argument("--run-dir", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify", help="校验提交物并生成 grader rubric")
    verify_parser.add_argument("--run-dir", type=Path, required=True)

    finalize_parser = subparsers.add_parser("finalize", help="校验评分并生成 result.json")
    finalize_parser.add_argument("--run-dir", type=Path, required=True)
    finalize_parser.add_argument("--assessment", type=Path, required=True)

    run_parser = subparsers.add_parser("run", help="使用两个临时 Codex 会话完成任务和评分")
    run_parser.add_argument("--eval-id", type=int, required=True)
    run_parser.add_argument("--run-dir", type=Path, required=True)
    run_parser.add_argument("--codex-bin", default="codex")
    run_parser.add_argument("--model")
    run_parser.add_argument("--grader-model")
    run_parser.add_argument("--timeout", type=int, default=1800)

    summary_parser = subparsers.add_parser("summary", help="汇总目录内的 result.json")
    summary_parser.add_argument("--runs-dir", type=Path, required=True)
    summary_parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "prepare":
            prepare(args.eval_id, args.run_dir.resolve())
        elif args.command == "verify":
            return 0 if verify(args.run_dir.resolve()) else 2
        elif args.command == "finalize":
            result = finalize(args.run_dir.resolve(), args.assessment.resolve())
            return 0 if result["status"] == "passed" else 2
        elif args.command == "run":
            if args.timeout < 1:
                raise ValueError("--timeout 必须大于 0")
            result = run_eval(
                args.eval_id,
                args.run_dir.resolve(),
                args.codex_bin,
                args.model,
                args.grader_model,
                args.timeout,
            )
            return 0 if result["status"] == "passed" else 2
        else:
            summarize(args.runs_dir.resolve(), args.output.resolve() if args.output else None)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
