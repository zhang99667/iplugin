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
from urllib.parse import unquote, urlparse


CODE_WRAP_RE = re.compile(r'<div\b[^>]*class=["\'][^"\']*\bcode-wrap\b[^"\']*["\'][^>]*>.*?</div>', re.DOTALL)
DIFF_VIEWER_RE = re.compile(r'<section\b[^>]*class=["\'][^"\']*\bdiff-viewer\b[^"\']*["\'][^>]*>.*?</section>', re.DOTALL)
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


@dataclass
class TagFrame:
    tag: str
    classes: set[str]


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
        if tag in {"img", "video"}:
            media = MediaItem(
                tag=tag,
                attrs=attr_map,
                line=line,
                figure_index=current_figure.index if current_figure else None,
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

        self.stack.append(TagFrame(tag=tag, classes=classes))

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

        if any(frame.tag in {"code", "pre", "script", "style"} for frame in self.stack):
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


def looks_like_unified_diff(text: str) -> bool:
    return bool(RAW_UNIFIED_DIFF_RE.search(text) or ("diff --git " in text and HUNK_MARKER_RE.search(text)))


def check_code_wrap_blocks(html: str, css: str) -> list[str]:
    errors: list[str] = []
    compact_css = re.sub(r"\s+", " ", css)
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

    compact_css = re.sub(r"\s+", " ", css)
    required_diff_css = {
        ".diff-card": "diff viewer 缺少 .diff-card 基础卡片样式",
        ".diff-header": "diff viewer 缺少 .diff-header 标题区样式",
        ".diff-scroll": "diff viewer 缺少 .diff-scroll 横向滚动容器样式",
        ".diff-viewer .diff-table": "diff viewer 缺少固定表格样式",
        ".diff-viewer .diff-gutter": "diff viewer 缺少紧凑 +/- 轨道样式",
        ".diff-viewer .diff-num": "diff viewer 缺少 old/new 行号列样式",
        ".diff-viewer .diff-code": "diff viewer 缺少代码列样式",
        ".diff-viewer .diff-add .diff-num": "diff viewer 缺少新增行 old/new 行号背景样式",
        ".diff-viewer .diff-del .diff-num": "diff viewer 缺少删除行 old/new 行号背景样式",
        ".diff-viewer .diff-add .diff-gutter": "diff viewer 缺少新增行左侧绿色变更轨道",
        ".diff-viewer .diff-del .diff-gutter": "diff viewer 缺少删除行左侧红色变更轨道",
        ".diff-viewer .diff-hunk .diff-code": "diff viewer 缺少 hunk/meta 行样式",
        "width: 1%": "diff viewer 行号列必须使用自适应内容宽度，避免固定宽列挤占代码区",
        "min-width: 40px": "diff viewer 行号列必须保留 40px 最小宽度，避免 2-4 位行号抖动",
        "min-width: 25px": "diff viewer +/- 轨道必须保持 25px 紧凑宽度",
        "white-space: nowrap": "diff viewer 行号列不能换行，避免 old/new 行号错位",
        "font-variant-numeric: tabular-nums": "diff viewer 行号列必须使用等宽数字，避免 old/new 列抖动",
        "white-space: pre": "diff viewer 代码列必须保持原始空格，避免代码缩进漂移",
    }
    for fragment, message in required_diff_css.items():
        if fragment not in compact_css:
            errors.append(message)

    return errors


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


def check_annotation_mode(
    html: str,
    css: str,
    require_review_pack: bool = False,
    block_ids: list[str] | None = None,
) -> list[str]:
    """检查离线批注模式的关键结构，避免审核版 HTML 交互缺件。"""
    errors: list[str] = []
    # 只识别真实 marker、标签和数据节点；正文代码示例里的同名字符串不能把普通报告误判为审核版。
    has_embedded_review = bool(
        EMBEDDED_REVIEW_START_RE.search(html)
        or EMBEDDED_REVIEW_END_RE.search(html)
        or EMBEDDED_REVIEW_DATA_RE.search(html)
    )
    has_annotation = bool(
        ANNOTATION_MODE_MARKER_RE.search(html)
        or ANNOTATION_SCRIPT_TAG_RE.search(html)
        or ANNOTATION_UI_TAG_RE.search(html)
        or ANNOTATION_CSS_ASSET_RE.search(css)
        or has_embedded_review
    )
    if not has_annotation:
        return ["未找到 HTML 内嵌审核包；请确认用户保存的是含批注审核版，而不是原始版或无批注发布版"] if require_review_pack else errors

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
        'id="qaLauncherLabel"': "批注模式右上角入口必须能在 0 批注时显示“导出无批注版”而不是“批注 0”",
        "updateLauncherMode": "批注模式必须根据批注数量切换右上角“导出无批注版”/“批注 N”入口",
        "publish-mode": "批注模式必须给 0 批注发布入口提供更醒目的视觉状态",
        'id="qaSaveReviewHtml"': "批注侧栏缺少“保存审核结果到 HTML”入口",
        "保存审核结果到 HTML": "批注侧栏必须把 HTML 内嵌交接作为主要审核操作",
        'id="qaExportPublic">导出无批注版</button>': "发布版按钮必须明确标注为不含批注",
        "qa-save-review-btn": "保存审核结果按钮必须作为醒目的主按钮展示",
        "saveReviewHtml": "批注模式缺少保存含批注审核版的交互逻辑",
        "saveHtmlFile": "审核版和发布版必须复用统一的 HTML 保存/下载回退逻辑",
        "reviewFallbackFileName": "下载审核版必须使用与当前草稿不同的默认文件名，避免本地状态碰撞",
        "buildReviewedHtml": "批注模式缺少含批注 HTML 构建逻辑",
        "buildEmbeddedReviewBlock": "批注模式缺少 AgentQuestionPack 内嵌逻辑",
        "serializeReviewPack": "批注模式缺少内嵌 JSON 安全序列化逻辑",
        "\\u003c": "内嵌 JSON 必须转义 <，防止 </script> 提前闭合或注入 HTML",
        "data-qa-review-data": "含批注审核版缺少稳定的内嵌数据节点",
        "readEmbeddedReviewPack": "批注模式缺少从 HTML 恢复内嵌批注的逻辑",
        "stored !== null": "批注加载必须区分 localStorage 不存在与用户明确清空的 []",
        "legacyStorageKey": "批注模式必须兼容迁移旧版 localStorage 草稿键",
        "hasPersistedReviewState": "清空最后一条批注后必须保留审核态，允许把空结果写回 HTML",
        "clearedReviewMode": "清空后的审核态必须使用独立入口并隐藏 0 数量徽标",
        "Math.max(blockSeq": "审核版必须从已有定位 ID 恢复序号，避免 Agent 增段后生成重复 blockId",
        "clearStoredAnnotations": "直接写入 HTML 后必须清理旧本地基线，避免 Agent 更新后复活旧批注",
        "stripEmbeddedReviewBlock": "重复保存和发布版导出必须能剥离旧内嵌审核包",
        "mode: 'embedded-html'": "AgentQuestionPack 必须声明 HTML 内嵌交付模式",
        "inject_annotation_mode.py": "AgentQuestionPack 必须明确处理后重新注入审核模式",
        "取消：取消导出": "导出发布版确认框的取消动作必须真正取消，不能触发下载",
        "buildPublicHtml": "批注模式缺少发布版 HTML 剥离逻辑",
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
        ">提交<": "批注输入浮层只保留一个“提交”按钮",
        'aria-keyshortcuts="Meta+Enter Control+Enter"': "批注输入浮层必须声明 ⌘/Ctrl + Enter 提交快捷键",
        "composerText?.addEventListener('keydown'": "批注输入框缺少局部键盘快捷键监听",
        "isComposerSubmitShortcut": "批注输入浮层缺少快捷键提交判断",
        "event.metaKey || event.ctrlKey": "批注输入浮层必须同时支持 ⌘ + Enter 和 Ctrl + Enter",
        "!event.isComposing": "批注输入浮层必须避开输入法组字阶段，防止 Enter 误提交",
    }
    for fragment, message in required_fragments.items():
        if fragment not in annotation_scope:
            errors.append(message)

    forbidden_fragments = {
        "qaComposerCancel": "批注输入浮层不要保留取消按钮；点击浮层外侧即关闭",
        ">保存<": "批注输入浮层按钮文案应为“提交”，不要使用“保存”",
        "qaDownloadJson": "批注侧栏不再提供独立 JSON 下载，应保存内嵌审核结果到 HTML",
        ">下载 JSON<": "批注侧栏不再提供独立 JSON 下载按钮",
        "建议使用当前文件名覆盖原审核版": "无批注发布版不能再建议覆盖含批注审核版",
        "取消：下载": "导出发布版确认框不能把取消解释为下载",
        "暂无批注可保存": "清空批注后仍必须允许保存空审核包，覆盖 HTML 中的旧批注",
        "result === 'saved' || result === 'downloaded'": "下载只能确认已发起，不能据此清空尚未持久化的本地草稿",
    }
    for fragment, message in forbidden_fragments.items():
        if fragment in annotation_scope:
            errors.append(message)

    compact_css = re.sub(r"\s+", " ", css)
    for fragment, message in {
        ".qa-selection-popover": "批注模式缺少选区气泡样式",
        ".qa-composer": "批注模式缺少输入浮层样式",
        ".qa-sidebar": "批注模式缺少右侧栏样式",
        ".qa-highlight": "批注模式缺少选中文本高亮样式",
        ".qa-panel-open": "批注模式缺少右侧栏打开时的正文避让样式",
    }.items():
        if fragment not in compact_css:
            errors.append(message)

    if ".qa-launcher-count[hidden]" not in compact_css and ".qa-launcher.publish-mode .qa-launcher-count" not in compact_css:
        errors.append("发布模式下必须强制隐藏右上角批注数量徽标，避免导出发布版按钮残留蓝色圆点")

    errors.extend(check_embedded_review_pack(html, required=require_review_pack, block_ids=block_ids))
    return errors


def check_embedded_review_pack(
    html: str,
    required: bool = False,
    block_ids: list[str] | None = None,
) -> list[str]:
    """当 HTML 已保存审核结果时，校验唯一内嵌包的标记、JSON 和 Agent 定位字段。"""

    errors: list[str] = []
    start_matches = list(EMBEDDED_REVIEW_START_RE.finditer(html))
    end_matches = list(EMBEDDED_REVIEW_END_RE.finditer(html))
    node_matches = list(EMBEDDED_REVIEW_DATA_RE.finditer(html))
    if not start_matches and not end_matches and not node_matches:
        if required:
            errors.append("未找到 HTML 内嵌审核包；请确认用户已点击“保存审核结果到 HTML”并提供了该文件")
        return errors
    if len(start_matches) != 1 or len(end_matches) != 1:
        errors.append("含批注审核版必须且只能包含一对 QA_EMBEDDED_REVIEW_START/END 标记")
    if len(node_matches) != 1:
        errors.append("含批注审核版必须且只能包含一个 #qaEmbeddedReviewData[data-qa-review-data] 节点")
        return errors

    node_match = node_matches[0]
    opening_tag = node_match.group(0).split(">", 1)[0] + ">"
    if not re.search(r"\btype\s*=\s*[\"']application/json[\"']", opening_tag, re.IGNORECASE):
        errors.append("HTML 内嵌审核包节点 type 必须为 application/json，不能作为可执行脚本")
    if len(start_matches) == 1 and len(end_matches) == 1:
        if not (start_matches[0].end() <= node_match.start() < node_match.end() <= end_matches[0].start()):
            errors.append("HTML 内嵌审核包必须位于 QA_EMBEDDED_REVIEW_START/END 标记之间且顺序正确")

    payload = node_match.group(1)
    unsafe_raw_chars = {"<": "<", ">": ">", "&": "&", "\u2028": "U+2028", "\u2029": "U+2029"}
    leaked_chars = [label for char, label in unsafe_raw_chars.items() if char in payload]
    if leaked_chars:
        errors.append("HTML 内嵌审核包 raw-text 含未转义字符：" + "、".join(leaked_chars))

    try:
        pack = json.loads(payload)
    except json.JSONDecodeError as exc:
        errors.append(f"HTML 内嵌审核包不是合法 JSON: {exc.msg}")
        return errors
    if not isinstance(pack, dict) or pack.get("type") != "AgentQuestionPack":
        errors.append("HTML 内嵌审核包 type 必须为 AgentQuestionPack")
        return errors
    if pack.get("version") != "0.3.0":
        errors.append("HTML 内嵌审核包 version 必须为 0.3.0")
    annotations = pack.get("annotations")
    if not isinstance(annotations, list) or not all(isinstance(item, dict) for item in annotations):
        errors.append("HTML 内嵌审核包 annotations 必须是对象数组")
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
                errors.append(f"HTML 内嵌审核包第 {index} 条 annotation 字段不完整：{detail}")
            block_id = item.get("blockId")
            if isinstance(block_id, str) and block_id.strip() and block_ids is not None:
                match_count = block_ids.count(block_id)
                if match_count != 1:
                    errors.append(
                        f"HTML 内嵌审核包第 {index} 条 annotation 的 blockId={block_id} "
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
            errors.append("HTML 内嵌审核包 annotation.id 必须唯一，发现重复：" + "、".join(duplicate_annotation_ids))
    source = pack.get("source")
    if not isinstance(source, dict) or not all(
        isinstance(source.get(key), str) and source[key] for key in ("fileName", "absolutePath", "fileUrl")
    ):
        errors.append("HTML 内嵌审核包 source 必须包含 fileName、absolutePath 和 fileUrl")
    delivery = pack.get("delivery")
    if not isinstance(delivery, dict) or delivery.get("mode") != "embedded-html":
        errors.append("HTML 内嵌审核包 delivery.mode 必须为 embedded-html")
    else:
        instruction = delivery.get("instruction")
        if (
            delivery.get("status") != "ready-for-agent"
            or not isinstance(instruction, str)
            or not instruction.strip()
            or "inject_annotation_mode.py" not in instruction
            or "check_html_report.py" not in instruction
        ):
            errors.append("HTML 内嵌审核包 delivery 必须包含 ready-for-agent 状态和完整的重新注入、校验 instruction")
    if not isinstance(pack.get("exportedAt"), str) or not pack["exportedAt"].strip():
        errors.append("HTML 内嵌审核包必须包含非空 exportedAt")
    return errors


def check_block_id_uniqueness(parser: ReportParser) -> list[str]:
    """审核定位属性必须唯一，否则批注点击定位会命中错误正文节点。"""

    counts: dict[str, int] = {}
    for block_id in parser.block_ids:
        counts[block_id] = counts.get(block_id, 0) + 1
    duplicates = sorted(block_id for block_id, count in counts.items() if count > 1)
    if not duplicates:
        return []
    return ["发现重复 data-block-id：" + "、".join(duplicates) + "；审核定位属性必须唯一"]


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
        "overflow-x: auto": "缺少横向滚动保护，宽表格/代码块/ASCII 图可能显示不全",
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


def validate_with_warnings(path: Path, require_review_pack: bool = False) -> tuple[list[str], list[str]]:
    html = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(html)

    errors = parser.errors
    warnings: list[str] = []
    errors.extend(check_document_chrome(parser))
    css = "\n".join(parser.style_chunks)
    errors.extend(check_code_wrap_blocks(html, css))
    errors.extend(check_diff_viewer_blocks(html, css))
    errors.extend(check_raw_unified_diff_outside_viewer(html))
    errors.extend(check_diff_viewer_tokens(html, css))
    errors.extend(
        check_annotation_mode(
            html,
            css,
            require_review_pack=require_review_pack,
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
    parser = argparse.ArgumentParser(description="校验 html-report 单文件 HTML 的代码块、外部依赖和已使用的媒体资源。")
    parser.add_argument("html", help="待检查的 HTML 文件路径。")
    parser.add_argument(
        "--require-review-pack",
        action="store_true",
        help="用户已声明完成 HTML 批注时，要求文件必须包含唯一、合法的内嵌审核包。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.html)
    errors, warnings = validate_with_warnings(path, require_review_pack=args.require_review_pack)
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
