#!/usr/bin/env python3
"""校验 html-report 生成的单文件 HTML。

这个脚本只做确定性结构检查，不评价内容质量或视觉审美。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


CODE_WRAP_RE = re.compile(r'<div\b[^>]*class=["\'][^"\']*\bcode-wrap\b[^"\']*["\'][^>]*>.*?</div>', re.DOTALL)
LANG_RE = re.compile(r'\blanguage-([a-zA-Z0-9_-]+)\b')
TOKEN_RE = re.compile(r'\btok-[a-zA-Z0-9_-]+\b')
INLINE_STYLE_RE = re.compile(r'<span\b[^>]*\bstyle=["\'][^"\']+["\']', re.DOTALL)
COPY_BTN_RE = re.compile(r'<button\b[^>]*class=["\'][^"\']*\bcopy-btn\b[^"\']*["\']', re.DOTALL)

TEXT_LIKE_LANGS = {"text", "txt", "log", "logs", "plain", "plaintext"}
SUPPORTED_LANGS = {"kotlin", "java", "js", "python", "xml", "sql", "json", "yaml", "bash", "diff", "text"}


@dataclass
class TagFrame:
    tag: str
    classes: set[str]


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[TagFrame] = []
        self.errors: list[str] = []
        self.in_style = False
        self.style_chunks: list[str] = []
        self.has_viewport_meta = False
        self.has_toc = False
        self.has_toc_details = False
        self.has_open_toc_details = False
        self.has_toc_summary = False
        self.toc_link_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        attr_names = {name.lower() for name, _value in attrs}
        classes = class_set(attr_map.get("class", ""))
        inside_toc = "toc" in classes or any("toc" in frame.classes for frame in self.stack)

        if tag == "meta" and attr_map.get("name", "").lower() == "viewport":
            self.has_viewport_meta = True

        if tag == "style":
            self.in_style = True

        if tag == "script" and attr_map.get("src"):
            self.errors.append(f"外部脚本依赖不符合单文件要求: {attr_map['src']}")
        if tag == "link" and "stylesheet" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.errors.append(f"外部样式依赖不符合单文件要求: {attr_map['href']}")

        if "toc" in classes:
            self.has_toc = True
        if tag == "details" and (inside_toc or "toc-details" in classes):
            self.has_toc_details = True
            if "open" in attr_names:
                self.has_open_toc_details = True
        if tag == "summary" and inside_toc:
            self.has_toc_summary = True
        if tag == "a" and inside_toc and attr_map.get("href", "").startswith("#"):
            self.toc_link_count += 1

        if tag == "pre":
            inside_code_wrap = any("code-wrap" in frame.classes for frame in self.stack)
            is_ascii = "ascii-diagram" in classes
            if not inside_code_wrap and not is_ascii:
                self.errors.append("发现未包在 .code-wrap 中的 <pre>；ASCII 图请使用 .ascii-diagram")

        if tag == "code":
            inside_pre = any(frame.tag == "pre" for frame in self.stack)
            inside_code_wrap = any("code-wrap" in frame.classes for frame in self.stack)
            if inside_pre and not inside_code_wrap:
                self.errors.append("发现未包在 .code-wrap 中的 <pre><code> 代码块")

        self.stack.append(TagFrame(tag=tag, classes=classes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_chunks.append(data)


def class_set(value: str) -> set[str]:
    return {part for part in value.split() if part}


def check_code_wrap_blocks(html: str) -> list[str]:
    errors: list[str] = []
    for index, block in enumerate(CODE_WRAP_RE.findall(html), start=1):
        lang_match = LANG_RE.search(block)
        if not lang_match:
            errors.append(f"第 {index} 个 .code-wrap 缺少 language-xxx class")
            continue

        lang = lang_match.group(1).lower()
        if lang not in SUPPORTED_LANGS and lang not in TEXT_LIKE_LANGS:
            errors.append(f"第 {index} 个 .code-wrap 使用未支持的 language-{lang}；请用 highlight_code.py 支持的语言或映射到 text")
        has_static_highlight = TOKEN_RE.search(block) or INLINE_STYLE_RE.search(block)
        if lang not in TEXT_LIKE_LANGS and not has_static_highlight:
            errors.append(f"第 {index} 个 .code-wrap 使用 language-{lang}，但没有 tok-* 或 inline style 高亮 token")
        if not COPY_BTN_RE.search(block):
            errors.append(f"第 {index} 个 .code-wrap 缺少 .copy-btn 复制按钮")
    return errors


def check_document_chrome(parser: ReportParser) -> list[str]:
    errors: list[str] = []
    css = "\n".join(parser.style_chunks)

    if not parser.has_viewport_meta:
        errors.append("缺少 viewport meta，窄屏/分屏模式可能显示不全")
    if not css.strip():
        errors.append("缺少内嵌 <style>，不符合单文件报告模板")
        return errors

    required_css_fragments = {
        "box-sizing: border-box": "缺少全局 box-sizing，卡片/表格在窄屏下更容易溢出",
        "overflow-x: auto": "缺少横向滚动保护，宽表格/代码块/ASCII 图可能显示不全",
        "@media (max-width": "缺少窄屏响应式样式，分屏或移动端可能显示不全",
        "@media print": "缺少打印样式，彩色/黑白打印或预览可能显示不全",
    }
    compact_css = re.sub(r"\s+", " ", css)
    for fragment, message in required_css_fragments.items():
        if fragment not in compact_css:
            errors.append(message)

    if parser.has_toc:
        if not parser.has_toc_details:
            errors.append("目录 .toc 必须使用 <details class=\"toc-details\" open>，支持点击折叠/展开")
        if not parser.has_open_toc_details:
            errors.append("目录默认必须展开：<details class=\"toc-details\" open>")
        if not parser.has_toc_summary:
            errors.append("目录缺少 <summary>，无法通过点击标题折叠/展开")
        if parser.toc_link_count == 0:
            errors.append("目录缺少指向章节 id 的锚点链接")

    return errors


def validate(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(html)

    errors = parser.errors
    errors.extend(check_document_chrome(parser))
    errors.extend(check_code_wrap_blocks(html))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 html-report 单文件 HTML 的代码块和外部依赖。")
    parser.add_argument("html", help="待检查的 HTML 文件路径。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.html)
    errors = validate(path)
    if errors:
        print(f"FAIL {path}")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"PASS {path}")


if __name__ == "__main__":
    main()
