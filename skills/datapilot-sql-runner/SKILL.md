---
name: datapilot-sql-runner
version: 0.1.2
tags: [datapilot, sql, mcp, chrome, data, baidu, analytics]
description: DataPilot SQL 跑数闭环助手。当用户要求在百度 DataPilot/datapilot 上跑 SQL、提交 SQL、批量运行本地 .sql/.SQL 文件、替换实验号/日期后跑数，或需要回收 DataPilot 任务 ID、排队/执行状态、运行中心跳检查时触发；优先使用 DataPilot MCP 提交、查状态和下载结果，MCP 不可用或能力不覆盖时再回退 Chrome 登录态、sql-exp-replace 和 Monaco 编辑器提交经验。
user_invocable: true
---

# DataPilot SQL Runner

目标：把“准备 SQL → 提交 DataPilot → 回收任务 ID → 跟进状态/下载结果 → 汇报状态”做成稳定闭环。当前首选 DataPilot MCP，因为它可以绕开页面编辑器脆弱性并直接拿到结构化任务信息；只有 MCP 不可用、认证失败、能力不覆盖用户指定操作，或需要依赖页面现有设置时，才回退到 `chrome:control-chrome` skill 和 Chrome 插件。

## 触发边界

### 适用

- 用户要求在 `https://datapilot.baidu-int.com/dataAnalysis` 跑 SQL。
- 用户给出一个目录、多份 `.sql` / `.SQL` 文件，要求批量提交。
- 用户要把 SQL 的日期、实验号、实验组/对照组替换后再提交。
- 用户需要拿到 DataPilot 任务 ID、排队状态、执行状态或失败信息。
- 用户说“帮我在 DataPilot 跑一下”“datapilot 跑数”“这几个 SQL 提交一下”“用 MCP 跑 DataPilot”“用 Chrome 跑 DataPilot”。

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
- 是否要心跳检查：如果任务提交后处于 `排队中` / `执行中` / `运行中`，且用户要求继续盯结果，或当前对话仍在等待跑数结果，可以按心跳机制定期复查。
- 运行队列或引擎：默认使用 MCP 提交接口能力；如果用户指定简单/中等任务或其他引擎而 MCP 无法表达该设置，回退 Chrome 并按页面控件选择。

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

## 执行路径选择

先检查当前环境是否暴露 DataPilot MCP 工具，例如 `mcp__datapilot` namespace 下的 `datapilot_submit_sql`、`datapilot_get_sql_result`、`datapilot_sql_download_judge`、`datapilot_sql_download`、`datapilot_sql_export` 或 `datapilot_sql_export_refresh`。如果工具列表里暂时不可见，先通过可用的工具发现能力搜索 `datapilot sql MCP`；完成这个检查前不要直接打开 Chrome 页面跑数。

路径优先级：

1. **MCP 主路径**：MCP 工具可用，且用户只是提交 SQL、查任务状态、等待结果、下载结果或转储结果时，优先走 MCP。
2. **Chrome 回退路径**：MCP 不可用、MCP 认证/权限不可恢复、MCP 没有覆盖用户指定的页面控件/队列/引擎设置，或用户明确要求沿用浏览器页面操作时，再使用 Chrome。
3. **混合路径**：如果 MCP 已经返回 `task_id`，后续查状态或下载失败时，不要直接重新提交同一 SQL。先用已有 `task_id` 继续查状态；必要时再打开 Chrome 运行中心按任务 ID 查询，避免重复跑数。

如果用户指定某个运行队列或引擎，而 MCP 提交接口没有对应参数，优先向用户说明会回退 Chrome 来保留该设置；不要静默忽略用户指定的运行条件。

## MCP 跑数主路径

MCP 主路径适合批量提交和结构化回收任务信息。

标准流程：

1. 完成 SQL 预处理和残留检查后，为每条 SQL 生成可识别的 `task_name`，优先使用文件名、日期范围和实验号，避免多个任务在 DataPilot 列表里难以区分。
2. 调用 `datapilot_submit_sql({ sql, task_name })` 提交任务。
3. 从返回值里记录 `task_id`、`status` 和 `task_type`。如果返回里没有 `task_type`，先按 `TASK` 记录；后续状态查询如果明确提示类型不匹配，再对同一 `task_id` 重试 `PRO` 一次，并把最终可用类型写进汇报。
4. 对每个 SQL 记录 `{文件名, taskId, taskType, 初始状态, 执行路径: 'MCP'}`。
5. 默认提交后立即汇报任务 ID 和初始状态；只有用户要求“等结果/看结果/下载结果/导出结果”时，才持续轮询。
6. 轮询状态时调用 `datapilot_get_sql_result({ task_id, task_type })`，把 `WAITING`、`RUNNING`、`SUCCESS`、`FAILED`、`OVERTIME` 映射为 `排队中`、`运行中`、`成功`、`失败`、`超时`。
7. 需要下载结果时，先调用 `datapilot_sql_download_judge({ task_id, task_type, separator })`。如果返回 `need_cycle`，按心跳规则继续轮询；如果 `can_download` 或返回下载地址，再调用 `datapilot_sql_download` 获取最终下载地址。
8. 需要转储到 HDFS/AFS 时，必须先让用户选择 `path_type` 并补齐对应参数；不要自行假设使用图灵引用路径、用户自定义路径或默认路径。转储提交后用 `datapilot_sql_export_refresh` 跟进状态。

MCP 出错处理：

- 如果提交接口没有返回 `task_id`，可以改走 Chrome 回退路径重新提交。
- 如果接口返回了 `task_id` 但状态/下载接口失败，先把任务 ID 交给用户，并尝试用 Chrome 运行中心按任务 ID 查状态；不要再次提交同一条 SQL。
- 如果错误明显是 SQL 语法、权限、表不存在或资源限制，停止重试并汇报错误片段。重试工具不能修复 SQL 本身。

## Chrome 回退路径

Chrome 回退路径只在 MCP 不可用或能力不覆盖时使用。使用 `chrome:control-chrome`，并遵循其 Chrome skill 的连接、标签接管和清理规则。

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
9. 对每个 SQL 记录 `{文件名, taskId, taskType, 初始状态, 执行路径: 'Chrome'}`。页面没有暴露 `taskType` 时可留空。
10. 如果任务仍在 `排队中` / `执行中` / `运行中`，按“心跳检查”规则决定是否继续等待。
11. 最后用 `browser.tabs.finalize({ keep: [{ tab, status: 'deliverable' }] })` 保留 DataPilot 页面，方便用户继续查看。

## Chrome 任务状态提取

只有 Chrome 回退路径需要从页面文本里提取状态。DataPilot 左侧任务卡片会重复出现 `任务ID:<id>` 和 `ID:<id>`。解析时不要简单截取固定长度后搜索，因为相邻卡片可能串在一起。

推荐做法：

- 起点：`任务ID:<id>`。
- 终点：从起点之后继续找对应的 `ID:<id>`。
- 在这段卡片文本里识别状态：`排队中`、`执行中`、`运行中`、`成功`、`失败`、`超时`。
- 如果终点没找到，就先截取有限长度并明确说明状态可能不完整。

默认不等待所有任务跑完。DataPilot 中等任务可能排队数百秒，用户通常先需要任务 ID。只有用户明确要求“等结果/看结果/导出结果”，或刚提交的任务已经进入运行态且用户希望继续盯结果时，才继续轮询或下载。

## 心跳检查

用于任务已经成功提交但仍处于 `排队中`、`执行中` 或 `运行中` 的场景。

- 默认心跳间隔为 3 分钟；用户指定“几分钟查一次”时按用户指定间隔执行。
- MCP 路径每次心跳优先调用 `datapilot_get_sql_result({ task_id, task_type })` 获取结构化状态。
- Chrome 路径每次心跳重新读取任务卡片，按任务 ID 边界提取状态，不要在整页文本里直接搜索 `成功` 或 `失败`。
- 每次状态变化都简短汇报，例如 `87053789：运行中 -> 成功`；状态未变时只在有必要时提示一次，避免刷屏。
- 到达终态 `成功` / `失败` / `超时` / `取消` 后停止心跳，并汇报任务 ID、最终状态和错误片段或结果入口。
- 没有用户明确要求长时间等待时，最多心跳 10 次或 30 分钟，先把任务 ID 交给用户；Chrome 路径还要保留 DataPilot 页面。
- 如果心跳期间 Chrome 插件断开、页面刷新或任务卡片暂时消失，不要重提 SQL；先尝试重新接管 DataPilot 标签页并按任务 ID 搜索状态。

## 汇报格式

完成提交后，用简洁列表汇报：

```text
已提交到 DataPilot：
- 智能体展点消.sql: 86299031，TASK，排队中，MCP
- 曝光部分展点消.SQL: 86299106，TASK，排队中，MCP
```

同时说明：

- 提交前做了哪些替换，例如 `日期 20260603-20260609，实验号 161703`。
- 原始 SQL 是否未改动。
- 临时提交版 SQL 的目录。
- 执行路径是 MCP 还是 Chrome；如果是 Chrome，说明 DataPilot 标签页是否已保留。
- 如果用户要求下载或导出结果，给出下载地址、转储路径或仍需继续轮询的原因。
- 如果有失败/超时，给出失败任务 ID、错误片段和下一步建议。

## 常见坑和处理

### MCP 已提交但后续查询失败

只要拿到了 `task_id`，就把它视为已提交任务。先用同一个任务 ID 继续查状态或打开 Chrome 运行中心定位，避免为了“确认是否成功”重复提交同一条 SQL。

### MCP 无法设置用户指定引擎

当用户明确要求某个页面里的运行队列、引擎、资源组或其他 MCP 提交参数里不存在的选项时，回退 Chrome 并通过页面控件选择。不要为了保持 MCP 路径而静默使用默认引擎。

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

如果 MCP 不可用才进入这条路径。遵循 `chrome:control-chrome` skill 的连接恢复流程。不要读取 cookies、localStorage、密码或个人资料；不要绕过登录、验证码或权限控制。Chrome 插件不可用时，向用户说明需要修复 Chrome 插件或手动登录，不要用不相关工具硬绕。

## 真实操作经验沉淀

- 目录下多份 SQL 可能只有部分需要替实验号；先扫描再判断，不要机械全改。
- `6.3-6.9` 在当前日期为 2026 年时应展开为 `20260603` 到 `20260609`。
- 某些 SQL 除 `event_day between ...` 外还有 `t3.event_day='旧结束日'` 这类单日维表分区，需要按语义同步成新区间结束日。
- 第一次粘贴后校验注释头失败，但实际 SQL 已粘贴成功并滚到末尾；任务卡片能看到注释头时可判定提交内容正确。
- 批量新建草稿后，固定 `textarea.inputarea.nth(0)` 会点到隐藏元素；改成查找可见 textarea 后稳定提交。
- 提交成功后新任务可能立即显示为 `排队中`，不代表失败；应回收任务 ID 并告知队列状态。
- MCP 路径拿到 `task_id` 后，即使后续状态接口临时失败，也不应自动改用 Chrome 再提交；应把已有任务 ID 作为唯一跟进锚点。
