"""生成 z-agent 的本地 hook 配置文件；不会接管原始 Agent 命令。"""

from __future__ import annotations

import stat
import sys
from pathlib import Path
from typing import Dict

from .agent_specs import get_agent_spec
from .config import install_root


def _cli_path() -> Path:
    # 安装脚本直接指向当前源码里的 cli.py，适合本地 editable/源码模式使用。
    return Path(__file__).resolve().with_name("cli.py")


def _hook_ingest_script(agent: str) -> str:
    """生成 Agent 原生 hook 调用的 shell 入口。"""
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "# z-agent hook 入口：从 stdin 接收原生 hook JSON 并回写状态文件。",
            "set -euo pipefail",
            # hook runner 只需要把 stdin 透传给 zagent hook ingest。
            f'exec "{sys.executable}" "{_cli_path()}" hook ingest --agent {agent} --json',
            "",
        ]
    )


def _native_hooks_template(agent: str) -> str:
    """生成原生 hook 配置示例；用户需要自行合并到对应 Agent 配置。"""
    # 不直接写入 Codex/Claude 的原生配置，避免破坏用户已有 hook 设置。
    return (
        "{\n"
        '  "hooks": [\n'
        "    {\n"
        '      "event": "session",\n'
        f'      "command": "~/.z-agent/{agent}/config/hooks/{agent}-hook-ingest.sh"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def build_install_plan(agent: str) -> Dict[str, str]:
    """返回将要写入的文件内容。"""
    spec = get_agent_spec(agent)
    root = install_root()
    agent_root = root / spec.name
    return {
        str(agent_root / "config" / "hooks" / f"{spec.name}-hook-ingest.sh"): _hook_ingest_script(spec.name),
        str(agent_root / "config" / "hooks" / f"{spec.name}-native-hooks.json"): _native_hooks_template(spec.name),
    }


def install_agent(agent: str) -> str:
    """按安装计划写文件，并只给 hook 脚本加执行权限。"""
    plan = build_install_plan(agent)
    written = []
    for path_text, content in plan.items():
        path = Path(path_text).expanduser()
        # 每个 agent 有独立安装目录，避免不同 Agent 的 hook 配置互相覆盖。
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if path.name.endswith("-hook-ingest.sh"):
            # 只有真正需要执行的 hook 脚本加 x 权限，配置文件保持普通文本。
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(str(path))
    return "已安装 z-agent 文件：\n" + "\n".join(f"- {path}" for path in written)
