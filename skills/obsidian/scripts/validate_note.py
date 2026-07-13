#!/usr/bin/env python3
"""校验 Obsidian 正文笔记的发布元数据和基础结构。"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse


FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]\n]+)\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\(([^)\n]+)\)")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
H1_RE = re.compile(r"^ {0,3}#\s+")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
SKIP_FILENAMES = {"AGENTS.md", "CLAUDE.md"}
SKIP_DIRS = {".git", ".obsidian", ".trash", ".githooks"}


@dataclass
class ValidationResult:
    """保存单个文件的错误和提示，便于严格模式统一升级提示。"""

    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def collect_markdown_files(inputs: list[Path]) -> list[Path]:
    """展开文件和目录，同时跳过 Vault 配置目录与约束文档。"""

    files: set[Path] = set()
    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() == ".md" and input_path.name not in SKIP_FILENAMES:
                files.add(input_path.resolve())
            continue
        if not input_path.is_dir():
            continue
        for path in input_path.rglob("*.md"):
            relative_parts = path.relative_to(input_path).parts
            if path.name in SKIP_FILENAMES or any(part in SKIP_DIRS for part in relative_parts):
                continue
            files.add(path.resolve())
    return sorted(files)


def extract_frontmatter(lines: list[str]) -> tuple[list[str] | None, list[str], str | None]:
    """提取文件头部 YAML；只允许在第一行开始，避免把正文分隔线误判为元数据。"""

    if not lines or lines[0].strip() != "---":
        return None, lines, "缺少文件开头的 YAML front matter"
    for index in range(1, min(len(lines), 200)):
        if lines[index].strip() == "---":
            return lines[1:index], lines[index + 1 :], None
    return None, lines, "front matter 未使用 --- 闭合"


def validate_flow_value(raw_value: str) -> str | None:
    """校验常用 YAML 标量和 flow collection 的引号、括号是否闭合。"""

    value = raw_value.strip()
    if not value or value in {"|", ">", "|-", ">-", "|+", ">+"}:
        return None

    # YAML plain scalar 不能直接包含冒号加空格；有此内容时必须整体加引号。
    if value[0] not in {"'", '"', "[", "{"} and ": " in value:
        return f"front matter 含冒号的标量必须加引号：{raw_value}"

    quote: str | None = None
    escaped = False
    stack: list[str] = []
    pairs = {"]": "[", "}": "{"}
    for character in value:
        if escaped:
            escaped = False
            continue
        if quote == '"' and character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character in "[{":
            stack.append(character)
        elif character in "]}":
            if not stack or stack.pop() != pairs[character]:
                return f"front matter flow value 括号不匹配：{raw_value}"

    if quote:
        return f"front matter 引号未闭合：{raw_value}"
    if stack:
        return f"front matter flow value 未闭合：{raw_value}"
    return None


def parse_fields(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    """解析发布契约需要的顶层字段，不尝试支持与校验无关的嵌套 YAML。"""

    fields: dict[str, str] = {}
    errors: list[str] = []
    for line in lines:
        if "\t" in line:
            errors.append("front matter 不能使用制表符缩进")
            continue
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
            continue
        match = FIELD_RE.match(line)
        if not match:
            errors.append(f"无法解析 front matter 行：{line}")
            continue
        key, raw_value = match.groups()
        flow_error = validate_flow_value(raw_value)
        if flow_error:
            errors.append(flow_error)
        if key in fields:
            errors.append(f"front matter 字段重复：{key}")
            continue
        fields[key] = raw_value.strip().strip('"').strip("'")
    return fields, errors


def is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return not value.strip() or normalized in {"...", "todo", "tbd"} or bool(PLACEHOLDER_RE.search(value))


def valid_tags(raw: str) -> bool:
    if not (raw.startswith("[") and raw.endswith("]")):
        return False
    tags = [tag.strip().strip('"').strip("'") for tag in raw[1:-1].split(",")]
    return bool(tags) and all(tags)


def visible_body_lines(lines: list[str]) -> list[tuple[int, str]]:
    """按 CommonMark 围栏规则排除代码块，保留原始行号供结构检查使用。"""

    visible: list[tuple[int, str]] = []
    fence_character: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if match:
            marker, remainder = match.groups()
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
                continue
            if marker[0] == fence_character and len(marker) >= fence_length and not remainder.strip():
                fence_character = None
                fence_length = 0
            continue
        if fence_character is None:
            visible.append((index, line))
    return visible


def scan_body_structure(lines: list[str]) -> tuple[list[str], list[str]]:
    """检查正文起始层级和固定收尾，区分错误与严格模式提示。"""

    errors: list[str] = []
    warnings: list[str] = []
    visible = [(index, line) for index, line in visible_body_lines(lines) if line.strip()]
    if not visible:
        return errors, warnings

    if not re.match(r"^ {0,3}##\s+", visible[0][1]):
        errors.append("正文必须从二级标题开始")
    if any(H1_RE.match(line) for _, line in visible):
        errors.append("正文不能包含一级标题，文件名已承担一级标题")
    for position, (_, line) in enumerate(visible[1:], start=1):
        if re.match(r"^ {0,3}=+\s*$", line) and not HEADING_RE.match(visible[position - 1][1]):
            errors.append("正文不能包含 Setext 一级标题，文件名已承担一级标题")
            break

    related_positions = [position for position, (_, line) in enumerate(visible) if line.strip() == "## 相关笔记"]
    if not related_positions:
        warnings.append("缺少 ## 相关笔记")
        return errors, warnings
    if len(related_positions) > 1:
        errors.append("## 相关笔记 只能出现一次")
        return errors, warnings

    related_position = related_positions[0]
    if related_position == 0 or visible[related_position - 1][1].strip() != "---":
        errors.append("## 相关笔记 前必须使用 --- 分隔")
    if not any(
        re.match(r"^ {0,3}##\s+", line) and line.strip() != "## 相关笔记"
        for _, line in visible[:related_position]
    ):
        errors.append("## 相关笔记 前至少需要一个正文二级章节")
    if any(HEADING_RE.match(line) for _, line in visible[related_position + 1 :]):
        errors.append("## 相关笔记 必须是最后一个标题")
    return errors, warnings


def strip_inline_code(line: str) -> str:
    """移除行内代码，避免把 Markdown 或 Obsidian 语法示例当成真实附件。"""

    return INLINE_CODE_RE.sub("", line)


def normalize_image_target(raw_target: str, *, obsidian: bool) -> str | None:
    """提取图片路径并忽略尺寸、锚点、标题和远程 URL 等非文件部分。"""

    target = raw_target.strip()
    if obsidian:
        target = target.split("|", 1)[0].split("#", 1)[0].strip()
    elif target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")].strip()
    else:
        # Markdown 图片允许在路径后附加标题；本仓库要求含空格路径使用 <...> 包裹。
        target = target.split(maxsplit=1)[0]

    target = unquote(target)
    if not target or target.startswith("#"):
        return None
    parsed = urlparse(target)
    if parsed.scheme or target.startswith("//"):
        return None
    return target


def referenced_images(lines: list[str]) -> list[str]:
    """收集正文中的本地图片引用；Obsidian 非图片 embed 不参与本门禁。"""

    targets: list[str] = []
    for _, raw_line in visible_body_lines(lines):
        line = strip_inline_code(raw_line)
        for match in OBSIDIAN_EMBED_RE.finditer(line):
            target = normalize_image_target(match.group(1), obsidian=True)
            if target and Path(target).suffix.lower() in IMAGE_SUFFIXES:
                targets.append(target)
        for match in MARKDOWN_IMAGE_RE.finditer(line):
            target = normalize_image_target(match.group(1), obsidian=False)
            if target:
                targets.append(target)
    return targets


def validate_local_images(note_path: Path, body: list[str]) -> list[str]:
    """验证本地图片存在，并确保 SVG 至少是可解析 XML。"""

    errors: list[str] = []
    checked: set[Path] = set()
    for target in referenced_images(body):
        raw_path = Path(target).expanduser()
        image_path = raw_path if raw_path.is_absolute() else note_path.parent / raw_path
        image_path = image_path.resolve()
        if image_path in checked:
            continue
        checked.add(image_path)
        if not image_path.is_file():
            errors.append(f"本地图片不存在：{target}")
            continue
        if image_path.suffix.lower() != ".svg":
            continue
        try:
            root = ET.parse(image_path).getroot()
            if root.tag.split("}")[-1].lower() != "svg":
                errors.append(f"文件扩展名为 .svg，但根元素不是 svg：{target}")
        except (ET.ParseError, OSError) as exc:
            errors.append(f"SVG 无法解析：{target}（{exc}）")
    return errors


def validate_file(path: Path) -> ValidationResult:
    result = ValidationResult(path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result.errors.append("文件不是有效 UTF-8")
        return result

    frontmatter, body, error = extract_frontmatter(text.splitlines())
    if error:
        result.errors.append(error)
        return result

    fields, parse_errors = parse_fields(frontmatter or [])
    result.errors.extend(parse_errors)

    publish = fields.get("publish")
    if publish not in {"true", "false"}:
        result.errors.append("publish 必须是 true 或 false")

    note_type = fields.get("type")
    if note_type not in {"post", "note"}:
        result.errors.append("type 必须是 post 或 note")

    if note_type == "post":
        for key in ("title", "date", "summary", "tags"):
            value = fields.get(key, "")
            if is_placeholder(value):
                result.errors.append(f"type: post 要求非占位的 {key}")
        raw_date = fields.get("date", "")
        if raw_date and not PLACEHOLDER_RE.search(raw_date):
            if not DATE_RE.match(raw_date):
                result.errors.append("date 必须使用 YYYY-MM-DD")
            else:
                try:
                    date.fromisoformat(raw_date)
                except ValueError:
                    result.errors.append("date 不是有效日历日期")
        raw_tags = fields.get("tags", "")
        if raw_tags and not PLACEHOLDER_RE.search(raw_tags) and not valid_tags(raw_tags):
            result.errors.append("tags 必须是非空行内数组，例如 [AI, Agent]")

    if note_type == "note" and is_placeholder(fields.get("topic", "")):
        result.errors.append("type: note 要求非占位的 topic")

    if not any(line.strip() for line in body):
        result.errors.append("正文不能为空")

    structure_errors, structure_warnings = scan_body_structure(body)
    result.errors.extend(structure_errors)
    result.warnings.extend(structure_warnings)
    result.errors.extend(validate_local_images(path, body))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Obsidian 笔记 front matter 与基础结构。")
    parser.add_argument("paths", nargs="+", type=Path, help="待检查的 Markdown 文件或目录")
    parser.add_argument("--strict", action="store_true", help="把结构提示也视为失败")
    args = parser.parse_args()

    files = collect_markdown_files(args.paths)
    if not files:
        print("未找到可校验的 Markdown 笔记。", file=sys.stderr)
        return 2

    failed = False
    for path in files:
        result = validate_file(path)
        for message in result.errors:
            print(f"ERROR {path}: {message}", file=sys.stderr)
        for message in result.warnings:
            print(f"WARN  {path}: {message}", file=sys.stderr)
        if result.errors or (args.strict and result.warnings):
            failed = True

    if failed:
        return 1
    print(f"Obsidian note validation passed: {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
