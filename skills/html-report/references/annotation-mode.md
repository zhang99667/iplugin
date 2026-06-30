# HTML 报告离线批注模式

当用户希望在 HTML 报告里直接对文字、段落、表格或图表提出疑问，或希望把批注导出给 Agent 继续处理时，使用本模式。默认不要为所有报告加入批注；只有用户明确要求“批注”“审核模式”“对 HTML 里内容提问”“导出给 Agent 的提问包”等场景才加入。

## 使用方式

先生成普通单文件 HTML，并通过基础校验：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

再注入批注模式：

```bash
python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>
```

最后再次校验：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

不要手写批注 CSS/JS。批注交互代码较长，必须由 `inject_annotation_mode.py` 统一注入，避免每次生成时按钮、路径字段、发布版剥离逻辑漂移。

## 交互契约

审核版 HTML 提供这些能力：

- 选中文本后显示轻量气泡，只包含 `提问` 和 `批注` 两个入口。
- 点击入口后出现贴近选区的小浮层，浮层只有一个 `提交` 按钮；点击浮层外侧自动关闭。
- 右键菜单作为辅助入口，支持对选中内容、本段或本节提问/批注。
- 右上角入口在 0 条批注时显示为明确的 `导出发布版`，点击直接导出发布版，且不能残留数字徽标或蓝色计数圆点；有批注时才显示 `批注 N` 并打开右侧栏。
- 右侧栏列出所有批注，支持定位、编辑、复制单条、删除、复制 Markdown、下载 Markdown、下载 JSON、导出发布版、清空批注；`导出发布版` 必须是右侧栏顶部最明显的主按钮。
- 复制剪贴板在 `file://` 下被浏览器限制时，必须显示手动复制 textarea 兜底。

不要加入问题类型下拉、双按钮确认框、大遮罩弹窗或需要后端服务的评论系统。这个模式的目标是轻、离线、单文件、可给 Agent 使用。

## 发布版契约

审核版必须带 `导出发布版` 按钮。发布版不是简单隐藏批注 UI，而是物理剥离：

- 删除批注侧边栏、选区气泡、右键菜单和输入浮层。
- 删除批注 JS 和批注 CSS。
- 删除批注高亮 class 和 `data-block-id`。
- 保留正文、目录、代码复制、表格、SVG 图等正常阅读能力。

浏览器支持 File System Access API 时，导出发布版可弹出保存/覆盖选择；不支持时退化为下载当前文件名，由用户在浏览器下载流程中决定是否覆盖。确认框里的 `取消` 必须真正取消导出，不能下载 `_public` 文件。

## Agent 提问包契约

Markdown 和 JSON 导出必须带来源定位，避免交给 Agent 或子 Agent 后找不到原报告。
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
  "version": "0.2.0",
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
  "annotations": []
}
```

每条批注至少包含：`sectionTitle`、`blockId`、`selectedText` 或 `blockText`、`contextBefore`、`contextAfter`、`kind`、`text`、`createdAt`。新增批注时也写入 `reportFileName`、`reportAbsolutePath` 和 `reportFileUrl`，保证单条复制也能回查原 HTML。编辑批注时保留原定位和 `createdAt`，更新 `text` 并写入 `updatedAt`。

## 稳定性要求

- 注入脚本必须幂等：重复运行不能生成两套批注 UI。
- 选区气泡出现时要缓存选区目标，避免点击按钮导致浏览器清空选区后无法打开输入浮层。
- 编辑已有批注必须复用轻量输入浮层，提交后更新本条数据、刷新右侧栏和导出包，不能要求用户删除后重加。
- 删除或清空批注后，必须同步清理正文里的 `.qa-highlight`、`.qa-annotated-block` 和浏览器选区；不能只删除右侧栏数据。
- 批注数据可以临时存 `localStorage`，但不能只依赖它；Markdown/JSON 导出是可靠交接方式。
- `check_html_report.py` 必须在最终报告上通过。它会检查批注标记、发布版剥离入口、路径字段、选区缓存和单按钮浮层。
