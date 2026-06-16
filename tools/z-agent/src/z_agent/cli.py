"""zagent 命令行入口，集中编排各子命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    # 支持 `python3 src/z_agent/cli.py` 直接运行，无需先安装包。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "z_agent"

from .agent_specs import AGENT_SPECS
from .doctor import run_doctor
from .ghostty import GhosttyAdapter, GhosttyError
from .hooks import HookIngestError, ingest_from_stdin
from .install import install_agent
from .planner import RestorePlanError, assert_plan_executable, build_restore_plan
from .state import StateError, load_state
from .wrapper import WrapperError, run_agent


class LocalizedArgumentParser(argparse.ArgumentParser):
    """统一命令行帮助文案，不改变参数解析行为。"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)
        # 禁用 argparse 默认 help 后手动注册，避免重复生成 -h/--help。
        self.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")

    def format_help(self) -> str:
        text = super().format_help()
        # 只替换 argparse 固定标题，命令名和参数名保持原样。
        return (
            text.replace("usage:", "用法:")
            .replace("positional arguments:", "位置参数:")
            .replace("options:", "可选参数:")
        )


def _parse_wrapper_args(argv: Sequence[str]) -> tuple[str | None, list[str]]:
    """wrapper 子命令允许 --binary 后透传剩余参数给真实 Agent。"""
    args = list(argv)
    binary = None
    rest: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--binary":
            if index + 1 >= len(args):
                raise WrapperError("--binary 需要指定路径")
            # --binary 是 z-agent wrapper 自己消费的参数，不再透传给真实 Agent。
            binary = args[index + 1]
            index += 2
            continue
        # 遇到第一个非 wrapper 参数后，剩余内容全部原样交给真实 Agent。
        rest.extend(args[index:])
        break
    return binary, rest


def build_parser() -> argparse.ArgumentParser:
    """声明全部 CLI 子命令和参数。"""
    parser = LocalizedArgumentParser(prog="zagent")
    # 子解析器沿用同一个 Parser 类，避免顶层命令和子命令的帮助格式不一致。
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=LocalizedArgumentParser)

    subparsers.add_parser("doctor", help="检查本机环境")

    install_parser = subparsers.add_parser("install", help="生成安装文件")
    install_parser.add_argument("agent", choices=sorted(AGENT_SPECS))

    hook_parser = subparsers.add_parser("hook", help="处理 Agent 原生钩子")
    hook_subparsers = hook_parser.add_subparsers(
        dest="hook_command",
        required=True,
        parser_class=LocalizedArgumentParser,
    )
    ingest_parser = hook_subparsers.add_parser("ingest", help="写入 hook 元数据")
    ingest_parser.add_argument("--agent", required=True, choices=sorted(AGENT_SPECS), help="Agent 类型")
    ingest_parser.add_argument("--json", action="store_true", help="从 stdin 读取 hook JSON")

    state_parser = subparsers.add_parser("state", help="查看状态文件")
    state_subparsers = state_parser.add_subparsers(
        dest="state_command",
        required=True,
        parser_class=LocalizedArgumentParser,
    )
    show_parser = state_subparsers.add_parser("show", help="展示当前状态")
    show_parser.add_argument("--json", action="store_true", help="输出完整 JSON")

    snapshot_parser = subparsers.add_parser("snapshot", help="采集 Ghostty 工作区快照")
    snapshot_subparsers = snapshot_parser.add_subparsers(
        dest="snapshot_command",
        required=True,
        parser_class=LocalizedArgumentParser,
    )
    capture_parser = snapshot_subparsers.add_parser("capture", help="采集当前工作区")
    capture_parser.add_argument("--name", help="快照名称")

    restore_parser = subparsers.add_parser("restore", help="恢复 Ghostty 工作区")

    return parser


def _print_state(json_output: bool) -> int:
    """展示状态摘要或完整 JSON。"""
    state = load_state()
    if json_output:
        # JSON 模式保持字段名原样，便于脚本消费。
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        # 文本模式只给摘要，避免把完整 session 路径刷满终端。
        active = state.get("active_terminals", {})
        latest = state.get("latest_workspace")
        print("z-agent 状态")
        print(f"active_terminals 数量：{len(active)}")
        print(f"latest_workspace：{'有' if latest else '无'}")
        print(f"更新时间：{state.get('updated_at')}")
    return 0


def _restore(args: argparse.Namespace) -> int:
    """执行 Ghostty 工作区恢复。"""
    workspace = load_state().get("latest_workspace")
    plan = build_restore_plan(workspace)
    # restore 只做执行；执行前仍用 planner 做结构化白名单校验。
    assert_plan_executable(plan)
    output = GhosttyAdapter().restore_workspace(workspace)
    if output:
        print(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 主入口；返回 shell 退出码。"""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in AGENT_SPECS:
        # `zagent codex ...` / `zagent claude ...` 是 wrapper 快捷入口，不走 argparse 子命令树。
        agent = argv[0]
        try:
            binary, agent_args = _parse_wrapper_args(argv[1:])
            return run_agent(agent, agent_args, explicit_binary=binary)
        except WrapperError as exc:
            print(f"zagent: {exc}", file=sys.stderr)
            return 2

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        # 保持显式分发，便于定位每个子命令的副作用入口。
        if args.command == "doctor":
            print(run_doctor())
            return 0
        if args.command == "install":
            print(install_agent(args.agent))
            return 0
        if args.command == "hook" and args.hook_command == "ingest":
            result = ingest_from_stdin(args.agent)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "state" and args.state_command == "show":
            return _print_state(args.json)
        if args.command == "snapshot" and args.snapshot_command == "capture":
            result = GhosttyAdapter().capture_workspace(name=args.name)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "restore":
            return _restore(args)
    except (HookIngestError, GhosttyError, RestorePlanError, StateError, WrapperError) as exc:
        print(f"zagent: {exc}", file=sys.stderr)
        return 2
    parser.error("未处理的命令")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
