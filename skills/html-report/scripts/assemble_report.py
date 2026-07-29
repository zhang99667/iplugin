#!/usr/bin/env python3
"""按组件注册表装配离线单文件 HTML 报告。

输入文件负责语义化正文和组件结构；本脚本自动识别组件标记、解析依赖、按稳定顺序
内联 CSS/JS。重复运行会替换自己管理的块，不会叠加相同资产。
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = SKILL_ROOT / "assets" / "components"
REGISTRY_PATH = COMPONENT_ROOT / "registry.json"
STYLE_BLOCK_RE = re.compile(
    r"<!-- HTML_REPORT_COMPONENT_STYLES_START -->.*?"
    r"<!-- HTML_REPORT_COMPONENT_STYLES_END -->",
    re.DOTALL,
)
RUNTIME_BLOCK_RE = re.compile(
    r"<!-- HTML_REPORT_COMPONENT_RUNTIME_START -->.*?"
    r"<!-- HTML_REPORT_COMPONENT_RUNTIME_END -->",
    re.DOTALL,
)
CLASS_ATTR_RE = re.compile(r"\bclass\s*=\s*([\"'])(.*?)\1", re.DOTALL | re.IGNORECASE)


class ComponentError(ValueError):
    """组件注册或装配输入不满足稳定契约。"""


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ComponentError(f"{label} 必须是非空字符串数组或空数组")
    return value


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """读取并校验组件注册表的最小结构，提前拦截拼写和悬空依赖。"""

    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ComponentError(f"无法读取组件注册表 {path}: {error}") from error

    if not isinstance(registry, dict) or registry.get("schemaVersion") != 1:
        raise ComponentError("组件注册表 schemaVersion 必须为 1")
    components = registry.get("components")
    if not isinstance(components, dict) or not components:
        raise ComponentError("组件注册表 components 必须是非空对象")
    defaults = require_string_list(registry.get("defaults"), "defaults")

    for name, raw in components.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            raise ComponentError(f"非法组件名: {name!r}")
        if not isinstance(raw, dict):
            raise ComponentError(f"组件 {name} 必须是对象")
        dependencies = require_string_list(raw.get("dependencies"), f"components.{name}.dependencies")
        require_string_list(raw.get("styles"), f"components.{name}.styles")
        require_string_list(raw.get("scripts"), f"components.{name}.scripts")
        detect = raw.get("detect", {})
        if not isinstance(detect, dict):
            raise ComponentError(f"components.{name}.detect 必须是对象")
        require_string_list(detect.get("classes", []), f"components.{name}.detect.classes")
        require_string_list(detect.get("attributes", []), f"components.{name}.detect.attributes")
        for dependency in dependencies:
            if dependency not in components:
                raise ComponentError(f"组件 {name} 依赖未注册组件 {dependency}")

    for name in defaults:
        if name not in components:
            raise ComponentError(f"默认组件未注册: {name}")
    return registry


def detect_components(source_html: str, registry: dict[str, Any]) -> list[str]:
    """根据稳定 class/attribute 标记识别组件，不依赖模糊正文关键词。"""

    classes: set[str] = set()
    for _, value in CLASS_ATTR_RE.findall(source_html):
        classes.update(part for part in value.split() if part)

    detected: list[str] = []
    for name, component in registry["components"].items():
        detect = component.get("detect", {})
        class_markers = detect.get("classes", [])
        attribute_markers = detect.get("attributes", [])
        has_class = any(marker in classes for marker in class_markers)
        has_attribute = any(
            re.search(rf"\s{re.escape(marker)}(?:\s|=|>)", source_html, re.IGNORECASE)
            for marker in attribute_markers
        )
        if has_class or has_attribute:
            detected.append(name)
    return detected


def resolve_components(requested: Iterable[str], registry: dict[str, Any]) -> list[str]:
    """拓扑展开依赖；保留调用顺序，使最终单文件可复现且便于审查。"""

    components = registry["components"]
    resolved: list[str] = []
    visiting: set[str] = set()
    complete: set[str] = set()

    def visit(name: str) -> None:
        if name in complete:
            return
        if name not in components:
            raise ComponentError(f"未知组件: {name}")
        if name in visiting:
            raise ComponentError(f"组件依赖存在循环: {name}")
        visiting.add(name)
        for dependency in components[name]["dependencies"]:
            visit(dependency)
        visiting.remove(name)
        complete.add(name)
        resolved.append(name)

    for component_name in requested:
        visit(component_name)
    return resolved


def resolve_asset_path(relative_path: str) -> Path:
    """组件可以引用相邻复合模块资产，但不能逃出 html-report skill。"""

    path = (COMPONENT_ROOT / relative_path).resolve()
    try:
        path.relative_to(SKILL_ROOT)
    except ValueError as error:
        raise ComponentError(f"组件资产越出 html-report 目录: {relative_path}") from error
    if not path.is_file():
        raise ComponentError(f"组件资产不存在: {relative_path}")
    return path


def collect_assets(component_names: list[str], registry: dict[str, Any]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """读取并去重 CSS/JS；同一资产被多个依赖引用时只内联一次。"""

    styles: list[tuple[str, str]] = []
    scripts: list[tuple[str, str]] = []
    seen_styles: set[Path] = set()
    seen_scripts: set[Path] = set()
    for name in component_names:
        component = registry["components"][name]
        for relative_path in component["styles"]:
            path = resolve_asset_path(relative_path)
            if path in seen_styles:
                continue
            seen_styles.add(path)
            content = path.read_text(encoding="utf-8").rstrip()
            if "</style" in content.lower():
                raise ComponentError(f"CSS 资产包含 </style>，无法安全内联: {path}")
            styles.append((name, content))
        for relative_path in component["scripts"]:
            path = resolve_asset_path(relative_path)
            if path in seen_scripts:
                continue
            seen_scripts.add(path)
            content = path.read_text(encoding="utf-8").rstrip()
            if "</script" in content.lower():
                raise ComponentError(f"JS 资产包含 </script>，无法安全内联: {path}")
            scripts.append((name, content))
    return styles, scripts


def insert_before_closing_tag(source: str, tag: str, content: str) -> str:
    matches = list(re.finditer(rf"</{re.escape(tag)}\s*>", source, re.IGNORECASE))
    if not matches:
        raise ComponentError(f"输入 HTML 缺少 </{tag}>，无法装配组件")
    match = matches[-1]
    # 统一管理块两侧空白，保证首次装配和重复装配产出逐字一致。
    prefix = source[: match.start()].rstrip()
    suffix = source[match.start() :].lstrip()
    return prefix + "\n" + content + "\n" + suffix


def render_style_block(component_names: list[str], styles: list[tuple[str, str]]) -> str:
    names = html_lib.escape(" ".join(component_names), quote=True)
    chunks = ["<!-- HTML_REPORT_COMPONENT_STYLES_START -->", f'<style data-html-report-components="{names}">']
    for name, content in styles:
        chunks.extend((f"/* html-report component: {name} */", content))
    chunks.extend(("</style>", "<!-- HTML_REPORT_COMPONENT_STYLES_END -->"))
    return "\n".join(chunks)


def render_runtime_block(scripts: list[tuple[str, str]]) -> str:
    chunks = ["<!-- HTML_REPORT_COMPONENT_RUNTIME_START -->"]
    for name, content in scripts:
        chunks.extend((f'<script data-html-report-runtime="{name}">', content, "</script>"))
    chunks.append("<!-- HTML_REPORT_COMPONENT_RUNTIME_END -->")
    return "\n".join(chunks)


def assemble_html(
    source_html: str,
    requested: Iterable[str] = (),
    *,
    auto_detect: bool = True,
    registry: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """返回装配后的 HTML 和最终组件列表，供 CLI 与其他构建脚本复用。"""

    active_registry = registry or load_registry()
    clean_html = STYLE_BLOCK_RE.sub("", source_html)
    clean_html = RUNTIME_BLOCK_RE.sub("", clean_html)
    selected = list(active_registry["defaults"])
    if auto_detect:
        selected.extend(detect_components(clean_html, active_registry))
    selected.extend(requested)
    resolved = resolve_components(selected, active_registry)
    styles, scripts = collect_assets(resolved, active_registry)

    assembled = insert_before_closing_tag(clean_html, "head", render_style_block(resolved, styles))
    if scripts:
        assembled = insert_before_closing_tag(assembled, "body", render_runtime_block(scripts))
    return assembled, resolved


def parse_component_args(values: list[str], comma_values: str) -> list[str]:
    components = list(values)
    components.extend(part.strip() for part in comma_values.split(",") if part.strip())
    return components


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按注册表装配 html-report 的 CSS/JS 组件。")
    parser.add_argument("input", nargs="?", help="包含语义正文和组件结构的 HTML 文件。")
    parser.add_argument("-o", "--output", help="输出 HTML；默认在输入文件名后增加 _assembled。")
    parser.add_argument("--component", action="append", default=[], help="显式加入一个组件，可重复。")
    parser.add_argument("--components", default="", help="逗号分隔的显式组件列表。")
    parser.add_argument("--no-auto-detect", action="store_true", help="关闭根据 class/attribute 自动识别组件。")
    parser.add_argument("--list-components", action="store_true", help="输出注册表中的组件信息后退出。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = load_registry()
    if args.list_components:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
        return
    if not args.input:
        raise SystemExit("缺少输入 HTML；使用 --list-components 可查看组件")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(f"输入 HTML 不存在: {input_path}")
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}_assembled{input_path.suffix}")
    )
    requested = parse_component_args(args.component, args.components)
    try:
        assembled, resolved = assemble_html(
            input_path.read_text(encoding="utf-8"),
            requested,
            auto_detect=not args.no_auto_detect,
            registry=registry,
        )
    except ComponentError as error:
        raise SystemExit(f"FAIL {error}") from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(assembled, encoding="utf-8")
    print(f"PASS {output_path}")
    print("components: " + ", ".join(resolved))


if __name__ == "__main__":
    main()
