#!/usr/bin/env python3
"""准备 Obsidian 行为评测任务包，并校验 grader 的逐项评分结果。"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVALS_DIR = Path(__file__).resolve().parent
SKILL_DIR = EVALS_DIR.parent
EVALS_FILE = EVALS_DIR / "evals.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_eval(eval_id: int) -> dict[str, Any]:
    data = load_json(EVALS_FILE)
    for item in data.get("evals", []):
        if item.get("id") == eval_id:
            return item
    raise ValueError(f"不存在 eval id: {eval_id}")


def input_digest(item: dict[str, Any]) -> str:
    """哈希 prompt 和原始 fixtures，保证不同轮次确实使用同一输入。"""

    digest = hashlib.sha256()
    digest.update(item["prompt"].encode("utf-8"))
    for file_ref in item.get("files", []):
        digest.update(file_ref.encode("utf-8"))
        digest.update((SKILL_DIR / file_ref).read_bytes())
    return digest.hexdigest()


def skill_files() -> list[Path]:
    """收集普通任务运行所需的 skill 快照，不把 eval rubric 打包给任务 Agent。"""

    files = [SKILL_DIR / "SKILL.md"]
    for relative_dir in ("references", "assets", "scripts"):
        root = SKILL_DIR / relative_dir
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return sorted(files)


def skill_digest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(SKILL_DIR).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare(eval_id: int, run_dir: Path) -> None:
    item = find_eval(eval_id)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"运行目录必须为空：{run_dir}")

    agent_dir = run_dir / "agent"
    input_dir = agent_dir / "inputs"
    snapshot_dir = agent_dir / "skill"
    grader_dir = run_dir / "grader"
    submission_dir = run_dir / "submission"
    input_dir.mkdir(parents=True, exist_ok=True)
    grader_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for file_ref in item.get("files", []):
        source = SKILL_DIR / file_ref
        destination = input_dir / Path(file_ref).name
        if destination.exists():
            raise ValueError(f"fixture 文件名冲突：{destination.name}")
        shutil.copy2(source, destination)
        copied_files.append(f"inputs/{destination.name}")

    digest = input_digest(item)
    snapshot_files = skill_files()
    for source in snapshot_files:
        destination = snapshot_dir / source.relative_to(SKILL_DIR)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    snapshot_digest = skill_digest(snapshot_files)
    write_json(
        agent_dir / "task.json",
        {
            "eval_id": eval_id,
            "name": item.get("name"),
            "prompt": item["prompt"],
            "files": copied_files,
            "skill_entrypoint": "skill/SKILL.md",
            "submission_contract": {
                "final_artifact": "../submission/final.md",
                "trace": "../submission/trace.md",
                "assets_dir": "../submission/assets",
            },
            "input_sha256": digest,
            "skill_sha256": snapshot_digest,
        },
    )

    expectations = [
        {"id": f"{eval_id}.{index}", "text": text}
        for index, text in enumerate(item["expectations"], start=1)
    ]
    write_json(
        grader_dir / "rubric.json",
        {
            "eval_id": eval_id,
            "name": item.get("name"),
            "expected_output": item["expected_output"],
            "expectations": expectations,
            "input_sha256": digest,
            "skill_sha256": snapshot_digest,
        },
    )
    write_json(
        grader_dir / "assessment-template.json",
        {
            "eval_id": eval_id,
            "input_sha256": digest,
            "skill_sha256": snapshot_digest,
            "expectations": [
                {"id": expectation["id"], "passed": None, "evidence": []}
                for expectation in expectations
            ],
            "notes": "",
        },
    )
    print(f"Prepared eval {eval_id}: {run_dir}")
    print(f"Agent task: {agent_dir / 'task.json'}")
    print(f"Grader rubric: {grader_dir / 'rubric.json'}")


def evidence_path(run_dir: Path, citation: str) -> tuple[Path, int]:
    """解析 submission/path:line 证据，并校验路径范围和真实行号。"""

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
    line_number = int(line_text)
    if line_number > line_count:
        raise ValueError(f"证据行号越界：{citation}，文件共 {line_count} 行")
    return candidate, line_number


def finalize(run_dir: Path, assessment_path: Path) -> None:
    rubric = load_json(run_dir / "grader" / "rubric.json")
    assessment = load_json(assessment_path)
    if assessment.get("eval_id") != rubric.get("eval_id"):
        raise ValueError("assessment 的 eval_id 与 rubric 不一致")
    if assessment.get("input_sha256") != rubric.get("input_sha256"):
        raise ValueError("assessment 的输入哈希与本次任务不一致")
    if assessment.get("skill_sha256") != rubric.get("skill_sha256"):
        raise ValueError("assessment 的 skill 哈希与本次任务不一致")

    for required_submission in (run_dir / "submission" / "final.md", run_dir / "submission" / "trace.md"):
        if not required_submission.is_file() or not required_submission.read_text(encoding="utf-8").strip():
            raise ValueError(f"缺少非空评测产物：{required_submission}")

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

    passed = all(item["passed"] for item in scored)
    result = {
        **assessment,
        "status": "passed" if passed else "failed",
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    }
    result_path = run_dir / "grader" / "result.json"
    write_json(result_path, result)
    print(f"Eval {rubric['eval_id']} {result['status']}: {result_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="准备并归档 Obsidian 行为评测。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="准备隔离任务包和 grader rubric")
    prepare_parser.add_argument("--eval-id", type=int, required=True)
    prepare_parser.add_argument("--run-dir", type=Path, required=True)

    finalize_parser = subparsers.add_parser("finalize", help="校验逐项评分并生成 result.json")
    finalize_parser.add_argument("--run-dir", type=Path, required=True)
    finalize_parser.add_argument("--assessment", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.eval_id, args.run_dir)
        else:
            finalize(args.run_dir, args.assessment)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
