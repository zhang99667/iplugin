---
name: datapilot-sql-runner
version: 0.1.4
tags: [datapilot, sql, mcp, result, download, pivot-table, chrome, data, baidu, analytics]
description: DataPilot SQL 跑数结果闭环助手。当用户要求在百度 DataPilot/datapilot 上提交 SQL、批量运行本地 .sql/.SQL 文件、查询任务状态、等待下载结果、下载结果文件，或跑完后直接生成商业 AB 实验透视表时触发；默认使用 DataPilot MCP 完成提交 SQL、查状态、判断可下载和下载结果，并在结果字段匹配时联动 nad-acx-pivot-table 产出 xlsx。只有 MCP 不可用、权限不可恢复、能力不覆盖页面专属设置或用户明确要求浏览器操作时，才读取 references/chrome_fallback.md 回退 Chrome。
user_invocable: true
---

# DataPilot SQL Runner

目标：把“准备 SQL -> MCP 提交 -> 心跳等待 -> 下载结果 -> 可选生成透视表”做成默认闭环。这个 skill 的主定位不是页面代操，而是通过 DataPilot MCP 直接拿到可交付结果；Chrome 只保留为兜底经验，按需读取 [references/chrome_fallback.md](references/chrome_fallback.md)。

## 触发边界

### 适用

- 用户要求在 `https://datapilot.baidu-int.com/dataAnalysis` 跑 SQL。
- 用户给出一个目录、多份 `.sql` / `.SQL` 文件，要求批量提交、等待或下载结果。
- 用户要替换 SQL 日期、实验号、实验组/对照组后再提交。
- 用户需要拿到 DataPilot 任务 ID、排队状态、执行状态、失败信息、下载链接或本地结果文件。
- 用户说“跑完直接出结果”“等下载结果”“跑完生成透视表”“DataPilot 结果转商业 AB 透视表”。

### 不适用

- 只解释、编写或优化 SQL 文本：使用对应 SQL 写作能力或直接回答。
- 只替换实验号和日期但不提交 DataPilot：使用 `sql-exp-replace`。
- 只对已有 CSV/TXT/XLSX 生成商业 AB 透视表，不需要跑 DataPilot：使用 `nad-acx-pivot-table`。

## 输入收集

从用户消息和上下文提取：

- SQL 来源：目录、文件列表、单个文件、附件，或用户直接贴的 SQL。
- 日期范围：例如 `6.3-6.9`。年份不明确时结合当前日期；仍不明确再确认。内部广告 SQL 通常使用 `YYYYMMDD`。
- 实验号：基础号如 `161703`，并保留 `-0` / `-dz` 后缀语义。
- 交付目标：默认提交并回收任务 ID；如果用户说“等结果/下载结果/出结果/生成透视表”，就进入等待下载和结果产出流程。
- 输出目录和实验名：生成透视表时优先使用用户给出的实验名；未给出时从 SQL 文件名、实验号和日期范围推断一个可读名称。
- 失败重试策略：沿同一逻辑 SQL、同一数据日期的 `retry_of` 链统计明确的 `FAILED` / `OVERTIME`；第二次明确失败后，下一次重试必须切换到 DataPilot 的 `PRO引擎`。

## SQL 预处理

1. 用 `rg --files` 列出目录下 SQL 文件；用户给出顺序时保留，否则按文件名稳定排序。
2. 需要替换实验号或日期时，优先触发并使用 `sql-exp-replace`：
   - 先扫描候选 SQL，识别实验号基础号和 `event_day` / `dt` / `log_date` 等日期字段。
   - 只替换确认需要替换的实验号和日期字段。
   - 基础实验号映射如 `160706=161703` 应同步覆盖 `160706-0` 和 `160706-dz`。
3. 不直接修改原始 SQL 文件。把提交版写到 `/private/tmp/datapilot_sql_run_<标识>/` 或类似临时目录。
4. 提交前做残留检查：旧实验号、旧日期不应留在提交版的目标位置；新实验号、新日期应出现在预期位置。发现多个旧实验号、多个日期语义或映射不清时先问用户。

## MCP 主流程

先检查当前环境是否暴露 DataPilot MCP 工具，例如 `mcp__datapilot` namespace 下的提交、查询、下载判断、下载或导出工具。工具列表不可见时，先用可用工具发现能力搜索 DataPilot SQL MCP；完成检查前不要打开 Chrome 页面跑数。

标准流程：

1. 为每条 SQL 生成可识别的 `task_name`，优先包含文件名、日期范围和实验号。
2. 调用 MCP 提交 SQL，记录 `task_id`、`task_type`、初始状态和执行路径 `MCP`。
3. 只要提交接口返回 `task_id`，就把它作为唯一跟进锚点；后续查询或下载失败时不要重新提交同一 SQL。
4. 调用 MCP 状态查询工具跟进任务，把 `WAITING`、`RUNNING`、`SUCCESS`、`FAILED`、`OVERTIME` 映射为 `排队中`、`运行中`、`成功`、`失败`、`超时`。
5. 用户只要求提交时，提交后立即汇报任务 ID、状态、临时 SQL 目录和替换摘要。
6. 用户要求结果时，进入心跳等待，直到任务成功且下载判断通过。

## 心跳等待下载

用于用户要求“等结果/下载结果/出结果/生成透视表”的场景。

- 默认心跳间隔为 3 分钟；用户指定间隔时按用户要求执行。
- 每轮先查任务状态；任务未终态时继续等待，终态失败/超时则停止并汇报错误片段。
- 任务成功后调用 MCP 下载判断工具。返回 `need_cycle` 或结果仍在准备时继续心跳；返回可下载时立刻调用 MCP 下载工具。
- 下载到本地后记录 `{文件名, taskId, taskType, resultPath, 执行路径: MCP}`。
- 状态变化时简短汇报，例如 `87053789：运行中 -> 成功`；状态未变时避免频繁刷屏。
- 没有用户明确要求长时间等待时，最多心跳 10 次或 30 分钟；到达上限后交付任务 ID 和当前状态，说明仍可继续等待或稍后再查。

## 结果产出

下载完成后按交付目标处理：

1. 普通结果：提供本地结果文件路径、任务 ID、最终状态和下载路径。
2. 商业 AB 透视表：如果用户要求透视表，或下载文件字段包含 `exp_id`、`event_day`、`eshow`、`click`、`charge`、`tcharge`、`conv` 及其常见别名，就触发并使用 `nad-acx-pivot-table`。
3. 透视表输入可以是单个下载文件，也可以是多个 SQL 任务下载出的 CSV/TXT/XLSX 合并结果。
4. 透视表输出使用 `nad-acx-pivot-table` 的 `commercial_ab_test` 预设；实验名优先取用户输入，其次取 SQL 文件名、实验号和日期范围。
5. 交付时同时列出 DataPilot 任务、下载文件和生成的 xlsx 文件，让用户能追溯从 SQL 到结果的完整链路。

## Chrome 回退

只有以下情况才读取并使用 [references/chrome_fallback.md](references/chrome_fallback.md)：

- MCP 不可用、认证失败或权限问题不可恢复。
- MCP 没有覆盖用户指定的页面控件、运行队列、引擎或资源组。
- 用户明确要求沿用浏览器页面操作。
- MCP 已返回 `task_id`，但查询/下载接口不可用，需要通过运行中心按任务 ID 辅助定位状态。

回退时仍要遵守重复提交保护：已经拿到 `task_id` 的 SQL 不得因为状态查询失败而再次提交。

## 失败重试与 PRO 引擎

按逻辑 SQL 和数据日期维护失败链路：从项目 `runs.jsonl` 沿 `retry_of` 统计明确的 `FAILED` / `OVERTIME` 终态。第二次明确失败后，从下一次重试开始改用 Chrome 插件选择 PRO 引擎；`UNKNOWN`、HTTP 500 或接口暂时不可用不计入失败次数，也不能因此重复提交。

1. 打开或接管原有 DataPilot 标签页，确认目标 SQL 和单日日期仍正确。
2. 在编辑器底部的运行按钮区域，点击主 `run` 按钮右侧的下拉箭头，打开引擎菜单。
3. 选择 `PRO引擎`，确认运行区域已切换到 PRO 模式后，再点击主 `run` 按钮提交。
4. 用“触发 PRO 任务”提示、PRO 任务卡片或 `task_type=PRO` 核对提交类型；如果没有产生新任务 ID，先检查引擎选择，不要重复点击提交。
5. 将实际提交的 SQL 保存为项目 `sql/` 下的新版本，并在 `runs.jsonl` 记录 `task_type=PRO`、`execution_path=WEB`、`retry_of` 和新任务 ID；后续继续按新 task ID 查询和下载。

如果页面没有 PRO 选项、Chrome 插件未连接或需要重新登录，说明阻塞原因并停止，不要静默切回智能引擎。

## 汇报格式

提交后：

```text
已提交到 DataPilot：
- 智能体展点消.sql: 86299031，TASK，排队中，MCP
```

结果完成后：

```text
DataPilot 结果已完成：
- 智能体展点消.sql: 86299031，TASK，成功
  下载结果：/private/tmp/datapilot_results/86299031.csv
  透视表：/private/tmp/datapilot_results/【0603-0609】智能体展点消.xlsx
```

同时说明：

- 提交前做了哪些替换，例如 `日期 20260603-20260609，实验号 161703`。
- 原始 SQL 是否未改动，以及临时提交版 SQL 目录。
- 如果没有生成透视表，说明原因：用户未要求、字段不匹配，或下载结果不是商业 AB 实验数据结构。
- 如果有失败/超时，给出失败任务 ID、错误片段和下一步建议。
