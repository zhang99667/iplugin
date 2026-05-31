#!/usr/bin/env python3
"""PostToolUse hook — 记录 Skill 调用事件到本地 JSONL 日志。

每次 Claude Code 调用 Skill tool，或 Codex hook 事件的工具输入里出现
skills/<name>/SKILL.md 访问痕迹时自动触发。从 stdin 读取事件 JSON，
提取 skill 名称和时间戳，append 到本地日志文件。完全离线，无网络请求。

Claude Code 安装方式：在 ~/.claude/settings.json 的 hooks.PostToolUse 中添加：
  {
    "matcher": "Skill",
    "hooks": [{"type": "command", "command": "python3 ~/.claude/plugins/marketplaces/iplugin/iplugin/hooks/skill-telemetry.py"}]
  }

Codex 安装方式：启用 iPlugin 后，Codex 会读取插件内置的 hooks/hooks.json。
首次启用或脚本变更后，在 Codex CLI 中执行 /hooks 并 trust 该 hook。

查看统计：
  cat ~/.claude/skill-usage.jsonl | jq -r '.skill' | sort | uniq -c | sort -rn
  cat ~/.codex/skill-usage.jsonl | jq -r '.skill' | sort | uniq -c | sort -rn

可用 IPPLUGIN_SKILL_USAGE_LOG 覆盖日志路径。
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


SKILL_FILE_RE = re.compile(r"(?:^|[\\/])skills[\\/]([^\\/]+)[\\/]SKILL\.md\b")


def stringify(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def normalize_skill(value: Any) -> Optional[str]:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, dict):
        for key in ("name", "skill", "skill_name"):
            normalized = normalize_skill(value.get(key))
            if normalized:
                return normalized
    return None


def find_skill_path(value: Any) -> Optional[str]:
    match = SKILL_FILE_RE.search(stringify(value))
    return match.group(1) if match else None


def extract_skill_name(event: dict) -> Optional[str]:
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    for key in ("skill", "skill_name", "name"):
        skill_name = normalize_skill(tool_input.get(key))
        if skill_name:
            return skill_name

    for source in (tool_input, event.get("arguments"), event.get("input")):
        skill_name = find_skill_path(source)
        if skill_name:
            return skill_name

    if event.get("tool_name") == "Skill":
        return "unknown"
    return None


def detect_platform(event: dict) -> str:
    if os.environ.get("PLUGIN_ROOT") or os.environ.get("PLUGIN_DATA"):
        return "codex"
    if os.environ.get("CODEX_HOME"):
        return "codex"
    if event.get("turn_id") and event.get("model"):
        return "codex"
    return "claude"


def log_path_for(platform: str) -> Path:
    override = os.environ.get("IPPLUGIN_SKILL_USAGE_LOG")
    if override:
        return Path(override).expanduser()

    if platform == "codex":
        # Keep a predictable fallback even when PLUGIN_DATA is not provided.
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            return Path(codex_home).expanduser() / "skill-usage.jsonl"
        return Path.home() / ".codex" / "skill-usage.jsonl"

    return Path.home() / ".claude" / "skill-usage.jsonl"


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(event, dict):
        return

    skill_name = extract_skill_name(event)
    if not skill_name:
        return

    platform = detect_platform(event)

    record = {
        "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "platform": platform,
        "skill": skill_name,
        "session": event.get("session_id", ""),
        "hook_event": event.get("hook_event_name", ""),
        "tool": event.get("tool_name", ""),
    }

    log_path = log_path_for(platform)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
