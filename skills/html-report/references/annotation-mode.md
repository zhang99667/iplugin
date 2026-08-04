# HTML 报告批注模式

当用户希望在 HTML 报告里直接对文字、段落、表格或图表提出问题或评论，并把一轮批注交给 Agent 处理时，使用批注模式。默认不要为所有报告加入；只有用户明确要求“批注模式”“评论模式”“审核模式”“对 HTML 内容提意见”“按 HTML 内嵌批注更新报告”等场景才加入。“批注”作为工作区和交接总称，单条内容分为“问题 / 评论”。

## 技术边界

批注模式仍是离线单文件 HTML，没有后端、原生桥接或本地常驻服务：

- 页面中的草稿只能存在于当前 DOM 和 `localStorage`，Agent 进程不能直接读取。
- `file://` 页面不能静默覆盖任意本地文件，也不能从浏览器直接调用 Agent 或 shell。
- File System Access API 只在部分浏览器可用，并且保存必须由用户手势发起；下载兜底只能确认“已发起”，不能确认最终路径或是否落盘。
- 页面不能实时知道 Agent 是否修改了磁盘文件。处理完成状态必须由 Agent 显式写入 `AgentReviewReceipt`，不能用“批注消失”或时间戳猜测。

因此默认交互采用诚实的异步轮次：

```text
编辑本轮批注 -> 复制批注给 Agent -> Agent 原地修改同一 HTML -> 写入处理回执 -> 用户重新打开查看 -> 下一轮
```

保存批注版 HTML 是跨会话、跨设备或归档时的备用交接，不是默认主路径。真正的原生实时协作需要宿主桥接，不能在静态基线里伪装实现。

## 注入方式

先生成普通单文件 HTML 并校验，再注入批注模式并复验：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

不要手写批注 CSS/JS。资产统一维护在 `assets/annotation-mode/annotation.css`、`annotation.html`、`annotation.js`，由 `inject_annotation_mode.py` 读取、注入来源路径元数据并幂等装配。

## 交互契约

- 用户可见总称统一为 `批注模式`、`批注`、`复制批注给 Agent`、`保存批注版 HTML`；单条类型明确使用 `问题` 和 `评论`。
- 旧包中的 `kind: 提问 | 问题` 归一为 `问题`，`kind: 注释 | 批注 | 评论` 归一为 `评论`；新建、编辑、卡片徽标和交接包都使用当前两类名称。
- 选中文本后显示 `问题` 和 `评论` 两个直接入口；点击后打开贴近选区的轻量输入浮层。浮层只有一个 `提交` 按钮，并显示 `Ctrl/⌘ + Enter`；普通 Enter 换行，输入法组字阶段不能误提交，点击外侧关闭。
- 右键菜单在选中内容、本段和本节三个作用范围下都提供问题和评论；不要通过第二层类型弹窗增加操作次数。
- 右上角固定为批注侧栏入口：0 条显示 `批注`，非零通过独立数量徽标表达；入口不能在零条时切换成发布动作。
- 侧栏顶部依次显示稳定标题、轮次状态和一个主操作 `复制批注给 Agent`。零批注时主操作明确禁用；`保存批注版` 与 `导出发布版` 并排直接展示，`清空本轮` 作为独立危险操作。复制给 Agent 已包含完整 Markdown 批注包，因此不再提供重复的复制/下载 Markdown 按钮，也不再使用“更多操作”折叠层。
- 轮次状态必须持久区分：本轮草稿、已复制/等待 Agent、Agent 已处理、部分处理或失败。短暂 toast 只补充即时反馈，不能代替状态。
- 列表不提供“全部 / 问题 / 评论”类型筛选。问题和评论通过卡片徽标区分；点击原文摘录可快速定位正文，显式 `定位` 按钮保留为备用入口。
- 自动定位失败的批注提供 `重新关联`；用户在 `<main>` 内选中新位置后确认，只更新定位字段，保留原 `id`、正文、创建时间和来源。
- 剪贴板在 `file://` 下被限制时，显示手动复制 textarea；不能把打开兜底弹层表述成“已经复制”。

不要加入类型下拉、选择类型后的二次确认框、大遮罩确认流程或需要后端服务的评论系统。

## 剪贴板交接

`复制批注给 Agent` 是默认主路径。复制内容必须包含：

```text
报告：...
文件名：...
绝对路径：/Users/.../report.html
File URL：file:///Users/.../report.html
轮次：round-...
交接时间：...
批注数量：...
```

每条批注包含 `id`、章节、`blockId`、原文、上下文、批注正文和创建时间。末尾必须明确要求 Agent：

1. 直接修改绝对路径指向的同一份 HTML，不另建结果副本。
2. 处理完成后用 `inject_annotation_mode.py --processed-round <round-id> --processed-count <count> --content-changed yes|no` 写回回执。
3. 运行 `check_html_report.py --require-review-receipt`，并回复实际路径、处理条数和未采纳项。

复制成功后在页面持久显示“本轮 N 条批注已复制，等待 Agent 处理”。剪贴板失败时保留草稿，不得提前进入“已复制”状态。

## 批注版 HTML 备用交接

点击 `保存批注版 HTML（备用）` 后，必须生成仍可继续批注的单文件 HTML，并把当前 `AgentQuestionPack` 放进唯一的非执行节点：

```html
<!-- QA_EMBEDDED_REVIEW_START: Agent 读取并逐条处理以下批注。 -->
<script type="application/json" id="qaEmbeddedReviewData" data-qa-review-data>
{ "type": "AgentQuestionPack", "version": "0.3.0", "roundId": "round-...", "annotations": [] }
</script>
<!-- QA_EMBEDDED_REVIEW_END -->
```

- 重复保存先替换旧区块，最终只能有一对 marker 和一个数据节点。
- JSON 写入 raw-text 前必须转义 `<`、`>`、`&`、U+2028、U+2029；读取使用 `textContent + JSON.parse()`。
- 保存前清理侧栏打开态、输入浮层、复制弹窗、focus pulse 和运行时高亮，重新打开后按包恢复。
- 新一轮待处理包必须移除上一轮 `AgentReviewReceipt`，避免页面同时显示“等待处理”和“已处理”。
- 同一路径正文变化时，初始化和交接前按原文、上下文与章节做唯一匹配迁移；不能唯一定位的批注明确标记并阻止交接。
- `localStorage` 数组存在时优先使用，即使是 `[]`；继续兼容旧版生成期绝对路径存储键。
- 支持 File System Access API 时弹保存选择；不支持时下载 `_reviewed`，当前文件已是 `_reviewed` 时使用 `_copy`。
- 只有 `writable.close()` 成功才能清理旧草稿。下载只能提示“已发起，请确认落盘”，并保留原页草稿。

`AgentQuestionPack.delivery` 必须保持 `mode: embedded-html`、`status: ready-for-agent`，并要求 Agent 完成后运行 `inject_annotation_mode.py --processed` 和 `check_html_report.py --require-review-receipt`。非空包中的每个 `blockId` 必须在当前 `<main>` 中恰好命中一次。

## Agent 处理回执

Agent 处理完成后删除待处理包，但必须写入独立回执，不能无痕结束：

```html
<!-- QA_AGENT_REVIEW_RECEIPT_START: Agent 本轮处理结果。 -->
<script type="application/json" id="qaEmbeddedReviewReceipt" data-qa-review-receipt>
{
  "type": "AgentReviewReceipt",
  "version": "0.1.0",
  "roundId": "round-...",
  "processedAt": "2026-08-03T00:00:00Z",
  "status": "processed",
  "total": 3,
  "handled": 3,
  "skipped": 0,
  "contentChanged": true,
  "changedSections": ["方案"],
  "results": []
}
</script>
<!-- QA_AGENT_REVIEW_RECEIPT_END -->
```

- `status` 只允许 `processed | partial | failed`；`contentChanged` 是 Agent 的显式回报，可以是 `true | false | null`，浏览器不能自行推断。
- HTML 内嵌包交接完成后运行：

  ```bash
  python3 skills/html-report/scripts/inject_annotation_mode.py <html-file> --processed --content-changed yes
  ```

- 剪贴板交接完成后运行：

  ```bash
  python3 skills/html-report/scripts/inject_annotation_mode.py <html-file> \
    --processed-round <round-id> --processed-count <count> --content-changed yes
  ```

- 需要记录逐条结果时，Agent 可准备符合 schema 的 JSON，通过 `--receipt-file <json>` 注入；HTML 含待处理包时，回执与批注包的 `roundId` 必须一致，脚本才会移除待处理包并写入回执。
- 写回后必须运行 `check_html_report.py <html-file> --require-review-receipt`。
- 页面加载回执后清理上一轮浏览器草稿；用户在该回执基础上新增批注时，新的草稿轮次继续保留。
- 页面持久显示“Agent 已处理 X/Y 条 · HTML 已更新 / 正文未修改 / 处理结果已写入回执”，并显示处理时间和改动章节。

## Agent 回写流程

### 用户粘贴批注包

1. 从包头读取绝对路径、轮次和批注数量，确认该路径是本轮回写目标。
2. 逐条按 `blockId`、章节、原文和上下文处理；无法定位或不采纳时明确说明，不能静默忽略。
3. 修改同一 HTML 后按包尾命令写入汇总回执；`contentChanged` 必须按实际结果传 `yes` 或 `no`。
4. 使用 `--require-review-receipt` 校验，回复同一路径、处理条数和未采纳项。

### 用户交付批注版 HTML

1. 先运行 `check_html_report.py <html-file> --require-review-pack`；缺包、坏包或多包时停止修改。
2. 解析 `#qaEmbeddedReviewData` 后逐条处理；不能先重新注入，否则会丢失待处理意见。
3. 处理完成后运行 `inject_annotation_mode.py <html-file> --processed --content-changed yes|no`。该命令移除待处理包、写入与 `roundId` 绑定的回执并规范化批注 UI。
4. 运行 `check_html_report.py <html-file> --require-review-receipt`；回复同一路径、处理条数和未采纳项。

## 发布版契约

批注版必须提供 `导出发布版`。发布版需要物理剥离：

- 批注侧栏、选区气泡、右键菜单、输入浮层、批注 CSS 和 JS。
- `AgentQuestionPack`、`AgentReviewReceipt`、相关 marker、本地绝对路径和处理状态。
- 批注高亮 class 与 `data-block-id`。

正文、目录、代码复制、表格、SVG 图等阅读能力必须保留。发布版默认使用 `_public` 后缀；确认框或文件选择器取消时不能继续下载。

## 稳定性要求

- 注入脚本幂等；三类批注资产必须保留 `QA_ANNOTATION_*` marker，处理回执必须保留 `QA_AGENT_REVIEW_RECEIPT_*` marker。
- `annotation.js` 保留 `__QA_REPORT_META__` 占位符，注入阶段写入文件名、绝对路径和 `file://` URL。
- 选区气泡缓存目标，避免点击按钮后选区丢失；编辑、删除、清空和重新关联必须同步正文高亮与浏览器选区。
- 既有 `data-block-id` 初始化时从最大序号继续分配；旧定位只能迁移到原文唯一命中的节点，不能模糊猜测。
- 手动重新关联只接受 `<main>` 内合法选区；Esc、取消或无效选区只退出临时模式，不修改批注数据。
- 复制和备用保存都必须在交接前完成定位校验；任一非空批注无法安全定位时停止交接。
- `localStorage` 只负责草稿和复制中的临时状态；可靠完成证明必须来自 HTML 内 `AgentReviewReceipt`。
- 最终报告必须通过普通 `check_html_report.py`；接收待处理文件用 `--require-review-pack`，Agent 声明处理完成用 `--require-review-receipt`。
