#!/usr/bin/env python3
"""给 html-report 单文件 HTML 注入离线批注模式。

这个脚本用于把已经生成好的普通 HTML 报告升级成“批注版”：
- 选中文本后显示轻量气泡，直接区分“问题”和“评论”。
- 输入浮层只有一个“提交”按钮，按钮显示 Ctrl/⌘ + Enter 提示，支持快捷提交，点击外侧自动关闭。
- 右侧栏可以编辑批注、复制给 Agent、备用保存批注版 HTML，并导出物理剥离批注能力和回执的发布版 HTML。

脚本只依赖 Python 标准库，输出仍是单文件 HTML。批注 UI 的 CSS / HTML / JS 维护在
assets/annotation-mode/，这里负责读取资产、注入来源路径元数据和幂等装配。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


CSS_MARKER_START = "/* QA_ANNOTATION_CSS_START:"
CSS_MARKER_END = "QA_ANNOTATION_CSS_END */"
HTML_MARKER_START = "<!-- QA_ANNOTATION_HTML_START:"
HTML_MARKER_END = "QA_ANNOTATION_HTML_END -->"
SCRIPT_MARKER_START = "<!-- QA_ANNOTATION_SCRIPT_START -->"
SCRIPT_MARKER_END = "<!-- QA_ANNOTATION_SCRIPT_END -->"
REVIEW_RECEIPT_START_MARKER = "QA_AGENT_REVIEW_RECEIPT_START"
REVIEW_RECEIPT_END_MARKER = "QA_AGENT_REVIEW_RECEIPT_END"
EMBEDDED_REVIEW_START_RE = re.compile(
    r"<!--\s*QA_EMBEDDED_REVIEW_START:[\s\S]*?-->", re.IGNORECASE
)
EMBEDDED_REVIEW_END_RE = re.compile(
    r"<!--\s*QA_EMBEDDED_REVIEW_END\s*-->", re.IGNORECASE
)
EMBEDDED_REVIEW_DATA_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']qaEmbeddedReviewData["\'])'
    r'(?=[^>]*\bdata-qa-review-data(?:\s|=|>))[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "annotation-mode"
ANNOTATION_CSS_PATH = ASSET_DIR / "annotation.css"
ANNOTATION_HTML_PATH = ASSET_DIR / "annotation.html"
ANNOTATION_JS_PATH = ASSET_DIR / "annotation.js"


def read_asset(path: Path) -> str:
    """读取批注模式资产，缺失时给出可定位的错误。"""

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"批注模式资产缺失: {path}") from exc


def read_marked_asset(path: Path, marker_start: str, marker_end: str) -> str:
    """读取带剥离标记的资产，确保发布版导出和重复注入仍能稳定定位。"""

    content = read_asset(path)
    if marker_start not in content or marker_end not in content:
        raise ValueError(f"批注模式资产缺少剥离标记: {path}")
    return content


def read_annotation_assets() -> tuple[str, str, str]:
    """读取批注模式三类资产，并校验 JS 里保留元数据占位符。"""

    css = read_marked_asset(ANNOTATION_CSS_PATH, CSS_MARKER_START, CSS_MARKER_END)
    html = read_marked_asset(ANNOTATION_HTML_PATH, HTML_MARKER_START, HTML_MARKER_END)
    js = read_marked_asset(ANNOTATION_JS_PATH, SCRIPT_MARKER_START, SCRIPT_MARKER_END)
    if "__QA_REPORT_META__" not in js:
        raise ValueError(f"批注模式 JS 缺少 __QA_REPORT_META__ 占位符: {ANNOTATION_JS_PATH}")
    return css, html, js


def strip_annotation_mode(html: str) -> str:
    """删除已经注入过的批注模式，保证脚本可重复运行。"""
    # 先删除整段批注脚本，避免脚本内部的正则文本被下面的标记清理误匹配。
    html = re.sub(r"\n?\s*<script\s+data-qa-script>[\s\S]*?</script>", "", html)
    html = re.sub(r"\n?\s*/\* QA_ANNOTATION_CSS_START:[\s\S]*?QA_ANNOTATION_CSS_END \*/", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_HTML_START:[\s\S]*?QA_ANNOTATION_HTML_END -->", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_SCRIPT_START -->[\s\S]*?<!-- QA_ANNOTATION_SCRIPT_END -->", "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


def build_annotation_js(js_template: str, output_path: Path | None = None) -> str:
    """生成带来源路径元数据的批注脚本。"""
    meta: dict[str, str] = {}
    if output_path is not None:
        # 在生成阶段写入绝对路径，避免通过 HTTP 预览时 location.pathname 退化为 URL 路径。
        absolute_path = output_path.expanduser().resolve()
        meta = {
            "fileName": absolute_path.name,
            "absolutePath": str(absolute_path),
            "fileUrl": absolute_path.as_uri(),
        }
    return js_template.replace("__QA_REPORT_META__", json.dumps(meta, ensure_ascii=False))


def serialize_raw_json(value: object) -> str:
    """把 JSON 写进 HTML raw-text 节点前做安全转义，阻断标签提前闭合。"""

    escapes = {
        "<": "\\u003c",
        ">": "\\u003e",
        "&": "\\u0026",
        "\u2028": "\\u2028",
        "\u2029": "\\u2029",
    }
    return json.dumps(value, ensure_ascii=False, indent=2).replace(
        "<", escapes["<"]
    ).replace(">", escapes[">"]).replace("&", escapes["&"]).replace(
        "\u2028", escapes["\u2028"]
    ).replace("\u2029", escapes["\u2029"])


def read_embedded_review_pack(html: str) -> dict[str, object] | None:
    """读取待处理包，供 --processed 生成与本轮绑定的回执。"""

    match = EMBEDDED_REVIEW_DATA_RE.search(html)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"HTML 内嵌批注包不是合法 JSON: {exc.msg}") from exc
    if not isinstance(payload, dict) or payload.get("type") != "AgentQuestionPack":
        raise ValueError("HTML 内嵌批注包 type 必须为 AgentQuestionPack")
    if not isinstance(payload.get("annotations"), list):
        raise ValueError("HTML 内嵌批注包 annotations 必须是数组")
    return payload


def strip_embedded_review_pack(html: str) -> str:
    """处理完成后移除待处理包，但保留批注 UI 和即将写入的回执。"""

    result = EMBEDDED_REVIEW_DATA_RE.sub("", html)
    result = EMBEDDED_REVIEW_START_RE.sub("", result)
    result = EMBEDDED_REVIEW_END_RE.sub("", result)
    return re.sub(r"\n{3,}", "\n\n", result)


def build_review_receipt_block(receipt: dict[str, object]) -> str:
    """构造独立回执节点；回执不复用待处理包，避免 Agent 重复消费。"""

    payload = serialize_raw_json(receipt)
    return "\n".join(
        [
            f"  <!-- {REVIEW_RECEIPT_START_MARKER}: Agent 本轮处理结果。 -->",
            '  <script type="application/json" id="qaEmbeddedReviewReceipt" data-qa-review-receipt>',
            "\n".join(f"  {line}" for line in payload.splitlines()),
            "  </script>",
            f"  <!-- {REVIEW_RECEIPT_END_MARKER} -->",
        ]
    )


def strip_review_receipt(html: str) -> str:
    """重复注入或导出前移除旧回执，保证页面只有一份最新结果。"""

    pattern = (
        rf"\n?\s*<!--\s*{REVIEW_RECEIPT_START_MARKER}:[\s\S]*?"
        rf"{REVIEW_RECEIPT_END_MARKER}\s*-->"
    )
    result = re.sub(pattern, "", html, flags=re.IGNORECASE)
    result = re.sub(
        r'\n?\s*<script\b[^>]*\bid=["\']qaEmbeddedReviewReceipt["\']'
        r'[^>]*data-qa-review-receipt[^>]*>[\s\S]*?</script>',
        "",
        result,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\n{3,}", "\n\n", result)


def build_default_review_receipt(
    pack: dict[str, object],
    output_path: Path,
    content_changed: str,
    changed_sections: list[str],
) -> dict[str, object]:
    """生成无额外参数时的全量处理回执，明确这是 Agent 回报而非浏览器推断。"""

    annotations = pack.get("annotations") or []
    results = []
    for item in annotations:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "annotationId": str(item.get("id") or ""),
                "status": "processed",
                "message": "已处理；具体改动请查看报告正文。",
            }
        )
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    changed_value: bool | None
    if content_changed == "yes":
        changed_value = True
    elif content_changed == "no":
        changed_value = False
    else:
        changed_value = None
    total = len(results)
    return {
        "type": "AgentReviewReceipt",
        "version": "0.1.0",
        "roundId": str(pack.get("roundId") or f"round-{int(datetime.now().timestamp())}"),
        "reportTitle": pack.get("reportTitle") or "HTML 报告",
        "reportFileName": output_path.name,
        "reportAbsolutePath": str(output_path.expanduser().resolve()),
        "reportFileUrl": output_path.expanduser().resolve().as_uri(),
        "processedAt": now,
        "status": "processed",
        "total": total,
        "handled": total,
        "skipped": 0,
        "contentChanged": changed_value,
        "changedSections": changed_sections,
        "results": results,
    }


def build_standalone_review_receipt(
    round_id: str,
    total: int,
    output_path: Path,
    content_changed: str,
    changed_sections: list[str],
) -> dict[str, object]:
    """为剪贴板交接生成汇总回执；该路径没有文件内待处理包可供逐条还原。"""

    synthetic_pack: dict[str, object] = {
        "roundId": round_id,
        "reportTitle": output_path.stem,
        "annotations": [],
    }
    receipt = build_default_review_receipt(
        synthetic_pack,
        output_path,
        content_changed,
        changed_sections,
    )
    receipt["total"] = total
    receipt["handled"] = total
    receipt["results"] = []
    return receipt


def inject_annotation_mode(
    html: str,
    output_path: Path | None = None,
    review_receipt: dict[str, object] | None = None,
) -> str:
    """把 CSS、HTML 容器和 JS 批注逻辑插入到单文件 HTML 中。"""
    annotation_css, annotation_html, annotation_js = read_annotation_assets()
    html = strip_annotation_mode(html)
    if review_receipt is not None:
        # 只有显式 --processed/--receipt-file 才替换回执，普通幂等注入不丢失历史状态。
        html = strip_review_receipt(html)
    if "</style>" not in html:
        raise ValueError("找不到 </style>，无法注入批注样式")
    if "</body>" not in html:
        raise ValueError("找不到 </body>，无法注入批注脚本")

    html = html.replace("</style>", annotation_css + "\n  </style>", 1)

    if review_receipt is not None:
        receipt_block = build_review_receipt_block(review_receipt)
        html = html.replace("</head>", receipt_block + "\n</head>", 1)

    # 优先放在现有 toast 后面，复用 html-report 的提示气泡。
    toast = '<div class="toast" id="toast">已复制</div>'
    if toast in html:
        html = html.replace(toast, toast + "\n" + annotation_html, 1)
    else:
        html = html.replace("</body>", annotation_html + "\n</body>", 1)

    return html.replace("</body>", build_annotation_js(annotation_js, output_path) + "\n</body>", 1)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="给 html-report 单文件 HTML 注入离线批注模式。")
    parser.add_argument("html", help="输入 HTML 文件。")
    parser.add_argument("-o", "--output", help="输出 HTML 文件；默认覆盖输入文件。")
    parser.add_argument(
        "--processed",
        action="store_true",
        help="读取当前 HTML 的 AgentQuestionPack，移除待处理包并写入全量处理回执。",
    )
    parser.add_argument(
        "--receipt-file",
        help="使用 JSON 文件作为 AgentReviewReceipt；与 --processed 二选一。",
    )
    parser.add_argument(
        "--processed-round",
        help="剪贴板交接完成后写回该轮次的汇总回执，不要求 HTML 已内嵌待处理包。",
    )
    parser.add_argument(
        "--processed-count",
        type=int,
        default=0,
        help="与 --processed-round 配合，记录本轮处理的批注总数。",
    )
    parser.add_argument(
        "--content-changed",
        choices=("yes", "no", "unknown"),
        default="unknown",
        help="--processed 时由 Agent 明确报告正文是否发生改动。",
    )
    parser.add_argument(
        "--changed-section",
        action="append",
        default=[],
        help="--processed 时记录发生改动的章节，可重复传入。",
    )
    return parser.parse_args()


def main() -> None:
    """读取 HTML、注入批注模式并写回文件。"""
    args = parse_args()
    input_path = Path(args.html)
    output_path = Path(args.output) if args.output else input_path

    receipt_modes = sum(bool(value) for value in (args.processed, args.receipt_file, args.processed_round))
    if receipt_modes > 1:
        raise ValueError("--processed、--processed-round 与 --receipt-file 只能选择一种")
    if args.processed_count < 0:
        raise ValueError("--processed-count 不能小于 0")
    if args.processed_count and not args.processed_round:
        raise ValueError("--processed-count 必须与 --processed-round 一起使用")
    html = input_path.read_text(encoding="utf-8")
    receipt: dict[str, object] | None = None
    if args.processed:
        pack = read_embedded_review_pack(html)
        if pack is None:
            raise ValueError("--processed 需要当前 HTML 包含 AgentQuestionPack")
        receipt = build_default_review_receipt(
            pack,
            output_path,
            args.content_changed,
            args.changed_section,
        )
        html = strip_embedded_review_pack(html)
    elif args.processed_round:
        if read_embedded_review_pack(html) is not None:
            raise ValueError("当前 HTML 含内嵌批注包，请使用 --processed 或 --receipt-file 完成本轮处理")
        receipt = build_standalone_review_receipt(
            args.processed_round,
            args.processed_count,
            output_path,
            args.content_changed,
            args.changed_section,
        )
    elif args.receipt_file:
        try:
            receipt_value = json.loads(Path(args.receipt_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取回执 JSON: {args.receipt_file}") from exc
        if not isinstance(receipt_value, dict):
            raise ValueError("回执 JSON 顶层必须是对象")
        receipt = receipt_value
        pack = read_embedded_review_pack(html)
        if pack is not None:
            # 逐条回执用于完成当前内嵌轮次；轮次不一致时停止，避免误删仍待处理的批注。
            if receipt.get("roundId") != pack.get("roundId"):
                raise ValueError("回执 roundId 与 HTML 内嵌批注包不一致")
            html = strip_embedded_review_pack(html)
    output_path.write_text(inject_annotation_mode(html, output_path, receipt), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
