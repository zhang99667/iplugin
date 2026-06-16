"""定义不同 Agent CLI 的二进制位置、session 目录和 resume 命令差异。"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence

from .models import shell_join_display


@dataclass(frozen=True)
class AgentSpec:
    """单个 Agent CLI 的稳定能力描述。

    字段说明：
    - name：z-agent 内部使用的 Agent 名称，也会写入状态文件。
    - binary_names：在 PATH 中按顺序查找真实 CLI 时使用的候选命令名。
    - env_binary_var：用户显式指定真实 CLI 路径时使用的环境变量名。
    - resume_argv_template：生成恢复命令 argv 的模板，`{session_id}` 会被会话 id 替换。
    - session_roots：该 Agent 默认保存 session 的目录，doctor 只做只读检查。
    """

    # z-agent 内部和状态文件里的稳定名称，例如 codex 或 claude。
    name: str
    # 真实 CLI 的候选命令名；find_binary 会按顺序在 PATH 中查找。
    binary_names: Sequence[str]
    # 指向真实 CLI 路径的环境变量名，用于覆盖 PATH 查找结果。
    env_binary_var: str
    # 恢复会话时使用的结构化 argv 模板，避免后续通过 shell 字符串拼命令。
    resume_argv_template: Sequence[str]
    # 该 Agent 可能存放 session 数据的根目录，doctor 用它提示本机配置状态。
    session_roots: Sequence[str]

    def build_resume(self, session_id: str) -> Dict[str, object]:
        """生成结构化 resume 命令，避免 restore 阶段拼接 shell 字符串。"""
        argv = [part.format(session_id=session_id) for part in self.resume_argv_template]
        return {
            "kind": "agent_resume",
            "agent": self.name,
            "argv": argv,
            "display": shell_join_display(argv),
        }


AGENT_SPECS: Dict[str, AgentSpec] = {
    "codex": AgentSpec(
        # Codex 当前 resume 入口是 `codex resume <session_id>`。
        name="codex",
        binary_names=("codex",),
        env_binary_var="Z_AGENT_CODEX_BINARY",
        resume_argv_template=("codex", "resume", "{session_id}"),
        session_roots=("~/.codex/sessions",),
    ),
    "claude": AgentSpec(
        # Claude Code 当前 resume 入口是 `claude --resume <session_id>`。
        name="claude",
        binary_names=("claude",),
        env_binary_var="Z_AGENT_CLAUDE_BINARY",
        resume_argv_template=("claude", "--resume", "{session_id}"),
        session_roots=("~/.claude/projects", "~/.claude"),
    ),
}


def get_agent_spec(name: str) -> AgentSpec:
    """按名称取得 Agent 配置，未知名称直接给出可选项。"""
    try:
        return AGENT_SPECS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(AGENT_SPECS))
        raise ValueError(f"未知 agent {name!r}；可选值：{choices}") from exc


def expand_session_roots(spec: AgentSpec) -> Iterable[Path]:
    """展开 session 根目录，doctor 用它做只读探测。"""
    for root in spec.session_roots:
        yield Path(root).expanduser()


def find_binary(spec: AgentSpec, explicit_binary: str | None = None) -> str | None:
    """按显式参数、环境变量、PATH 的优先级查找真实 CLI。"""
    if explicit_binary:
        # zagent codex/claude 可显式指定真实 CLI，适合 PATH 中有多个版本时使用。
        return str(Path(explicit_binary).expanduser())
    env_value = os.environ.get(spec.env_binary_var)
    if env_value:
        # 环境变量适合用户机器上真实 CLI 不在 PATH 或有多个版本时指定。
        return str(Path(env_value).expanduser())
    for name in spec.binary_names:
        # 最后才查 PATH，保持和用户直接输入 codex/claude 的习惯一致。
        found = shutil.which(name)
        if found:
            return found
    return None
