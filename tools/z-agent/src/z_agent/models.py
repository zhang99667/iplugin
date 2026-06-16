"""状态 JSON 和 workspace snapshot 的轻量模型工具。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, MutableMapping


StateDict = Dict[str, Any]
PaneDict = Dict[str, Any]

TERMINAL_KEY_PREFIX = "za_terminal_"
RUN_ID_PREFIX = "za_run_"
TERMINAL_KEY_RE = re.compile(r"^za_terminal_[A-Za-z0-9]{8,32}$")
MARKER_RE = re.compile(r"__zagent_terminal_([A-Za-z0-9]{8,32})__")


def now_iso() -> str:
    """生成带本地时区 offset 的 ISO 时间。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def empty_state() -> StateDict:
    """返回 schema=1 的空状态。"""
    return {
        "schema": 1,
        "updated_at": now_iso(),
        "active_terminals": {},
        "latest_workspace": None,
        "previous_workspace": None,
    }


def marker_for_terminal_key(terminal_key: str) -> str:
    """把 terminal_key 转成写入终端标题的 marker。"""
    # marker 暴露在终端标题里，去掉公共前缀后更短，也便于人工查看。
    suffix = terminal_key.removeprefix(TERMINAL_KEY_PREFIX)
    return f"__zagent_terminal_{suffix}__"


def terminal_key_from_marker(value: str | None) -> str | None:
    """从 terminal title/name 文本中解析 z-agent marker。"""
    if not value:
        return None
    # title/name 里可能混有 shell prompt 或用户自定义标题，所以用 search 而不是 fullmatch。
    match = MARKER_RE.search(value)
    if not match:
        return None
    return TERMINAL_KEY_PREFIX + match.group(1)


def normalize_state(raw: MutableMapping[str, Any] | None) -> StateDict:
    """把旧状态或损坏结构补齐为当前 schema 的最小可用形态。"""
    if not isinstance(raw, MutableMapping):
        return empty_state()
    # dict(raw) 做浅拷贝，避免调用方传入的对象被原地改动。
    state = dict(raw)
    # schema=1 是当前唯一版本；后续迁移可从这里接入。
    state.setdefault("schema", 1)
    state.setdefault("updated_at", now_iso())
    if not isinstance(state.get("active_terminals"), dict):
        # active_terminals 类型不对时直接置空，避免后续 update 误写到非 dict 上。
        state["active_terminals"] = {}
    state.setdefault("latest_workspace", None)
    state.setdefault("previous_workspace", None)
    return state


def iter_panes(split_tree: Any) -> Iterator[PaneDict]:
    """深度遍历 split tree，把叶子节点都视为 terminal pane。"""
    if not isinstance(split_tree, dict):
        return
    children = split_tree.get("children")
    if isinstance(children, list) and children:
        for child in children:
            # split_tree 可以任意嵌套，递归展开后 planner 只关心叶子 pane。
            yield from iter_panes(child)
        return
    yield split_tree


def iter_workspace_panes(workspace: Any) -> Iterator[PaneDict]:
    """遍历整个 workspace 中的所有 pane。"""
    if not isinstance(workspace, dict):
        return
    for window in workspace.get("windows", []) or []:
        for tab in window.get("tabs", []) or []:
            yield from iter_panes(tab.get("split_tree"))


def count_workspace_panes(workspace: Any) -> int:
    """统计 workspace 中的 pane 数量。"""
    return sum(1 for _ in iter_workspace_panes(workspace))


def count_workspace_tabs(workspace: Any) -> int:
    """统计 workspace 中的 tab 数量。"""
    if not isinstance(workspace, dict):
        return 0
    # window 缺少 tabs 时按空列表处理，兼容不完整的 capture 结果。
    return sum(len(window.get("tabs", []) or []) for window in workspace.get("windows", []) or [])


def shell_join_display(argv: Iterable[str]) -> str:
    """只用于展示命令；真实执行仍依赖结构化 argv。"""
    parts: List[str] = []
    for token in argv:
        if re.fullmatch(r"[A-Za-z0-9_./:@%+=,-]+", token):
            parts.append(token)
        else:
            # 展示时做 shell 风格转义，避免恢复计划文本误导用户复制后含义变化。
            parts.append("'" + token.replace("'", "'\\''") + "'")
    return " ".join(parts)
