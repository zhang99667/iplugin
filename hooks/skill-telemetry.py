#!/usr/bin/env python3
"""PostToolUse hook — 记录 Skill 调用事件到 ~/.claude/skill-usage.jsonl。

每次 Claude Code 调用 Skill tool 后自动触发，从 stdin 读取事件 JSON，
提取 skill 名称和时间戳，append 到本地日志文件。完全离线，无网络请求。

安装方式：在 ~/.claude/settings.json 的 hooks.PostToolUse 中添加：
  {
    "matcher": "Skill",
    "hooks": [{"type": "command", "command": "python3 ~/.claude/plugins/marketplaces/iplugin/iplugin/hooks/skill-telemetry.py"}]
  }

查看统计：
  cat ~/.claude/skill-usage.jsonl | jq -r '.skill' | sort | uniq -c | sort -rn
"""

import datetime
import json
import sys
from pathlib import Path


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return

    skill_name = (
        event.get("tool_input", {}).get("skill")
        or event.get("tool_name", "unknown")
    )

    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "skill": skill_name,
        "session": event.get("session_id", ""),
    }

    log_path = Path.home() / ".claude" / "skill-usage.jsonl"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
