"""集中管理 z-agent 的默认路径和环境变量覆盖入口。"""

from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "z-agent"
STATE_FILE_NAME = "workspace_state.json"


def state_dir() -> Path:
    """返回状态目录；隔离运行环境时可用 Z_AGENT_STATE_DIR 覆盖。"""
    override = os.environ.get("Z_AGENT_STATE_DIR")
    if override:
        # 临时运行可以把状态写到独立目录，避免污染真实用户状态。
        return Path(override).expanduser()
    # 默认遵循 XDG 风格，把运行态数据放在 ~/.local/share 下。
    return Path.home() / ".local" / "share" / APP_NAME


def install_root() -> Path:
    """返回安装目录；默认只生成 hook 相关文件。"""
    override = os.environ.get("Z_AGENT_INSTALL_ROOT")
    if override:
        # 安装路径可覆盖，便于在隔离目录里核对生成文件。
        return Path(override).expanduser()
    return Path.home() / ".z-agent"


def state_file_path(root: Path | None = None) -> Path:
    """返回 workspace_state.json 的完整路径。"""
    directory = root if root is not None else state_dir()
    return directory / STATE_FILE_NAME
