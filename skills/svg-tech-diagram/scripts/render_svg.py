#!/usr/bin/env python3
"""把 SVG 文件渲染成 PNG，供绘图 skill 做交付前视觉自审。

脚本只做一件事：调用本机 librsvg 提供的 `rsvg-convert`。
不在这里解析或修改 SVG 内容，避免把绘图逻辑和渲染检查耦合在一起。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    输入 SVG 是必填项；输出 PNG 可省略，省略时默认放在输入文件同目录并复用文件名。
    宽高参数透传给 `rsvg-convert`，用于需要固定预览尺寸的场景。
    """

    parser = argparse.ArgumentParser(description="使用 rsvg-convert 将 SVG 渲染成 PNG。")
    parser.add_argument("svg", type=Path, help="输入的 .svg 文件")
    parser.add_argument("png", type=Path, nargs="?", help="输出的 .png 文件；默认使用输入文件同名路径")
    parser.add_argument("--width", "-w", type=int, help="可选输出宽度，单位像素")
    parser.add_argument("--height", "-H", type=int, help="可选输出高度，单位像素")
    return parser.parse_args()


def main() -> int:
    """执行 SVG 到 PNG 的渲染流程，并用退出码表达失败原因。"""

    args = parse_args()
    svg_path = args.svg
    png_path = args.png or svg_path.with_suffix(".png")

    # 先确认输入存在，避免把 rsvg-convert 的底层报错暴露给使用者。
    if not svg_path.is_file():
        print(f"输入 SVG 不存在：{svg_path}", file=sys.stderr)
        return 1

    # rsvg-convert 来自 librsvg；缺失时直接给安装提示，方便下一步补齐环境。
    converter = shutil.which("rsvg-convert")
    if not converter:
        print(
            "未找到 rsvg-convert。请先安装 librsvg，例如：brew install librsvg",
            file=sys.stderr,
        )
        return 2

    # 输出目录可能还不存在，先创建目录，再把最终路径交给 rsvg-convert。
    png_path.parent.mkdir(parents=True, exist_ok=True)
    command = [converter, str(svg_path), "-o", str(png_path)]

    # 宽高都保持可选；不传时由 rsvg-convert 按 SVG 自身尺寸渲染。
    if args.width:
        command.extend(["--width", str(args.width)])
    if args.height:
        command.extend(["--height", str(args.height)])

    # 捕获输出后再透传，保证调用方能看到 rsvg-convert 的原始诊断信息。
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    # 成功时只输出 PNG 路径，方便其他脚本或 agent 继续读取预览图。
    print(png_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
