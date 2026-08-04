#!/usr/bin/env python3
"""校验 html-report 生成的单文件 HTML。

这个脚本只做确定性结构检查，不评价内容质量或视觉审美。
"""

from __future__ import annotations

import argparse
import html as html_lib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


CODE_WRAP_RE = re.compile(r'<div\b[^>]*class=["\'][^"\']*\bcode-wrap\b[^"\']*["\'][^>]*>.*?</div>', re.DOTALL)
DIFF_VIEWER_RE = re.compile(r'<section\b[^>]*class=["\'][^"\']*\bdiff-viewer\b[^"\']*["\'][^>]*>.*?</section>', re.DOTALL)
CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
DIFF_META_ROW_RE = re.compile(r'<tr\b[^>]*class=["\'][^"\']*\bdiff-meta\b[^"\']*["\'][^>]*>.*?</tr>', re.DOTALL)
LANG_RE = re.compile(r'\blanguage-([a-zA-Z0-9_-]+)\b')
TOKEN_SPAN_RE = re.compile(r'<span\b[^>]*\bclass=["\'][^"\']*\b(tok-[a-zA-Z0-9_-]+)\b[^"\']*["\'][^>]*>.*?</span>', re.DOTALL)
INLINE_STYLE_RE = re.compile(r'<span\b[^>]*\bstyle=["\'][^"\']+["\']', re.DOTALL)
COPY_BTN_RE = re.compile(r'<button\b[^>]*class=["\'][^"\']*\bcopy-btn\b[^"\']*["\']', re.DOTALL)
RAW_INLINE_CODE_RE = re.compile(r'`[^`\n]+`')
TAG_RE = re.compile(r"<[^>]+>")
RAW_UNIFIED_DIFF_RE = re.compile(
    r"(?m)(?:^|\n)(?:diff --git [^\n]+\n)?--- [^\n]+\n\+\+\+ [^\n]+\n@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@"
)
HUNK_MARKER_RE = re.compile(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")
EMBEDDED_REVIEW_DATA_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']qaEmbeddedReviewData["\'])(?=[^>]*\bdata-qa-review-data(?:\s|=|>))[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
EMBEDDED_REVIEW_START_RE = re.compile(r"<!--\s*QA_EMBEDDED_REVIEW_START:[\s\S]*?-->", re.IGNORECASE)
EMBEDDED_REVIEW_END_RE = re.compile(r"<!--\s*QA_EMBEDDED_REVIEW_END\s*-->", re.IGNORECASE)
EMBEDDED_REVIEW_RECEIPT_DATA_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']qaEmbeddedReviewReceipt["\'])'
    r'(?=[^>]*\bdata-qa-review-receipt(?:\s|=|>))[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
EMBEDDED_REVIEW_RECEIPT_START_RE = re.compile(
    r"<!--\s*QA_AGENT_REVIEW_RECEIPT_START:[\s\S]*?-->", re.IGNORECASE
)
EMBEDDED_REVIEW_RECEIPT_END_RE = re.compile(
    r"<!--\s*QA_AGENT_REVIEW_RECEIPT_END\s*-->", re.IGNORECASE
)
ANNOTATION_MODE_MARKER_RE = re.compile(
    r"<!--\s*QA_ANNOTATION_(?:HTML_START:|SCRIPT_START\s*-->)",
    re.IGNORECASE,
)
ANNOTATION_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*\bdata-qa-script(?:\s|=|>)", re.IGNORECASE)
ANNOTATION_UI_TAG_RE = re.compile(r"<(?:button|aside|div)\b[^>]*\bdata-qa-ui(?:\s|=|>)", re.IGNORECASE)
ANNOTATION_CSS_ASSET_RE = re.compile(
    r"/\*\s*QA_ANNOTATION_CSS_START:[\s\S]*?QA_ANNOTATION_CSS_END\s*\*/",
    re.IGNORECASE,
)
ANNOTATION_ASSET_BLOCK_RE = re.compile(
    r"(?:<!--\s*QA_ANNOTATION_HTML_START:[\s\S]*?QA_ANNOTATION_HTML_END\s*-->"
    r"|<!--\s*QA_ANNOTATION_SCRIPT_START\s*-->\s*<script\b[^>]*\bdata-qa-script(?:\s|=|>)[\s\S]*?</script>\s*<!--\s*QA_ANNOTATION_SCRIPT_END\s*-->)",
    re.IGNORECASE,
)
REVIEW_WORKSPACE_SECTION_RE = re.compile(
    r'<section\b(?=[^>]*\bclass=["\'][^"\']*\breview-workspace\b[^"\']*["\'])'
    r'(?=[^>]*\bdata-review-workspace(?:\s|=|>))[^>]*>(.*?)</section>',
    re.DOTALL | re.IGNORECASE,
)
REVIEW_WORKSPACE_DATA_RE = re.compile(
    r'<script\b(?=[^>]*\btype=["\']application/json["\'])'
    r'(?=[^>]*\bdata-review-workspace-data(?:\s|=|>))[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
REVIEW_WORKSPACE_RUNTIME_RE = re.compile(
    r'<script\b(?=[^>]*\bdata-review-workspace-runtime(?:\s|=|>))[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
COMPONENT_STYLE_RE = re.compile(
    r'<style\b[^>]*\bdata-html-report-components=["\']([^"\']*)["\'][^>]*>(.*?)</style>',
    re.DOTALL | re.IGNORECASE,
)
COMPONENT_RUNTIME_RE = re.compile(
    r'<script\b[^>]*\bdata-html-report-runtime=["\']([^"\']+)["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
SORTABLE_TABLE_RE = re.compile(
    r'<table\b[^>]*class=["\'][^"\']*\bsortable\b[^"\']*["\'][^>]*>.*?</table>',
    re.DOTALL | re.IGNORECASE,
)
FILE_LOCATION_LINK_RE = re.compile(
    r'<a\b(?=[^>]*\bclass=["\'][^"\']*\bfile-location\b[^"\']*["\'])'
    r'([^>]*)>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)

TEXT_LIKE_LANGS = {"markdown", "text", "txt", "log", "logs", "plain", "plaintext"}
MEDIA_EXTENSIONS = {".apng", ".avif", ".gif", ".jpeg", ".jpg", ".m4v", ".mov", ".mp4", ".ogg", ".ogv", ".png", ".svg", ".webm", ".webp"}


def load_supported_langs() -> set[str]:
    """从高亮脚本读取语言白名单，避免校验脚本维护第二份旧清单。"""

    highlighter_path = Path(__file__).with_name("highlight_code.py")
    spec = importlib.util.spec_from_file_location("html_report_highlight_code", highlighter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载高亮脚本语言清单: {highlighter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.SUPPORTED_LANGS)


SUPPORTED_LANGS = load_supported_langs()


def load_component_registry() -> dict[str, Any]:
    """读取装配器注册表，让生成和校验共用同一份组件依赖真源。"""

    path = Path(__file__).resolve().parents[1] / "assets" / "components" / "registry.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"无法读取 html-report 组件注册表: {path}") from error
    if not isinstance(registry, dict) or not isinstance(registry.get("components"), dict):
        raise RuntimeError(f"html-report 组件注册表结构错误: {path}")
    return registry


COMPONENT_REGISTRY = load_component_registry()


@dataclass
class TagFrame:
    tag: str
    classes: set[str]
    attrs: dict[str, str]


@dataclass
class MediaResource:
    tag: str
    src: str
    line: int


@dataclass
class MediaItem:
    tag: str
    attrs: dict[str, str]
    line: int
    figure_index: int | None
    source_count: int = 0
    lightbox_href: str = ""
    lightbox_enabled: bool = False


@dataclass
class FigureState:
    index: int
    attrs: dict[str, str]
    classes: set[str]
    media_indices: list[int] = field(default_factory=list)
    has_figcaption: bool = False
    figcaption_text_chunks: list[str] = field(default_factory=list)

    @property
    def figcaption_text(self) -> str:
        return " ".join(chunk.strip() for chunk in self.figcaption_text_chunks if chunk.strip())


@dataclass
class TabsState:
    """保存单个 Tabs 根节点内的 ARIA 关系，避免不同实例互相掩盖错误。"""

    line: int
    attrs: dict[str, str]
    tablist_count: int = 0
    tabs: list[dict[str, str]] = field(default_factory=list)
    panels: list[dict[str, str]] = field(default_factory=list)


class TabsMarkupParser(HTMLParser):
    """逐实例收集 Tabs 结构；只关心原生属性，不依赖脆弱的嵌套标签正则。"""

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.instances: list[TabsState] = []
        self.active: list[tuple[int, TabsState]] = []

    @staticmethod
    def normalized_attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: value or "" for name, value in attrs}

    def collect(self, attrs: dict[str, str]) -> None:
        role = attrs.get("role")
        for _, instance in self.active:
            if role == "tablist":
                instance.tablist_count += 1
            elif role == "tab":
                instance.tabs.append(attrs)
            elif role == "tabpanel":
                instance.panels.append(attrs)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = self.normalized_attrs(attrs)
        classes = set(attr_map.get("class", "").split())
        if "report-tabs" in classes:
            instance = TabsState(line=self.getpos()[0], attrs=attr_map)
            self.instances.append(instance)
            self.active.append((self.depth, instance))
        self.collect(attr_map)
        self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.collect(self.normalized_attrs(attrs))

    def handle_endtag(self, tag: str) -> None:
        self.depth = max(0, self.depth - 1)
        self.active = [(depth, instance) for depth, instance in self.active if depth != self.depth]


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[TagFrame] = []
        self.errors: list[str] = []
        self.in_style = False
        self.style_chunks: list[str] = []
        self.has_viewport_meta = False
        self.has_toc = False
        self.has_toc_title = False
        self.has_toc_toggle = False
        self.has_toc_details = False
        self.toc_link_count = 0
        self.raw_inline_code_samples: list[str] = []
        self.has_diff_viewer = False
        self.has_non_viewer_diff_card = False
        self.regular_table_lines: list[int] = []
        self.media_items: list[MediaItem] = []
        self.media_resources: list[MediaResource] = []
        self.figures: list[FigureState] = []
        self.figure_stack: list[FigureState] = []
        self.video_media_stack: list[int] = []
        self.figcaption_depth = 0
        self.next_figure_index = 1
        self.block_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        classes = class_set(attr_map.get("class", ""))
        inside_toc = "toc" in classes or any("toc" in frame.classes for frame in self.stack)
        inside_main = tag == "main" or any(frame.tag == "main" for frame in self.stack)
        current_figure = self.figure_stack[-1] if self.figure_stack else None

        if tag == "meta" and attr_map.get("name", "").lower() == "viewport":
            self.has_viewport_meta = True

        if tag == "style":
            self.in_style = True

        if inside_main and attr_map.get("data-block-id"):
            self.block_ids.append(attr_map["data-block-id"])

        if tag == "figure":
            figure = FigureState(index=self.next_figure_index, attrs=attr_map, classes=classes)
            self.next_figure_index += 1
            self.figure_stack.append(figure)
            current_figure = figure
        if tag == "figcaption" and current_figure:
            current_figure.has_figcaption = True
            self.figcaption_depth += 1

        line, _ = self.getpos()
        if tag == "table" and "diff-table" not in classes:
            self.regular_table_lines.append(line)
            inside_table_wrap = any("table-wrap" in frame.classes for frame in self.stack)
            if not inside_table_wrap:
                self.errors.append(f"第 {line} 行普通表格未包在 .table-wrap 中，窄屏滚动和统一网格线无法保证")

        if tag in {"img", "video"}:
            lightbox_frame = next(
                (
                    frame
                    for frame in reversed(self.stack)
                    if frame.tag == "a" and "image-lightbox-trigger" in frame.classes
                ),
                None,
            )
            media = MediaItem(
                tag=tag,
                attrs=attr_map,
                line=line,
                figure_index=current_figure.index if current_figure else None,
                lightbox_href=lightbox_frame.attrs.get("href", "") if lightbox_frame else "",
                lightbox_enabled=bool(lightbox_frame and "data-image-lightbox" in lightbox_frame.attrs),
            )
            self.media_items.append(media)
            media_index = len(self.media_items) - 1
            if current_figure:
                current_figure.media_indices.append(media_index)
            if attr_map.get("src"):
                self.media_resources.append(MediaResource(tag=tag, src=attr_map["src"], line=line))
            if tag == "video":
                self.video_media_stack.append(media_index)
                if attr_map.get("poster"):
                    self.media_resources.append(MediaResource(tag="video poster", src=attr_map["poster"], line=line))
        elif tag == "source" and self.video_media_stack:
            if attr_map.get("src"):
                self.media_resources.append(MediaResource(tag="source", src=attr_map["src"], line=line))
                self.media_items[self.video_media_stack[-1]].source_count += 1
        elif tag == "a" and attr_map.get("href") and is_media_url(attr_map["href"]):
            self.media_resources.append(MediaResource(tag="a", src=attr_map["href"], line=line))

        if tag == "script" and attr_map.get("src"):
            self.errors.append(f"外部脚本依赖不符合单文件要求: {attr_map['src']}")
        if tag == "link" and "stylesheet" in attr_map.get("rel", "").lower() and attr_map.get("href"):
            self.errors.append(f"外部样式依赖不符合单文件要求: {attr_map['href']}")

        if "toc" in classes:
            self.has_toc = True
        if inside_toc and "toc-title" in classes:
            self.has_toc_title = True
        if inside_toc and tag == "button" and "toc-toggle" in classes:
            self.has_toc_toggle = True
        if tag == "details" and (inside_toc or "toc-details" in classes):
            self.has_toc_details = True
        if tag == "a" and inside_toc and attr_map.get("href", "").startswith("#"):
            self.toc_link_count += 1
        if "diff-card" in classes:
            if "diff-viewer" in classes:
                self.has_diff_viewer = True
            else:
                self.has_non_viewer_diff_card = True

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

        self.stack.append(TagFrame(tag=tag, classes=classes, attrs=attr_map))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False
        if tag == "figcaption" and self.figcaption_depth:
            self.figcaption_depth -= 1
        if tag == "video" and self.video_media_stack:
            self.video_media_stack.pop()
        if tag == "figure" and self.figure_stack:
            self.figures.append(self.figure_stack.pop())
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_chunks.append(data)
            return

        if self.figcaption_depth and self.figure_stack:
            self.figure_stack[-1].figcaption_text_chunks.append(data)

        # Diff/Workspace 源码也可能合法包含反引号，不能当成正文 Markdown 漏渲染。
        if any(
            frame.tag in {"code", "pre", "script", "style"}
            or "diff-code" in frame.classes
            or "rw-src" in frame.classes
            for frame in self.stack
        ):
            return

        for match in RAW_INLINE_CODE_RE.findall(data):
            if len(self.raw_inline_code_samples) < 3:
                self.raw_inline_code_samples.append(match)


def class_set(value: str) -> set[str]:
    return {part for part in value.split() if part}


def is_media_url(url: str) -> bool:
    parsed = urlparse(html_lib.unescape(url))
    path = parsed.path.lower()
    return any(path.endswith(extension) for extension in MEDIA_EXTENSIONS)


def local_resource_path(url: str, report_path: Path) -> Path | None:
    parsed = urlparse(html_lib.unescape(url))
    scheme = parsed.scheme.lower()
    if scheme in {"about", "blob", "data", "http", "https", "idea", "javascript", "mailto"}:
        return None
    if parsed.netloc:
        return None
    if scheme == "file":
        return Path(unquote(parsed.path))
    if scheme:
        return None

    raw_path = unquote(parsed.path)
    if not raw_path or raw_path.startswith("#"):
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = report_path.parent / candidate
    return candidate


def fragment_text(fragment: str) -> str:
    return html_lib.unescape(TAG_RE.sub("", fragment))


def has_class(fragment: str, class_name: str) -> bool:
    return bool(re.search(rf'\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\']', fragment))


def css_rule_has(css: str, selector_fragments: tuple[str, ...], declaration_fragments: tuple[str, ...]) -> bool:
    """检查同一条 CSS 规则同时包含指定选择器和声明，避免跨规则误判。"""

    for selectors, body in CSS_RULE_RE.findall(css):
        compact_selectors = re.sub(r"\s+", " ", selectors)
        compact_body = re.sub(r"\s+", " ", body)
        if all(fragment in compact_selectors for fragment in selector_fragments) and all(
            fragment in compact_body for fragment in declaration_fragments
        ):
            return True
    return False


def html_class_tokens(source_html: str) -> set[str]:
    """提取 class token，供注册表检测和组件契约检查复用。"""

    tokens: set[str] = set()
    for match in re.finditer(r'\bclass\s*=\s*(["\'])(.*?)\1', source_html, re.DOTALL | re.IGNORECASE):
        tokens.update(part for part in match.group(2).split() if part)
    return tokens


def detect_registered_components(source_html: str) -> list[str]:
    classes = html_class_tokens(source_html)
    detected: list[str] = []
    for name, component in COMPONENT_REGISTRY["components"].items():
        detect = component.get("detect", {})
        has_class = any(marker in classes for marker in detect.get("classes", []))
        has_attribute = any(
            re.search(rf"\s{re.escape(marker)}(?:\s|=|>)", source_html, re.IGNORECASE)
            for marker in detect.get("attributes", [])
        )
        if has_class or has_attribute:
            detected.append(name)
    return detected


def check_component_bundle(source_html: str) -> list[str]:
    """校验统一装配器写入的组件声明、依赖和 runtime 唯一性。"""

    errors: list[str] = []
    style_blocks = COMPONENT_STYLE_RE.findall(source_html)
    runtime_blocks = COMPONENT_RUNTIME_RE.findall(source_html)
    has_managed_marker = "HTML_REPORT_COMPONENT_STYLES_START" in source_html
    if not style_blocks and not has_managed_marker:
        return errors  # 兼容重构前生成的历史报告；新报告由 SKILL.md 强制走装配器。
    if len(style_blocks) != 1:
        return ["组件化报告必须且只能有一个 data-html-report-components 样式块"]

    declared = style_blocks[0][0].split()
    declared_set = set(declared)
    components = COMPONENT_REGISTRY["components"]
    if len(declared) != len(declared_set):
        errors.append("data-html-report-components 包含重复组件")
    for name in declared:
        if name not in components:
            errors.append(f"data-html-report-components 声明未知组件: {name}")
            continue
        for dependency in components[name].get("dependencies", []):
            if dependency not in declared_set:
                errors.append(f"组件 {name} 缺少依赖 {dependency}")
        if components[name].get("styles") and f"html-report component: {name}" not in style_blocks[0][1]:
            errors.append(f"组件 {name} 已声明但样式块缺少对应资产标记")

    for detected in detect_registered_components(source_html):
        if detected not in declared_set:
            errors.append(f"页面使用组件 {detected}，但装配声明未包含它")

    runtime_counts: dict[str, int] = {}
    for name, runtime in runtime_blocks:
        runtime_counts[name] = runtime_counts.get(name, 0) + 1
        if name not in components:
            errors.append(f"页面内联未知组件 runtime: {name}")
        if not runtime.strip():
            errors.append(f"组件 runtime {name} 为空")
        if name in components and components[name].get("scripts"):
            # 所有标准 runtime 都使用同一命名标记，校验时可统一发现截断或手工漏贴。
            marker_name = name.replace("-", "_").upper()
            for suffix in ("START", "END"):
                marker = f"HTML_REPORT_{marker_name}_RUNTIME_{suffix}"
                if marker not in runtime:
                    errors.append(f"组件 runtime {name} 缺少完整性标记 {marker}")
    for name in declared:
        if name not in components or not components[name].get("scripts"):
            continue
        count = runtime_counts.get(name, 0)
        if count != 1:
            errors.append(f"组件 {name} 必须且只能内联一个 data-html-report-runtime，当前 {count} 个")
    for name, count in runtime_counts.items():
        if count > 1:
            errors.append(f"组件 runtime {name} 重复内联 {count} 次")
    return errors


def check_behavior_component_markup(source_html: str) -> list[str]:
    """检查交互组件的语义结构，使无障碍和无 JS 回退不依赖模型临场发挥。"""

    errors: list[str] = []
    for index, table in enumerate(SORTABLE_TABLE_RE.findall(source_html), start=1):
        if "sort-button" not in html_class_tokens(table):
            errors.append(f"第 {index} 个可排序表格表头缺少 .sort-button")
        if "sort-arrow" not in html_class_tokens(table):
            errors.append(f"第 {index} 个可排序表格表头缺少 .sort-arrow 状态槽")

    tabs_parser = TabsMarkupParser()
    tabs_parser.feed(source_html)
    for index, instance in enumerate(tabs_parser.instances, start=1):
        prefix = f"第 {index} 个标签页（第 {instance.line} 行）"
        if "data-tabs" not in instance.attrs:
            errors.append(f"{prefix}根节点缺少 data-tabs 初始化标记")
        if instance.tablist_count != 1:
            errors.append(f"{prefix}必须且只能包含一个 role=tablist，当前 {instance.tablist_count} 个")
        if not instance.tabs:
            errors.append(f"{prefix}缺少 role=tab")
        if not instance.panels:
            errors.append(f"{prefix}缺少 role=tabpanel")

        tab_ids = [tab.get("id", "") for tab in instance.tabs]
        panel_ids = [panel.get("id", "") for panel in instance.panels]
        if any(not tab_id for tab_id in tab_ids):
            errors.append(f"{prefix}每个 role=tab 都必须有 id")
        if any(not panel_id for panel_id in panel_ids):
            errors.append(f"{prefix}每个 role=tabpanel 都必须有 id")
        if len(set(filter(None, tab_ids))) != len(list(filter(None, tab_ids))):
            errors.append(f"{prefix}包含重复的 tab id")
        if len(set(filter(None, panel_ids))) != len(list(filter(None, panel_ids))):
            errors.append(f"{prefix}包含重复的 tabpanel id")

        panel_by_id = {panel_id: panel for panel_id, panel in zip(panel_ids, instance.panels) if panel_id}
        tab_by_id = {tab_id: tab for tab_id, tab in zip(tab_ids, instance.tabs) if tab_id}
        for tab in instance.tabs:
            tab_id = tab.get("id", "")
            panel_id = tab.get("aria-controls", "")
            if not panel_id:
                errors.append(f"{prefix} tab {tab_id or '<missing-id>'} 缺少 aria-controls")
                continue
            panel = panel_by_id.get(panel_id)
            if panel is None:
                errors.append(f"{prefix} tab {tab_id or '<missing-id>'} 的 aria-controls 未指向本组件 tabpanel: {panel_id}")
            elif tab_id and panel.get("aria-labelledby", "") != tab_id:
                errors.append(f"{prefix} tab {tab_id} 与 tabpanel {panel_id} 的 ARIA 引用不互为对应")
        for panel in instance.panels:
            panel_id = panel.get("id", "")
            tab_id = panel.get("aria-labelledby", "")
            if not tab_id:
                errors.append(f"{prefix} tabpanel {panel_id or '<missing-id>'} 缺少 aria-labelledby")
                continue
            tab = tab_by_id.get(tab_id)
            if tab is None:
                errors.append(f"{prefix} tabpanel {panel_id or '<missing-id>'} 的 aria-labelledby 未指向本组件 tab: {tab_id}")
            elif panel_id and tab.get("aria-controls", "") != panel_id:
                errors.append(f"{prefix} tabpanel {panel_id} 与 tab {tab_id} 的 ARIA 引用不互为对应")
    return errors


def check_file_location_links(source_html: str) -> list[str]:
    """IDE 跳转显示文件名和行范围，完整路径只放在 href/title。"""

    errors: list[str] = []
    for index, (attributes, body) in enumerate(FILE_LOCATION_LINK_RE.findall(source_html), start=1):
        label = fragment_text(body)
        href_match = re.search(r'\bhref=["\']([^"\']+)["\']', attributes, re.IGNORECASE)
        title_match = re.search(r'\btitle=["\']([^"\']+)["\']', attributes, re.IGNORECASE)
        href = html_lib.unescape(href_match.group(1)) if href_match else ""
        title = html_lib.unescape(title_match.group(1)) if title_match else ""
        # 文件名可以包含空格，但可见路径仍限制为文件名或一级父目录。
        label_match = re.fullmatch(r"([^/<>\r\n]+(?:/[^/<>\r\n]+)?):(\d+)(?:-(\d+))?", label)
        if not label_match:
            errors.append(
                f"第 {index} 个文件定位链接显示文本应为 文件名:行号-行号；同名时最多增加一级父目录，当前为 {label!r}"
            )
        parsed_href = urlparse(href)
        query = parse_qs(parsed_href.query)
        href_file = query.get("file", [""])[0]
        href_line = query.get("line", [""])[0]
        if parsed_href.scheme != "idea" or parsed_href.netloc != "open" or not href_file or not href_line.isdigit():
            errors.append(f"第 {index} 个文件定位链接缺少 idea:// 文件和起始行参数")
        elif not Path(href_file).is_absolute():
            errors.append(f"第 {index} 个文件定位链接 href 必须使用绝对路径")
        title_match_value = re.fullmatch(r"(.+):(\d+)(?:-(\d+))?", title)
        if not title_match_value or not Path(title_match_value.group(1)).is_absolute():
            errors.append(f"第 {index} 个文件定位链接 title 必须保留完整路径和行号")
            continue
        title_file, title_start, title_end = title_match_value.groups()
        if href_file and href_file != title_file:
            errors.append(f"第 {index} 个文件定位链接 href 与 title 的完整路径不一致")
        if href_line.isdigit() and href_line != title_start:
            errors.append(f"第 {index} 个文件定位链接 href 起始行与 title 不一致")
        if label_match:
            label_path, label_start, label_end = label_match.groups()
            expected_paths = {Path(title_file).name}
            parent_name = Path(title_file).parent.name
            if parent_name:
                expected_paths.add(f"{parent_name}/{Path(title_file).name}")
            if label_path not in expected_paths:
                errors.append(f"第 {index} 个文件定位链接短标签与完整路径不一致")
            if (label_start, label_end) != (title_start, title_end):
                errors.append(f"第 {index} 个文件定位链接短标签与 title 行范围不一致")
    return errors


def looks_like_unified_diff(text: str) -> bool:
    return bool(RAW_UNIFIED_DIFF_RE.search(text) or ("diff --git " in text and HUNK_MARKER_RE.search(text)))


def check_code_wrap_blocks(html: str, css: str) -> list[str]:
    errors: list[str] = []
    compact_css = re.sub(r"\s+", " ", css)
    if CODE_WRAP_RE.search(html) and not css_rule_has(css, (".code-wrap pre",), ("overflow-x: auto",)):
        errors.append("报告包含代码块，但 .code-wrap pre 缺少 overflow-x: auto 横向滚动保护")
    for index, block in enumerate(CODE_WRAP_RE.findall(html), start=1):
        lang_match = LANG_RE.search(block)
        if not lang_match:
            errors.append(f"第 {index} 个 .code-wrap 缺少 language-xxx class")
            continue

        lang = lang_match.group(1).lower()
        if lang not in SUPPORTED_LANGS and lang not in TEXT_LIKE_LANGS:
            errors.append(f"第 {index} 个 .code-wrap 使用未支持的 language-{lang}；请用 highlight_code.py 支持的语言或映射到 text")
        if looks_like_unified_diff(fragment_text(block)):
            errors.append(
                f"第 {index} 个 .code-wrap 包含 raw unified diff；真实 diff 必须用 highlight_code.py --lang diff --diff-view 生成 .diff-card.diff-viewer"
            )
            continue
        if lang == "diff":
            errors.append(f"第 {index} 个 .code-wrap 使用 language-diff；真实 diff 必须用 highlight_code.py --lang diff --diff-view 生成 .diff-card.diff-viewer")
            continue
        token_classes = set(TOKEN_SPAN_RE.findall(block))
        has_inline_style = bool(INLINE_STYLE_RE.search(block))
        has_static_highlight = bool(token_classes) or has_inline_style
        if lang not in TEXT_LIKE_LANGS and not has_static_highlight:
            errors.append(f"第 {index} 个 .code-wrap 使用 language-{lang}，但没有 tok-* 或 inline style 高亮 token")
        if token_classes:
            missing_classes = sorted(class_name for class_name in token_classes if f".{class_name}" not in compact_css)
            if missing_classes:
                errors.append(f"第 {index} 个 .code-wrap 使用 {', '.join(missing_classes)}，但 CSS 缺少对应 token 样式，代码会显示成未高亮")
        if not COPY_BTN_RE.search(block):
            errors.append(f"第 {index} 个 .code-wrap 缺少 .copy-btn 复制按钮")
    return errors


def check_diff_viewer_blocks(html: str, css: str) -> list[str]:
    errors: list[str] = []
    blocks = DIFF_VIEWER_RE.findall(html)
    if not blocks:
        return errors

    for index, block in enumerate(blocks, start=1):
        required_classes = {
            "diff-card": "必须同时使用 .diff-card 和 .diff-viewer，避免退化成普通代码块外壳",
            "diff-header": "缺少 .diff-header，无法保持标准 diff 标题区",
            "change-chip": "缺少 .change-chip，无法稳定展示“代码差异”标识",
            "diff-file": "缺少 .diff-file，无法标明当前卡片对应的文件",
            "diff-scroll": "缺少 .diff-scroll，宽 diff 在窄屏下可能撑破正文",
            "diff-table": "缺少 .diff-table，old/new 行号和代码列无法稳定对齐",
            "diff-gutter": "缺少 .diff-gutter，无法展示左侧 +/- 变更轨道",
            "diff-old-num": "缺少 .diff-old-num，无法展示 old 行号列",
            "diff-new-num": "缺少 .diff-new-num，无法展示 new 行号列",
            "diff-code": "缺少 .diff-code，代码列无法套用标准样式",
            "diff-hunk": "缺少 .diff-hunk，无法展示 unified diff hunk header",
        }
        for class_name, message in required_classes.items():
            if not has_class(block, class_name):
                errors.append(f"第 {index} 个 diff viewer {message}")

        if not (has_class(block, "diff-add") or has_class(block, "diff-del")):
            errors.append(f"第 {index} 个 diff viewer 缺少 .diff-add 或 .diff-del 行，真实修改点不可见")
        if "统一 diff · old/new 行号" not in fragment_text(block):
            errors.append(f"第 {index} 个 diff viewer 标题区缺少“统一 diff · old/new 行号”说明")

        meta_texts = [fragment_text(row) for row in DIFF_META_ROW_RE.findall(block)]
        git_file_count = sum(text.startswith("diff --git ") for text in meta_texts)
        fallback_file_count = sum(text.startswith("--- ") for text in meta_texts)
        file_count = git_file_count or fallback_file_count
        if file_count > 1:
            errors.append(f"第 {index} 个 diff viewer 混入 {file_count} 个文件；必须由 highlight_code.py 自动拆成每文件一个卡片")

    compact_css = re.sub(r"\s+", " ", css)
    required_diff_css = {
        ".diff-card": "diff viewer 缺少 .diff-card 基础卡片样式",
        ".diff-header": "diff viewer 缺少 .diff-header 标题区样式",
        ".diff-file": "diff viewer 缺少 .diff-file 文件名样式",
        ".diff-scroll": "diff viewer 缺少 .diff-scroll 横向滚动容器样式",
        ".diff-viewer .diff-table": "diff viewer 缺少固定表格样式",
        ".diff-viewer .diff-gutter": "diff viewer 缺少紧凑 +/- 轨道样式",
        ".diff-viewer .diff-num": "diff viewer 缺少 old/new 行号列样式",
        ".diff-viewer .diff-old-num": "diff viewer 缺少 old/new 行号内部边界样式",
        ".diff-viewer .diff-code": "diff viewer 缺少代码列样式",
        ".diff-viewer .diff-add .diff-num": "diff viewer 缺少新增行 old/new 行号背景样式",
        ".diff-viewer .diff-del .diff-num": "diff viewer 缺少删除行 old/new 行号背景样式",
        ".diff-viewer .diff-add .diff-gutter": "diff viewer 缺少新增行左侧绿色变更轨道",
        ".diff-viewer .diff-del .diff-gutter": "diff viewer 缺少删除行左侧红色变更轨道",
        ".diff-viewer .diff-hunk .diff-code": "diff viewer 缺少 hunk/meta 行样式",
        "min-width: 25px": "diff viewer +/- 轨道必须保持 25px 紧凑宽度",
        "white-space: pre": "diff viewer 代码列必须保持原始空格，避免代码缩进漂移",
    }
    for fragment, message in required_diff_css.items():
        if fragment not in compact_css:
            errors.append(message)

    if not css_rule_has(
        css,
        (".diff-viewer .diff-num",),
        ("width: 1%", "min-width: 0", "white-space: nowrap", "font-variant-numeric: tabular-nums"),
    ):
        errors.append("diff viewer 行号列必须按内容收缩并保持数字对齐，避免 old/new 空白占宽")
    if not css_rule_has(css, (".diff-viewer .diff-old-num",), ("border-right: 0 !important",)):
        errors.append("diff viewer old/new 行号之间不应显示多余竖线")

    # 三种行使用相同的细轨道宽度，透明上下文轨道负责保持 +/- 列横向对齐。
    change_track_rules = (
        (".diff-viewer .diff-add .diff-gutter", "border-left: 2px solid #16a34a"),
        (".diff-viewer .diff-del .diff-gutter", "border-left: 2px solid #dc2626"),
        (".diff-viewer .diff-context .diff-gutter", "border-left: 2px solid transparent"),
    )
    if not all(css_rule_has(css, (selector,), (declaration,)) for selector, declaration in change_track_rules):
        errors.append("diff viewer 左侧变更指示条必须统一使用 2px 细轨道")

    return errors


def check_table_support(parser: ReportParser, css: str) -> list[str]:
    """普通表格必须复用基础组件，保证圆角外框、完整网格线和窄屏滚动。"""

    if not parser.regular_table_lines:
        return []

    errors: list[str] = []
    if not css_rule_has(css, (".table-wrap",), ("overflow-x: auto",)):
        errors.append("报告包含普通表格，但 .table-wrap 缺少 overflow-x: auto 横向滚动保护")
    if not css_rule_has(css, (".table-wrap",), ("border-radius:",)):
        errors.append("报告包含普通表格，但 .table-wrap 缺少统一圆角外框")
    if not css_rule_has(css, (".table-wrap table:not(.diff-table)",), ("border-collapse: collapse",)):
        errors.append("报告包含普通表格，但基础表格规则缺少 border-collapse: collapse")
    if not css_rule_has(
        css,
        (".table-wrap table:not(.diff-table) th", ".table-wrap table:not(.diff-table) td"),
        ("border: 1px solid",),
    ):
        errors.append("报告包含普通表格，但 th/td 缺少完整 1px 网格线；不能只设置 border-bottom")
    return errors


def check_tag_support(html: str, css: str) -> list[str]:
    """状态标签必须自带前景与背景兜底，避免漏写变体类时出现白底白字。"""

    if not has_class(html, "tag"):
        return []

    if not css_rule_has(css, (".tag",), ("background:", "color:")):
        return ["报告使用 .tag 标签，但默认规则未同时设置 background 和 color；漏写 p0/p1/p2 时文字可能不可见"]
    return []


def check_raw_unified_diff_outside_viewer(html: str) -> list[str]:
    without_diff_viewers = DIFF_VIEWER_RE.sub("", html)
    if looks_like_unified_diff(fragment_text(without_diff_viewers)):
        return ["发现未包在 .diff-card.diff-viewer 中的 raw unified diff；请用 highlight_code.py --lang diff --diff-view 生成标准 diff viewer"]
    return []


def check_diff_viewer_tokens(html: str, css: str) -> list[str]:
    errors: list[str] = []
    compact_css = re.sub(r"\s+", " ", css)
    token_classes: set[str] = set()
    for block in DIFF_VIEWER_RE.findall(html):
        token_classes.update(TOKEN_SPAN_RE.findall(block))

    missing_classes = sorted(class_name for class_name in token_classes if f".{class_name}" not in compact_css)
    if missing_classes:
        errors.append(
            f"diff viewer 使用 {', '.join(missing_classes)}，但 CSS 缺少对应 token 样式，代码列会显示成未高亮"
        )
    return errors


def check_review_workspace_pack(pack: object, index: int, css: str) -> list[str]:
    """校验单个 Workspace 数据包，避免运行时才暴露缺版本、越界行号或不安全源码 HTML。"""

    errors: list[str] = []
    prefix = f"第 {index} 个 Review Workspace"
    if not isinstance(pack, dict):
        return [f"{prefix} 数据必须是 JSON 对象"]

    for field_name in ("workspaceId", "storageKey"):
        if not isinstance(pack.get(field_name), str) or not pack[field_name].strip():
            errors.append(f"{prefix} 缺少非空 {field_name}")

    versions = pack.get("versions")
    if not isinstance(versions, list) or not 2 <= len(versions) <= 3:
        errors.append(f"{prefix} versions 必须包含 2 到 3 个版本")
        return errors

    version_ids: list[str] = []
    for version_index, version in enumerate(versions, start=1):
        if not isinstance(version, dict):
            errors.append(f"{prefix} 第 {version_index} 个 version 必须是对象")
            continue
        version_id = version.get("id")
        if not isinstance(version_id, str) or not version_id.strip():
            errors.append(f"{prefix} 第 {version_index} 个 version 缺少非空 id")
            continue
        version_ids.append(version_id)
        if not isinstance(version.get("label"), str) or not version["label"].strip():
            errors.append(f"{prefix} version {version_id} 缺少非空 label")
    if len(set(version_ids)) != len(version_ids):
        errors.append(f"{prefix} version id 必须唯一")

    files = pack.get("files")
    if not isinstance(files, list) or not files:
        errors.append(f"{prefix} files 必须是非空数组")
        return errors

    token_classes: set[str] = set()
    seen_file_ids: set[str] = set()
    allowed_line_tag = re.compile(r'(?:<span class="(tok-[a-zA-Z0-9_-]+)">|</span>)')
    for file_index, file in enumerate(files, start=1):
        file_prefix = f"{prefix} 第 {file_index} 个文件"
        if not isinstance(file, dict):
            errors.append(f"{file_prefix} 必须是对象")
            continue
        file_id = file.get("id")
        if not isinstance(file_id, str) or not file_id.strip():
            errors.append(f"{file_prefix} 缺少非空 id")
        elif file_id in seen_file_ids:
            errors.append(f"{prefix} file id 重复：{file_id}")
        else:
            seen_file_ids.add(file_id)
        if not isinstance(file.get("filename"), str) or not file["filename"].strip():
            errors.append(f"{file_prefix} 缺少非空 filename")
        idea_href = file.get("ideaHref", "")
        if idea_href and (not isinstance(idea_href, str) or not idea_href.startswith("idea://open?")):
            errors.append(f"{file_prefix} ideaHref 只能为空或使用 idea://open")

        file_versions = file.get("versions")
        if not isinstance(file_versions, dict):
            errors.append(f"{file_prefix} versions 必须是对象")
            continue
        if set(file_versions) != set(version_ids):
            errors.append(f"{file_prefix} versions 必须与顶层版本一一对应")
            continue

        for version_id in version_ids:
            source = file_versions.get(version_id)
            source_prefix = f"{file_prefix} 的 {version_id}"
            if not isinstance(source, dict):
                errors.append(f"{source_prefix} 必须是对象")
                continue
            lines = source.get("lines")
            if not isinstance(lines, list) or not lines or not all(isinstance(line, str) for line in lines):
                errors.append(f"{source_prefix}.lines 必须是非空字符串数组")
                continue

            # 运行时会把源码行写入 innerHTML，因此只允许高亮脚本生成的 tok-* span。
            for line_number, line in enumerate(lines, start=1):
                for match in allowed_line_tag.finditer(line):
                    if match.group(1):
                        token_classes.add(match.group(1))
                residue = allowed_line_tag.sub("", line)
                if "<" in residue or ">" in residue:
                    errors.append(
                        f"{source_prefix}.lines 第 {line_number} 行包含非 tok-* HTML 标签；"
                        "请使用 build_review_workspace.py 生成"
                    )
                    break

            marks = source.get("marks")
            if not isinstance(marks, dict):
                errors.append(f"{source_prefix}.marks 必须是对象")
                continue
            for mark_name in ("primary", "secondary", "focus", "context"):
                values = marks.get(mark_name)
                if not isinstance(values, list) or not all(
                    isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= len(lines)
                    for value in values
                ):
                    errors.append(f"{source_prefix}.marks.{mark_name} 必须是未越界的整数行号数组")

    compact_css = re.sub(r"\s+", " ", css)
    missing_token_css = sorted(class_name for class_name in token_classes if f".{class_name}" not in compact_css)
    if missing_token_css:
        errors.append(
            f"{prefix} 使用 {', '.join(missing_token_css)}，但 CSS 缺少对应 token 样式"
        )
    return errors


def check_review_workspaces(html: str, css: str) -> list[str]:
    """检查按需多版本审阅组件的结构、数据、安全转义、运行时和响应式样式。"""

    errors: list[str] = []
    sections = REVIEW_WORKSPACE_SECTION_RE.findall(html)
    data_nodes = REVIEW_WORKSPACE_DATA_RE.findall(html)
    runtimes = REVIEW_WORKSPACE_RUNTIME_RE.findall(html)
    if not sections and not data_nodes and not runtimes:
        return errors

    if not sections:
        errors.append("发现 Review Workspace 数据或运行时，但缺少 .review-workspace[data-review-workspace] 容器")
        return errors
    if len(data_nodes) != len(sections):
        errors.append("每个 Review Workspace 必须且只能包含一个 application/json 数据节点")
    for index, section in enumerate(sections, start=1):
        if "data-review-workspace-root" not in section:
            errors.append(f"第 {index} 个 Review Workspace 缺少 data-review-workspace-root 挂载点")
        section_data = REVIEW_WORKSPACE_DATA_RE.findall(section)
        if len(section_data) != 1:
            errors.append(f"第 {index} 个 Review Workspace 必须且只能包含一个数据节点")

    if len(runtimes) != 1:
        errors.append("使用 Review Workspace 时，整份报告必须且只能内联一个 data-review-workspace-runtime")
    elif runtimes:
        runtime = runtimes[0]
        required_runtime_fragments = {
            "HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_START": "Review Workspace runtime 缺少完整性起始标记",
            "HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_END": "Review Workspace runtime 缺少完整性结束标记",
            "HtmlReportReviewWorkspace": "Review Workspace runtime 缺少全局初始化入口",
            "reviewWorkspaceReady": "Review Workspace runtime 缺少重复初始化保护",
            "rw-diff-only": "Review Workspace runtime 缺少只看差异切换",
            "localStorage": "Review Workspace runtime 缺少已审阅状态持久化",
            "navigator.clipboard": "Review Workspace runtime 缺少现代复制入口",
            "document.execCommand": "Review Workspace runtime 缺少 file:// 复制回退",
        }
        for fragment, message in required_runtime_fragments.items():
            if fragment not in runtime:
                errors.append(message)

    compact_css = re.sub(r"\s+", " ", css)
    required_css = {
        ".review-workspace .rw-toolbar": "Review Workspace 缺少工具栏样式",
        ".review-workspace .rw-body": "Review Workspace 缺少文件导航与审阅区布局",
        ".review-workspace .rw-file-nav": "Review Workspace 缺少文件列表样式",
        ".review-workspace .rw-panes": "Review Workspace 缺少多版本窗格布局",
        ".review-workspace .rw-code-scroll": "Review Workspace 缺少源码滚动容器样式",
        ".review-workspace .rw-code-line": "Review Workspace 缺少行号与源码行样式",
        ".review-workspace.rw-diff-only": "Review Workspace 缺少只看差异 CSS",
        "@media (max-width: 900px)": "Review Workspace 缺少窄屏单列降级",
        "@media print": "Review Workspace 缺少打印降级",
    }
    for fragment, message in required_css.items():
        if fragment not in compact_css:
            errors.append(message)

    for index, payload in enumerate(data_nodes, start=1):
        leaked = [label for char, label in {"<": "<", ">": ">", "&": "&", "\u2028": "U+2028", "\u2029": "U+2029"}.items() if char in payload]
        if leaked:
            errors.append(
                f"第 {index} 个 Review Workspace JSON raw-text 含未转义字符："
                + "、".join(leaked)
                + "；请使用 build_review_workspace.py 生成"
            )
        try:
            pack = json.loads(payload)
        except json.JSONDecodeError as exc:
            errors.append(f"第 {index} 个 Review Workspace 数据不是合法 JSON: {exc.msg}")
            continue
        errors.extend(check_review_workspace_pack(pack, index, css))
    return errors


def check_annotation_mode(
    html: str,
    css: str,
    require_review_pack: bool = False,
    require_review_receipt: bool = False,
    block_ids: list[str] | None = None,
) -> list[str]:
    """检查离线批注模式的关键结构，避免批注版 HTML 交互缺件。"""
    errors: list[str] = []
    # 只识别真实 marker、标签和数据节点；正文代码示例里的同名字符串不能把普通报告误判为批注版。
    has_embedded_review = bool(
        EMBEDDED_REVIEW_START_RE.search(html)
        or EMBEDDED_REVIEW_END_RE.search(html)
        or EMBEDDED_REVIEW_DATA_RE.search(html)
    )
    has_embedded_receipt = bool(
        EMBEDDED_REVIEW_RECEIPT_START_RE.search(html)
        or EMBEDDED_REVIEW_RECEIPT_END_RE.search(html)
        or EMBEDDED_REVIEW_RECEIPT_DATA_RE.search(html)
    )
    has_annotation = bool(
        ANNOTATION_MODE_MARKER_RE.search(html)
        or ANNOTATION_SCRIPT_TAG_RE.search(html)
        or ANNOTATION_UI_TAG_RE.search(html)
        or ANNOTATION_CSS_ASSET_RE.search(css)
        or has_embedded_review
        or has_embedded_receipt
    )
    if not has_annotation:
        if require_review_pack:
            return ["未找到 HTML 内嵌批注包；请确认用户保存的是批注版，而不是原始版或发布版"]
        if require_review_receipt:
            return ["未找到 AgentReviewReceipt；无法确认 Agent 是否处理并回写了当前 HTML"]
        return errors

    # 只在三段批注资产中检查实现片段，避免正文代码示例里的旧按钮名造成误报或掩盖缺件。
    annotation_parts = ANNOTATION_CSS_ASSET_RE.findall(css) + ANNOTATION_ASSET_BLOCK_RE.findall(html)
    annotation_scope = "\n".join(annotation_parts) or html

    required_fragments = {
        "QA_ANNOTATION_CSS_START": "批注模式缺少 CSS 起始标记，导出发布版无法稳定剥离样式",
        "QA_ANNOTATION_HTML_START": "批注模式缺少 HTML 起始标记，导出发布版无法稳定剥离 UI",
        "QA_ANNOTATION_SCRIPT_START": "批注模式缺少脚本起始标记，导出发布版无法稳定剥离 JS",
        "data-qa-script": "批注模式缺少 data-qa-script，导出发布版无法从 DOM 中移除批注脚本",
        "data-qa-ui": "批注模式缺少 data-qa-ui，导出发布版无法从 DOM 中移除批注 UI",
        'id="qaSelectionPopover"': "批注模式缺少选中文本气泡",
        'id="qaComposer"': "批注模式缺少轻量输入浮层",
        'id="qaSidebar"': "批注模式缺少右侧批注栏",
        'id="qaExportPublic"': "批注模式缺少导出发布版按钮",
        'id="qaLauncherLabel"': "批注模式缺少稳定的右上角批注入口",
        'id="qaRoundStatus"': "批注侧栏缺少持久轮次状态",
        "updateLauncherMode": "批注模式必须根据批注数量更新右上角状态徽标",
        "updateRoundStatus": "批注模式缺少草稿、待处理和已处理轮次状态",
        'class="qa-quote qa-quote-link"': "批注原文缺少直接定位正文的快捷入口",
        'id="qaCopyForAgent"': "批注侧栏缺少复制给 Agent 的主入口",
        'id="qaSaveReviewHtml"': "批注侧栏缺少 HTML 备用交接入口",
        'class="qa-secondary-actions"': "保存批注版和导出发布版必须并排展示",
        'aria-label="保存批注版 HTML（备用）"': "保存批注版入口必须保留备用 HTML 交接语义",
        'id="qaExportPublic">导出发布版</button>': "发布版按钮文案必须与批注交接动作区分",
        'id="qaClearAll">清空本轮</button>': "清空本轮必须作为侧栏直接可见操作",
        "qa-copy-agent-btn": "复制批注给 Agent 必须作为醒目的主按钮展示",
        "copyAnnotationsForAgent": "批注模式缺少剪贴板主交接逻辑",
        "saveReviewHtml": "批注模式缺少保存批注版的备用交互逻辑",
        "saveHtmlFile": "批注版和发布版必须复用统一的 HTML 保存/下载回退逻辑",
        "reviewFallbackFileName": "下载批注版必须使用与当前草稿不同的默认文件名，避免本地状态碰撞",
        "buildReviewedHtml": "批注模式缺少含批注 HTML 构建逻辑",
        "buildEmbeddedReviewBlock": "批注模式缺少 AgentQuestionPack 内嵌逻辑",
        "serializeReviewPack": "批注模式缺少内嵌 JSON 安全序列化逻辑",
        "\\u003c": "内嵌 JSON 必须转义 <，防止 </script> 提前闭合或注入 HTML",
        "data-qa-review-data": "批注版缺少稳定的内嵌数据节点",
        "readEmbeddedReviewPack": "批注模式缺少从 HTML 恢复内嵌批注的逻辑",
        "readEmbeddedReviewReceipt": "批注模式缺少读取 AgentReviewReceipt 的逻辑",
        "stripReviewReceiptBlock": "新一轮交接和发布版必须物理剥离旧处理回执",
        "handoffStorageKey": "批注模式缺少剪贴板交接轮次的临时状态键",
        "ensureRoundId": "批注交接必须使用稳定轮次 ID",
        "stored !== null": "批注加载必须区分 localStorage 不存在与用户明确清空的 []",
        "legacyStorageKey": "批注模式必须兼容迁移旧版 localStorage 草稿键",
        "Math.max(blockSeq": "批注版必须从已有定位 ID 恢复序号，避免 Agent 增段后生成重复 blockId",
        "clearStoredAnnotations": "直接写入 HTML 后必须清理旧本地基线，避免 Agent 更新后复活旧批注",
        "stripEmbeddedReviewBlock": "重复保存和发布版导出必须能剥离旧内嵌批注包",
        "mode: 'embedded-html'": "AgentQuestionPack 必须声明 HTML 内嵌交付模式",
        "inject_annotation_mode.py": "AgentQuestionPack 必须明确处理后重新注入批注模式",
        "取消：取消导出": "导出发布版确认框的取消动作必须真正取消，不能触发下载",
        "buildPublicHtml": "批注模式缺少发布版 HTML 剥离逻辑",
        "data-qa-review-receipt": "发布版剥离逻辑必须识别 AgentReviewReceipt",
        "buildMarkdownPack": "批注模式缺少 Markdown 批注包导出逻辑",
        "buildJsonPack": "批注模式缺少 JSON 批注包导出逻辑",
        'data-qa-card-action="edit"': "批注侧栏必须支持编辑已有批注，避免只能删除重加",
        "openEditAnnotation": "批注模式缺少编辑已有批注的交互逻辑",
        "editingAnnotationId": "批注模式编辑已有批注时必须记录当前编辑目标",
        "updatedAt": "批注模式编辑已有批注后必须记录更新时间",
        "injectedReportMeta": "批注模式必须在生成时注入原 HTML 路径元数据，避免打开方式改变后丢失绝对路径",
        "reportAbsolutePath": "批注模式导出包必须包含原 HTML 绝对路径",
        "reportFileUrl": "批注模式导出包必须包含 file URL",
        "File URL：": "Markdown 批注包必须写入 file URL，方便 Agent 回查原文件",
        "绝对路径：": "Markdown 批注包必须写入绝对路径，方便 Agent 回查原文件",
        "cachedSelectionTarget": "批注模式必须缓存选区，避免点击气泡后选区丢失",
        "syncAnnotatedState": "批注模式必须在保存、删除、清空后同步正文高亮和边框状态",
        "removeAllRanges": "批注模式删除批注后必须清理浏览器选区，避免正文残留选中态",
        'id="qaComposerSave"': "批注输入浮层缺少唯一提交按钮",
        'aria-keyshortcuts="Meta+Enter Control+Enter"': "批注输入浮层必须声明 ⌘/Ctrl + Enter 提交快捷键",
        "composerText?.addEventListener('keydown'": "批注输入框缺少局部键盘快捷键监听",
        "isComposerSubmitShortcut": "批注输入浮层缺少快捷键提交判断",
        "event.metaKey || event.ctrlKey": "批注输入浮层必须同时支持 ⌘ + Enter 和 Ctrl + Enter",
        "!event.isComposing": "批注输入浮层必须避开输入法组字阶段，防止 Enter 误提交",
    }
    # 接收上一版本已保存的批注包时允许旧 UI 文案；处理完成并重新注入后，普通校验强制升级新名称。
    if not require_review_pack:
        required_fragments['<span class="qa-mode-chip">批注模式</span>'] = "批注模式标签缺失或仍使用混用名称"
        required_fragments['<span class="qa-launcher-label" id="qaLauncherLabel">批注</span>'] = "右上角入口必须固定显示“批注”，不能在零条时切换为发布操作"
        required_fragments["launcherLabel.textContent = '批注'"] = "右上角入口运行时必须保持“批注”文案稳定"
        required_fragments["launcherCount.hidden = count === 0"] = "右上角数量徽标必须在零条时隐藏"
        required_fragments['<span class="qa-submit-label">提交</span>'] = "批注输入浮层只保留一个“提交”按钮"
        required_fragments['<kbd class="qa-shortcut-hint" aria-hidden="true">Ctrl/⌘ + Enter</kbd>'] = "批注提交按钮必须显示 Ctrl/⌘ + Enter 快捷键提示"
        required_fragments["复制批注给 Agent"] = "批注侧栏必须以剪贴板交接作为主操作"
        required_fragments["保存批注版 HTML（备用）"] = "批注侧栏必须明确 HTML 文件交接只是备用路径"
        required_fragments["copyForAgent.disabled = count === 0"] = "零批注时必须禁用主交接按钮，避免展示无效主操作"
        required_fragments["reconcileAnnotationTargets"] = "批注模式必须在加载和交接前迁移或识别失效的正文定位"
        required_fragments["findAnnotationElementByText"] = "批注模式缺少按原文唯一匹配旧批注位置的回退逻辑"
        required_fragments["reconciliation.unresolved.length"] = "批注模式交接前必须阻止无法定位的批注进入交接内容"
        required_fragments["原文已变化，当前报告中无法安全定位"] = "批注卡片必须明确提示正文变化导致的定位失效"
        required_fragments['id="qaSelectionQuestionAction"'] = "选区气泡缺少问题入口"
        required_fragments['id="qaSelectionQuestionLabel"'] = "问题入口缺少稳定文案节点"
        required_fragments['id="qaSelectionAction"'] = "批注模式缺少可切换的选区操作入口"
        required_fragments['id="qaSelectionActionLabel"'] = "选区操作入口缺少可更新的文案节点"
        required_fragments["annotationKindForAction"] = "批注模式缺少问题/评论入口到类型的映射逻辑"
        required_fragments["normalizeAnnotationKind"] = "批注模式缺少旧类型到问题/评论的兼容映射"
        required_fragments["lines.push('- 类型：' + kind)"] = "Markdown 批注包必须逐条标明问题或评论类型"
        required_fragments["rebindAnnotationId"] = "批注模式缺少当前重新关联批注的临时状态"
        required_fragments["startAnnotationRebind"] = "失效批注卡片缺少进入手动重新关联的入口"
        required_fragments["cancelAnnotationRebind"] = "重新关联模式缺少不改数据的取消路径"
        required_fragments["buildReboundAnnotation"] = "重新关联必须通过独立函数只更新定位字段"
        required_fragments["finishAnnotationRebind"] = "重新关联缺少选区确认与保存逻辑"
        required_fragments["updateSelectionActionMode"] = "选区气泡缺少重新关联模式文案切换"
        required_fragments["按 Esc 取消"] = "重新关联模式必须提供 Esc 取消提示"
        required_fragments["main.contains(target.element)"] = "重新关联必须限制在当前报告正文内"
        required_fragments["selectionQuestionAction.hidden = rebinding"] = "重新关联时必须隐藏问题入口，避免把类型选择误当成重新关联"
        required_fragments["value === '问题' || value === '提问'"] = "旧提问类型必须兼容映射为问题"
        required_fragments["value === '评论' || value === '注释' || value === '批注'"] = "旧注释和批注类型必须兼容映射为评论"
    for fragment, message in required_fragments.items():
        if fragment not in annotation_scope:
            errors.append(message)

    if not require_review_pack:
        launcher_handler = re.search(
            r"launcher\?\.addEventListener\(\s*['\"]click['\"]\s*,\s*\(\)\s*=>\s*\{(.*?)\n\s*\}\);",
            annotation_scope,
            re.DOTALL,
        )
        if not launcher_handler or "setSidebarOpen" not in launcher_handler.group(1):
            errors.append("右上角批注入口必须始终打开或关闭批注侧栏")
        elif "exportPublicHtml" in launcher_handler.group(1):
            errors.append("右上角批注入口不能在零条时直接导出发布版")

        popover_match = re.search(
            r'<div\b[^>]*\bid=["\']qaSelectionPopover["\'][^>]*>(.*?)</div>',
            annotation_scope,
            re.DOTALL | re.IGNORECASE,
        )
        if not popover_match:
            errors.append("批注模式缺少选中文本气泡")
        else:
            popover_html = popover_match.group(1)
            if len(re.findall(r"<button\b", popover_html, re.IGNORECASE)) != 2:
                errors.append("选中文本气泡必须直接提供“问题”和“评论”两个按钮")
            expected_actions = {
                "question-selection": ("qaSelectionQuestionLabel", "问题"),
                "comment-selection": ("qaSelectionActionLabel", "评论"),
            }
            for action, (label_id, label) in expected_actions.items():
                action_match = re.search(
                    rf'<button\b[^>]*\bdata-qa-action=["\']{re.escape(action)}["\'][^>]*>(.*?)</button>',
                    popover_html,
                    re.DOTALL | re.IGNORECASE,
                )
                if not action_match or not re.search(
                    rf'<span\b[^>]*\bid=["\']{label_id}["\'][^>]*>\s*{label}\s*</span>',
                    action_match.group(1),
                ):
                    errors.append(f"选中文本气泡缺少可直接点击的“{label}”入口")
        if "qaFilterBar" in annotation_scope or "data-qa-filter" in annotation_scope:
            errors.append("问题/评论在创建时选择即可，批注侧栏不再保留类型筛选")
        secondary_actions_match = re.search(
            r'<div\b[^>]*\bclass=["\'][^"\']*\bqa-secondary-actions\b[^"\']*["\'][^>]*>(.*?)</div>',
            annotation_scope,
            re.DOTALL | re.IGNORECASE,
        )
        if not secondary_actions_match or not all(
            fragment in secondary_actions_match.group(1)
            for fragment in ('id="qaSaveReviewHtml"', 'id="qaExportPublic"')
        ):
            errors.append("保存批注版和导出发布版必须位于同一个直接可见的并排操作组")

    save_review_start = annotation_scope.find("async function saveReviewHtml()")
    save_review_end = annotation_scope.find("// 发布版只保留正文", save_review_start)
    if not require_review_pack and save_review_start >= 0 and save_review_end > save_review_start:
        save_review_scope = annotation_scope[save_review_start:save_review_end]
        reconcile_index = save_review_scope.find("reconcileAnnotationTargets()")
        save_file_index = save_review_scope.find("await saveHtmlFile(")
        if reconcile_index < 0 or save_file_index < 0 or reconcile_index > save_file_index:
            errors.append("保存批注版前必须先校验并迁移正文定位，不能先生成含失效 blockId 的 HTML")

    copy_review_start = annotation_scope.find("async function copyAnnotationsForAgent()")
    copy_review_end = annotation_scope.find("async function copyText(", copy_review_start)
    if not require_review_pack and copy_review_start >= 0 and copy_review_end > copy_review_start:
        copy_review_scope = annotation_scope[copy_review_start:copy_review_end]
        reconcile_index = copy_review_scope.find("reconcileAnnotationTargets()")
        copy_index = copy_review_scope.find("await copyText(")
        if reconcile_index < 0 or copy_index < 0 or reconcile_index > copy_index:
            errors.append("复制批注给 Agent 前必须先校验正文定位，不能交接失效 blockId")

    forbidden_fragments = {
        "qaComposerCancel": "批注输入浮层不要保留取消按钮；点击浮层外侧即关闭",
        ">保存<": "批注输入浮层按钮文案应为“提交”，不要使用“保存”",
        "qaDownloadJson": "批注侧栏不再提供独立 JSON 下载，应使用复制交接或备用批注版 HTML",
        ">下载 JSON<": "批注侧栏不再提供独立 JSON 下载按钮",
        "建议使用当前文件名覆盖原评论版": "无批注发布版不能再建议覆盖评论版",
        "建议使用当前文件名覆盖原审核版": "无批注发布版不能再建议覆盖旧称审核版",
        "取消：下载": "导出发布版确认框不能把取消解释为下载",
        "暂无批注可保存": "清空批注后仍必须允许保存空批注包，覆盖 HTML 中的旧批注",
        "result === 'saved' || result === 'downloaded'": "下载只能确认已发起，不能据此清空尚未持久化的本地草稿",
    }
    if not require_review_pack:
        forbidden_fragments['<span class="qa-mode-chip">审核模式</span>'] = "批注模式标签不能使用旧名称“审核模式”"
        forbidden_fragments['<span class="qa-mode-chip">评论模式</span>'] = "可见模式名称必须统一为“批注模式”"
        forbidden_fragments['id="qaSelectionActionLabel">注释</span>'] = "选区入口不能继续使用“注释”"
        forbidden_fragments['id="qaSelectionActionLabel">添加批注</span>'] = "选区入口不能再次收敛为单一“添加批注”"
        forbidden_fragments['data-qa-action="note-selection"'] = "选区入口必须使用明确的问题/评论动作"
        forbidden_fragments['data-qa-filter='] = "问题/评论在创建时选择，侧栏不再保留类型筛选"
        forbidden_fragments["完成批注"] = "文件保存不等于 Agent 已处理，不能继续使用“完成批注”"
        forbidden_fragments["导出无批注版"] = "发布动作统一命名为“导出发布版”"
        forbidden_fragments["publish-mode"] = "右上角入口职责必须稳定，不能保留零批注发布模式"
        forbidden_fragments["请删除后在新位置重新添加"] = "失效批注必须提供重新关联入口，不能要求删除重建"
        forbidden_fragments['id="qaCopyMarkdown"'] = "复制给 Agent 已覆盖 Markdown 交接，不再保留重复的复制 Markdown 按钮"
        forbidden_fragments['id="qaDownloadMarkdown"'] = "批注侧栏不再提供下载 Markdown 按钮"
        forbidden_fragments['<details class="qa-more">'] = "常用文件操作和清空本轮必须直接展示，不再收进更多操作"
    for fragment, message in forbidden_fragments.items():
        if fragment in annotation_scope:
            errors.append(message)

    compact_css = re.sub(r"\s+", " ", css)
    required_css = {
        ".qa-selection-popover": "批注模式缺少选区气泡样式",
        ".qa-composer": "批注模式缺少输入浮层样式",
        ".qa-sidebar": "批注模式缺少右侧栏样式",
        ".qa-round-status": "批注侧栏缺少持久轮次状态样式",
        ".qa-copy-agent-btn": "复制批注主操作缺少稳定样式",
        ".qa-secondary-actions": "保存批注版和导出发布版缺少并排布局样式",
        ".qa-clear-btn": "清空本轮缺少直接可见的危险操作样式",
        ".qa-quote-link": "批注原文快捷定位缺少按钮样式",
        ".qa-highlight": "批注模式缺少选中文本高亮样式",
        ".qa-panel-open": "批注模式缺少右侧栏打开时的正文避让样式",
    }
    if not require_review_pack:
        required_css[".qa-shortcut-hint"] = "批注提交按钮缺少可见快捷键提示样式"
        required_css[".qa-copy-agent-btn:disabled"] = "零批注主交接按钮缺少明确的禁用样式"
        required_css[".qa-card.location-missing"] = "批注模式缺少失效定位卡片的警示样式"
        required_css[".qa-location-warning"] = "批注模式缺少失效定位提示样式"
        required_css[".qa-card.kind-comment"] = "评论卡片缺少与问题区分的左侧标识"
        required_css[".qa-card.kind-comment .qa-kind"] = "评论卡片缺少与问题区分的徽标样式"
        required_css[".qa-card.rebinding"] = "批注模式缺少重新关联中的卡片状态样式"
        required_css[".qa-mini-btn.rebind"] = "失效批注缺少重新关联按钮样式"
    for fragment, message in required_css.items():
        if fragment not in compact_css:
            errors.append(message)

    if ".qa-launcher-count[hidden]" not in compact_css:
        errors.append("零批注时必须强制隐藏右上角数量徽标，避免显示空白圆点")

    if not require_review_pack:
        if not css_rule_has(css, (".qa-kind",), ("flex: 0 0 auto", "white-space: nowrap")):
            errors.append("批注卡片徽标必须禁止 flex 收缩和文字换行")
        if not css_rule_has(css, (".qa-section",), ("min-width: 0", "overflow-wrap: anywhere")):
            errors.append("批注卡片长章节标题必须承担收缩并允许换行，不能挤压左侧徽标")
        if not css_rule_has(css, (".qa-card",), ("font-size: 12px",)):
            errors.append("批注卡片基础字号应保持紧凑，避免侧栏内容显得过大")
        if not css_rule_has(css, (".qa-question",), ("font-size: 12px",)):
            errors.append("批注正文应使用紧凑字号，避免长意见占用过多侧栏空间")
        if not css_rule_has(css, (".qa-quote",), ("font-size: 12px", "line-height: 1.55")):
            errors.append("批注原文摘录应保持 12px 紧凑字号和稳定行高")
        if not css_rule_has(css, (".qa-quote-link",), ("font-family: inherit",)):
            errors.append("批注原文按钮只能继承字体族，不能覆盖摘录自身的字号和行高")
        if ".qa-selection-popover [hidden]" not in compact_css:
            errors.append("重新关联时必须能稳定隐藏问题入口，只保留重新关联动作")

    errors.extend(check_embedded_review_pack(html, required=require_review_pack, block_ids=block_ids))
    errors.extend(check_embedded_review_receipt(html, required=require_review_receipt))
    if has_embedded_review and has_embedded_receipt:
        errors.append("同一 HTML 不能同时包含待处理 AgentQuestionPack 和已处理 AgentReviewReceipt")
    return errors


def check_embedded_review_pack(
    html: str,
    required: bool = False,
    block_ids: list[str] | None = None,
) -> list[str]:
    """当 HTML 已保存批注结果时，校验唯一内嵌包的标记、JSON 和 Agent 定位字段。"""

    errors: list[str] = []
    start_matches = list(EMBEDDED_REVIEW_START_RE.finditer(html))
    end_matches = list(EMBEDDED_REVIEW_END_RE.finditer(html))
    node_matches = list(EMBEDDED_REVIEW_DATA_RE.finditer(html))
    if not start_matches and not end_matches and not node_matches:
        if required:
            errors.append("未找到 HTML 内嵌批注包；请确认用户已保存批注版 HTML 并提供了该文件")
        return errors
    if len(start_matches) != 1 or len(end_matches) != 1:
        errors.append("批注版必须且只能包含一对 QA_EMBEDDED_REVIEW_START/END 标记")
    if len(node_matches) != 1:
        errors.append("批注版必须且只能包含一个 #qaEmbeddedReviewData[data-qa-review-data] 节点")
        return errors

    node_match = node_matches[0]
    opening_tag = node_match.group(0).split(">", 1)[0] + ">"
    if not re.search(r"\btype\s*=\s*[\"']application/json[\"']", opening_tag, re.IGNORECASE):
        errors.append("HTML 内嵌批注包节点 type 必须为 application/json，不能作为可执行脚本")
    if len(start_matches) == 1 and len(end_matches) == 1:
        if not (start_matches[0].end() <= node_match.start() < node_match.end() <= end_matches[0].start()):
            errors.append("HTML 内嵌批注包必须位于 QA_EMBEDDED_REVIEW_START/END 标记之间且顺序正确")

    payload = node_match.group(1)
    unsafe_raw_chars = {"<": "<", ">": ">", "&": "&", "\u2028": "U+2028", "\u2029": "U+2029"}
    leaked_chars = [label for char, label in unsafe_raw_chars.items() if char in payload]
    if leaked_chars:
        errors.append("HTML 内嵌批注包 raw-text 含未转义字符：" + "、".join(leaked_chars))

    try:
        pack = json.loads(payload)
    except json.JSONDecodeError as exc:
        errors.append(f"HTML 内嵌批注包不是合法 JSON: {exc.msg}")
        return errors
    if not isinstance(pack, dict) or pack.get("type") != "AgentQuestionPack":
        errors.append("HTML 内嵌批注包 type 必须为 AgentQuestionPack")
        return errors
    if pack.get("version") != "0.3.0":
        errors.append("HTML 内嵌批注包 version 必须为 0.3.0")
    round_id = pack.get("roundId")
    if round_id is not None and (not isinstance(round_id, str) or not round_id.strip()):
        errors.append("HTML 内嵌批注包 roundId 必须是非空字符串")
    annotations = pack.get("annotations")
    if not isinstance(annotations, list) or not all(isinstance(item, dict) for item in annotations):
        errors.append("HTML 内嵌批注包 annotations 必须是对象数组")
    elif annotations:
        required_annotation_fields = {
            "id", "sectionTitle", "blockId", "contextBefore", "contextAfter", "kind", "text", "createdAt"
        }
        annotation_ids: list[str] = []
        for index, item in enumerate(annotations, start=1):
            missing = sorted(required_annotation_fields - item.keys())
            invalid = [
                field
                for field in ("id", "sectionTitle", "blockId", "kind", "text", "createdAt")
                if field in item and (not isinstance(item[field], str) or not item[field].strip())
            ]
            invalid.extend(
                field
                for field in ("contextBefore", "contextAfter")
                if field in item and not isinstance(item[field], str)
            )
            has_source_text = any(
                isinstance(item.get(field), str) and item[field].strip() for field in ("selectedText", "blockText")
            )
            if missing or invalid or not has_source_text:
                detail = ("缺少 " + "、".join(missing)) if missing else ""
                if invalid:
                    detail += ("；" if detail else "") + "字段值无效 " + "、".join(sorted(set(invalid)))
                if not has_source_text:
                    detail += ("；" if detail else "") + "缺少 selectedText/blockText 原文"
                errors.append(f"HTML 内嵌批注包第 {index} 条 annotation 字段不完整：{detail}")
            block_id = item.get("blockId")
            if isinstance(block_id, str) and block_id.strip() and block_ids is not None:
                match_count = block_ids.count(block_id)
                if match_count != 1:
                    errors.append(
                        f"HTML 内嵌批注包第 {index} 条 annotation 的 blockId={block_id} "
                        f"在当前 HTML 的 main 中命中 {match_count} 个节点，必须恰好为 1"
                    )
            annotation_id = item.get("id")
            if isinstance(annotation_id, str) and annotation_id.strip():
                annotation_ids.append(annotation_id)
        annotation_id_counts: dict[str, int] = {}
        for annotation_id in annotation_ids:
            annotation_id_counts[annotation_id] = annotation_id_counts.get(annotation_id, 0) + 1
        duplicate_annotation_ids = sorted(
            annotation_id for annotation_id, count in annotation_id_counts.items() if count > 1
        )
        if duplicate_annotation_ids:
            errors.append("HTML 内嵌批注包 annotation.id 必须唯一，发现重复：" + "、".join(duplicate_annotation_ids))
    source = pack.get("source")
    if not isinstance(source, dict) or not all(
        isinstance(source.get(key), str) and source[key] for key in ("fileName", "absolutePath", "fileUrl")
    ):
        errors.append("HTML 内嵌批注包 source 必须包含 fileName、absolutePath 和 fileUrl")
    delivery = pack.get("delivery")
    if not isinstance(delivery, dict) or delivery.get("mode") != "embedded-html":
        errors.append("HTML 内嵌批注包 delivery.mode 必须为 embedded-html")
    else:
        instruction = delivery.get("instruction")
        if (
            delivery.get("status") != "ready-for-agent"
            or not isinstance(instruction, str)
            or not instruction.strip()
            or "inject_annotation_mode.py" not in instruction
            or "check_html_report.py" not in instruction
        ):
            errors.append("HTML 内嵌批注包 delivery 必须包含 ready-for-agent 状态和完整的重新注入、校验 instruction")
        elif not required and ("--processed" not in instruction or "--require-review-receipt" not in instruction):
            errors.append("新批注包 delivery.instruction 必须要求 Agent 写入并校验处理回执")
    if not isinstance(pack.get("exportedAt"), str) or not pack["exportedAt"].strip():
        errors.append("HTML 内嵌批注包必须包含非空 exportedAt")
    return errors


def check_embedded_review_receipt(html: str, required: bool = False) -> list[str]:
    """校验 Agent 回写后的唯一处理回执，避免把“批注消失”误判为已完成。"""

    errors: list[str] = []
    start_matches = list(EMBEDDED_REVIEW_RECEIPT_START_RE.finditer(html))
    end_matches = list(EMBEDDED_REVIEW_RECEIPT_END_RE.finditer(html))
    node_matches = list(EMBEDDED_REVIEW_RECEIPT_DATA_RE.finditer(html))
    if not start_matches and not end_matches and not node_matches:
        if required:
            errors.append("未找到 AgentReviewReceipt；无法确认 Agent 是否处理并回写了当前 HTML")
        return errors
    if len(start_matches) != 1 or len(end_matches) != 1:
        errors.append("处理回执必须且只能包含一对 QA_AGENT_REVIEW_RECEIPT_START/END 标记")
    if len(node_matches) != 1:
        errors.append("处理回执必须且只能包含一个 #qaEmbeddedReviewReceipt[data-qa-review-receipt] 节点")
        return errors

    node_match = node_matches[0]
    opening_tag = node_match.group(0).split(">", 1)[0] + ">"
    if not re.search(r"\btype\s*=\s*[\"']application/json[\"']", opening_tag, re.IGNORECASE):
        errors.append("AgentReviewReceipt 节点 type 必须为 application/json")
    if len(start_matches) == 1 and len(end_matches) == 1:
        if not (start_matches[0].end() <= node_match.start() < node_match.end() <= end_matches[0].start()):
            errors.append("AgentReviewReceipt 必须位于处理回执标记之间且顺序正确")

    payload = node_match.group(1)
    unsafe_raw_chars = {"<": "<", ">": ">", "&": "&", "\u2028": "U+2028", "\u2029": "U+2029"}
    leaked_chars = [label for char, label in unsafe_raw_chars.items() if char in payload]
    if leaked_chars:
        errors.append("AgentReviewReceipt raw-text 含未转义字符：" + "、".join(leaked_chars))
    try:
        receipt = json.loads(payload)
    except json.JSONDecodeError as exc:
        errors.append(f"AgentReviewReceipt 不是合法 JSON: {exc.msg}")
        return errors
    if not isinstance(receipt, dict) or receipt.get("type") != "AgentReviewReceipt":
        errors.append("处理回执 type 必须为 AgentReviewReceipt")
        return errors
    if receipt.get("version") != "0.1.0":
        errors.append("AgentReviewReceipt version 必须为 0.1.0")
    for field in ("roundId", "processedAt", "reportFileName", "reportAbsolutePath", "reportFileUrl"):
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"AgentReviewReceipt.{field} 必须是非空字符串")
    if receipt.get("status") not in {"processed", "partial", "failed"}:
        errors.append("AgentReviewReceipt.status 必须为 processed、partial 或 failed")
    for field in ("total", "handled", "skipped"):
        value = receipt.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"AgentReviewReceipt.{field} 必须是非负整数")
    total = receipt.get("total")
    handled = receipt.get("handled")
    if isinstance(total, int) and isinstance(handled, int) and handled > total:
        errors.append("AgentReviewReceipt.handled 不能大于 total")
    content_changed = receipt.get("contentChanged")
    if content_changed is not True and content_changed is not False and content_changed is not None:
        errors.append("AgentReviewReceipt.contentChanged 必须为 true、false 或 null")
    changed_sections = receipt.get("changedSections")
    if not isinstance(changed_sections, list) or not all(isinstance(item, str) for item in changed_sections):
        errors.append("AgentReviewReceipt.changedSections 必须是字符串数组")
    results = receipt.get("results")
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        errors.append("AgentReviewReceipt.results 必须是对象数组")
        return errors
    result_ids: list[str] = []
    allowed_statuses = {"processed", "applied", "answered", "skipped", "failed"}
    for index, result in enumerate(results, start=1):
        annotation_id = result.get("annotationId")
        if not isinstance(annotation_id, str) or not annotation_id.strip():
            errors.append(f"AgentReviewReceipt.results 第 {index} 项缺少非空 annotationId")
        else:
            result_ids.append(annotation_id)
        if result.get("status") not in allowed_statuses:
            errors.append(f"AgentReviewReceipt.results 第 {index} 项 status 无效")
        if not isinstance(result.get("message", ""), str):
            errors.append(f"AgentReviewReceipt.results 第 {index} 项 message 必须是字符串")
    duplicates = sorted({item for item in result_ids if result_ids.count(item) > 1})
    if duplicates:
        errors.append("AgentReviewReceipt annotationId 必须唯一，发现重复：" + "、".join(duplicates))
    return errors


def check_block_id_uniqueness(parser: ReportParser) -> list[str]:
    """批注定位属性必须唯一，否则点击定位会命中错误正文节点。"""

    counts: dict[str, int] = {}
    for block_id in parser.block_ids:
        counts[block_id] = counts.get(block_id, 0) + 1
    duplicates = sorted(block_id for block_id, count in counts.items() if count > 1)
    if not duplicates:
        return []
    return ["发现重复 data-block-id：" + "、".join(duplicates) + "；批注定位属性必须唯一"]


def check_media_support(parser: ReportParser, report_path: Path, css: str) -> tuple[list[str], list[str]]:
    """检查已出现在报告里的图片/视频证据。

    媒体不是所有报告的必需内容；这里不要求报告必须有图片或视频。只有当报告已经使用
    <img>/<video> 或媒体文件链接时，才检查断链、基础可访问性和响应式保护。
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not parser.media_items and not parser.media_resources:
        return errors, warnings

    for resource in parser.media_resources:
        local_path = local_resource_path(resource.src, report_path)
        if local_path and not local_path.is_file():
            errors.append(f"第 {resource.line} 行 {resource.tag} 引用的媒体文件不存在: {resource.src}")

    compact_css = re.sub(r"\s+", " ", css)
    if not ("img" in compact_css and "video" in compact_css and "max-width: 100%" in compact_css and "height: auto" in compact_css):
        errors.append("报告使用了图片/视频，但 CSS 缺少图片/视频响应式保护（建议 img, svg, canvas, video { max-width: 100%; height: auto; }）")

    figure_by_index = {figure.index: figure for figure in parser.figures}
    for index, media in enumerate(parser.media_items, start=1):
        if media.tag == "img":
            alt = media.attrs.get("alt", "")
            if not alt.strip():
                errors.append(f"第 {media.line} 行第 {index} 个图片缺少非空 alt，影响无障碍阅读和证据理解")
        elif media.tag == "video":
            if "controls" not in media.attrs:
                errors.append(f"第 {media.line} 行第 {index} 个视频缺少 controls，报告内无法直接播放预览")
            if not media.attrs.get("src") and media.source_count == 0:
                errors.append(f"第 {media.line} 行第 {index} 个视频没有 src 或 <source src>，无法定位媒体文件")
            if media.attrs.get("preload", "").lower() != "metadata":
                warnings.append(f"第 {media.line} 行第 {index} 个视频建议使用 preload=\"metadata\"，避免打开报告时加载完整视频")

        figure = figure_by_index.get(media.figure_index or -1)
        if figure and ("media-evidence" in figure.classes or "media-card" in figure.classes):
            if media.tag == "img":
                if not media.lightbox_enabled:
                    errors.append(
                        f"第 {media.line} 行媒体证据图片必须包在 a.image-lightbox-trigger[data-image-lightbox] 中，保留原图链接并支持点击放大"
                    )
                elif not media.lightbox_href:
                    errors.append(f"第 {media.line} 行图片灯箱触发链接缺少 href 原图地址")
            if not figure.figcaption_text:
                warnings.append(f"第 {media.line} 行媒体证据卡建议提供 figcaption，说明标题、内容和结论")
            if not figure.attrs.get("data-case"):
                warnings.append(f"第 {media.line} 行媒体证据卡建议用 data-case 标注对应 case")
            if not figure.attrs.get("data-conclusion"):
                warnings.append(f"第 {media.line} 行媒体证据卡建议用 data-conclusion 标注证据结论")
        elif media.tag == "video" and (not figure or not figure.figcaption_text):
            warnings.append(f"第 {media.line} 行视频建议配关键帧截图、标题或说明，避免读者必须播放后才知道证据内容")

    return errors, warnings


def check_document_chrome(parser: ReportParser) -> list[str]:
    errors: list[str] = []
    css = "\n".join(parser.style_chunks)

    if not parser.has_viewport_meta:
        errors.append("缺少 viewport meta，窄屏/分屏模式可能显示不全")
    if parser.raw_inline_code_samples:
        samples = "、".join(parser.raw_inline_code_samples)
        errors.append(f"发现未渲染的 Markdown 行内代码 {samples}；请改为 <code>...</code> 并先转义内容")
    if not css.strip():
        errors.append("缺少内嵌 <style>，不符合单文件报告模板")
        return errors

    required_css_fragments = {
        "box-sizing: border-box": "缺少全局 box-sizing，卡片/表格在窄屏下更容易溢出",
        "@media (max-width": "缺少窄屏响应式样式，分屏或移动端可能显示不全",
        "@media print": "缺少打印样式，彩色/黑白打印或预览可能显示不全",
    }
    compact_css = re.sub(r"\s+", " ", css)
    for fragment, message in required_css_fragments.items():
        if fragment not in compact_css:
            errors.append(message)

    if parser.has_toc:
        if parser.has_toc_details:
            errors.append("目录不要使用 <details class=\"toc-details\">；应保持旧版浮动侧栏，并用 .toc-toggle 收起/展开整个侧栏")
        if not parser.has_toc_title:
            errors.append("目录缺少 .toc-title，无法保持旧版浮动目录标题样式")
        if not parser.has_toc_toggle:
            errors.append("目录缺少 .toc-toggle 按钮，无法收起/展开整个目录侧栏")
        if "toc-collapsed" not in css:
            errors.append("目录缺少 .toc-collapsed 样式，无法收起整个目录侧栏")
        if parser.toc_link_count == 0:
            errors.append("目录缺少指向章节 id 的锚点链接")

    if parser.has_non_viewer_diff_card:
        errors.append("发现非 .diff-card.diff-viewer 的 diff 卡片；真实 diff 必须由 highlight_code.py --lang diff --diff-view 生成，避免手写样式漂移")

    return errors


def validate_with_warnings(
    path: Path,
    require_review_pack: bool = False,
    require_review_receipt: bool = False,
) -> tuple[list[str], list[str]]:
    html = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(html)

    errors = parser.errors
    warnings: list[str] = []
    errors.extend(check_document_chrome(parser))
    css = "\n".join(parser.style_chunks)
    errors.extend(check_component_bundle(html))
    errors.extend(check_behavior_component_markup(html))
    errors.extend(check_file_location_links(html))
    errors.extend(check_table_support(parser, css))
    errors.extend(check_tag_support(html, css))
    errors.extend(check_code_wrap_blocks(html, css))
    errors.extend(check_diff_viewer_blocks(html, css))
    errors.extend(check_raw_unified_diff_outside_viewer(html))
    errors.extend(check_diff_viewer_tokens(html, css))
    errors.extend(check_review_workspaces(html, css))
    errors.extend(
        check_annotation_mode(
            html,
            css,
            require_review_pack=require_review_pack,
            require_review_receipt=require_review_receipt,
            block_ids=parser.block_ids,
        )
    )
    errors.extend(check_block_id_uniqueness(parser))
    media_errors, media_warnings = check_media_support(parser, path, css)
    errors.extend(media_errors)
    warnings.extend(media_warnings)
    return errors, warnings


def validate(path: Path) -> list[str]:
    errors, _ = validate_with_warnings(path)
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="校验 html-report 单文件 HTML 的表格、代码/diff、Review Workspace、外部依赖和已使用的媒体资源。"
    )
    parser.add_argument("html", help="待检查的 HTML 文件路径。")
    parser.add_argument(
        "--require-review-pack",
        action="store_true",
        help="用户已保存批注版 HTML 时，要求文件必须包含唯一、合法的内嵌批注包。",
    )
    parser.add_argument(
        "--require-review-receipt",
        action="store_true",
        help="Agent 已声明处理完成时，要求文件必须包含唯一、合法的 AgentReviewReceipt。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.html)
    if args.require_review_pack and args.require_review_receipt:
        raise ValueError("--require-review-pack 与 --require-review-receipt 不能同时使用")
    errors, warnings = validate_with_warnings(
        path,
        require_review_pack=args.require_review_pack,
        require_review_receipt=args.require_review_receipt,
    )
    if errors:
        print(f"FAIL {path}")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"WARN {warning}")
        raise SystemExit(1)

    print(f"PASS {path}")
    for warning in warnings:
        print(f"WARN {warning}")


if __name__ == "__main__":
    main()
