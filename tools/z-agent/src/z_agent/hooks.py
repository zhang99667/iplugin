"""接收 Agent 原生 hook 事件，并回写当前 terminal 的 session 元数据。"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from .agent_specs import get_agent_spec
from .models import marker_for_terminal_key, now_iso
from .state import update_active_terminal


SESSION_KEYS = {
    # 不同 Agent/版本的 hook payload 字段命名不完全一致，先列出常见别名。
    "session_id",
    "sessionId",
    "conversation_id",
    "conversationId",
    "thread_id",
    "threadId",
}
SESSION_FILE_KEYS = {
    # 会话文件路径和对话转录路径只用于推断 session_id，不读取文件正文。
    "session_file",
    "sessionFile",
    "transcript_path",
    "transcriptPath",
    "transcript",
    "log_path",
    "logPath",
}
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class HookIngestError(RuntimeError):
    """hook payload 或 wrapper 环境不满足写入要求时抛出。"""

    pass


def _walk_items(value: Any) -> Iterable[tuple[str, Any]]:
    """递归扫描 hook payload，兼容不同 Agent 版本的字段嵌套。"""
    if isinstance(value, dict):
        for key, child in value.items():
            # 先产出当前层，再递归子节点；这样浅层显式字段优先被 _first_string_for_keys 命中。
            yield str(key), child
            yield from _walk_items(child)
    elif isinstance(value, list):
        for child in value:
            # payload 中数组元素可能包着 session 信息，比如事件列表或工具调用列表。
            yield from _walk_items(child)


def _first_string_for_keys(payload: Any, keys: set[str]) -> str | None:
    """在递归字段里取第一个非空字符串值。"""
    for key, value in _walk_items(payload):
        # 只接受字符串，避免把嵌套对象/数字误当成 session id 写入状态。
        if key in keys and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _derive_session_id(session_file: str | None) -> str | None:
    """优先从路径里的 UUID 提取 session id，兜底使用文件名 stem。"""
    if not session_file:
        return None
    # Codex session 路径里常见 UUID，优先提取这种稳定标识。
    match = UUID_RE.search(session_file)
    if match:
        return match.group(0)
    # Claude 或其他 CLI 可能只有文件名可用，去掉常见扩展名作为保底 id。
    stem = Path(session_file).name
    for suffix in (".jsonl", ".json", ".log", ".txt"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem or None


def extract_session_metadata(payload: Any) -> tuple[str | None, str | None]:
    """只提取恢复所需元数据，不读取对话转录正文。"""
    # 显式 session_id 最可信；路径推断只作为缺字段时的兜底策略。
    session_id = _first_string_for_keys(payload, SESSION_KEYS)
    session_file = _first_string_for_keys(payload, SESSION_FILE_KEYS)
    if not session_id:
        session_id = _derive_session_id(session_file)
    return session_id, session_file


def ingest_hook_event(agent: str, payload: Any, env: dict[str, str] | None = None) -> dict[str, Any]:
    """把一次 hook 事件合并进 active_terminals。"""
    env = env if env is not None else os.environ
    spec = get_agent_spec(agent)
    terminal_key = env.get("Z_AGENT_TERMINAL_KEY")
    if not terminal_key:
        # 没有 terminal_key 就无法知道 hook 来自哪个 pane，强行写入会污染 active_terminals。
        raise HookIngestError("缺少 Z_AGENT_TERMINAL_KEY；请先通过 z-agent 包装器启动 agent")

    # cwd 优先使用 wrapper 注入值；没有时才读当前进程 cwd，避免 hook runner 切目录造成误判。
    cwd = env.get("Z_AGENT_CWD") or os.getcwd()
    run_id = env.get("Z_AGENT_RUN_ID")
    session_id, session_file = extract_session_metadata(payload)

    # 即使暂时拿不到 session_id，也保留 cwd/agent，供后续 snapshot 解释 pane 来源。
    patch: dict[str, Any] = {
        "terminal_key": terminal_key,
        "marker": marker_for_terminal_key(terminal_key),
        "agent": spec.name,
        "cwd": cwd,
        "run_id": run_id,
        "session_id": session_id,
        "session_file": session_file,
        "last_seen_at": now_iso(),
        "source": "agent_hook",
        "resumable": bool(session_id),
    }
    if session_id:
        # restore 阶段只信任结构化 argv，restore_cmd 仅作为计划展示兼容字段。
        restore = spec.build_resume(session_id)
        patch["restore"] = restore
        patch["restore_cmd"] = restore["display"]
    else:
        # 没有 session_id 时明确标记不可恢复，查看恢复计划时才能给出清晰原因。
        patch["restore"] = None
        patch["restore_cmd"] = None
    # 只更新当前 terminal_key 对应记录，不影响同一工作区里的其他 pane。
    update_active_terminal(terminal_key, patch)
    return patch


def ingest_from_stdin(agent: str) -> dict[str, Any]:
    """CLI 入口：从 stdin 读取原生 hook JSON 后交给 ingest_hook_event。"""
    raw = sys.stdin.read()
    try:
        # 空 stdin 按空事件处理，便于验证 hook 入口是否接通。
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        raise HookIngestError(f"hook stdin 不是合法 JSON：{exc}") from exc
    return ingest_hook_event(agent, payload)
