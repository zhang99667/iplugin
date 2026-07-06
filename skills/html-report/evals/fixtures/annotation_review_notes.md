# Annotation Review Notes

用户目标：在普通 HTML 技术报告上开启离线批注审核模式，方便 reviewer 选中文本提问，并把问题导出给 Agent。

验收重点：

- 原始 HTML 必须先通过 `check_html_report.py`。
- 注入必须通过 `inject_annotation_mode.py` 完成。
- 注入后必须再次通过 `check_html_report.py`。
- 审核版需要能导出 Markdown/JSON 提问包，也需要有“导出发布版”入口。
- 不要手写或复制一份批注 JS。
