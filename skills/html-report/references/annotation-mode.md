# HTML 报告评论模式

当用户希望在 HTML 报告里直接对文字、段落、表格或图表提出疑问，或希望把评论结果内嵌回 HTML 交给 Agent 继续处理时，使用评论模式。默认不要为所有报告加入；只有用户明确要求“评论模式”“批注”“对 HTML 里内容提问”“把评论结果写回 HTML”“按 HTML 内嵌批注更新报告”等场景才加入。为兼容旧请求，用户说“审核模式”或“审核结果”时也按评论模式处理，但生成页面和回复统一使用“评论模式”。

## 使用方式

先生成普通单文件 HTML，并通过基础校验：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

再注入评论模式：

```bash
python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>
```

最后再次校验：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

不要手写评论 CSS/JS。交互代码较长，维护源码时放在 `assets/annotation-mode/annotation.css`、`annotation.html`、`annotation.js`，生成评论版时必须由 `inject_annotation_mode.py` 统一读取并内联注入，避免每次生成时按钮、路径字段、发布版剥离逻辑漂移。

## 交互契约

评论版 HTML 提供这些能力：

- 选中文本后显示轻量气泡，只保留一个 `注释` 入口；问题和修改建议都从这个入口输入，不再让用户先判断类型。
- 点击 `注释` 后出现贴近选区的小浮层，浮层只有一个 `提交` 按钮；按钮内必须显示 `Ctrl/⌘ + Enter` 快捷键标识，支持 `⌘ + Enter`（Windows/Linux 为 `Ctrl + Enter`）提交，普通 Enter 保留换行，点击浮层外侧自动关闭。
- 右键菜单作为辅助入口，保留对选中内容、本段或本节提问，以及添加注释的细分操作。
- 右上角固定为批注工作区入口：0 条时显示 `批注`，有批注时通过独立数量徽标表达 `批注 N`；点击始终打开或关闭侧栏，不能在零条时切换成 `导出无批注版`。删除或清空最后一条批注后仍保持侧栏可达，以便把空结果写回 HTML。
- 侧栏列表提供 `全部`、`提问`、`注释` 三个轻量筛选视图，各自显示当前数量；点击批注原文摘录即可快速定位正文，显式 `定位` 按钮继续保留为备用入口。
- 右侧栏列出所有批注，支持定位、编辑、复制单条、删除、`完成批注`、复制 Markdown、下载 Markdown、导出无批注版、清空批注；`完成批注` 必须是最明显的主按钮，并明确表示会把当前批注写入 HTML 供 Agent 处理。
- `下载 JSON` 不再作为用户入口；结构化 `AgentQuestionPack` 直接内嵌进评论版 HTML，Markdown 只保留为兼容和人工复制兜底。
- 复制剪贴板在 `file://` 下被浏览器限制时，必须显示手动复制 textarea 兜底。

不要加入问题类型下拉、双按钮确认框、大遮罩弹窗或需要后端服务的评论系统。这个模式的目标是轻、离线、单文件、可给 Agent 使用。

## 评论版契约

点击 `完成批注` 后，必须生成仍可继续评论的单文件 HTML，并把当前 `AgentQuestionPack` 放进 `<head>` 中唯一的非执行节点：

```html
<!-- QA_EMBEDDED_REVIEW_START: Agent 读取并逐条处理以下评论结果。 -->
<script type="application/json" id="qaEmbeddedReviewData" data-qa-review-data>
{ "type": "AgentQuestionPack", "annotations": [] }
</script>
<!-- QA_EMBEDDED_REVIEW_END -->
```

- 重复保存必须先替换旧区块，最终只能有一对 marker 和一个 `#qaEmbeddedReviewData[data-qa-review-data]`。
- 删除或清空最后一条批注后仍要保持评论态，并允许保存 `annotations: []` 的空包；这样才能覆盖磁盘里的旧批注，不能以“暂无批注”为由拒绝保存。
- JSON 写入 `script` raw-text 前必须把 `<`、`>`、`&`、U+2028、U+2029 转成 JSON Unicode 转义，防止批注里的 `</script>` 提前闭合节点或注入 HTML；读取时用 `textContent + JSON.parse()`，不能用 `innerHTML`。
- 保存前清理侧栏打开态、输入浮层、复制弹窗、focus pulse 和运行时高亮；重新打开时再根据批注包恢复定位与高亮。
- 同一路径的报告正文被重新生成时，旧 `localStorage` 评论可能仍引用上一版的顺序型 `blockId`。初始化和保存前必须先按 `blockText`、选中文本、上下文与章节做唯一匹配迁移；无法唯一命中的评论要明确标记为“原文已变化”并停止保存，不能继续产出评论存在但无法定位的 HTML。
- `localStorage` 中存在当前文件的数组时优先使用，即使它是 `[]`；只有 key 不存在、不可用或损坏时才回退到内嵌包，避免用户清空后旧批注复活。
- 读取草稿时必须兼容旧版“生成期绝对路径”存储键：新键不存在时读取并迁移旧键，保存和清理时同时覆盖兼容键，避免 HTTP 预览或 Windows `file://` 路径升级后草稿看似丢失。
- 支持 File System Access API 时弹出系统保存选择，默认使用当前文件名，用户可选择原文件覆盖；网页不能静默改写本地文件。不支持时下载带 `_reviewed` 后缀的 HTML；当前文件已是 `_reviewed` 时改用 `_copy`，避免默认路径碰撞。
- 只有 `writable.close()` 成功的直接写入才能清理旧 `localStorage` 基线。下载兜底只能确认“已发起”，不能知道用户是否取消或被浏览器拦截，因此必须保留原页草稿并明确提示；下载文件依靠不同运行时路径从内嵌包恢复。

## 发布版契约

评论版必须带 `导出无批注版` 按钮。发布版不是简单隐藏评论 UI，而是物理剥离：

- 删除批注侧边栏、选区气泡、右键菜单和输入浮层。
- 删除批注 JS 和批注 CSS。
- 删除 `QA_EMBEDDED_REVIEW_START/END` 和 `[data-qa-review-data]`，避免内部意见、上下文及本地绝对路径泄漏到外部版本。
- 删除批注高亮 class 和 `data-block-id`。
- 保留正文、目录、代码复制、表格、SVG 图等正常阅读能力。

浏览器支持 File System Access API 时，导出发布版弹出保存选择，默认使用 `_public` 后缀并建议另存，避免覆盖唯一的评论版；不支持时退化为下载 `_public` HTML。确认框或文件选择器里的取消必须真正取消导出，不能继续下载。

## Agent 提问包契约

Markdown 和 HTML 内嵌 JSON 必须带来源定位，避免交给 Agent 或子 Agent 后找不到原报告。
注入脚本必须在生成阶段把输出 HTML 的文件名、绝对路径和 `file://` URL 写入批注 JS；运行时从 `location` 推断只能作为兜底，不能作为唯一来源。

Markdown 顶部必须包含：

```text
报告：...
文件名：...
绝对路径：/Users/.../report.html
File URL：file:///Users/.../report.html
导出时间：...
批注数量：...
```

JSON 顶层必须包含：

```json
{
  "type": "AgentQuestionPack",
  "version": "0.3.0",
  "reportTitle": "...",
  "reportFileName": "...",
  "reportAbsolutePath": "/Users/.../report.html",
  "reportFileUrl": "file:///Users/.../report.html",
  "source": {
    "title": "...",
    "fileName": "...",
    "absolutePath": "/Users/.../report.html",
    "fileUrl": "file:///Users/.../report.html"
  },
  "delivery": {
    "mode": "embedded-html",
    "status": "ready-for-agent",
    "instruction": "以当前承载此包的 HTML 为回写目标；逐条处理 annotations；完成后删除评论区块，重新运行 inject_annotation_mode.py，再运行不带 --require-review-pack 的 check_html_report.py。"
  },
  "exportedAt": "2026-07-13T00:00:00.000Z",
  "annotations": []
}
```

每条批注至少包含唯一且非空的 `id`，以及 `sectionTitle`、`blockId`、`selectedText` 或 `blockText`、`contextBefore`、`contextAfter`、`kind`、`text`、`createdAt`。新增批注时也写入 `reportFileName`、`reportAbsolutePath` 和 `reportFileUrl`，保证单条复制也能回查原 HTML。编辑批注时保留原定位和 `createdAt`，更新 `text` 并写入 `updatedAt`。

非空评论包中的每个 `blockId` 必须在当前 HTML 的 `<main>` 内 `data-block-id` 属性中恰好命中一个节点；缺失、位于 main 外或重复都属于不可安全回写的交接错误，必须先修复定位，不能只靠模糊文本猜测后继续修改。

`source` 和单条批注里的路径字段只表示报告最初生成位置，用于内容回查；用户另存或浏览器下载后，Agent 的实际回写目标始终是当前承载该评论包、由用户交付的 HTML 文件，不能根据旧 `source.absolutePath` 改写另一个副本。

## Agent 回写流程

当用户说“我已在 HTML 里完成批注，请更新报告”或同义表达时：

1. 先运行 `python3 skills/html-report/scripts/check_html_report.py <html-file> --require-review-pack`。如果缺少评论包、JSON 损坏或存在多个包，必须停止修改并请用户点击 `完成批注` 后提供正确文件；不能把校验失败解释成“没有批注”。
2. 校验通过后再读取当前交付的 HTML，定位 `QA_EMBEDDED_REVIEW_START/END`，解析 `#qaEmbeddedReviewData`；该文件本身是回写目标，`source` 仅用于回查。不能先重新注入评论模式，否则可能丢失待处理意见。
3. 按 `annotations` 顺序结合 `blockId`、章节、原文和上下文逐条处理；批注是修改要求，提问需要回答并在必要时修正文档表达或证据。合法的空数组表示用户已明确清空，无需猜测旧意见。
4. 所有批注处理完成后，从 HTML 中物理删除整个内嵌评论区块，避免下一轮重复处理。
5. 重新运行 `inject_annotation_mode.py` 规范化评论 UI，再运行不带 `--require-review-pack` 的普通 `check_html_report.py`，确保已移除旧包的更新报告可以进入下一轮评论。
6. 回复用户更新后的同一 HTML 路径和处理条数；存在未采纳项时逐条说明原因，不能静默忽略。

## 稳定性要求

- 注入脚本必须幂等：重复运行不能生成两套批注 UI。
- 批注资产必须保留 `QA_ANNOTATION_CSS_START/END`、`QA_ANNOTATION_HTML_START/END`、`QA_ANNOTATION_SCRIPT_START/END` 标记；这些标记用于重复注入前清理旧 UI，也用于浏览器端导出发布版时物理剥离批注能力。
- `annotation.js` 必须保留 `__QA_REPORT_META__` 占位符，由注入脚本在生成阶段写入文件名、绝对路径和 `file://` URL。
- 选区气泡出现时要缓存选区目标，避免点击按钮导致浏览器清空选区后无法打开输入浮层。
- 编辑已有批注必须复用轻量输入浮层，提交后更新本条数据、刷新右侧栏和导出包，不能要求用户删除后重加。
- 筛选属于编辑期 UI 状态，不写入 `AgentQuestionPack`；切换筛选只能影响列表视图，不能改变批注顺序或交接数据。
- 批注原文摘录可以作为快捷定位按钮使用，并保留显式 `定位` 备用按钮；定位失败时仍必须沿用原文变化提示和安全迁移门禁。
- 评论卡片中的“提问/注释”是评论模块内部类型徽标，不注册成独立顶层组件；徽标必须禁止 flex 收缩和换行，长章节标题承担剩余空间的收缩与换行，不能把两个字挤成竖排。
- 输入浮层的快捷键监听必须限制在输入框内，并跳过输入法组字阶段；快捷键与按钮必须复用同一提交逻辑。
- 删除或清空批注后，必须同步清理正文里的 `.qa-highlight`、`.qa-annotated-block` 和浏览器选区；不能只删除右侧栏数据。
- 评论版保留既有 `data-block-id` 时，初始化必须从已有最大序号继续分配，避免 Agent 增加段落后生成重复定位 ID。
- 点击定位时如果原 `blockId` 已失效，只允许迁移到原文唯一命中的当前正文节点；找不到或存在多个候选时提示用户在新位置重新添加，不能静默失败或模糊猜测。
- `完成批注` 必须在打开文件选择器前完成定位校验；任何非空评论无法在当前 `<main>` 中安全定位时停止保存，保证生成的评论包通过 `--require-review-pack`。
- 批注数据可以临时存 `localStorage`，但不能只依赖它；内嵌评论版 HTML 是默认可靠交接方式，Markdown 是兜底。
- `check_html_report.py` 必须在最终报告上通过。它会检查批注标记、稳定批注入口、完成批注入口、内嵌包 schema 与唯一性、安全序列化、发布版剥离、路径字段、选区缓存、单按钮浮层和快捷提交契约；接收用户已完成评论的文件时额外使用 `--require-review-pack`，防止错拿原始版或发布版。
