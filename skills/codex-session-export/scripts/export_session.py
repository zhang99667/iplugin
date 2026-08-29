#!/usr/bin/env python3
"""Export Codex session JSONL or exec JSON events to readable Markdown."""

# 本脚本基于 session-export 开源项目适配为 codex-session-export；保留上游 MIT 许可证。

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
SESSIONS_DIR = CODEX_HOME / "sessions"
SESSION_INDEX = CODEX_HOME / "session_index.jsonl"


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"warning: skipped invalid JSON at {path}:{line_number}: {exc}", file=sys.stderr)


def index_titles() -> dict[str, str]:
    if not SESSION_INDEX.exists():
        return {}
    titles: dict[str, str] = {}
    for item in read_jsonl(SESSION_INDEX):
        session_id = item.get("id")
        if session_id:
            titles[str(session_id)] = str(item.get("thread_name") or session_id)
    return titles


def rollout_files() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.rglob("rollout-*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)


def available_rollout_files() -> list[Path]:
    """Return all rollouts, including sessions that have no index title yet.

    `codex exec` sessions can finish before Codex writes a title index entry.
    Filtering those files out makes a later `latest` export silently choose the
    wrong conversation, so the exporter treats every rollout as exportable.
    """
    return rollout_files()


def session_id_from_path(path: Path) -> str:
    match = re.search(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\.jsonl$", path.name)
    return match.group(1) if match else path.stem


def resolve_session(selector: str) -> Path:
    candidate = Path(selector).expanduser()
    if candidate.is_file():
        return candidate.resolve()

    files = rollout_files()
    if not files:
        raise SystemExit(f"No rollout JSONL files found under {SESSIONS_DIR}")

    if selector == "current":
        current_thread_id = os.environ.get("CODEX_THREAD_ID")
        if current_thread_id:
            matches = [path for path in files if current_thread_id in path.name]
            if len(matches) == 1:
                return matches[0]
        return available_rollout_files()[0]

    if selector == "latest":
        return available_rollout_files()[0]

    matches = [path for path in files if selector in path.name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"No session rollout matched {selector!r}")
    raise SystemExit(f"Session selector {selector!r} matched multiple rollouts; use a longer ID")


def redact(text: str) -> str:
    home = str(Path.home())
    text = text.replace(home, "~")
    patterns = [
        (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s\"']+", r"\1[REDACTED]"),
        (r"(?i)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,\"'}]+", r"\1[REDACTED]"),
        (r"(?i)(sk-[a-z0-9_-]{12,})", "[REDACTED]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def message_text(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, str):
        return message.strip()
    return ""


def content_text(content: Any) -> str:
    """Extract visible text from a Codex response-item message content list."""
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type")
        if part_type not in {"input_text", "output_text", "text"}:
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def append_message(
    transcript: list[tuple[str, str, str | None]],
    role: str,
    text: str,
    phase: str | None = None,
) -> None:
    """Append one visible message while avoiding old/new schema duplicates."""
    text = text.strip()
    if not text:
        return
    if transcript and transcript[-1] == (role, text, phase):
        return
    transcript.append((role, text, phase))


def serialise_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def parse_rollout(path: Path, include_tools: bool, max_tool_output: int) -> dict[str, Any]:
    transcript: list[tuple[str, str, str | None]] = []
    tools: list[dict[str, str]] = []
    metadata: dict[str, str] = {}
    pending_tools: dict[str, dict[str, str]] = {}

    for item in read_jsonl(path):
        item_type = item.get("type")

        # `codex exec --json` emits top-level events rather than rollout
        # records wrapped in `payload`.  Supporting both here keeps one
        # renderer usable from the TUI, persistent sessions, and CI scripts.
        if "payload" not in item:
            if item_type == "thread.started":
                if item.get("thread_id"):
                    metadata["id"] = str(item["thread_id"])
                continue
            if item_type == "item.completed":
                event_item = item.get("item") or {}
                event_item_type = event_item.get("type")
                if event_item_type in {"agent_message", "message", "user_message"}:
                    event_role = "User" if event_item_type == "user_message" or event_item.get("role") == "user" else "Codex"
                    append_message(
                        transcript,
                        event_role,
                        content_text(event_item.get("text") or event_item.get("content")),
                        event_item.get("phase"),
                    )
                elif event_item_type in {"command_execution", "function_call", "custom_tool_call"}:
                    tools.append(
                        {
                            "name": str(event_item.get("name") or event_item_type),
                            "arguments": redact(serialise_value(event_item.get("command") or event_item.get("arguments") or event_item.get("input") or "")),
                            "output": redact(serialise_value(event_item.get("aggregated_output") or event_item.get("output") or "")),
                        }
                    )
                continue
            continue

        payload = item.get("payload") or {}

        if item_type == "session_meta":
            for key in ("id", "cwd", "timestamp", "model_provider"):
                if payload.get(key) is not None:
                    metadata[key] = str(payload[key])
            continue

        if item_type == "event_msg":
            payload_type = payload.get("type")
            if payload_type == "user_message":
                text = message_text(payload)
                append_message(transcript, "User", text)
            elif payload_type == "agent_message":
                text = message_text(payload)
                append_message(transcript, "Codex", text, payload.get("phase"))
            continue

        if item_type != "response_item":
            continue
        payload_type = payload.get("type")
        if payload_type == "message" and payload.get("role") in {"user", "assistant"}:
            role = "User" if payload.get("role") == "user" else "Codex"
            append_message(transcript, role, content_text(payload.get("content")), payload.get("phase"))
        elif payload_type in {"function_call", "custom_tool_call", "command_execution"}:
            call = {
                "name": str(payload.get("name") or payload_type),
                "arguments": redact(serialise_value(payload.get("arguments") or payload.get("input") or payload.get("command") or "")),
                "output": "",
            }
            tools.append(call)
            if payload.get("call_id"):
                pending_tools[str(payload["call_id"])] = call
        elif include_tools and payload_type in {"function_call_output", "custom_tool_call_output", "command_execution_output"}:
            call = pending_tools.get(str(payload.get("call_id") or ""))
            if call is not None:
                output = redact(serialise_value(payload.get("output") or payload.get("aggregated_output") or ""))
                if len(output) > max_tool_output:
                    output = output[:max_tool_output] + "\n...[truncated]"
                call["output"] = output

    metadata.setdefault("id", session_id_from_path(path))
    metadata["rollout_path"] = str(path)
    return {"metadata": metadata, "transcript": transcript, "tools": tools}


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return slug[:72] or "codex-session"


def fenced(text: str) -> str:
    fence = "```"
    if "```" in text:
        fence = "````"
    return f"{fence}text\n{text}\n{fence}"


def compact(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def build_markdown(
    data: dict[str, Any],
    title: str,
    include_tools: bool,
    exported_files: list[Path],
) -> str:
    metadata = data["metadata"]
    transcript = data["transcript"]
    tools = data["tools"]
    first_request = next((text for role, text, _ in transcript if role == "User"), "")
    user_count = sum(role == "User" for role, _, _ in transcript)
    codex_count = sum(role == "Codex" for role, _, _ in transcript)
    lines = [
        f"# {title}",
        "",
        f"- Session ID: `{metadata.get('id', '')}`",
        f"- Started: `{metadata.get('timestamp', '')}`",
        f"- Working directory: `{redact(metadata.get('cwd', ''))}`",
        f"- Source: `{redact(metadata.get('rollout_path', ''))}`",
        "- Exported files:",
        *[f"  - `{path}`" for path in exported_files],
        "",
        "## Session Summary",
        "",
        f"{title}. {compact(first_request)}",
        "",
        f"This archive contains {user_count} user message(s), {codex_count} Codex message(s), and {len(tools)} tool call(s).",
        "",
        "## Conversation",
        "",
    ]
    for role, text, phase in transcript:
        phase_suffix = f" ({phase})" if role == "Codex" and phase else ""
        lines.extend([f"### {role}{phase_suffix}", "", text, ""])

    lines.extend(["## Tool Summary", ""])
    if not tools:
        lines.append("No tool calls recorded.")
    else:
        counts: dict[str, int] = {}
        for tool in tools:
            counts[tool["name"]] = counts.get(tool["name"], 0) + 1
        for name, count in sorted(counts.items()):
            lines.append(f"- `{name}`: {count}")

    if include_tools and tools:
        lines.extend(["", "## Tool Details", "", "> Best-effort redaction applied. Review before sharing.", ""])
        for index, tool in enumerate(tools, start=1):
            lines.extend([f"### {index}. `{tool['name']}`", ""])
            if tool["arguments"]:
                lines.extend(["Arguments:", "", fenced(tool["arguments"]), ""])
            if tool["output"]:
                lines.extend(["Output:", "", fenced(tool["output"]), ""])

    return "\n".join(lines).rstrip() + "\n"


def list_sessions(limit: int) -> None:
    titles = index_titles()
    print("SESSION ID                            UPDATED              TITLE")
    for path in available_rollout_files()[:limit]:
        session_id = session_id_from_path(path)
        updated = dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone().strftime("%Y-%m-%d %H:%M")
        print(f"{session_id:<36}  {updated:<19}  {titles.get(session_id, '')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", default="current", help="current thread, latest thread, session ID, or rollout/exec JSONL path")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd() / "session-exports")
    parser.add_argument("--user-message", help="include the original prompt when exporting a codex exec event stream")
    parser.add_argument("--include-tools", action="store_true", help="include redacted tool arguments and truncated outputs")
    parser.add_argument("--max-tool-output", type=int, default=4000)
    parser.add_argument("--list", action="store_true", help="list recent local Codex sessions")
    parser.add_argument("--limit", type=int, default=20, help="number of sessions shown by --list")
    args = parser.parse_args()

    if args.list:
        list_sessions(args.limit)
        return 0

    path = resolve_session(args.session)
    data = parse_rollout(path, args.include_tools, args.max_tool_output)
    if args.user_message:
        data["transcript"].insert(0, ("User", args.user_message.strip(), None))
    session_id = data["metadata"]["id"]
    title = index_titles().get(session_id, f"Codex Session {session_id}")
    timestamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d-%H%M")
    stem = f"{timestamp}-{safe_slug(title)}"

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{stem}.md"
    exported_files = [markdown_path]
    markdown_text = build_markdown(data, title, args.include_tools, exported_files)

    markdown_path.write_text(markdown_text, encoding="utf-8")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
