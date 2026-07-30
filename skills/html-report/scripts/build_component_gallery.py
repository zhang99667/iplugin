#!/usr/bin/env python3
"""使用正式组件生成器构建 html-report 的标准组件 Gallery。"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import assemble_report
import build_review_workspace
import check_html_report
import highlight_code
import inject_annotation_mode


SKILL_DIR = Path(__file__).resolve().parents[1]
GALLERY_DIR = SKILL_DIR / "assets" / "component-gallery"
SOURCE_PATH = GALLERY_DIR / "source.html"
OUTPUT_PATH = GALLERY_DIR / "component-gallery.html"


SAMPLE_CODE = """from pathlib import Path


def build_report(source: Path, output: Path) -> None:
    \"\"\"装配组件并写入离线单文件报告。\"\"\"

    html = source.read_text(encoding=\"utf-8\")
    assembled, components = assemble_html(html)
    output.write_text(assembled, encoding=\"utf-8\")
    print(f\"components={{','.join(components)}}\")
"""

SAMPLE_DIFF = """diff --git a/report.py b/report.py
index 5f67da1..9cb52bf 100644
--- a/report.py
+++ b/report.py
@@ -8,2 +8,4 @@ def build_report(source: Path, output: Path) -> None:
-    output.write_text(html, encoding=\"utf-8\")
+    assembled, components = assemble_html(html)
+    output.write_text(assembled, encoding=\"utf-8\")
+    print(f\"components={','.join(components)}\")
"""

SAMPLE_MEDIA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620" viewBox="0 0 1200 620">
<rect width="1200" height="620" fill="#f8fafc"/>
<rect x="70" y="110" width="300" height="400" rx="24" fill="#eff6ff" stroke="#2563eb" stroke-width="4"/>
<rect x="450" y="110" width="300" height="400" rx="24" fill="#f0fdf4" stroke="#15803d" stroke-width="4"/>
<rect x="830" y="110" width="300" height="400" rx="24" fill="#fff7ed" stroke="#c2410c" stroke-width="4"/>
<text x="220" y="285" text-anchor="middle" font-family="Arial,sans-serif" font-size="42" font-weight="700" fill="#1e3a8a">Content</text>
<text x="600" y="285" text-anchor="middle" font-family="Arial,sans-serif" font-size="42" font-weight="700" fill="#166534">Behavior</text>
<text x="980" y="285" text-anchor="middle" font-family="Arial,sans-serif" font-size="42" font-weight="700" fill="#9a3412">Pattern</text>
<text x="220" y="340" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#475569">table · code · media</text>
<text x="600" y="340" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#475569">tabs · sort · lightbox</text>
<text x="980" y="340" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#475569">diff · workspace</text>
</svg>"""


def sample_media_uri() -> str:
    """用确定性 data URI 提供可放大的媒体样例，避免 Gallery 引入外部文件。"""

    encoded = base64.b64encode(SAMPLE_MEDIA_SVG.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def sample_workspace() -> str:
    """使用正式 Workspace builder 生成两版本样例，不复制复合组件 DOM。"""

    with tempfile.TemporaryDirectory(prefix="html-report-gallery-") as directory:
        temp_dir = Path(directory)
        before_path = temp_dir / "ReportBuilder.before.py"
        after_path = temp_dir / "ReportBuilder.after.py"
        before_path.write_text("def build(html):\n    return html\n", encoding="utf-8")
        after_path.write_text(
            "def build(html):\n    assembled, _ = assemble_html(html)\n    return assembled\n",
            encoding="utf-8",
        )
        spec: dict[str, Any] = {
            "workspace_id": "component-gallery-workspace",
            "title": "Review Workspace",
            "versions": [
                {"id": "before", "label": "Before", "jump_label": "Before"},
                {"id": "after", "label": "After", "jump_label": "After"},
            ],
            "legend": {
                "focus": "参考行",
                "primary": "Before ↔ After 差异",
                "secondary": "补充差异",
            },
            "files": [
                {
                    "id": "report-builder",
                    "filename": "ReportBuilder.py",
                    "path": "report/ReportBuilder.py",
                    "display_path": "ReportBuilder.py:2-3",
                    "absolute_path": "/repo/demo/report/ReportBuilder.py",
                    "idea_line": 2,
                    "group": "gallery",
                    "status": {"id": "modified", "label": "已修改", "tone": "warning"},
                    "relation": "Before ≠ After",
                    "reference": "参考行：2-3",
                    "conclusion": "修改后通过统一装配器生成报告。",
                    "action": "核对组件声明与最终校验结果。",
                    "versions": {
                        "before": {
                            "source_path": str(before_path),
                            "language": "python",
                            "marks": {"primary": [2], "secondary": [], "focus": [2]},
                        },
                        "after": {
                            "source_path": str(after_path),
                            "language": "python",
                            "marks": {"primary": [2, 3], "secondary": [], "focus": [2]},
                        },
                    },
                }
            ],
        }
        config = build_review_workspace.build_config(spec, GALLERY_DIR / "workspace.json")
        return build_review_workspace.render_fragment(config, include_runtime=True)


def replace_once(source: str, marker: str, replacement: str) -> str:
    """要求每个占位符只出现一次，避免模板拼写错误生成半成品 Gallery。"""

    count = source.count(marker)
    if count != 1:
        raise ValueError(f"Gallery 模板占位符 {marker} 应出现 1 次，实际 {count} 次")
    return source.replace(marker, replacement)


def render_gallery(source: str) -> tuple[str, list[str]]:
    """装配全部注册组件并注入评论模式，返回最终 HTML 和组件声明。"""

    rendered = replace_once(
        source,
        "{{CODE_BLOCK}}",
        highlight_code.render_code_wrap(SAMPLE_CODE, "python"),
    )
    rendered = replace_once(
        rendered,
        "{{DIFF_VIEWER}}",
        highlight_code.render_diff_viewer(SAMPLE_DIFF),
    )
    rendered = replace_once(rendered, "{{REVIEW_WORKSPACE}}", sample_workspace())
    if rendered.count("{{MEDIA_URI}}") != 2:
        raise ValueError("Gallery 模板中的 {{MEDIA_URI}} 应出现 2 次")
    rendered = rendered.replace("{{MEDIA_URI}}", sample_media_uri())
    for marker in ("{{CODE_BLOCK}}", "{{DIFF_VIEWER}}", "{{REVIEW_WORKSPACE}}", "{{MEDIA_URI}}"):
        if marker in rendered:
            raise ValueError(f"Gallery 模板仍包含未替换占位符: {marker}")

    assembled, components = assemble_report.assemble_html(rendered)
    registered = set(assemble_report.load_registry()["components"])
    missing = sorted(registered - set(components))
    if missing:
        raise ValueError("Gallery 未覆盖注册组件: " + ", ".join(missing))
    # Gallery 需要同时验收评论复合模块，但不把它错误注册成普通页面组件。
    annotated = inject_annotation_mode.inject_annotation_mode(assembled)
    # 组件资产中的缩进行空白不影响浏览器，但提交的生成物必须稳定通过 diff 检查。
    normalized = "\n".join(line.rstrip() for line in annotated.splitlines()) + "\n"
    return normalized, components


def validate_output(path: Path) -> None:
    errors = check_html_report.validate(path)
    if errors:
        raise ValueError("Gallery 校验失败:\n- " + "\n- ".join(errors))


def build(output: Path) -> str:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    rendered, components = render_gallery(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    validate_output(output)
    return ", ".join(components)


def check_current(output: Path) -> None:
    if not output.is_file():
        raise ValueError(f"Gallery 文件不存在: {output}")
    expected, _ = render_gallery(SOURCE_PATH.read_text(encoding="utf-8"))
    actual = output.read_text(encoding="utf-8")
    if actual != expected:
        raise ValueError(f"Gallery 已过期，请重新运行 {Path(__file__).name}")
    validate_output(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建或检查 html-report 组件 Gallery。")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="输出文件路径。")
    parser.add_argument("--check", action="store_true", help="检查已提交 Gallery 是否与源码和组件资产一致。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.expanduser().resolve()
    try:
        if args.check:
            check_current(output)
            print(f"PASS {output}")
        else:
            components = build(output)
            print(f"PASS {output}")
            print("components: " + components)
    except (OSError, ValueError, build_review_workspace.SpecError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
