# Annotation Review Notes

用户目标：在普通 HTML 技术报告上开启离线评论模式，方便 reviewer 选中文本提问，并把评论结果直接内嵌回 HTML 交给 Agent。

验收重点：

- 原始 HTML 必须先通过 `check_html_report.py`。
- 注入必须通过 `inject_annotation_mode.py` 完成。
- 注入后必须再次通过 `check_html_report.py`。
- 右上角需要稳定显示“批注”并打开侧栏，数量只表达工作状态，不能在零条时切换为发布导出。
- 侧栏可以按“全部/提问/注释”筛选，点击批注原文可快速定位正文；筛选不应写入交接包。
- 评论版需要有“完成批注”主入口，将唯一、可解析且安全转义的 `AgentQuestionPack` 内嵌回 HTML，Markdown 仅作为兜底。
- 新注入但尚未点击“完成批注”的评论版不应伪造空评论包；用户声明完成批注后，必须用 `--require-review-pack` 验证实际交接文件。
- 评论版需要有“导出无批注版”入口，发布版必须剥离评论 UI 和内嵌批注。
- 不再提供独立“下载 JSON”按钮。
- 不要手写或复制一份批注 JS。
