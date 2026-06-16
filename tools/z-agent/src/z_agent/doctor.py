"""输出 z-agent 运行前的本地环境诊断信息。"""

from __future__ import annotations

import shutil
from pathlib import Path

from .agent_specs import AGENT_SPECS, expand_session_roots, find_binary
from .config import install_root, state_file_path


def run_doctor() -> str:
    """只读探测 binary、session 目录和 osascript，不做安装或授权操作。"""
    lines = ["z-agent 诊断"]
    # doctor 只输出路径和存在性，不创建目录、不请求 Ghostty Automation 授权。
    lines.append(f"状态文件：{state_file_path()}")
    lines.append(f"安装目录：{install_root()}")
    osascript = shutil.which("osascript")
    lines.append(f"osascript：{osascript or '未找到'}")
    for spec in AGENT_SPECS.values():
        # binary 探测复用 agent spec 逻辑，确保 doctor 与 install/wrapper 看到的结果一致。
        binary = find_binary(spec)
        lines.append(f"{spec.name}.binary：{binary or '未找到'}")
        roots = []
        for root in expand_session_roots(spec):
            # session 根目录只做存在性检查，不扫描具体对话转录，避免读取会话正文。
            roots.append(f"{root}:{'存在' if Path(root).exists() else '未找到'}")
        lines.append(f"{spec.name}.session_roots：{', '.join(roots)}")
    return "\n".join(lines)
