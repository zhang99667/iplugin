#!/usr/bin/env python3
"""给 html-report 单文件 HTML 注入离线评论模式。

这个脚本用于把已经生成好的普通 HTML 报告升级成“评论版”：
- 选中文本后显示轻量气泡，只保留一个“注释”入口。
- 输入浮层只有一个“提交”按钮，按钮显示 Ctrl/⌘ + Enter 提示，支持快捷提交，点击外侧自动关闭。
- 右侧栏可以编辑批注、把评论结果内嵌回 HTML、复制/下载 Markdown，并导出物理剥离批注能力和内嵌评论包的发布版 HTML。

脚本只依赖 Python 标准库，输出仍是单文件 HTML。批注 UI 的 CSS / HTML / JS 维护在
assets/annotation-mode/，这里负责读取资产、注入来源路径元数据和幂等装配。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CSS_MARKER_START = "/* QA_ANNOTATION_CSS_START:"
CSS_MARKER_END = "QA_ANNOTATION_CSS_END */"
HTML_MARKER_START = "<!-- QA_ANNOTATION_HTML_START:"
HTML_MARKER_END = "QA_ANNOTATION_HTML_END -->"
SCRIPT_MARKER_START = "<!-- QA_ANNOTATION_SCRIPT_START -->"
SCRIPT_MARKER_END = "<!-- QA_ANNOTATION_SCRIPT_END -->"


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "annotation-mode"
ANNOTATION_CSS_PATH = ASSET_DIR / "annotation.css"
ANNOTATION_HTML_PATH = ASSET_DIR / "annotation.html"
ANNOTATION_JS_PATH = ASSET_DIR / "annotation.js"


def read_asset(path: Path) -> str:
    """读取评论模式资产，缺失时给出可定位的错误。"""

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"评论模式资产缺失: {path}") from exc


def read_marked_asset(path: Path, marker_start: str, marker_end: str) -> str:
    """读取带剥离标记的资产，确保发布版导出和重复注入仍能稳定定位。"""

    content = read_asset(path)
    if marker_start not in content or marker_end not in content:
        raise ValueError(f"评论模式资产缺少剥离标记: {path}")
    return content


def read_annotation_assets() -> tuple[str, str, str]:
    """读取评论模式三类资产，并校验 JS 里保留元数据占位符。"""

    css = read_marked_asset(ANNOTATION_CSS_PATH, CSS_MARKER_START, CSS_MARKER_END)
    html = read_marked_asset(ANNOTATION_HTML_PATH, HTML_MARKER_START, HTML_MARKER_END)
    js = read_marked_asset(ANNOTATION_JS_PATH, SCRIPT_MARKER_START, SCRIPT_MARKER_END)
    if "__QA_REPORT_META__" not in js:
        raise ValueError(f"评论模式 JS 缺少 __QA_REPORT_META__ 占位符: {ANNOTATION_JS_PATH}")
    return css, html, js


def strip_annotation_mode(html: str) -> str:
    """删除已经注入过的评论模式，保证脚本可重复运行。"""
    # 先删除整段批注脚本，避免脚本内部的正则文本被下面的标记清理误匹配。
    html = re.sub(r"\n?\s*<script\s+data-qa-script>[\s\S]*?</script>", "", html)
    html = re.sub(r"\n?\s*/\* QA_ANNOTATION_CSS_START:[\s\S]*?QA_ANNOTATION_CSS_END \*/", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_HTML_START:[\s\S]*?QA_ANNOTATION_HTML_END -->", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_SCRIPT_START -->[\s\S]*?<!-- QA_ANNOTATION_SCRIPT_END -->", "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


def build_annotation_js(js_template: str, output_path: Path | None = None) -> str:
    """生成带来源路径元数据的批注脚本。"""
    meta: dict[str, str] = {}
    if output_path is not None:
        # 在生成阶段写入绝对路径，避免通过 HTTP 预览时 location.pathname 退化为 URL 路径。
        absolute_path = output_path.expanduser().resolve()
        meta = {
            "fileName": absolute_path.name,
            "absolutePath": str(absolute_path),
            "fileUrl": absolute_path.as_uri(),
        }
    return js_template.replace("__QA_REPORT_META__", json.dumps(meta, ensure_ascii=False))


def inject_annotation_mode(html: str, output_path: Path | None = None) -> str:
    """把 CSS、HTML 容器和 JS 批注逻辑插入到单文件 HTML 中。"""
    annotation_css, annotation_html, annotation_js = read_annotation_assets()
    html = strip_annotation_mode(html)
    if "</style>" not in html:
        raise ValueError("找不到 </style>，无法注入批注样式")
    if "</body>" not in html:
        raise ValueError("找不到 </body>，无法注入批注脚本")

    html = html.replace("</style>", annotation_css + "\n  </style>", 1)

    # 优先放在现有 toast 后面，复用 html-report 的提示气泡。
    toast = '<div class="toast" id="toast">已复制</div>'
    if toast in html:
        html = html.replace(toast, toast + "\n" + annotation_html, 1)
    else:
        html = html.replace("</body>", annotation_html + "\n</body>", 1)

    return html.replace("</body>", build_annotation_js(annotation_js, output_path) + "\n</body>", 1)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="给 html-report 单文件 HTML 注入离线评论模式。")
    parser.add_argument("html", help="输入 HTML 文件。")
    parser.add_argument("-o", "--output", help="输出 HTML 文件；默认覆盖输入文件。")
    return parser.parse_args()


def main() -> None:
    """读取 HTML、注入评论模式并写回文件。"""
    args = parse_args()
    input_path = Path(args.html)
    output_path = Path(args.output) if args.output else input_path

    html = input_path.read_text(encoding="utf-8")
    output_path.write_text(inject_annotation_mode(html, output_path), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
