"""负责 workspace_state.json 的读取、加锁更新和原子写入。"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

try:
    import fcntl
except ImportError:  # pragma: no cover - 非 POSIX 平台兜底
    # Windows 等平台没有 fcntl；目标运行环境为 macOS，这里只保留可导入兜底。
    fcntl = None  # type: ignore[assignment]

from .config import state_file_path
from .models import StateDict, empty_state, normalize_state, now_iso


class StateError(RuntimeError):
    """状态文件无法安全读取或写入时抛出。"""

    pass


def _ensure_dir(path: Path) -> None:
    """写入前确保父目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def _lock(path: Path):
    """用同目录 lock 文件保护读改写，避免 hook 和 snapshot 并发覆盖。"""
    _ensure_dir(path.parent)
    # lock 文件放在状态文件旁边，保证不同 Z_AGENT_STATE_DIR 之间互不影响。
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            # macOS 上用进程级排他锁；同一时刻只允许一个写入者进入读改写区间。
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                # 释放动作放在 finally，避免 mutator 抛异常后锁遗留。
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def backup_broken_state(path: Path) -> Path | None:
    """损坏 JSON 不直接覆盖，先改名备份，保留故障现场。"""
    if not path.exists():
        return None
    # 文件名带时间，避免连续损坏时后一次备份覆盖前一次现场。
    backup_path = path.with_name(f"{path.name}.broken.{now_iso().replace(':', '').replace('+', '_')}")
    path.replace(backup_path)
    return backup_path


def _read_without_lock(path: Path) -> StateDict:
    """调用方已持锁；这里只负责读取和 schema 归一化。"""
    if not path.exists():
        return empty_state()
    try:
        with path.open("r", encoding="utf-8") as handle:
            # 读取后统一走 normalize_state，兼容旧版本缺字段或字段类型异常。
            return normalize_state(json.load(handle))
    except json.JSONDecodeError as exc:
        # JSON 坏了说明状态文件已经不可增量修复，先备份再让上层重建空状态。
        backup = backup_broken_state(path)
        message = f"状态文件不是合法 JSON，已备份到 {backup}"
        raise StateError(message) from exc


def _write_without_lock(path: Path, state: StateDict) -> None:
    """调用方已持锁；这里只负责临时文件 + fsync + 原子替换。"""
    _ensure_dir(path.parent)
    # 每次写入都补齐 schema 和 updated_at，避免调用方漏填公共字段。
    state = normalize_state(state)
    state["updated_at"] = now_iso()
    # 临时文件必须和目标文件在同一目录，os.replace 才能保持原子替换语义。
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            # fsync 让内容先落到磁盘，再替换目标文件，减少断电/崩溃后的半写风险。
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            # 如果 json.dump 或 fsync 中途失败，清理残留临时文件。
            tmp_path.unlink()


def load_state(root: Path | None = None) -> StateDict:
    path = state_file_path(root)
    # 纯读取命令不能因为状态文件不存在就创建用户 home 目录。
    if not path.exists():
        return empty_state()
    with _lock(path):
        try:
            return _read_without_lock(path)
        except StateError as exc:
            print(f"z-agent 警告：{exc}", file=sys.stderr)
            # 坏文件已经在 _read_without_lock 里备份，这里写回空状态让后续命令可继续工作。
            fresh = empty_state()
            _write_without_lock(path, fresh)
            return fresh


def save_state(state: StateDict, root: Path | None = None) -> None:
    """完整覆盖保存状态，供迁移工具或调试入口使用。"""
    path = state_file_path(root)
    with _lock(path):
        _write_without_lock(path, state)


def mutate_state(mutator: Callable[[StateDict], Any], root: Path | None = None) -> StateDict:
    """所有写操作统一走读-改-写，减少字段丢失风险。"""
    path = state_file_path(root)
    with _lock(path):
        try:
            state = _read_without_lock(path)
        except StateError:
            # 写路径遇到坏状态时不把异常继续抛给 hook；恢复为空状态后继续写本次更新。
            state = empty_state()
        # mutator 只负责业务字段变更，公共时间戳和原子写由 _write_without_lock 统一处理。
        mutator(state)
        _write_without_lock(path, state)
        return state


def update_active_terminal(terminal_key: str, patch: dict[str, Any], root: Path | None = None) -> StateDict:
    """局部更新一个 terminal 记录，未涉及字段保持不变。"""
    def mutator(state: StateDict) -> None:
        active = state.setdefault("active_terminals", {})
        # 先复制旧记录再覆盖 patch，防止 hook 更新 session_id 时丢掉 wrapper 写入的 cwd/marker。
        current = dict(active.get(terminal_key, {}))
        current.update(patch)
        current["terminal_key"] = terminal_key
        # last_seen_at 没有显式传入时，用当前时间表示这次状态确实被刷新过。
        current["last_seen_at"] = patch.get("last_seen_at") or now_iso()
        active[terminal_key] = current

    return mutate_state(mutator, root=root)


def save_latest_workspace(workspace: dict[str, Any], root: Path | None = None) -> StateDict:
    """保存最新快照，并把旧 latest_workspace 轮转到 previous_workspace。"""
    def mutator(state: StateDict) -> None:
        # 只保留一份 previous_workspace，满足手动回退需要，避免状态文件无限膨胀。
        state["previous_workspace"] = state.get("latest_workspace")
        state["latest_workspace"] = workspace

    return mutate_state(mutator, root=root)
