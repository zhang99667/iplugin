#!/usr/bin/env python3
"""回归 html-report 的组件装配、表格、Diff、导航和媒体交互契约。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
assemble_report = load_module("html_report_assemble_test", SKILL_DIR / "scripts" / "assemble_report.py")
inject_annotation_mode = load_module(
    "html_report_annotation_test",
    SKILL_DIR / "scripts" / "inject_annotation_mode.py",
)
sys.modules["highlight_code"] = highlight_code
sys.modules["assemble_report"] = assemble_report
build_review_workspace = load_module(
    "html_report_workspace_test",
    SKILL_DIR / "scripts" / "build_review_workspace.py",
)


class ReportComponentTest(unittest.TestCase):
    def test_annotation_submit_button_exposes_keyboard_shortcut(self) -> None:
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))

        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-shortcut-report.html"),
        )

        self.assertIn('<span class="qa-submit-label">提交</span>', annotated)
        self.assertIn('<kbd class="qa-shortcut-hint" aria-hidden="true">Ctrl/⌘ + Enter</kbd>', annotated)
        self.assertIn('aria-keyshortcuts="Meta+Enter Control+Enter"', annotated)
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-kind",),
                ("flex: 0 0 auto", "white-space: nowrap"),
            )
        )
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-section",),
                ("min-width: 0", "overflow-wrap: anywhere"),
            )
        )
        popover_start = annotated.index('id="qaSelectionPopover"')
        popover_end = annotated.index("</div>", popover_start)
        popover = annotated[popover_start:popover_end]
        self.assertEqual(1, popover.count("<button"))
        self.assertIn('data-qa-action="note-selection"', popover)
        self.assertIn('id="qaSelectionActionLabel">添加批注</span>', popover)
        self.assertEqual([], self.validate_html(annotated))

    def test_annotation_rebind_contract_is_present(self) -> None:
        """失效批注应能在当前正文选区上重绑，而不是要求删除重建。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-rebind-report.html"),
        )

        self.assertIn('id="qaSelectionAction"', annotated)
        self.assertIn("startAnnotationRebind", annotated)
        self.assertIn("buildReboundAnnotation", annotated)
        self.assertIn("main.contains(target.element)", annotated)
        self.assertIn("按 Esc 取消", annotated)
        self.assertNotIn("请删除后在新位置重新添加", annotated)
        self.assertEqual([], self.validate_html(annotated))

    def test_annotation_validator_rejects_missing_rebind_logic(self) -> None:
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-rebind-contract-report.html"),
        )
        broken = annotated.replace("buildReboundAnnotation", "buildAnchorCopy")

        errors = self.validate_html(broken)

        self.assertTrue(any("只更新定位字段" in error for error in errors))

    def test_annotation_launcher_remains_a_stable_sidebar_entry(self) -> None:
        """零批注只隐藏数量，不能把右上角入口变成发布版导出。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-stable-launcher-report.html"),
        )

        launcher_start = annotated.index('id="qaLauncher"')
        launcher_end = annotated.index("</button>", launcher_start)
        launcher = annotated[launcher_start:launcher_end]
        handler_start = annotated.index("launcher?.addEventListener('click'")
        handler_end = annotated.index("closeBtn?.addEventListener", handler_start)
        handler = annotated[handler_start:handler_end]

        self.assertIn('<span class="qa-launcher-label" id="qaLauncherLabel">批注</span>', launcher)
        self.assertIn('id="qaLauncherCount" hidden', launcher)
        self.assertNotIn("导出无批注版", launcher)
        self.assertNotIn("publish-mode", annotated)
        self.assertNotIn('id="qaFilterBar"', annotated)
        self.assertNotIn('data-qa-filter="', annotated)
        self.assertIn('class="qa-quote qa-quote-link"', annotated)
        self.assertIn("setSidebarOpen", handler)
        self.assertNotIn("exportPublicHtml", handler)
        self.assertIn('id="qaCopyForAgent"', annotated)
        self.assertIn('id="qaCopyForAgent" disabled', annotated)
        self.assertIn("copyForAgent.disabled = count === 0", annotated)
        self.assertIn("复制批注给 Agent", annotated)
        self.assertIn("保存批注版 HTML（备用）", annotated)
        self.assertIn('id="qaRoundStatus"', annotated)
        self.assertIn('class="qa-secondary-actions"', annotated)
        self.assertIn('aria-label="保存批注版 HTML（备用）"', annotated)
        self.assertIn('id="qaExportPublic">导出发布版</button>', annotated)
        self.assertIn('id="qaClearAll">清空本轮</button>', annotated)
        self.assertNotIn('id="qaCopyMarkdown"', annotated)
        self.assertNotIn('id="qaDownloadMarkdown"', annotated)
        self.assertNotIn('<details class="qa-more">', annotated)
        self.assertIn("copyText(buildSinglePrompt(item), '已复制此条批注')", annotated)
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-card",),
                ("font-size: 12px",),
            )
        )
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-question",),
                ("font-size: 12px",),
            )
        )
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-quote",),
                ("font-size: 12px", "line-height: 1.55"),
            )
        )
        self.assertTrue(
            check_html_report.css_rule_has(
                annotated,
                (".qa-quote-link",),
                ("font-family: inherit",),
            )
        )
        self.assertNotIn("完成批注", annotated)
        self.assertEqual([], self.validate_html(annotated))

    def test_annotation_validator_rejects_reintroduced_action_clutter(self) -> None:
        """重复 Markdown 入口或拆散文件操作时，校验器应阻止旧布局回归。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-action-layout-report.html"),
        )
        broken = annotated.replace(
            '<button class="qa-secondary-btn" type="button" id="qaExportPublic">导出发布版</button>',
            "</div>"
            '<button class="qa-secondary-btn" type="button" id="qaCopyMarkdown">复制 Markdown</button>'
            '<button class="qa-secondary-btn" type="button" id="qaExportPublic">导出发布版</button>'
            '<div class="qa-secondary-actions">',
            1,
        )

        errors = self.validate_html(broken)

        self.assertTrue(any("重复的复制 Markdown 按钮" in error for error in errors))
        self.assertTrue(any("同一个直接可见的并排操作组" in error for error in errors))

    def test_annotation_validator_rejects_oversized_card_text(self) -> None:
        """批注卡片字号回退到偏大值时，校验器应给出明确错误。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-card-font-report.html"),
        )
        broken = annotated.replace("font-size: 12px;\n    }\n    .qa-card.location-missing", "font-size: 13px;\n    }\n    .qa-card.location-missing", 1)
        broken = broken.replace(
            ".qa-question { margin: 8px 0; color: #111827; font-size: 12px;",
            ".qa-question { margin: 8px 0; color: #111827; font-size: 13px;",
            1,
        )

        errors = self.validate_html(broken)

        self.assertTrue(any("批注卡片基础字号" in error for error in errors))
        self.assertTrue(any("批注正文应使用紧凑字号" in error for error in errors))

    def test_annotation_validator_rejects_launcher_role_switching(self) -> None:
        """校验器必须阻止旧版“零条即导出”的职责切换重新混入资产。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-role-switch-report.html"),
        )
        broken = annotated.replace(
            "// 右上角始终是批注工作区入口，发布动作只从侧栏触发，避免零批注时按钮职责突变。\n        setSidebarOpen(!sidebar.classList.contains('open'));",
            "if (!annotations.length) {\n          exportPublicHtml();\n          return;\n        }\n        setSidebarOpen(!sidebar.classList.contains('open'));",
            1,
        )

        errors = self.validate_html(broken)

        self.assertTrue(any("不能在零条时直接导出发布版" in error for error in errors))

    def test_annotation_validator_rejects_legacy_type_filter(self) -> None:
        """主路径不再要求用户区分提问和注释，旧类型筛选重新混入时应失败。"""

        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-filter-contract-report.html"),
        )
        broken = annotated.replace(
            '<div class="qa-list" id="qaList"></div>',
            '<div id="qaFilterBar"><button data-qa-filter="question">提问</button></div>'
            '<div class="qa-list" id="qaList"></div>',
            1,
        )

        errors = self.validate_html(broken)

        self.assertTrue(any("移除类型筛选" in error for error in errors))

    def test_annotation_processed_receipt_is_persistent_and_valid(self) -> None:
        """Agent 回写后必须保留可校验回执，不能只让待处理批注无痕消失。"""

        output_path = Path("/tmp/annotation-receipt-report.html")
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        receipt = inject_annotation_mode.build_standalone_review_receipt(
            "round-test",
            3,
            output_path,
            "yes",
            ["验证范围"],
        )
        annotated = inject_annotation_mode.inject_annotation_mode(assembled, output_path, receipt)

        self.assertIn('id="qaEmbeddedReviewReceipt" data-qa-review-receipt', annotated)
        self.assertIn('"roundId": "round-test"', annotated)
        self.assertIn('"contentChanged": true', annotated)
        self.assertIn("readEmbeddedReviewReceipt", annotated)
        self.assertIn("Agent 已处理 ", annotated)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "receipt.html"
            path.write_text(annotated, encoding="utf-8")
            errors, _ = check_html_report.validate_with_warnings(path, require_review_receipt=True)
        self.assertEqual([], errors)

    def test_embedded_pack_can_be_converted_to_processed_receipt(self) -> None:
        """备用 HTML 交接完成后应移除待处理包，并保留同 roundId 的处理回执。"""

        output_path = Path("/tmp/annotation-processed-report.html")
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(assembled, output_path)
        pack = {
            "type": "AgentQuestionPack",
            "version": "0.3.0",
            "roundId": "round-embedded",
            "reportTitle": "报告",
            "annotations": [{"id": "q-1"}, {"id": "q-2"}],
        }
        pack_block = "\n".join(
            (
                "<!-- QA_EMBEDDED_REVIEW_START: Agent 读取并逐条处理以下批注。 -->",
                '<script type="application/json" id="qaEmbeddedReviewData" data-qa-review-data>',
                inject_annotation_mode.serialize_raw_json(pack),
                "</script>",
                "<!-- QA_EMBEDDED_REVIEW_END -->",
            )
        )
        with_pack = annotated.replace("</head>", pack_block + "\n</head>", 1)

        parsed_pack = inject_annotation_mode.read_embedded_review_pack(with_pack)
        self.assertIsNotNone(parsed_pack)
        receipt = inject_annotation_mode.build_default_review_receipt(
            parsed_pack,
            output_path,
            "yes",
            ["正文"],
        )
        processed = inject_annotation_mode.inject_annotation_mode(
            inject_annotation_mode.strip_embedded_review_pack(with_pack),
            output_path,
            receipt,
        )

        # 批注运行时会保留未来构造备用包所需的 id 字符串；应按真实节点解析，避免把脚本源码误判成待处理包。
        self.assertIsNone(inject_annotation_mode.read_embedded_review_pack(processed))
        self.assertNotIn("QA_EMBEDDED_REVIEW_START: Agent 读取并逐条处理以下批注。", processed)
        self.assertIn('id="qaEmbeddedReviewReceipt"', processed)
        self.assertIn('"roundId": "round-embedded"', processed)
        self.assertIn('"handled": 2', processed)

    def test_receipt_file_completes_only_the_matching_embedded_round(self) -> None:
        """逐条回执必须消费同轮次待处理包，不能把其他轮次误标成已完成。"""

        output_path = Path("/tmp/annotation-receipt-file-report.html")
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(assembled, output_path)
        pack = {
            "type": "AgentQuestionPack",
            "version": "0.3.0",
            "roundId": "round-receipt-file",
            "annotations": [{"id": "q-1"}],
        }
        pack_block = "\n".join(
            (
                "<!-- QA_EMBEDDED_REVIEW_START: Agent 读取并逐条处理以下批注。 -->",
                '<script type="application/json" id="qaEmbeddedReviewData" data-qa-review-data>',
                inject_annotation_mode.serialize_raw_json(pack),
                "</script>",
                "<!-- QA_EMBEDDED_REVIEW_END -->",
            )
        )
        with_pack = annotated.replace("</head>", pack_block + "\n</head>", 1)
        receipt = {
            "type": "AgentReviewReceipt",
            "version": "0.1.0",
            "roundId": "round-receipt-file",
            "processedAt": "2026-08-03T00:00:00Z",
            "status": "processed",
            "total": 1,
            "handled": 1,
            "skipped": 0,
            "contentChanged": True,
            "changedSections": ["正文"],
            "results": [{"annotationId": "q-1", "status": "applied", "message": "已更新"}],
        }

        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "report.html"
            receipt_path = Path(directory) / "receipt.json"
            html_path.write_text(with_pack, encoding="utf-8")
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    "python3",
                    str(SKILL_DIR / "scripts" / "inject_annotation_mode.py"),
                    str(html_path),
                    "--receipt-file",
                    str(receipt_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            processed = html_path.read_text(encoding="utf-8")
            self.assertIsNone(inject_annotation_mode.read_embedded_review_pack(processed))
            self.assertIn('id="qaEmbeddedReviewReceipt"', processed)

            receipt["roundId"] = "round-other"
            html_path.write_text(with_pack, encoding="utf-8")
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
            rejected = subprocess.run(
                [
                    "python3",
                    str(SKILL_DIR / "scripts" / "inject_annotation_mode.py"),
                    str(html_path),
                    "--receipt-file",
                    str(receipt_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("回执 roundId 与 HTML 内嵌批注包不一致", rejected.stderr)

    def test_annotation_kind_badge_without_stable_width_is_rejected(self) -> None:
        assembled, _ = assemble_report.assemble_html(self.report_html("", "<p>报告正文</p>"))
        annotated = inject_annotation_mode.inject_annotation_mode(
            assembled,
            Path("/tmp/annotation-kind-badge-report.html"),
        )
        broken = annotated.replace("      flex: 0 0 auto;\n", "").replace("      white-space: nowrap;\n", "")

        errors = self.validate_html(broken)

        self.assertTrue(any("批注卡片徽标必须禁止 flex 收缩和文字换行" in error for error in errors))

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
        css = self.component_css("base", "code-block", "diff-viewer")
        html = self.report_html(css, highlight_code.render_diff_viewer(source))

        self.assertEqual([], self.validate_html(html))

    def test_diff_line_numbers_are_compact_without_internal_rule(self) -> None:
        """行号列随内容收缩，并且 old/new 之间不重复绘制分隔线。"""

        css = self.component_css("base", "code-block", "diff-viewer")

        self.assertTrue(
            check_html_report.css_rule_has(
                css,
                (".diff-viewer .diff-num",),
                ("width: 1%", "min-width: 0", "white-space: nowrap", "font-variant-numeric: tabular-nums"),
            )
        )
        self.assertTrue(
            check_html_report.css_rule_has(
                css,
                (".diff-viewer .diff-old-num",),
                ("border-right: 0 !important",),
            )
        )
        for selector, declaration in (
            (".diff-viewer .diff-add .diff-gutter", "border-left: 2px solid #16a34a"),
            (".diff-viewer .diff-del .diff-gutter", "border-left: 2px solid #dc2626"),
            (".diff-viewer .diff-context .diff-gutter", "border-left: 2px solid transparent"),
        ):
            self.assertTrue(check_html_report.css_rule_has(css, (selector,), (declaration,)))

    def test_validator_rejects_wide_divided_or_thick_diff_gutter(self) -> None:
        """防止行号区回退为固定宽列、多余竖线或过粗变更轨道。"""

        source = (SKILL_DIR / "evals" / "fixtures" / "focused_diff_patch.diff").read_text(encoding="utf-8")
        css = self.component_css("base", "code-block", "diff-viewer")
        body = highlight_code.render_diff_viewer(source)
        wide_css = css.replace(
            ".diff-viewer .diff-num {\n  width: 1%;\n  min-width: 0;",
            ".diff-viewer .diff-num {\n  width: 1%;\n  min-width: 40px;",
            1,
        )
        divided_css = css.replace(
            ".diff-viewer .diff-old-num {\n  border-right: 0 !important;\n}\n",
            "",
            1,
        )
        thick_track_css = css.replace("border-left: 2px", "border-left: 5px")

        wide_errors = self.validate_html(self.report_html(wide_css, body))
        divided_errors = self.validate_html(self.report_html(divided_css, body))
        thick_track_errors = self.validate_html(self.report_html(thick_track_css, body))

        self.assertTrue(any("必须按内容收缩" in error for error in wide_errors))
        self.assertTrue(any("不应显示多余竖线" in error for error in divided_errors))
        self.assertTrue(any("必须统一使用 2px 细轨道" in error for error in thick_track_errors))

    def test_validator_rejects_multi_file_diff_in_one_card(self) -> None:
        source = (SKILL_DIR / "evals" / "fixtures" / "code_review_patch.diff").read_text(encoding="utf-8")
        css = self.component_css("base", "code-block", "diff-viewer")
        html = self.report_html(css, highlight_code.render_diff_viewer_block(source))

        errors = self.validate_html(html)

        self.assertTrue(any("必须由 highlight_code.py 自动拆成每文件一个卡片" in error for error in errors))

    def test_base_table_component_passes_validation(self) -> None:
        css = self.component_css("base", "table")
        html = self.report_html(css, '<div class="table-wrap"><table><tr><th>项目</th></tr><tr><td>通过</td></tr></table></div>')

        self.assertEqual([], self.validate_html(html))

    def test_base_tag_has_default_contrast_and_print_fallback(self) -> None:
        css = self.component_css("base")
        html = self.report_html(css, '<p><span class="tag">推荐方案</span> 使用已曝光内容</p>')

        self.assertTrue(check_html_report.css_rule_has(css, (".tag",), ("background: #475569", "color: #ffffff")))
        self.assertTrue(
            check_html_report.css_rule_has(
                css,
                (".tag",),
                ("background: #f3f4f6", "color: #111827", "border: 1px solid #d1d5db"),
            )
        )
        self.assertEqual([], self.validate_html(html))

    def test_tag_without_default_background_is_rejected(self) -> None:
        css = """
        * { box-sizing: border-box; }
        .tag { color: #ffffff; }
        @media (max-width: 720px) { body { margin: 0; } }
        @media print { body { color: #000000; } }
        """
        html = self.report_html(css, '<p><span class="tag">推荐方案</span> 使用已曝光内容</p>')

        errors = self.validate_html(html)

        self.assertTrue(any("默认规则未同时设置 background 和 color" in error for error in errors))

    def test_table_without_wrapper_rounded_frame_or_full_grid_is_rejected(self) -> None:
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
        self.assertTrue(any("缺少统一圆角外框" in error for error in errors))
        self.assertTrue(any("缺少完整 1px 网格线" in error for error in errors))

    def test_assembler_detects_components_and_is_idempotent(self) -> None:
        body = (
            '<div class="table-wrap"><table><tr><th>项目</th></tr><tr><td>通过</td></tr></table></div>'
            + highlight_code.render_diff_viewer(
                (SKILL_DIR / "evals" / "fixtures" / "focused_diff_patch.diff").read_text(encoding="utf-8")
            )
        )
        source = self.report_html("", body)

        first, components = assemble_report.assemble_html(source)
        second, second_components = assemble_report.assemble_html(first)

        self.assertEqual(first, second)
        self.assertEqual(components, second_components)
        self.assertEqual(
            ["base", "interactions", "table", "code-block", "diff-viewer"],
            components,
        )
        self.assertEqual(1, first.count('data-html-report-runtime="code-block"'))
        self.assertEqual([], self.validate_html(first))

    def test_registry_resolves_every_component_asset(self) -> None:
        registry = assemble_report.load_registry()
        component_names = list(registry["components"])

        resolved = assemble_report.resolve_components(component_names, registry)
        styles, scripts = assemble_report.collect_assets(resolved, registry)

        self.assertEqual(set(component_names), set(resolved))
        self.assertTrue(styles)
        self.assertTrue(scripts)

    def test_validator_rejects_truncated_component_runtime(self) -> None:
        body = '<div class="code-wrap"><button class="copy-btn" type="button">复制</button><pre><code class="language-text">plain</code></pre></div>'
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))
        broken = assembled.replace("HTML_REPORT_CODE_BLOCK_RUNTIME_END", "HTML_REPORT_CODE_BLOCK_RUNTIME_BROKEN", 1)

        errors = self.validate_html(broken)

        self.assertTrue(any("缺少完整性标记 HTML_REPORT_CODE_BLOCK_RUNTIME_END" in error for error in errors))

    def test_media_lightbox_is_auto_assembled_and_passes_validation(self) -> None:
        body = """
<figure class="media-evidence" data-case="case-01" data-conclusion="图片可复核">
  <div class="media-frame">
    <a class="image-lightbox-trigger" data-image-lightbox href="data:image/png;base64,AA==">
      <img src="data:image/png;base64,AA==" alt="case-01 结果截图">
    </a>
  </div>
  <figcaption>case-01 结果截图</figcaption>
</figure>
"""
        assembled, components = assemble_report.assemble_html(self.report_html("", body))

        self.assertIn("media", components)
        self.assertIn("image-lightbox", components)
        self.assertEqual(1, assembled.count('data-html-report-runtime="image-lightbox"'))
        self.assertEqual([], self.validate_html(assembled))

    def test_media_evidence_without_lightbox_is_rejected(self) -> None:
        body = """
<figure class="media-evidence" data-case="case-01" data-conclusion="图片可复核">
  <div class="media-frame"><img src="data:image/png;base64,AA==" alt="case-01 结果截图"></div>
  <figcaption>case-01 结果截图</figcaption>
</figure>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))

        errors = self.validate_html(assembled)

        self.assertTrue(any("必须包在 a.image-lightbox-trigger" in error for error in errors))

    def test_file_location_keeps_short_label_and_full_target(self) -> None:
        body = """
<a class="file-location file-link"
   href="idea://open?file=/repo/business/flowvideo/FlowVideoHelper.kt&amp;line=1050"
   title="/repo/business/flowvideo/FlowVideoHelper.kt:1050-1070">FlowVideoHelper.kt:1050-1070</a>
"""
        assembled, components = assemble_report.assemble_html(self.report_html("", body))

        self.assertIn("file-location", components)
        self.assertEqual([], self.validate_html(assembled))

    def test_file_location_rejects_visible_full_path(self) -> None:
        body = """
<a class="file-location file-link"
   href="idea://open?file=/repo/business/flowvideo/FlowVideoHelper.kt&amp;line=1050"
   title="/repo/business/flowvideo/FlowVideoHelper.kt:1050-1070">repo/business/flowvideo/FlowVideoHelper.kt:1050-1070</a>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))

        errors = self.validate_html(assembled)

        self.assertTrue(any("同名时最多增加一级父目录" in error for error in errors))

    def test_file_location_rejects_mismatched_target(self) -> None:
        body = """
<a class="file-location file-link"
   href="idea://open?file=/repo/business/flowvideo/Other.kt&amp;line=1050"
   title="/repo/business/flowvideo/FlowVideoHelper.kt:1050-1070">FlowVideoHelper.kt:1050-1070</a>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))

        errors = self.validate_html(assembled)

        self.assertTrue(any("href 与 title 的完整路径不一致" in error for error in errors))

    def test_file_location_accepts_encoded_absolute_path_with_spaces(self) -> None:
        body = """
<a class="file-location file-link"
   href="idea://open?file=/repo/My%20File.kt&amp;line=10"
   title="/repo/My File.kt:10">My File.kt:10</a>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))

        self.assertEqual([], self.validate_html(assembled))

    def test_file_location_rejects_relative_ide_target(self) -> None:
        body = """
<a class="file-location file-link"
   href="idea://open?file=repo/Foo.kt&amp;line=10"
   title="repo/Foo.kt:10">Foo.kt:10</a>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", body))

        errors = self.validate_html(assembled)

        self.assertTrue(any("href 必须使用绝对路径" in error for error in errors))
        self.assertTrue(any("title 必须保留完整路径" in error for error in errors))

    def test_review_workspace_rejects_relative_absolute_path(self) -> None:
        spec = {
            "workspace_id": "relative-path-eval",
            "versions": [{"id": "before", "label": "Before"}, {"id": "after", "label": "After"}],
            "files": [
                {
                    "id": "foo",
                    "filename": "Foo.kt",
                    "absolute_path": "repo/Foo.kt",
                    "versions": {
                        "before": {"source": "class Foo", "language": "kotlin"},
                        "after": {"source": "class Foo", "language": "kotlin"},
                    },
                }
            ],
        }

        with self.assertRaisesRegex(build_review_workspace.SpecError, "absolute_path 必须是绝对路径"):
            build_review_workspace.build_config(spec, Path("workspace.json"))

    def test_review_workspace_uses_short_ide_location_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "FlowVideoHelper.kt"
            source_path.write_text("class FlowVideoHelper\nfun bind() = Unit\n", encoding="utf-8")
            spec_path = temp_path / "workspace.json"
            spec = {
                "workspace_id": "file-location-eval",
                "versions": [
                    {"id": "before", "label": "Before"},
                    {"id": "after", "label": "After"},
                ],
                "files": [
                    {
                        "id": "flow-video-helper",
                        "filename": "FlowVideoHelper.kt",
                        "path": "flowvideo/FlowVideoHelper.kt",
                        "display_path": "FlowVideoHelper.kt:2",
                        "absolute_path": "/repo/business/flowvideo/FlowVideoHelper.kt",
                        "idea_line": 2,
                        "versions": {
                            "before": {"source_path": str(source_path), "language": "kotlin", "marks": {"focus": [2]}},
                            "after": {"source_path": str(source_path), "language": "kotlin", "marks": {"focus": [2]}},
                        },
                    }
                ],
            }

            config = build_review_workspace.build_config(spec, spec_path)
            fragment = build_review_workspace.render_fragment(config)
            assembled, components = assemble_report.assemble_html(self.report_html("", fragment))

        self.assertIn("file-location", components)
        self.assertIn(">FlowVideoHelper.kt:2</a>", assembled)
        self.assertIn('title="/repo/business/flowvideo/FlowVideoHelper.kt:2"', assembled)
        self.assertNotIn(">/repo/business/flowvideo/FlowVideoHelper.kt:2</a>", assembled)
        self.assertEqual([], self.validate_html(assembled))

    def test_sortable_table_uses_semantic_button_and_runtime(self) -> None:
        body = """
<div class="table-wrap">
  <table class="sortable"><thead><tr><th><button class="sort-button" type="button" data-sort-type="number">数量<span class="sort-arrow" aria-hidden="true"></span></button></th></tr></thead>
  <tbody><tr><td>2</td></tr><tr><td>1</td></tr></tbody></table>
</div>
"""
        assembled, components = assemble_report.assemble_html(self.report_html("", body))

        self.assertIn("sortable-table", components)
        self.assertEqual(1, assembled.count('data-html-report-runtime="sortable-table"'))
        self.assertEqual([], self.validate_html(assembled))

    def test_tabs_keep_accessible_structure_and_runtime(self) -> None:
        body = """
<section class="report-tabs" data-tabs>
  <div class="tabs" role="tablist" aria-label="报告视图">
    <button id="tab-a" class="tab-label" type="button" role="tab" aria-selected="true" aria-controls="panel-a">问题清单</button>
    <button id="tab-b" class="tab-label" type="button" role="tab" aria-selected="false" aria-controls="panel-b">修复方案</button>
  </div>
  <div class="tab-content">
    <section id="panel-a" class="tab-panel" role="tabpanel" aria-labelledby="tab-a">问题</section>
    <section id="panel-b" class="tab-panel" role="tabpanel" aria-labelledby="tab-b">方案</section>
  </div>
</section>
"""
        assembled, components = assemble_report.assemble_html(self.report_html("", body))

        self.assertIn("tabs", components)
        self.assertEqual(1, assembled.count('data-html-report-runtime="tabs"'))
        self.assertNotIn("CSS.escape(", assembled)
        self.assertEqual([], self.validate_html(assembled))

    def test_tabs_validate_each_instance_and_aria_relationship(self) -> None:
        valid = """
<section class="report-tabs" data-tabs>
  <div role="tablist"><button id="tab-good" role="tab" aria-controls="panel-good">正确</button></div>
  <section id="panel-good" role="tabpanel" aria-labelledby="tab-good">内容</section>
</section>
"""
        broken = """
<section class="report-tabs" data-tabs>
  <div role="tablist"><button id="tab-bad" role="tab" aria-controls="missing-panel">错误</button></div>
  <section id="panel-bad" role="tabpanel" aria-labelledby="missing-tab">内容</section>
</section>
"""
        assembled, _ = assemble_report.assemble_html(self.report_html("", valid + broken))

        errors = self.validate_html(assembled)

        self.assertTrue(any("第 2 个标签页" in error and "aria-controls 未指向" in error for error in errors))
        self.assertTrue(any("第 2 个标签页" in error and "aria-labelledby 未指向" in error for error in errors))

    def test_toc_is_auto_assembled_with_runtime(self) -> None:
        body = """
<div class="layout-with-toc">
  <nav class="toc" aria-label="目录">
    <div class="toc-header"><p class="toc-title">目录</p><button class="toc-toggle" type="button" aria-expanded="true" aria-label="收起目录" title="收起目录"><span class="toc-toggle-icon" aria-hidden="true">‹</span></button></div>
    <a href="#summary">摘要</a>
  </nav>
  <main><section id="summary"><h2>摘要</h2><p>正文</p></section></main>
</div>
"""
        assembled, components = assemble_report.assemble_html(self.report_html("", body))

        self.assertIn("toc", components)
        self.assertEqual(1, assembled.count('data-html-report-runtime="toc"'))
        self.assertEqual([], self.validate_html(assembled))

    @staticmethod
    def component_css(*components: str) -> str:
        """读取组件拆分后的真实 CSS，避免测试维护旧路径或复制样式。"""

        return "\n".join(
            (SKILL_DIR / "assets" / "components" / name / "style.css").read_text(encoding="utf-8")
            for name in components
        )

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
