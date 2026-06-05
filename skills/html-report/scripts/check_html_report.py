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

TEXT_LIKE_LANGS = {"text", "txt", "log", "logs", "plain", "plaintext"}


@dataclass
class TagFrame:
    tag: str
    classes: set[str]


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[TagFrame] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        classes = class_set(attr_map.get("class", ""))

        if tag == "script" and attr_map.get("src"):
            self.errors.append(f"外部脚本依赖不符合单文件要求: {attr_map['src']}")
        if tag == "link" and "stylesheet" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.errors.append(f"外部样式依赖不符合单文件要求: {attr_map['href']}")

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
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break


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
        if lang not in TEXT_LIKE_LANGS and not TOKEN_RE.search(block):
            errors.append(f"第 {index} 个 .code-wrap 使用 language-{lang}，但没有 tok-* 高亮 token")
    return errors


def validate(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(html)

    errors = parser.errors
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
