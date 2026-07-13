# Annotation Review Notes

用户目标：在普通 HTML 技术报告上开启离线批注审核模式，方便 reviewer 选中文本提问，并把审核结果直接内嵌回 HTML 交给 Agent。

验收重点：

- 原始 HTML 必须先通过 `check_html_report.py`。
- 注入必须通过 `inject_annotation_mode.py` 完成。
- 注入后必须再次通过 `check_html_report.py`。
- 审核版需要有“保存审核结果到 HTML”主入口，内嵌唯一、可解析且安全转义的 `AgentQuestionPack`，Markdown 仅作为兜底。
- 新注入但尚未点击保存的审核版不应伪造空审核包；用户声明完成批注后，必须用 `--require-review-pack` 验证实际交接文件。
- 审核版需要有“导出无批注版”入口，发布版必须剥离审核 UI 和内嵌批注。
- 不再提供独立“下载 JSON”按钮。
- 不要手写或复制一份批注 JS。
