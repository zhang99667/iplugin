# Annotation Review Notes

用户目标：在普通 HTML 技术报告上开启离线批注模式，统一可见术语，按轮次把批注交给 Agent，并在 Agent 回写后看到可验证的处理回执。

验收重点：

- 原始 HTML 必须先通过 `check_html_report.py`。
- 注入必须通过 `inject_annotation_mode.py` 完成，注入后再次校验。
- 页面可见术语统一为“批注”：批注模式、添加批注、复制批注给 Agent、保存批注版 HTML、导出发布版。
- 右上角稳定打开批注侧栏；选区气泡只有一个“添加批注”入口，右键只按选中内容/本段/本节区分范围。
- 不保留“全部/提问/注释”类型筛选；旧 `kind` 只做数据兼容并统一显示为批注。
- 侧栏主操作是“复制批注给 Agent”，复制失败提供手动 textarea；“保存批注版 HTML（备用）”不再伪装成处理完成。
- 不提供重复的“复制 Markdown / 下载 Markdown”按钮；保存批注版与导出发布版并排展示，清空本轮直接可见。
- 批注卡片字号保持紧凑，原文摘录和批注正文不应显著大于侧栏其他信息。
- 页面持久区分本轮草稿、已复制待处理和 Agent 已处理状态，不能只靠短暂 toast。
- 自动定位失败的批注可以点击“重新关联”，在 `<main>` 内选择新原文后确认；Esc 或无效选区安全取消。
- 备用批注版 HTML 内嵌唯一、安全转义的 `AgentQuestionPack`；Agent 处理后移除待处理包并写入唯一 `AgentReviewReceipt`。
- Agent 声明完成时必须通过 `check_html_report.py --require-review-receipt`；不能把批注消失解释成已处理。
- 发布版必须剥离批注 UI、待处理包、处理回执、本地路径和 `data-block-id`。
- 不提供独立“下载 JSON”按钮，不手写或复制一份批注 JS。
