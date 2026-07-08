# Chrome Fallback

本文件只服务 `datapilot-sql-runner` 的兜底路径。默认不要读取或使用 Chrome；只有 DataPilot MCP 不可用、认证/权限不可恢复、MCP 无法表达页面专属设置，或用户明确要求浏览器操作时才进入这里。

## 回退原则

- 已经拿到 MCP `task_id` 时，不要重新提交同一条 SQL。先用任务 ID 在 DataPilot 运行中心或页面任务列表里查状态。
- Chrome 只负责兜底提交、页面状态定位或页面专属设置，不改变主流程“提交 -> 查状态 -> 下载结果 -> 可选透视表”的交付目标。
- 遵循 `chrome:control-chrome` skill 的连接、标签接管和清理规则。
- 不读取 cookies、localStorage、密码或个人资料；不绕过登录、验证码或权限控制。

## 页面连接

1. 连接 Chrome 插件。
2. 用 `browser.user.openTabs()` 查找已有 DataPilot 标签页。
3. 如果已有 `https://datapilot.baidu-int.com/dataAnalysis`，用 `browser.user.claimTab(tabInfo)` 接管；否则新建标签页并打开该 URL。
4. 等待页面 `domcontentloaded`，用 `domSnapshot()` 或截图确认已登录且页面可用。
5. 优先使用现有 `草稿:newSql`，或点击 `Add tab` 新建草稿。

## Monaco 粘贴 SQL

1. 将 SQL 写入剪贴板：`tab.clipboard.writeText(sql)`。
2. 动态选择可见的 `textarea.inputarea`，判断条件建议是 `getBoundingClientRect().width > 50 && height > 10`。
3. 点击可见 textarea，执行 `ControlOrMeta+A`，再执行 `ControlOrMeta+V`。
4. 不要固定使用第一个 `textarea.inputarea`；DataPilot 多标签后旧编辑器会保留隐藏 textarea，固定 `nth(0)` 容易点到隐藏元素。

粘贴后校验：

- 检查页面文本是否包含 SQL 注释头、关键表名、实验号或日期。
- 或截图确认编辑器行数与 SQL 大致匹配。
- 长 SQL 粘贴成功后 Monaco 可能自动滚到末尾，不能只看第一屏判断失败。

## 页面提交

1. 点击按钮名包含 `run` 的按钮。
2. 点击前记录页面已有 `任务ID:\d+`。
3. 点击后轮询页面文本，找新出现的任务 ID。
4. 对每个 SQL 记录 `{文件名, taskId, taskType, 初始状态, 执行路径: Chrome}`。页面没有暴露 `taskType` 时可留空。
5. 最后用 `browser.tabs.finalize({ keep: [{ tab, status: 'deliverable' }] })` 保留 DataPilot 页面，方便用户继续查看。

## 状态提取

DataPilot 左侧任务卡片会重复出现 `任务ID:<id>` 和 `ID:<id>`。解析时不要简单截取固定长度后搜索，因为相邻卡片可能串在一起。

推荐做法：

- 起点：`任务ID:<id>`。
- 终点：从起点之后继续找对应的 `ID:<id>`。
- 在这段卡片文本里识别状态：`排队中`、`执行中`、`运行中`、`成功`、`失败`、`超时`。
- 如果终点没找到，就先截取有限长度并明确说明状态可能不完整。

默认不等待所有任务跑完。只有用户明确要求“等结果/看结果/导出结果”，或刚提交的任务已经进入运行态且用户希望继续盯结果时，才继续轮询或下载。

## Chrome 心跳

- 默认心跳间隔为 3 分钟；用户指定“几分钟查一次”时按用户指定间隔执行。
- 每次心跳重新读取任务卡片，按任务 ID 边界提取状态，不要在整页文本里直接搜索 `成功` 或 `失败`。
- 每次状态变化都简短汇报，例如 `87053789：运行中 -> 成功`；状态未变时只在有必要时提示一次。
- 到达终态 `成功` / `失败` / `超时` / `取消` 后停止心跳，并汇报任务 ID、最终状态和错误片段或结果入口。
- 没有用户明确要求长时间等待时，最多心跳 10 次或 30 分钟，先把任务 ID 交给用户并保留 DataPilot 页面。
- 如果 Chrome 插件断开、页面刷新或任务卡片暂时消失，不要重提 SQL；先尝试重新接管 DataPilot 标签页并按任务 ID 搜索状态。

## 常见坑

### 新建草稿后点击隐藏 textarea

DataPilot 会保留多个隐藏的 Monaco textarea。批量提交时每新增一个草稿，可见 textarea 的索引可能从 `3`、`4`、`5` 递增。始终动态选择可见 textarea，不要硬编码索引。

### Monaco 粘贴看起来失败

如果 `document.body.innerText.includes(marker)` 返回 false，不代表一定失败。长 SQL 粘贴后 Monaco 可能滚到末尾，第一屏看不到注释头。检查编辑器行号、可见 textarea 的 `value`、页面截图或任务卡片里的 SQL 注释头。

### Run 后没有新任务 ID

检查是否弹出运行配置、权限提示或错误 alert；SQL 是否真的粘到当前草稿而不是隐藏编辑器；run 按钮是否被禁用；页面左侧任务列表是否需要刷新。

### 状态误判

如果直接在长页面文本里搜索 `成功`，可能匹配到相邻旧任务。必须按任务卡片边界截取状态。

### 登录态或 Chrome 插件问题

Chrome 插件不可用时，向用户说明需要修复 Chrome 插件或手动登录，不要用不相关工具硬绕。
