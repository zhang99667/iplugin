"""Ghostty AppleScript 适配层：生成脚本、采集快照、执行恢复。"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from typing import Any

from .models import iter_workspace_panes, marker_for_terminal_key, now_iso, terminal_key_from_marker
from .planner import build_restore_plan, assert_plan_executable
from .state import load_state, save_latest_workspace


class GhosttyError(RuntimeError):
    """Ghostty 或 osascript 交互失败时抛出。"""

    pass


def _apple_string(value: str | None) -> str:
    """把 Python 字符串转成 AppleScript 字符串字面量。"""
    text = value or ""
    # AppleScript 字符串只需要处理反斜杠和双引号；命令内容在 planner 阶段已做白名单。
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _command_text(argv: list[str]) -> str:
    """把结构化 argv 转成要输入到 terminal 并立即执行的命令文本。"""
    # shlex.join 只用于生成“输入到终端的文本”，不参与本进程 shell 执行。
    text = shlex.join(argv)
    # Ghostty input text 收到换行后等价于用户按回车执行命令。
    return text + "\n"


def build_capture_script() -> str:
    """生成 Ghostty workspace 采集脚本；调用方决定是否真实执行。"""
    return r'''
use scripting additions

-- 将 Ghostty 字段转成 JSON 字符串前先做必要转义。
on json_escape(value)
  set textValue to value as text
  set textValue to my replace_text(textValue, "\", "\\")
  set textValue to my replace_text(textValue, quote, "\" & quote)
  set textValue to my replace_text(textValue, return, "\n")
  return textValue
end json_escape

on replace_text(sourceText, searchText, replacementText)
  set AppleScript's text item delimiters to searchText
  set parts to text items of sourceText
  set AppleScript's text item delimiters to replacementText
  set resultText to parts as text
  set AppleScript's text item delimiters to ""
  return resultText
end replace_text

tell application "Ghostty"
  -- 逐层读取 window / tab / terminal，保持和恢复计划的层级一致。
  set windowItems to {}
  set windowIndex to 0
  repeat with ghostWindow in windows
    set windowIndex to windowIndex + 1
    set tabItems to {}
    set tabIndex to 0
    repeat with ghostTab in tabs of ghostWindow
      set tabIndex to tabIndex + 1
      set terminalItems to {}
      set terminalIndex to 0
      repeat with ghostTerminal in terminals of ghostTab
        -- Ghostty 版本差异可能导致部分字段不可读，所以逐项 try。
        set terminalIndex to terminalIndex + 1
        set terminalTitle to ""
        set terminalCwd to ""
        try
          set terminalTitle to name of ghostTerminal
        end try
        try
          set terminalCwd to working directory of ghostTerminal
        end try
        set terminalJson to "{\"pane_index\":" & terminalIndex & ",\"title\":\"" & my json_escape(terminalTitle) & "\",\"cwd\":\"" & my json_escape(terminalCwd) & "\"}"
        set end of terminalItems to terminalJson
      end repeat
      set splitTree to "{\"direction\":\"unknown\",\"children\":[" & my join_json(terminalItems) & "]}"
      set tabJson to "{\"tab_index\":" & tabIndex & ",\"name\":\"\",\"split_tree\":" & splitTree & "}"
      set end of tabItems to tabJson
    end repeat
    set windowJson to "{\"window_index\":" & windowIndex & ",\"tabs\":[" & my join_json(tabItems) & "]}"
    set end of windowItems to windowJson
  end repeat
  return "{\"terminal_app\":\"Ghostty\",\"windows\":[" & my join_json(windowItems) & "]}"
end tell

-- AppleScript 没有内置 JSON join，这里只拼接已经转义好的片段。
on join_json(items)
  set AppleScript's text item delimiters to ","
  set joined to items as text
  set AppleScript's text item delimiters to ""
  return joined
end join_json
'''.strip()


def build_restore_script(workspace: dict[str, Any]) -> str:
    """根据已校验计划生成恢复脚本。"""
    # 先复用 planner 做校验，脚本生成层不再信任 workspace 里的原始 restore 字段。
    plan = build_restore_plan(workspace)
    assert_plan_executable(plan)
    commands = []
    for item in plan["items"]:
        restore = item.get("restore")
        if not item.get("allowed") or not isinstance(restore, dict):
            # shell pane 或不可执行 pane 不会生成 input text，避免误触发历史命令。
            continue
        argv = restore.get("argv")
        if not isinstance(argv, list):
            continue
        commands.append(
            {
                # Ghostty 新 window/tab 支持 initial working directory；缺失 cwd 时回到用户 home。
                "cwd": item.get("cwd") or "~",
                "text": _command_text([str(part) for part in argv]),
            }
        )

    lines = [
        'tell application "Ghostty"',
        "  activate",
    ]
    if not commands:
        lines.append("  -- 当前恢复计划没有可自动执行的 Agent resume 命令。")
    for index, command in enumerate(commands, start=1):
        cwd = _apple_string(str(command["cwd"]))
        text = _apple_string(str(command["text"]))
        if index == 1:
            # 第一条命令创建新窗口，后续命令追加 tab；v0.1.0 暂不承诺精确还原 split 比例。
            lines.append(f"  set restoredWindow to new window with properties {{initial working directory:{cwd}}}")
            lines.append("  delay 0.2")
            lines.append(f"  input text {text}")
        else:
            # 后续 pane 先恢复为 tab，等 Ghostty split API 验证稳定后再细化 split_tree 还原。
            lines.append(f"  set restoredTab to new tab in restoredWindow with properties {{initial working directory:{cwd}}}")
            lines.append("  delay 0.2")
            lines.append(f"  input text {text}")
    lines.append("end tell")
    return "\n".join(lines)


def _bind_active_terminals(workspace: dict[str, Any], active_terminals: dict[str, Any]) -> dict[str, Any]:
    """把 Ghostty pane 与 active_terminals 绑定，marker 命中优先。"""
    for pane in iter_workspace_panes(workspace):
        # marker 可能出现在 title/name/marker 任一字段，合并后统一解析。
        marker_source = " ".join(str(pane.get(key) or "") for key in ("marker", "title", "name"))
        terminal_key = terminal_key_from_marker(marker_source)
        if terminal_key and terminal_key in active_terminals:
            active = active_terminals[terminal_key]
            # marker 命中说明这个 Ghostty terminal 就是 wrapper 注入过的 pane，置信度最高。
            pane.update(
                {
                    "terminal_key": terminal_key,
                    "marker": marker_for_terminal_key(terminal_key),
                    "binding_method": "terminal_marker",
                    "binding_confidence": "high",
                    "agent": active.get("agent"),
                    "session_id": active.get("session_id"),
                    "session_file": active.get("session_file"),
                    "restore": active.get("restore"),
                    "restore_cmd": active.get("restore_cmd"),
                }
            )
            # Ghostty 可能没有返回 cwd，此时用 wrapper 记录的 cwd 兜底。
            pane.setdefault("cwd", active.get("cwd"))
            continue

        cwd = pane.get("cwd")
        # marker 不可用时才尝试 cwd 兜底；只有唯一候选才绑定，避免同目录多 pane 误匹配。
        candidates = [
            (key, value)
            for key, value in active_terminals.items()
            if cwd and isinstance(value, dict) and value.get("cwd") == cwd
        ]
        if len(candidates) == 1:
            # marker 不可读时只做低置信 cwd 兜底，planner 默认不会自动执行。
            key, active = candidates[0]
            pane.update(
                {
                    "terminal_key": key,
                    "binding_method": "cwd_fallback",
                    "binding_confidence": "low",
                    "agent": active.get("agent"),
                    "session_id": active.get("session_id"),
                    "session_file": active.get("session_file"),
                    "restore": active.get("restore"),
                    "restore_cmd": active.get("restore_cmd"),
                }
            )
        else:
            # 没有可靠绑定时保留 pane，但不附加 agent resume 信息。
            pane.setdefault("binding_confidence", "none")
    return workspace


class GhosttyAdapter:
    """封装真实 osascript 调用，隔离脚本生成和系统调用。"""

    def run_osascript(self, script: str) -> str:
        """执行 AppleScript，并把系统错误转换成可读的 GhosttyError。"""
        try:
            # 不用 shell=True，避免 AppleScript 内容被本机 shell 再解释一遍。
            result = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                text=True,
                capture_output=True,
            )
        except FileNotFoundError as exc:
            raise GhosttyError("当前系统找不到 osascript") from exc
        if result.returncode != 0:
            # Automation 权限、Ghostty 未运行、字段不可用都会走到这里，保留原始 stderr 作为诊断信息。
            stderr = result.stderr.strip() or result.stdout.strip()
            raise GhosttyError(f"Ghostty AppleScript 执行失败：{stderr}")
        return result.stdout.strip()

    def capture_workspace(self, name: str | None = None) -> dict[str, Any]:
        """采集当前 Ghostty 布局，绑定 active terminal 后写入 latest_workspace。"""
        script = build_capture_script()
        raw = self.run_osascript(script)
        try:
            workspace = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GhosttyError(f"Ghostty 采集结果不是 JSON：{raw[:200]}") from exc
        state = load_state()
        # snapshot_id 使用本地时间数字，便于按时间肉眼排序；不承担全局唯一 ID 语义。
        workspace["snapshot_id"] = "ws_" + re.sub(r"[^0-9]", "", now_iso())[:14]
        workspace["name"] = name
        workspace["captured_at"] = now_iso()
        workspace.setdefault("terminal_app", "Ghostty")
        # capture 只负责把布局和 active terminal 合并，真正可否执行由 planner 再判断。
        _bind_active_terminals(workspace, state.get("active_terminals", {}))
        save_latest_workspace(workspace)
        return workspace

    def restore_workspace(self, workspace: dict[str, Any]) -> str:
        """执行恢复脚本，并返回 osascript 输出。"""
        script = build_restore_script(workspace)
        return self.run_osascript(script)
