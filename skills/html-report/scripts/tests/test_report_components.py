#!/usr/bin/env python3
"""回归 html-report 中最容易发生视觉漂移的表格和多文件 diff 组件。"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = ROOT / "skills" / "html-report"


def load_module(name: str, path: Path):
    """按文件路径加载脚本，测试无需修改仓库的 Python 包结构。"""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载测试模块: {path}")
    module = importlib.util.module_from_spec(spec)
    # Python 3.14 的 dataclass 会从 sys.modules 回查类型注解所在模块，执行前必须先注册。
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


highlight_code = load_module("html_report_highlight_code_test", SKILL_DIR / "scripts" / "highlight_code.py")
check_html_report = load_module("html_report_check_test", SKILL_DIR / "scripts" / "check_html_report.py")


class ReportComponentTest(unittest.TestCase):
    def test_multi_file_diff_is_split_into_independent_cards(self) -> None:
        source = (SKILL_DIR / "evals" / "fixtures" / "code_review_patch.diff").read_text(encoding="utf-8")

        rendered = highlight_code.render_diff_viewer(source)
        cards = check_html_report.DIFF_VIEWER_RE.findall(rendered)

        self.assertEqual(2, len(cards))
        self.assertIn("FeedDetailViewModel.kt", cards[0])
        self.assertIn("FeedBridge.m", cards[1])
        self.assertTrue(all(card.count("diff --git ") == 1 for card in cards))

    def test_single_file_diff_keeps_one_card(self) -> None:
        source = (SKILL_DIR / "evals" / "fixtures" / "focused_diff_patch.diff").read_text(encoding="utf-8")

        rendered = highlight_code.render_diff_viewer(source)

        self.assertEqual(1, len(check_html_report.DIFF_VIEWER_RE.findall(rendered)))
        self.assertIn('<span class="diff-file"', rendered)

    def test_non_git_multi_file_diff_is_also_split(self) -> None:
        source = """--- a/One.kt
+++ b/One.kt
@@ -1 +1 @@
-val one = 1
+val one = 2
--- a/Two.kt
+++ b/Two.kt
@@ -1 +1 @@
-val two = 1
+val two = 2
"""

        rendered = highlight_code.render_diff_viewer(source)

        self.assertEqual(2, len(check_html_report.DIFF_VIEWER_RE.findall(rendered)))
        self.assertIn("One.kt", rendered)
        self.assertIn("Two.kt", rendered)

    def test_generated_multi_file_diff_passes_full_validation(self) -> None:
        source = (SKILL_DIR / "evals" / "fixtures" / "code_review_patch.diff").read_text(encoding="utf-8")
        css = "\n".join(
            (SKILL_DIR / "references" / "css" / name).read_text(encoding="utf-8")
            for name in ("base.css", "code-diff.css")
        )
        html = self.report_html(css, highlight_code.render_diff_viewer(source))

        self.assertEqual([], self.validate_html(html))

    def test_validator_rejects_multi_file_diff_in_one_card(self) -> None:
        source = (SKILL_DIR / "evals" / "fixtures" / "code_review_patch.diff").read_text(encoding="utf-8")
        css = "\n".join(
            (SKILL_DIR / "references" / "css" / name).read_text(encoding="utf-8")
            for name in ("base.css", "code-diff.css")
        )
        html = self.report_html(css, highlight_code.render_diff_viewer_block(source))

        errors = self.validate_html(html)

        self.assertTrue(any("必须由 highlight_code.py 自动拆成每文件一个卡片" in error for error in errors))

    def test_base_table_component_passes_validation(self) -> None:
        css = (SKILL_DIR / "references" / "css" / "base.css").read_text(encoding="utf-8")
        html = self.report_html(css, '<div class="table-wrap"><table><tr><th>项目</th></tr><tr><td>通过</td></tr></table></div>')

        self.assertEqual([], self.validate_html(html))

    def test_table_without_wrapper_or_full_grid_is_rejected(self) -> None:
        css = """
        * { box-sizing: border-box; }
        .table-wrap { overflow-x: auto; }
        .table-wrap table:not(.diff-table) { border-collapse: collapse; }
        .table-wrap table:not(.diff-table) th,
        .table-wrap table:not(.diff-table) td { border-bottom: 1px solid #ddd; }
        @media (max-width: 720px) { body { margin: 0; } }
        @media print { body { color: #000; } }
        """
        html = self.report_html(css, "<table><tr><th>项目</th></tr><tr><td>失败</td></tr></table>")

        errors = self.validate_html(html)

        self.assertTrue(any("未包在 .table-wrap" in error for error in errors))
        self.assertTrue(any("缺少完整 1px 网格线" in error for error in errors))

    @staticmethod
    def report_html(css: str, body: str) -> str:
        """构造满足通用页面门禁的最小单文件报告。"""

        return f"""<!doctype html>
<html lang="zh-CN"><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style></head><body><main>{body}</main></body></html>"""

    @staticmethod
    def validate_html(content: str) -> list[str]:
        """通过真实文件入口运行校验，覆盖解析器和各组件门禁的组合行为。"""

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.html"
            path.write_text(content, encoding="utf-8")
            return check_html_report.validate(path)


if __name__ == "__main__":
    unittest.main()
