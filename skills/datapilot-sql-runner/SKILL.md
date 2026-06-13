---
name: datapilot-sql-runner
version: 0.1.0
tags: [datapilot, sql, chrome, data, baidu, analytics]
description: DataPilot SQL 跑数闭环助手。当用户要求在百度 DataPilot/datapilot 上跑 SQL、提交 SQL、批量运行本地 .sql/.SQL 文件、替换实验号/日期后跑数，或需要回收 DataPilot 任务 ID、排队/执行状态时触发；优先配合 Chrome 登录态、sql-exp-replace 和 Monaco 编辑器提交经验完成“准备 SQL → 提交 run → 回收任务 ID → 汇报状态”。
user_invocable: true
---

# DataPilot SQL Runner

目标：把“准备 SQL → 打开 DataPilot → 填入编辑器 → 点击 run → 回收任务 ID → 汇报状态”做成稳定闭环。DataPilot 是内部站点，通常依赖用户 Chrome 登录态，因此浏览器侧优先使用 `chrome:control-chrome` skill 和 Chrome 插件。

## 触发边界

### 适用

- 用户要求在 `https://datapilot.baidu-int.com/dataAnalysis` 跑 SQL。
- 用户给出一个目录、多份 `.sql` / `.SQL` 文件，要求批量提交。
- 用户要把 SQL 的日期、实验号、实验组/对照组替换后再提交。
- 用户需要拿到 DataPilot 任务 ID、排队状态、执行状态或失败信息。
- 用户说“帮我在 DataPilot 跑一下”“datapilot 跑数”“这几个 SQL 提交一下”“用 Chrome 跑 DataPilot”。

### 不适用

- 只是解释 SQL、写 SQL、优化口径或生成 SQL 文本：使用对应 SQL 写作、代码阅读或直接回答。
- 只替换实验号和日期但不提交 DataPilot：使用 `sql-exp-replace`。
- 需要生成商业/NAD SQL 但还不跑数：使用 `commercial-sql-writer`。

## 输入收集

从用户消息和上下文提取：

- SQL 来源：目录、文件列表、单个文件、附件，或用户直接贴的 SQL。
- 日期范围：例如 `6.3-6.9`。当前年份不明确时结合当前日期；仍不明确就向用户确认。内部广告 SQL 通常使用 `YYYYMMDD`。
- 实验号：基础号如 `161703`，并保留 `-0` / `-dz` 后缀语义。
- 是否要等结果完成：默认只提交并回收任务 ID；如果用户要求“跑完看结果”，再持续轮询。
- 运行队列或引擎：默认使用页面当前 run 设置；如果用户指定简单/中等任务或其他引擎，按页面控件选择。

## SQL 预处理

1. 用 `rg --files` 列出目录下 SQL 文件，保留用户给出的文件顺序；如果没有顺序，就按文件名稳定排序。
2. 如果需要替换实验号或日期，优先触发并使用 `sql-exp-replace`：
   - 先 `--scan` 每个 SQL，识别实验号基础号、`event_day` / `dt` / `log_date` 等日期字段。
   - 只替换确认需要替换的实验号和日期字段。
   - 基础实验号映射如 `160706=161703` 应同步覆盖 `160706-0` 和 `160706-dz`。
   - 日期范围如 `6.3-6.9` 应转成 `20260603` 到 `20260609` 这样的明确格式。
3. 不直接修改原始 SQL 文件。把提交版写到 `/private/tmp/datapilot_sql_run_<exp>_<start>_<end>/` 或类似临时目录。
4. 对脚本覆盖不到的单日分区做最小补丁。例如维表关联 `t3.event_day='20260519'` 通常应改成区间结束日 `20260609`，但必须基于 SQL 语义判断。
5. 提交前做残留检查：
   - 旧实验号、旧日期不应残留在提交版里。
   - 新实验号、新日期应出现在预期位置。
   - 如果发现多个旧实验号、多个日期语义或标签映射不清，先询问用户。

## Chrome 和 DataPilot 操作

优先使用 `chrome:control-chrome`，并遵循其 Chrome skill 的连接、标签接管和清理规则。

标准流程：

1. 连接 Chrome 插件。
2. `browser.user.openTabs()` 查找已有 DataPilot 标签页。
3. 如果已有 `https://datapilot.baidu-int.com/dataAnalysis`，用 `browser.user.claimTab(tabInfo)` 接管；否则新建标签页并打开该 URL。
4. 等待页面 `domcontentloaded`，用 `domSnapshot()` 或截图确认已登录且页面可用。
5. 优先使用现有 `草稿:newSql`，或点击 `Add tab` 新建草稿。
6. 将 SQL 写入剪贴板，再粘贴到 Monaco 编辑器：
   - 用 `tab.clipboard.writeText(sql)`。
   - 动态选择可见的 `textarea.inputarea`，条件建议是 `getBoundingClientRect().width > 50 && height > 10`。
   - 点击可见 textarea，执行 `ControlOrMeta+A`，再 `ControlOrMeta+V`。
   - 不要固定使用第一个 `textarea.inputarea`；DataPilot 多标签后旧编辑器会保留隐藏 textarea，固定 `nth(0)` 容易点到隐藏元素。
7. 粘贴后校验：
   - 检查页面文本是否包含 SQL 注释头、关键表名、实验号或日期。
   - 或截图确认编辑器行数与 SQL 大致匹配。
   - 注意长 SQL 粘贴成功后 Monaco 可能自动滚到末尾，不能只看第一屏判断失败。
8. 提交：
   - 点击按钮名包含 `run` 的按钮。
   - 点击前记录页面已有 `任务ID:\d+`。
   - 点击后轮询页面文本，找新出现的任务 ID。
9. 对每个 SQL 记录 `{文件名, taskId, 初始状态}`。
10. 最后用 `browser.tabs.finalize({ keep: [{ tab, status: 'deliverable' }] })` 保留 DataPilot 页面，方便用户继续查看。

## 任务状态提取

DataPilot 左侧任务卡片会重复出现 `任务ID:<id>` 和 `ID:<id>`。解析时不要简单截取固定长度后搜索，因为相邻卡片可能串在一起。

推荐做法：

- 起点：`任务ID:<id>`。
- 终点：从起点之后继续找对应的 `ID:<id>`。
- 在这段卡片文本里识别状态：`排队中`、`执行中`、`运行中`、`成功`、`失败`、`超时`。
- 如果终点没找到，就先截取有限长度并明确说明状态可能不完整。

默认不等待所有任务跑完。DataPilot 中等任务可能排队数百秒，用户通常先需要任务 ID。只有用户明确要求“等结果/看结果/导出结果”时，才继续轮询或下载。

## 汇报格式

完成提交后，用简洁列表汇报：

```text
已提交到 DataPilot：
- 智能体展点消.sql: 86299031，排队中
- 曝光部分展点消.SQL: 86299106，排队中
```

同时说明：

- 提交前做了哪些替换，例如 `日期 20260603-20260609，实验号 161703`。
- 原始 SQL 是否未改动。
- 临时提交版 SQL 的目录。
- DataPilot 标签页是否已保留。
- 如果有失败/超时，给出失败任务 ID、错误片段和下一步建议。

## 常见坑和处理

### Monaco 粘贴看起来失败

如果 `document.body.innerText.includes(marker)` 返回 false，不代表一定失败。长 SQL 粘贴后 Monaco 可能滚到末尾，第一屏看不到注释头。检查：

- 编辑器行号是否变多。
- 可见 textarea 的 `value` 是否是 SQL 末尾片段。
- 页面截图或任务卡片是否显示了 SQL 注释头。

### 新建草稿后点击隐藏 textarea

DataPilot 会保留多个隐藏的 Monaco textarea。批量提交时每新增一个草稿，可见 textarea 的索引可能从 `3`、`4`、`5` 递增。始终动态选择可见 textarea，不要硬编码索引。

### run 后没有新任务 ID

检查：

- 是否弹出运行配置、权限提示或错误 alert。
- SQL 是否真的粘到当前草稿，而不是隐藏编辑器。
- run 按钮是否被禁用。
- 页面左侧任务列表是否需要刷新。

### 状态误判

如果直接在长页面文本里搜索 `成功`，可能匹配到相邻旧任务。必须按任务卡片边界截取状态。

### 登录态或 Chrome 插件问题

遵循 `chrome:control-chrome` skill 的连接恢复流程。不要读取 cookies、localStorage、密码或个人资料；不要绕过登录、验证码或权限控制。Chrome 插件不可用时，向用户说明需要修复 Chrome 插件或手动登录，不要用不相关工具硬绕。

## 真实操作经验沉淀

- 目录下多份 SQL 可能只有部分需要替实验号；先扫描再判断，不要机械全改。
- `6.3-6.9` 在当前日期为 2026 年时应展开为 `20260603` 到 `20260609`。
- 某些 SQL 除 `event_day between ...` 外还有 `t3.event_day='旧结束日'` 这类单日维表分区，需要按语义同步成新区间结束日。
- 第一次粘贴后校验注释头失败，但实际 SQL 已粘贴成功并滚到末尾；任务卡片能看到注释头时可判定提交内容正确。
- 批量新建草稿后，固定 `textarea.inputarea.nth(0)` 会点到隐藏元素；改成查找可见 textarea 后稳定提交。
- 提交成功后新任务可能立即显示为 `排队中`，不代表失败；应回收任务 ID 并告知队列状态。
