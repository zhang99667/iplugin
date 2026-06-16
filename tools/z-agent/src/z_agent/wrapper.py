"""Agent wrapper：启动真实 CLI 前注入 terminal 身份和状态元数据。"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence

from .agent_specs import find_binary, get_agent_spec
from .models import RUN_ID_PREFIX, TERMINAL_KEY_PREFIX, marker_for_terminal_key, now_iso
from .state import update_active_terminal


@dataclass(frozen=True)
class WrapperContext:
    """一次 wrapper 启动真实 Agent 前准备好的全部上下文。

    字段说明：
    - agent：z-agent 归一化后的 Agent 名称。
    - binary：最终要执行的真实 CLI 路径。
    - args：透传给真实 CLI 的用户参数。
    - terminal_key：当前 terminal/pane 的稳定身份。
    - run_id：本次真实 Agent 进程启动的诊断 id。
    - cwd：wrapper 启动时的工作目录。
    - marker：由 terminal_key 派生的标题标记，供外部快照识别 pane。
    - env：传给真实 CLI 子进程的完整环境变量。
    """

    # 归一化后的 Agent 名称，会写入 active_terminals 并传给 hook。
    agent: str
    # 真实 CLI 的可执行文件路径，已经过 --binary、环境变量和 PATH 查找。
    binary: str
    # 用户传给 zagent codex/claude 的剩余参数，启动真实 CLI 时原样透传。
    args: Sequence[str]
    # pane 级稳定身份；hook 通过环境变量读取它，外部快照通过标题 marker 反查它。
    terminal_key: str
    # 单次进程启动 id；同一个 terminal_key 下重复启动 Agent 时会刷新。
    run_id: str
    # wrapper 被调用时的当前工作目录，用于状态展示和低置信兜底绑定。
    cwd: str
    # 写入终端标题的派生标记，不是真正身份源，真正身份源始终是 terminal_key。
    marker: str
    # 子进程环境，包含 z-agent 注入的 Z_AGENT_* 变量和用户原有环境。
    env: dict[str, str]


class WrapperError(RuntimeError):
    """wrapper 无法定位真实 CLI 或参数不合法时抛出。"""

    pass


def new_terminal_key() -> str:
    """生成 pane 级身份，默认在同一环境中可复用。"""
    return TERMINAL_KEY_PREFIX + secrets.token_hex(4)


def new_run_id() -> str:
    """生成单次真实 Agent 进程启动的诊断 id。"""
    return RUN_ID_PREFIX + secrets.token_hex(4)


def write_terminal_marker(marker: str) -> None:
    """通过终端标题控制序列写入 marker，供 Ghostty capture 高置信绑定。"""
    # OSC 0 控制序列会改当前终端标题；Ghostty AppleScript 后续可从 title/name 读回。
    sys.stdout.write(f"\033]0;{marker}\007")
    # 真实 Agent 马上要启动，立即 flush，避免 marker 滞留在 Python 缓冲区。
    sys.stdout.flush()


def prepare_wrapper_context(
    agent: str,
    args: Sequence[str],
    explicit_binary: str | None = None,
    env: dict[str, str] | None = None,
) -> WrapperContext:
    """构造子进程环境；同一 pane 内已有 terminal_key 时优先复用。"""
    # 调用方可传入 env；真实运行时复制 os.environ，避免直接修改当前进程环境。
    base_env = dict(env if env is not None else os.environ)
    spec = get_agent_spec(agent)
    # binary 可以来自 --binary、环境变量或 PATH；wrapper 自身不猜测安装位置。
    binary = find_binary(spec, explicit_binary)
    if not binary:
        raise WrapperError(
            f"找不到真实 {agent} binary；请传入 --binary 或设置 {spec.env_binary_var}"
        )

    # 如果 wrapper 在已有 z-agent pane 中再次启动，复用 terminal_key，保持 pane 身份稳定。
    terminal_key = base_env.get("Z_AGENT_TERMINAL_KEY") or new_terminal_key()
    # run_id 每次启动都刷新，用来区分同一 pane 内的多次 Agent 进程。
    run_id = new_run_id()
    cwd = os.getcwd()
    marker = marker_for_terminal_key(terminal_key)
    child_env = dict(base_env)
    # 这些环境变量会被 Agent 原生 hook 继承，hook ingest 靠它们回写正确 pane。
    child_env.update(
        {
            "Z_AGENT_AGENT": spec.name,
            "Z_AGENT_TERMINAL_KEY": terminal_key,
            "Z_AGENT_RUN_ID": run_id,
            "Z_AGENT_CWD": cwd,
        }
    )
    return WrapperContext(
        agent=spec.name,
        binary=binary,
        args=list(args),
        terminal_key=terminal_key,
        run_id=run_id,
        cwd=cwd,
        marker=marker,
        env=child_env,
    )


def record_wrapper_start(context: WrapperContext) -> None:
    """真实 Agent 启动前先登记 pane，hook 稍后再补 session_id。"""
    # 这里先写 resumable=False，因为真实 session_id 只有 Agent hook 触发后才知道。
    patch = {
        "terminal_key": context.terminal_key,
        "marker": context.marker,
        "agent": context.agent,
        "cwd": context.cwd,
        "run_id": context.run_id,
        "last_seen_at": now_iso(),
        "source": "wrapper",
        "resumable": False,
    }
    update_active_terminal(context.terminal_key, patch)


def run_agent(agent: str, args: Sequence[str], explicit_binary: str | None = None) -> int:
    """记录状态和 marker 后启动真实 Agent，并透传退出码。"""
    context = prepare_wrapper_context(agent, args, explicit_binary=explicit_binary)
    try:
        # 状态写入失败不应阻止用户使用真实 Agent，所以只告警不退出。
        record_wrapper_start(context)
    except Exception as exc:  # pragma: no cover - 防御性告警路径
        print(f"z-agent 警告：写入状态失败：{exc}", file=sys.stderr)
    try:
        # marker 写入失败只会影响 snapshot 绑定置信度，不应阻断真实 Agent。
        write_terminal_marker(context.marker)
    except Exception as exc:  # pragma: no cover - 防御性告警路径
        print(f"z-agent 警告：写入 terminal marker 失败：{exc}", file=sys.stderr)
    # 直接以 argv 方式启动真实 CLI，不经过 shell；用户参数原样透传。
    return subprocess.call([context.binary, *context.args], env=context.env)
