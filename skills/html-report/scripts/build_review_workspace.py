#!/usr/bin/env python3
"""根据 JSON 规格生成可内联的多版本 Review Workspace。

脚本负责读取源码快照、生成安全静态高亮、校验行号标记，并把 JSON 做 raw-text
转义后嵌入 HTML。最终交互由 assets/review-workspace/workspace.js 提供。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from assemble_report import assemble_html
from highlight_code import highlight, normalize_lang


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = SKILL_ROOT / "assets" / "review-workspace" / "workspace.js"
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
MARK_NAMES = ("primary", "secondary", "focus", "context")
STATUS_TONES = {"neutral", "info", "success", "warning", "danger"}
IDE_LABELS = {"idea": "IDEA", "xcode": "Xcode"}


class SpecError(ValueError):
    """输入规格不满足组件契约。"""


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpecError(f"{label} 必须是 JSON 对象")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{label} 必须是非空字符串")
    return value.strip()


def require_id(value: Any, label: str) -> str:
    identifier = require_text(value, label)
    if not ID_RE.fullmatch(identifier):
        raise SpecError(f"{label} 只允许小写字母、数字、下划线和短横线，且必须以字母开头")
    return identifier


def optional_text(value: Any, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def normalize_ide(value: Any, label: str) -> str:
    """规范化可选 IDE 标识，空值表示继续使用技术方案默认值"""

    if value is None or value == "":
        return ""
    ide = require_text(value, label).lower()
    if ide not in IDE_LABELS:
        raise SpecError(f"{label} 必须是 {', '.join(sorted(IDE_LABELS))} 之一")
    return ide


def optional_positive_line(value: Any, label: str) -> int | None:
    """校验可选跳转行，显式排除 Python 中与整数相等的布尔值"""

    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SpecError(f"{label} 必须是正整数")
    return value


def normalize_lines(source: str) -> list[str]:
    """按编辑器行号语义拆分源码；空文件仍保留一行，避免窗格完全空白。"""

    lines = source.splitlines()
    return lines or [""]


def normalize_mark_lines(value: Any, label: str, line_count: int) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError(f"{label} 必须是行号数组")

    normalized: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise SpecError(f"{label} 只能包含整数行号")
        if item < 1 or item > line_count:
            raise SpecError(f"{label} 包含越界行号 {item}，当前源码共 {line_count} 行")
        normalized.append(item)
    return sorted(set(normalized))


def default_context(marks: dict[str, list[int]], line_count: int, radius: int = 3) -> list[int]:
    """没有显式 context 时自动扩展差异行上下文，保证“只看差异”仍可读。"""

    anchors = set(marks["primary"]) | set(marks["secondary"]) | set(marks["focus"])
    if not anchors:
        return list(range(1, line_count + 1))

    context: set[int] = set()
    for anchor in anchors:
        start = max(1, anchor - radius)
        end = min(line_count, anchor + radius)
        context.update(range(start, end + 1))
    return sorted(context)


def build_ide_href(absolute_path: str, line: int | None, ide: str) -> str:
    if not absolute_path:
        return ""
    href = f"{ide}://open?file={quote(absolute_path, safe='/')}"
    if line:
        href += f"&line={line}"
    return href


def first_focus_line(file_versions: dict[str, Any], version_ids: list[str]) -> int | None:
    """优先使用较新的右侧版本焦点行，符合审阅时从结果回看来源的习惯。"""

    for version_id in reversed(version_ids):
        marks = require_object(file_versions[version_id].get("marks", {}), f"versions.{version_id}.marks")
        focus = marks.get("focus")
        if isinstance(focus, list) and focus and isinstance(focus[0], int):
            return focus[0]
    return None


def read_versions(spec: dict[str, Any]) -> list[dict[str, str]]:
    versions = spec.get("versions")
    if not isinstance(versions, list) or not 2 <= len(versions) <= 3:
        raise SpecError("versions 必须包含 2 到 3 个版本")

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(versions, start=1):
        item = require_object(raw, f"versions[{index}]")
        version_id = require_id(item.get("id"), f"versions[{index}].id")
        if version_id in seen:
            raise SpecError(f"versions id 重复：{version_id}")
        seen.add(version_id)
        result.append(
            {
                "id": version_id,
                "label": require_text(item.get("label"), f"versions[{index}].label"),
                "jumpLabel": optional_text(item.get("jump_label"), optional_text(item.get("label"))),
                "ref": optional_text(item.get("ref")),
            }
        )
    return result


def build_source(
    raw: dict[str, Any],
    label: str,
    spec_dir: Path,
    default_ref: str,
) -> dict[str, Any]:
    source_path_text = require_text(raw.get("source_path"), f"{label}.source_path")
    source_path = Path(source_path_text).expanduser()
    if not source_path.is_absolute():
        source_path = spec_dir / source_path
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise SpecError(f"{label}.source_path 不存在：{source_path}")

    try:
        language = normalize_lang(require_text(raw.get("language"), f"{label}.language"))
    except SystemExit as error:
        raise SpecError(f"{label}.language 不受支持：{error}") from error
    source_lines = normalize_lines(source_path.read_text(encoding="utf-8"))
    marks_raw = require_object(raw.get("marks", {}), f"{label}.marks")
    marks = {
        name: normalize_mark_lines(marks_raw.get(name), f"{label}.marks.{name}", len(source_lines))
        for name in MARK_NAMES
    }
    if "context" not in marks_raw:
        marks["context"] = default_context(marks, len(source_lines))

    # Workspace 逐行切换和定位，不适合跨行 token；逐行调用 builtin 高亮能保持稳定闭合标签。
    highlighted_lines = [highlight(line, language) for line in source_lines]
    return {
        "ref": optional_text(raw.get("ref"), default_ref),
        "language": language,
        "lines": highlighted_lines,
        "marks": marks,
    }


def build_status(raw: Any, label: str) -> dict[str, str]:
    status = require_object({} if raw is None else raw, label)
    status_id = require_id(status.get("id", "unclassified"), f"{label}.id")
    tone = optional_text(status.get("tone"), "neutral")
    if tone not in STATUS_TONES:
        raise SpecError(f"{label}.tone 必须是 {', '.join(sorted(STATUS_TONES))} 之一")
    return {
        "id": status_id,
        "label": optional_text(status.get("label"), status_id),
        "tone": tone,
    }


def build_file(
    raw: dict[str, Any],
    index: int,
    versions: list[dict[str, str]],
    spec_dir: Path,
    default_ide: str,
) -> dict[str, Any]:
    label = f"files[{index}]"
    file_id = require_id(raw.get("id"), f"{label}.id")
    filename = require_text(raw.get("filename"), f"{label}.filename")
    raw_versions = require_object(raw.get("versions"), f"{label}.versions")
    version_ids = [version["id"] for version in versions]

    missing = [version_id for version_id in version_ids if version_id not in raw_versions]
    extra = [version_id for version_id in raw_versions if version_id not in version_ids]
    if missing or extra:
        details = []
        if missing:
            details.append("缺少 " + "、".join(missing))
        if extra:
            details.append("多出 " + "、".join(extra))
        raise SpecError(f"{label}.versions 与顶层 versions 不一致：" + "；".join(details))

    absolute_path = optional_text(raw.get("absolute_path"))
    # IDE deep link 必须拿到可直接定位的绝对路径；相对路径只能作为普通文本展示
    if absolute_path and not Path(absolute_path).is_absolute():
        raise SpecError(f"{label}.absolute_path 必须是绝对路径")

    built_versions = {
        version["id"]: build_source(
            require_object(raw_versions[version["id"]], f"{label}.versions.{version['id']}"),
            f"{label}.versions.{version['id']}",
            spec_dir,
            version["ref"],
        )
        for version in versions
    }

    explicit_ide = normalize_ide(raw.get("ide"), f"{label}.ide")
    ide = explicit_ide or default_ide or "idea"

    focus_line = optional_positive_line(raw.get("ide_line"), f"{label}.ide_line")
    legacy_idea_line = optional_positive_line(raw.get("idea_line"), f"{label}.idea_line")
    if focus_line is not None and legacy_idea_line is not None and focus_line != legacy_idea_line:
        raise SpecError(f"{label}.ide_line 与兼容字段 idea_line 不一致")
    if focus_line is None:
        focus_line = legacy_idea_line
    if focus_line is None:
        focus_line = first_focus_line(raw_versions, version_ids)

    path_text = optional_text(raw.get("path"), filename)
    explicit_display_path = optional_text(raw.get("display_path"))
    display_path = explicit_display_path or (f"{filename}:{focus_line}" if focus_line else filename)
    line_suffix = re.search(r":\d+(?:-\d+)?$", display_path)
    location_title = absolute_path or path_text
    if line_suffix and not re.search(r":\d+(?:-\d+)?$", location_title):
        location_title += line_suffix.group(0)
    return {
        "id": file_id,
        "filename": filename,
        "path": path_text,
        "displayPath": display_path,
        "_displayPathExplicit": bool(explicit_display_path),
        "locationTitle": location_title,
        "absolutePath": absolute_path,
        "ideKind": ide,
        "ideLabel": IDE_LABELS[ide],
        "ideHref": build_ide_href(absolute_path, focus_line, ide),
        "group": optional_text(raw.get("group"), optional_text(raw.get("repo"))),
        "status": build_status(raw.get("status"), f"{label}.status"),
        "relation": optional_text(raw.get("relation"), "版本关系未标注"),
        "conclusion": optional_text(raw.get("conclusion"), "未提供"),
        "action": optional_text(raw.get("action"), "未提供"),
        "reference": optional_text(raw.get("reference")),
        "versions": built_versions,
    }


def build_config(spec: dict[str, Any], spec_path: Path) -> dict[str, Any]:
    workspace_id = require_id(spec.get("workspace_id"), "workspace_id")
    versions = read_versions(spec)
    default_ide = normalize_ide(spec.get("default_ide"), "default_ide")
    files_raw = spec.get("files")
    if not isinstance(files_raw, list) or not files_raw:
        raise SpecError("files 必须是非空数组")

    files: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for index, raw in enumerate(files_raw, start=1):
        item = build_file(
            require_object(raw, f"files[{index}]"),
            index,
            versions,
            spec_path.parent,
            default_ide,
        )
        if item["id"] in seen_files:
            raise SpecError(f"files id 重复：{item['id']}")
        seen_files.add(item["id"])
        files.append(item)

    # 默认只展示文件名；同页文件名冲突时补一级父目录，仍避免完整仓库路径撑宽布局。
    filename_counts: dict[str, int] = {}
    for item in files:
        filename_counts[item["filename"]] = filename_counts.get(item["filename"], 0) + 1
    for item in files:
        if filename_counts[item["filename"]] > 1 and not item["_displayPathExplicit"]:
            source_path = item["absolutePath"] or item["path"]
            parent_name = Path(source_path).parent.name
            if parent_name:
                item["displayPath"] = item["displayPath"].replace(
                    item["filename"],
                    f"{parent_name}/{item['filename']}",
                    1,
                )
        item.pop("_displayPathExplicit")

    legend_raw = require_object(spec.get("legend", {}), "legend")
    return {
        "workspaceId": workspace_id,
        "storageKey": optional_text(
            spec.get("storage_key"),
            f"html-report-review-workspace:{workspace_id}",
        ),
        "title": optional_text(spec.get("title"), "Review Workspace"),
        "versions": versions,
        "legend": {
            "focus": optional_text(legend_raw.get("focus"), "参考行 / 修复聚焦行"),
            "primary": optional_text(legend_raw.get("primary"), "主要版本差异"),
            "secondary": optional_text(legend_raw.get("secondary"), "次要版本差异"),
        },
        "files": files,
    }


def script_safe_json(value: Any) -> str:
    """转义 HTML raw-text 敏感字符，防止源码中的结束标签截断 JSON script。"""

    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    replacements = {
        "&": "\\u0026",
        "<": "\\u003c",
        ">": "\\u003e",
        "\u2028": "\\u2028",
        "\u2029": "\\u2029",
    }
    for source, target in replacements.items():
        payload = payload.replace(source, target)
    return payload


def render_static_line(source_html: str, line_number: int, marks: dict[str, list[int]]) -> str:
    """为无 JavaScript 预览生成首文件源码行；runtime 启动后会替换这份静态快照。"""

    classes = ["rw-code-line"]
    if line_number in marks["primary"]:
        classes.append("rw-mark-primary")
    if line_number in marks["secondary"]:
        classes.append("rw-mark-secondary")
    if line_number in marks["focus"]:
        classes.append("rw-focus-line")
    if line_number in marks["context"]:
        classes.append("rw-keep-line")
    code = source_html or "&nbsp;"
    return (
        f'<div class="{" ".join(classes)}" data-line="{line_number}">'
        f'<span class="rw-ln">{line_number}</span><span class="rw-src">{code}</span></div>'
    )


def render_static_mount(config: dict[str, Any]) -> str:
    """输出首文件静态快照，让 Quick Look、禁用 JS 和脚本失败时仍能看到核心证据。"""

    current = config["files"][0]
    status = current["status"]
    path_tag = "a" if current["ideHref"] else "span"
    href = f' href="{html.escape(current["ideHref"], quote=True)}"' if current["ideHref"] else ""
    path_classes = "file-location file-link path rw-path" if "&line=" in current["ideHref"] else "path rw-path"
    nav_items = []
    for index, file in enumerate(config["files"]):
        file_status = file["status"]
        active = " is-active" if index == 0 else ""
        nav_items.append(
            f'<div class="rw-file-item{active}">'
            f'<span class="rw-file-name">{html.escape(file["filename"])}</span>'
            '<span class="rw-file-sub">'
            f'<span class="rw-status rw-tone-{html.escape(file_status["tone"], quote=True)}">'
            f'{html.escape(file_status["label"])}</span>'
            f'<span>{html.escape(file["group"])}</span>'
            "</span></div>"
        )

    panes = []
    for version in config["versions"]:
        source = current["versions"][version["id"]]
        lines = "\n".join(
            render_static_line(source_html, line_number, source["marks"])
            for line_number, source_html in enumerate(source["lines"], start=1)
        )
        panes.append(
            '<div class="rw-code-pane">'
            '<header class="rw-pane-header"><div>'
            f'<span class="rw-pane-title">{html.escape(version["label"])}</span>'
            f'<span class="rw-pane-ref">{html.escape(source["ref"])} · {len(source["lines"])} 行</span>'
            '</div><button class="rw-pane-copy" type="button" disabled>复制</button></header>'
            f'<div class="rw-code-scroll"><div class="rw-code-lines">{lines}</div></div>'
            "</div>"
        )

    legend = config["legend"]
    return (
        '<div class="rw-toolbar">'
        '<input class="rw-input rw-search" type="search" placeholder="筛选文件名、结论或路径" disabled />'
        '<select class="rw-input" disabled><option>全部结论</option></select>'
        '<button class="rw-button is-active" type="button" disabled>同步滚动：开</button>'
        '<button class="rw-button" type="button" disabled>只看差异：关</button>'
        '<button class="rw-button" type="button" disabled>跳到参考行</button>'
        '<span class="rw-toolbar-spacer"></span>'
        f'<span class="rw-progress">静态预览 · {len(config["files"])} 个文件</span>'
        "</div>"
        '<div class="rw-body">'
        f'<nav class="rw-file-nav" aria-label="文件列表">{"".join(nav_items)}</nav>'
        '<div class="rw-stage">'
        '<div class="rw-overview">'
        '<div class="rw-overview-top"><div>'
        f'<h3>{html.escape(current["filename"])}</h3><div class="rw-meta">'
        f'<{path_tag} class="{path_classes}"{href} title="{html.escape(current["locationTitle"], quote=True)}">'
        f'{html.escape(current["displayPath"])}</{path_tag}>'
        f'<span class="rw-status rw-tone-{html.escape(status["tone"], quote=True)}">{html.escape(status["label"])}</span>'
        f'<span class="rw-relation">{html.escape(current["relation"])}</span>'
        "</div></div>"
        f'<div class="rw-reference">{html.escape(current["reference"])}</div></div>'
        f'<p><b>结论：</b>{html.escape(current["conclusion"])}</p>'
        f'<p><b>处理：</b>{html.escape(current["action"])}</p>'
        "</div>"
        f'<div class="rw-panes" style="--rw-pane-count:{len(config["versions"])}">{"".join(panes)}</div>'
        '<div class="rw-legend">'
        f'<span class="rw-legend-item"><i class="rw-legend-dot rw-dot-focus"></i>{html.escape(legend["focus"])}</span>'
        f'<span class="rw-legend-item"><i class="rw-legend-dot rw-dot-primary"></i>{html.escape(legend["primary"])}</span>'
        f'<span class="rw-legend-item"><i class="rw-legend-dot rw-dot-secondary"></i>{html.escape(legend["secondary"])}</span>'
        "</div></div></div>"
    )


def render_fragment(config: dict[str, Any], include_runtime: bool = True) -> str:
    workspace_id = html.escape(config["workspaceId"], quote=True)
    payload = script_safe_json(config)
    static_mount = render_static_mount(config)
    parts = [
        f'<section class="review-workspace" data-review-workspace data-workspace-id="{workspace_id}">',
        f'  <div data-review-workspace-root>{static_mount}</div>',
        f'  <script type="application/json" data-review-workspace-data>{payload}</script>',
        "  <noscript><p>当前显示首文件静态快照；启用 JavaScript 后可切换文件和版本。</p></noscript>",
        "</section>",
    ]
    if include_runtime:
        runtime = RUNTIME_PATH.read_text(encoding="utf-8").rstrip()
        parts.extend(
            [
                '<script data-review-workspace-runtime>',
                runtime,
                "</script>",
            ]
        )
    return "\n".join(parts)


def render_standalone(config: dict[str, Any]) -> str:
    """生成仅用于组件预览和回归检查的完整 HTML。

    预览页也走正式组件装配器，防止 Workspace 维护第二套 CSS 依赖清单。
    """

    title = html.escape(config["title"])
    fragment = render_fragment(config, include_runtime=True)
    source = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
</head>
<body>
<main class="rw-layout-wide">
  <header class="doc-header">
    <h1>{title}</h1>
    <p class="doc-subtitle">Review Workspace 组件预览：多文件、2-3 版本完整源码审阅。</p>
    <div class="doc-meta"><span class="doc-chip">html-report component preview</span></div>
  </header>
  {fragment}
</main>
</body>
</html>
"""
    assembled, _ = assemble_html(source)
    return assembled


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据 JSON 规格生成 html-report Review Workspace。")
    parser.add_argument("spec", help="Workspace JSON 规格文件。")
    parser.add_argument("-o", "--output", help="输出路径；省略时写到 stdout。")
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help="只输出组件和数据，不重复内联 workspace.js；同一报告包含多个 Workspace 时使用。",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="生成完整预览 HTML，供视觉自审和 check_html_report.py 回归；正式报告仍应使用默认片段模式。",
    )
    args = parser.parse_args()
    if args.standalone and args.no_runtime:
        parser.error("--standalone 不能与 --no-runtime 同时使用")
    return args


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec).expanduser().resolve()
    try:
        spec = require_object(json.loads(spec_path.read_text(encoding="utf-8")), "spec")
        config = build_config(spec, spec_path)
        output = render_standalone(config) if args.standalone else render_fragment(
            config,
            include_runtime=not args.no_runtime,
        )
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, SpecError) as error:
        print(f"build_review_workspace.py: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(output_path.resolve())
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")


if __name__ == "__main__":
    main()
