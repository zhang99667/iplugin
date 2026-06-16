"""把 latest_workspace 转换成可审查、可安全执行的恢复计划。"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import count_workspace_panes, count_workspace_tabs, iter_panes


# 这里校验的是单个 argv token，而不是 shell 字符串；排除 shell 元字符是最后一道防线。
SAFE_TOKEN_RE = re.compile(r"^[^\s;&|`$<>\\\\]+$")


class RestorePlanError(RuntimeError):
    """恢复计划不可执行或缺少快照时抛出。"""

    pass


def _is_safe_session_token(token: str) -> bool:
    """session id 必须是单个安全 argv token，不能像参数或 shell 片段。"""
    # 以 "-" 开头会被真实 CLI 当成参数，不能作为 session id 自动执行。
    if not token or token.startswith("-"):
        return False
    return bool(SAFE_TOKEN_RE.fullmatch(token))


def validate_restore(restore: Any) -> tuple[bool, str]:
    """只允许结构化的 Codex/Claude 原生 resume 命令进入执行路径。"""
    if not isinstance(restore, dict):
        return False, "缺少结构化恢复命令"
    agent = restore.get("agent")
    argv = restore.get("argv")
    # Codex 只接受 codex resume <session_id> 三段结构，多一个 token 都拒绝。
    if agent == "codex" and isinstance(argv, list) and len(argv) == 3:
        if argv[0] == "codex" and argv[1] == "resume" and _is_safe_session_token(str(argv[2])):
            return True, "通过"
    # Claude Code 只接受 claude --resume <session_id>，不允许任意命令回放。
    if agent == "claude" and isinstance(argv, list) and len(argv) == 3:
        if argv[0] == "claude" and argv[1] == "--resume" and _is_safe_session_token(str(argv[2])):
            return True, "通过"
    return False, "恢复命令不在白名单内"


def build_restore_plan(workspace: Any) -> Dict[str, Any]:
    """生成恢复计划，并把每个 pane 是否可执行标出来。"""
    if not isinstance(workspace, dict):
        raise RestorePlanError("没有 latest_workspace；请先执行 zagent snapshot capture")

    items: List[Dict[str, Any]] = []
    for window in workspace.get("windows", []) or []:
        window_index = window.get("window_index")
        for tab in window.get("tabs", []) or []:
            tab_index = tab.get("tab_index")
            # split_tree 可能是嵌套结构，iter_panes 会只产出叶子 terminal pane。
            for pane_index, pane in enumerate(iter_panes(tab.get("split_tree")), start=1):
                restore = pane.get("restore")
                if restore is None and isinstance(pane.get("restore_cmd"), str):
                    # 旧状态里的字符串命令只展示，不参与自动执行。
                    restore = None
                # has_agent 表示这个 pane 有恢复意图；普通 shell pane 不需要白名单校验。
                has_agent = bool(pane.get("agent") and (restore or pane.get("restore_cmd")))
                confidence = pane.get("binding_confidence") or "none"
                allowed = False
                reason = "普通 shell 窗格"
                if has_agent:
                    # 先校验命令结构，再结合绑定置信度决定能否自动执行。
                    allowed, reason = validate_restore(restore)
                    if allowed and confidence == "low":
                        # 低置信绑定可能把 session 贴错 pane，必须让用户人工确认。
                        allowed = False
                        reason = "低置信绑定需要人工确认"
                items.append(
                    {
                        "window_index": window_index,
                        "tab_index": tab_index,
                        "pane_index": pane_index,
                        "cwd": pane.get("cwd"),
                        "agent": pane.get("agent"),
                        "session_id": pane.get("session_id"),
                        "binding_confidence": confidence,
                        "restore": restore,
                        "restore_cmd": pane.get("restore_cmd")
                        or (restore.get("display") if isinstance(restore, dict) else None),
                        "allowed": allowed,
                        "reason": reason,
                    }
                )
    return {
        "snapshot_id": workspace.get("snapshot_id"),
        "name": workspace.get("name"),
        "captured_at": workspace.get("captured_at"),
        "terminal_app": workspace.get("terminal_app"),
        "window_count": len(workspace.get("windows", []) or []),
        "tab_count": count_workspace_tabs(workspace),
        "pane_count": count_workspace_panes(workspace),
        "items": items,
    }


def assert_plan_executable(plan: Dict[str, Any]) -> None:
    """执行前做最后一道闸门，避免计划中的风险项被误执行。"""
    for item in plan.get("items", []):
        # 只要出现恢复意图，就必须是 allowed；普通 shell pane 不阻塞恢复脚本生成。
        has_restore_intent = bool(item.get("restore") or item.get("restore_cmd"))
        if has_restore_intent and not item.get("allowed"):
            raise RestorePlanError(
                "恢复计划包含不可自动执行的 pane："
                f"window={item.get('window_index')} tab={item.get('tab_index')} "
                f"pane={item.get('pane_index')}，原因：{item.get('reason')}"
            )

