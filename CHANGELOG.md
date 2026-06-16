## [0.18.0] - 2026-06-16
### Added
- nad-acx-pivot-table: 新增商业 AB 实验数据透视表 skill，用于从 CSV/TXT/XLSX 生成 Excel 原生透视表，支持多文件合并、字段别名映射、相对差指标和自动命名
- nad-acx-pivot-table: 随 skill 引入零外部依赖的 `pivot_tool` 脚本、`commercial_ab_test` 预设、配置 schema 与 OOXML 注意事项 references

### Changed
- README / manifest: 插件能力清单加入商业 AB 透视表生成，版本升级到 `0.18.0`

## [0.17.4] - 2026-06-16
### Changed
- html-report: `highlight_code.py --lang diff --diff-view` 会根据 `---` / `+++` 文件路径后缀推断语言，并复用普通代码高亮逻辑给 diff 代码列生成 `tok-*` token
- html-report: CSS 模板补充 diff viewer 专用 token 配色，避免浅色新增/删除背景下语法高亮对比度不足
- html-report: 校验脚本新增 diff viewer token CSS 检查，避免 diff 代码列有 `tok-*` span 但页面缺少对应样式
- manifest: 插件版本升级到 `0.17.4`

## [0.17.3] - 2026-06-15
### Changed
- html-report: 强化 Markdown 行内代码渲染规则，要求 `` `d` ``、`` `support_full_screen` `` 等短标识输出为 `<code>...</code>`，并由校验脚本拒绝正文中残留的原始反引号代码
- html-report: 校验脚本新增 token CSS 检查，避免代码块里有 `tok-*` span 但页面缺少 `.tok-*` 样式时仍通过
- html-report: 真实 unified diff 统一要求使用 `highlight_code.py --lang diff --diff-view` 生成 `.diff-card.diff-viewer`，并由校验脚本拒绝普通 `language-diff` 代码块和手写 diff card，稳定变更展示样式
- manifest: 插件版本升级到 `0.17.3`

## [0.17.2] - 2026-06-15
### Removed
- commands: 删除与 skills 重复的 command 文件（htmlreport、ask-user-question、best-of-web），避免被 harness 重复注册为 skill 条目
- manifest: 插件版本升级到 `0.17.2`

## [0.17.1] - 2026-06-15
### Changed
- obsidian: 将 Markdown 表格前后必要空行列为紧凑排版规则的明确例外，避免表格紧跟引导句时在 Obsidian/GFM 中无法正常渲染
- manifest: 插件版本升级到 `0.17.1`

## [0.17.0] - 2026-06-10
### Added
- datapilot-sql-runner: 新增 DataPilot SQL 跑数闭环 skill，用于提交单条或多条 SQL、处理 Chrome 登录态和 Monaco 编辑器粘贴、回收任务 ID 并汇报排队/执行状态
- datapilot-sql-runner: 沉淀 DataPilot 实操经验，包括临时 SQL 副本、不污染原始文件、SQL 实验号/日期预处理、任务卡片状态边界解析和长 SQL 粘贴校验

### Changed
- README / manifest: 插件能力清单加入 DataPilot SQL 跑数，版本升级到 `0.17.0`

## [0.14.3] - 2026-06-07
### Fixed
- hooks/codex-hooks.json: 恢复 Codex telemetry 的稳定 wrapper 入口 `$HOME/.codex/hooks/iplugin-skill-telemetry.py`，避免 session 继续引用已删除的版本化 `${PLUGIN_ROOT}` 缓存路径
- validate-plugin.py / docs: 校验和文档同步 Codex wrapper 契约，防止后续变更再次回退到 `${PLUGIN_ROOT}/hooks/skill-telemetry.py`
- manifest: 插件版本升级到 `0.14.3`

## [0.14.2] - 2026-06-07
### Changed
- obsidian: 新增示意图表达策略，要求在 Mermaid、ASCII、SVG/矢量图和图像生成之间按清晰度选择，不再默认用 ASCII 表达复杂链路
- README / manifest: 插件版本升级到 `0.14.2`

## [0.14.1] - 2026-06-07
### Changed
- delegated-search: 扩展为执行前委派判断能力，在高输出命令、长日志、全仓扫描和跨源检索前优先判断是否拆给 explorer/subagent
- delegated-search: 增加主 Agent 委派判断模板，要求明确是否委派、拆分问题、子 Agent 边界和期望输出
- README / manifest: 插件版本升级到 `0.14.1`

## [0.14.0] - 2026-06-07
### Added
- obsidian: 从外部个人 skills 目录迁入 Obsidian 笔记写作 skill，统一管理 Vault 路径、紧凑排版、标题层级、引用块、代码块和双向链接规范
- README / manifest: 插件能力清单加入 Obsidian 笔记写作，版本升级到 `0.14.0`

## [0.13.7] - 2026-06-07
### Changed
- html-report: 精简重复声明，主 skill 只保留触发、路由和输出契约，代码高亮、目录和响应式细节继续下沉到 references
- html-report: 移除 CDN 图表库例外，统一要求单文件离线 HTML，图表优先使用表格、内联 SVG 或生成期静态内容
- README / manifest: 插件版本升级到 `0.13.7`

## [0.13.6] - 2026-06-06
### Changed
- html-report: 长文档目录恢复旧版浮动侧栏视觉，不再使用 `<details>` 折叠目录内部链接
- html-report: 目录新增 `.toc-toggle` 和 `.toc-collapsed`，支持整体收起/展开侧栏，并同步更新生成后校验
- README / manifest: 插件版本升级到 `0.13.6`

## [0.13.5] - 2026-06-06
### Changed
- mgit: 执行 MGIT 只读诊断前增加 Ruby/gem 启动依赖预检，覆盖 `colored2`、`peach`、`tty-pager` 和 `logger`
- mgit: 区分 gem 缺失与 rbenv 临时文件写入受限，避免把 MGIT 启动失败误判为工作区问题
- mgit: EasyBox 规则补充完整 iCode 仓库名反推配置层级、无仓库输入不默认开启广告仓库、非目标 `syncSource` 默认保留和壳工程主分支映射
- README / manifest: 插件版本升级到 `0.13.5`

## [0.13.4] - 2026-06-06
### Changed
- html-report: 明确 Pygments 是可选增强依赖，生成报告时不自动安装；仅在用户明确要求时安装，缺失时继续回退 builtin
- html-report: `highlight_code.py` 支持 Pygments 模块和 `pygmentize` CLI 两种本地预渲染形态
- README / manifest: 插件版本升级到 `0.13.4`

## [0.13.3] - 2026-06-06
### Changed
- html-report: 强化 HTML 生成稳定性，要求代码块覆盖 SQL/JSON/YAML/Bash 等常见片段并通过静态高亮脚本输出
- html-report: `highlight_code.py` 新增 `--engine auto/pygments`，可在本机 Pygments 可用时进行增强静态预渲染，最终 HTML 仍不加载外部高亮库
- html-report: 长文档目录改为默认展开、可点击折叠的原生 `<details>` 结构
- html-report: 校验脚本新增 viewport、响应式/打印样式、复制按钮和可折叠目录结构检查，降低窄屏/分屏显示不全风险
- README / manifest: 插件版本升级到 `0.13.3`

## [0.13.2] - 2026-06-06
### Changed
- best-of-web: 收窄触发边界，仅允许通过 `/best-of-web` slash command 显式触发，避免普通自然语言联网请求误触发
- commands/best-of-web: 改为“命令即 skill 激活入口”的表述，避免模型只读取或总结 `SKILL.md` 而不执行联网精选流程
- README / manifest: 插件版本升级到 `0.13.2`

## [0.13.1] - 2026-06-06
### Changed
- best-of-web: 强化联网精选流程，补充研究强度、查询设计、来源分层、证据标准和冲突处理
- best-of-web: 增加公开网页 prompt-injection 防护与公开/私有资料分阶段处理边界
- README / manifest: 插件版本升级到 `0.13.1`

## [0.13.0] - 2026-06-05
### Added
- aidisheng-xueba: 新增爱迪生学霸答题 skill，用于按题干和选项语义快速回答爱迪生考试单选/多选题
- aidisheng-xueba: 新增题库 reference，收录灰度实验、D 平台、eid、pv 不平、实验切走、资源评估、参数同步等高频题
- aidisheng-xueba: 新增题库自我更新流程，用户给出未见过题目或标准答案后直接沉淀到基础题库

### Changed
- README / manifest: 插件能力清单加入爱迪生答题题库，版本升级到 `0.13.0`

## [0.12.2] - 2026-06-05
### Changed
- ask-user-question: 放宽触发描述，覆盖仓库/流程规则要求询问、提交前确认、风险操作确认和阻塞性方案选择
- ask-user-question: 更新 command 与 README 文案，弱化“只能手动调用”的误导，保留轻微不确定性不主动打断的边界
- manifest: 补充 confirmation/choice/risky-action 等触发关键词

## [0.12.1] - 2026-06-05
### Added
- mgit: 新增 EasyBox/xbuild `overlay` / `local` 上车配置参考，覆盖 `syncSource`、开发分支上车、master 合入和 overlay 不能带上的判断流程
- mgit: 补充仓库、EasyBox 模块路径、`xbuild/modules/default` 基础配置文件和 overlay/local 目标文件的映射规则

### Changed
- mgit: 触发边界扩展到 EasyBox modules 配置、源码模式和多仓模块范围判断
- README / manifest: 插件版本升级到 `0.12.1`

## [0.12.0] - 2026-06-04
### Added
- commercial-sql-writer: 新增商业广告 SQL 写作 skill，用于编写、改写和检查商业/NAD 广告分析 SQL
- commercial-sql-writer: 新增表与字段指南、指标口径、查询模板、场景路由和输出前自查 5 份 reference
- commercial-sql-writer: 根据 KU 文档补充 `nativeads_feed_asp_view` 使用要点、计费单位和 CPM 曝光对账排查经验
- commercial-sql-writer: 补充商业大盘展点消转母版优先原则，要求覆盖/命中部分优先在母版 `t1` 上内联并复用原 `t2` 转化目标成本逻辑
- commercial-sql-writer: 补充高频 `cmatch` 与 `event_type` 绑定，特别是 719 默认 `event_type = 'browser'`

### Changed
- manifest / README: 插件能力清单加入商业 SQL 写作，版本升级到 `0.12.0`
- html-report: 强化代码块高亮为离线单文件静态预高亮，包含代码、SQL、XML、JSON、配置或 diff 时必须使用 `highlight_code.py`
- html-report: 增加生成后检查，避免报告中遗留未高亮的裸 `<pre>` / `<code>` 代码块
- html-report: 调整代码块 CSS token 配色为接近 IDE 的深绿色主题，保持单文件离线输出
- html-report: 新增 `scripts/check_html_report.py`，将外部依赖、裸代码块和缺失高亮 token 的检查脚本化，并收敛重复文案

## [0.11.3] - 2026-06-04
### Changed
- html-report: 优化触发边界，支持显式 HTML 请求、复杂交付物自动判断和其他 skill 调用，同时保留普通短总结默认 Markdown
- manifest: 插件版本升级到 `0.11.3`

## [0.11.2] - 2026-06-03
### Added
- html-report: 新增 `scripts/highlight_code.py`，用标准库生成已转义、基础高亮、可复制的 HTML 代码块
- html-report: `highlight_code.py` 新增 `--diff-view`，可把 unified diff 渲染成带 old/new 行号、红绿背景和左侧变更轨道的修改点视图
- html-report: `artifact-patterns.md` 新增“问题排查/修复方案”模板，覆盖现象、影响、根因、证据、修复、验证和回归

### Changed
- html-report: 代码高亮规范改为优先使用脚本生成，脚本不可用时才手工高亮确定 token，降低 HTML 转义和 `tok-*` span 出错风险
- manifest: 插件版本升级到 `0.11.2`

## [0.11.1] - 2026-06-02
### Added
- html-report: 新增 `references/artifact-patterns.md`，先沉淀技术方案和技术调研两个高频 HTML 报告结构模板

### Changed
- html-report: 增加 HTML 价值信号，明确复杂对比、diff、架构图、时间线、长报告和交付物场景更适合 HTML
- html-report: 强化正式报告的首屏 TL;DR、证据来源区和生成后 Review/Improve 自查要求
- html-report: 补充响应式、打印友好、可访问性和语义 HTML 底线
- manifest: 插件版本升级到 `0.11.1`

## [0.11.0] - 2026-06-02
### Added
- html2md: 新增 HTML 转 Markdown skill，支持本地 `.html`、`file://` URL 和粘贴 HTML 内容，默认输出同名 `.md`
- html2md: 新增 bundled script `skills/html2md/scripts/html2md.py`，使用 Python 标准库保留标题、列表、表格、代码块、链接和 diff 表格

### Changed
- manifest / README: 插件能力清单加入 HTML 转 Markdown，版本升级到 `0.11.0`

## [0.10.2] - 2026-05-31
### Added
- hooks/codex-hooks.json: 新增 Codex 专用 hook 配置，继续使用 `${PLUGIN_ROOT}` 和脚本内过滤

### Changed
- hooks/hooks.json: 改为 Claude Code 默认扫描专用配置，使用 `${CLAUDE_PLUGIN_ROOT}` 和 `matcher: "Skill"`，避免 Claude Code 将 `${PLUGIN_ROOT}` 展开为空导致 `/hooks/skill-telemetry.py` 路径错误
- manifest: 插件版本升级到 `0.10.2`，Codex manifest 改为指向 `hooks/codex-hooks.json`
- validate-plugin.py: hook 配置校验覆盖 Claude 默认 hooks 与 Codex manifest hooks 两条路径
- README / 维护指南: 明确 Claude Code 与 Codex hook 变量名和配置文件分离

## [0.10.1] - 2026-05-31
### Added
- hooks/hooks.json: 新增 Codex 插件内置 PostToolUse hook 配置，启用插件后可通过 `/hooks` trust 并运行 telemetry

### Changed
- hooks/skill-telemetry.py: 兼容 Claude Code `Skill` tool 事件与 Codex hook 事件，Codex 侧从 `skills/<name>/SKILL.md` 访问痕迹提取 skill 名称并写入 `~/.codex/skill-usage.jsonl`
- manifest: 插件版本升级到 `0.10.1`，Codex manifest 显式声明 `hooks/hooks.json`
- validate-plugin.py: 新增 Codex hooks 配置校验，检查 manifest hooks 路径和 hooks JSON 结构
- README / 维护指南: 补充 Codex hook 刷新、trust、日志路径和双端验证说明

## [0.10.0] - 2026-05-31
### Added
- hooks/skill-telemetry.py: 新增 PostToolUse hook 脚本，监听 Skill 调用并写入 ~/.claude/skill-usage.jsonl，完全离线，支持 `jq` 统计各 skill 使用频次

### Changed
- delegated-search: 不适用补充互斥说明，明确互联网搜索请用 best-of-web
- best-of-web: 不适用互斥说明更精准，明确本地多源检索/子 agent 请用 delegated-search
- icafe-delivery-archive: 修复 5 处 /Users/markz/ 硬编码路径为 Path.home()，依赖说明补注百度内网限制
- session-rename: 修复 2 处硬编码路径，description 补注"仅适用 Claude Code 环境"，主文件 236→65 行
- lite-diff-marker: Progressive Disclosure 拆分，主文件 291→90 行，规则细节移入 references/marking-rules.md
- project-summary: Progressive Disclosure 拆分，主文件 291→64 行，写作规范移入 references/writing-guide.md
- validate-plugin.py: 新增 CLAUDE.md/AGENTS.md 哈希同步校验和 SKILL.md 硬编码路径检测，校验项从 7 增至 9

## [0.9.0] - 2026-05-31
### Added
- best-of-web: 新增联网精选 skill，用于让模型根据语境主动触发“结合互联网上最优秀内容”的搜索与综合能力
- commands: 新增 `/best-of-web` slash command，作为手动强制触发 `best-of-web` skill 的入口
- README: 补充 `best-of-web` skill 与 `/best-of-web` 命令说明，并在插件能力描述中加入联网精选

## [0.8.10] - 2026-05-29
### Changed
- html-report: 强化源码定位 chip 规则，行号范围必须合并到同一个可跳转链接中，不再另起独立行号 badge
- html-report: 从 CSS 模板移除 `.line` 示例样式，避免生成不可跳转的路径/行号分离展示
- html-report: 明确源码定位由 HTML 结构驱动，CSS 只负责视觉样式

## [0.8.9] - 2026-05-29
### Changed
- html-report: 增加代码变更标识规范，要求新增、删除、修改和上下文行在报告中可视区分
- html-report: CSS 模板补充 diff card、change chip、行级 `+/-/~` 和 `<ins>/<del>` 行内变化样式
- html-report: 修正文件定位模板，要求路径和行号范围合并为一个可跳转 IDEA chip，避免拆成不可点击的路径/行号两段

## [0.8.8] - 2026-05-29
### Changed
- karpathy-guidelines: 放宽触发边界，在实际写代码、修 bug、重构、code review 或实现方案落地时自动作为工程约束使用，不再要求用户必须点名 Karpathy

## [0.8.7] - 2026-05-29
### Changed
- mgit: 放宽触发边界，允许模型在多仓库工程上下文中主动使用只读 MGIT 诊断，不再要求用户必须点名 mgit
- mgit: 明确写入、同步、推送、清理、reset 和跨仓自定义命令仍需先确认影响范围
- README: 更新 mgit 触发示例，强调多仓任务意图而非手动命令名

## [0.8.6] - 2026-05-29
### Added
- scripts: 新增 `scripts/text_replace.py` 通用替换引擎，支持 literal/token/regex 替换计划、计数和 0 命中失败
- sql-exp-replace: 新增 `scripts/sql_exp_replace.py`，作为 SQL 领域 wrapper 扫描候选字段并调用通用替换引擎
### Changed
- sql-exp-replace: 升级为“模型判断语义 + 脚本执行替换”的混合流程，字段名不再固定为 `event_day`
- scripts: token 替换改为同轮匹配，支持实验号互换映射，并收紧连字符边界与按字段计数
- README: 标注 SQL 实验替换使用确定性脚本

## [0.8.5] - 2026-05-29
### Changed
- html-report: 将内容规则、视觉规则和 CSS 模板拆成 references，SKILL.md 只保留触发边界、导航和最短执行流程
- mgit: 将命令手册、配置与中间态处理拆成 references，SKILL.md 只保留触发边界、安全底线和命令路由
- 开发准则：补充 `skills/<name>/references/` 目录约定，要求长规则和长示例优先按需披露

## [0.8.4] - 2026-05-29
### Changed
- skills: 为所有 skill 补充“适用 / 不适用 / 需要确认”触发边界，减少轻量问答误触发
- code-reading: 进一步收窄触发条件，避免“这个方法在哪里调用”等局部代码问题升级为深度导读
- README: 更新 code-reading 触发示例，强调完整执行链路场景

## [0.8.3] - 2026-05-29
### Added
- html-report: 新增 `/htmlreport` slash command，补齐 README 和 skill 中已声明的 HTML 报告命令入口
- scripts: 新增 `scripts/validate-plugin.py`，将 manifest、skills、README、CHANGELOG、versions 和 command 引用一致性纳入提交前校验
### Changed
- 开发准则：提交前检查增加 `python3 scripts/validate-plugin.py`
- manifest: 补齐所有 skill 名称和拆分关键词，提升能力清单一致性

## [0.8.2] - 2026-05-28
### Changed
- code-reading: 收紧触发边界，仅在明确需要深度代码导读、完整链路或 HTML 报告时触发，避免轻量代码问答误用该 skill
- code-reading: 强化执行链路输出结构，补充数据来源、对象创建、触发入口、动态分发、状态变化和流程图要求

## [0.8.1] - 2026-05-28
### Changed
- ask-user-question: 仅保留 `/ask-user-question` 一个 slash command 入口，删除 `/askuserquestion` 别名，避免命令列表重复

## [0.8.0] - 2026-05-28
### Added
- ask-user-question: 新增手动调用的结构化询问助手和 `/askuserquestion`、`/ask-user-question` 命令，用于把 UI 方案、实现分支、风险操作等不确定点交给 AskUserQuestion / request_user_input
### Changed
- 开发准则：完成文件改动并校验后，通过 `/ask-user-question` 询问用户是否提交本次改动，确认前不主动执行 `git commit`
- 开发准则：明确 `CLAUDE.md` 与 `AGENTS.md` 为同源维护指南，修改时必须同步

## [0.7.0] - 2026-05-28
### Added
- delegated-search: 新增通用广域检索委派助手，用于在代码、文档、日志、配置、网页资料等发散搜索任务中优先拆给 explorer/subagent 收集证据，主线程负责验证、整合和交付

## [0.6.1] - 2026-05-26
### Changed
- html-report: 文件位置统一按 `{path}:{line}` / `{path}:{line}:{column}` 展示，并在有绝对路径时生成 `idea://open` 跳转链接

## [0.6.0] - 2026-05-26
### Added
- karpathy-guidelines: 翻译引入上游 Karpathy 风格编码准则，用于写代码、重构、修 Bug 和 code review 时避免过度复杂化、保持外科手术式改动并定义可验证成功标准

## [0.5.0] - 2026-05-26
### Added
- lite-diff-marker: 矩阵产品差异化标记助手，按 Android Java/Kotlin、XML 和脚本配置的新增、修改、删除场景补齐 @LiteAdd/@LiteModified/@LiteDelete/@BaseSplit 等标记

## [0.4.2] - 2026-05-22
### Changed
- html-report: 生成 HTML 前先判断正式技术/业务文档、分析报告或普通对话转 HTML；正式文档增加包含文档类型、仓库、任务、负责人、日期等信息的抬头

## [0.4.1] - 2026-05-21
### Changed
- icafe-delivery-archive: 归档时检查目标目录是否已有总结；没有总结时调用 project-summary 生成总结文档

## [0.4.0] - 2026-05-21
### Added
- icafe-delivery-archive: iCafe 需求交付材料归档助手，根据详设文件或卡片号查询需求描述并整理到桌面“需求交付”目录

## [0.3.1] - 2026-05-20
### Changed
- html-report: 长文档生成 HTML 时加入左侧目录导航，支持快速切换章节
- html-report: 强化代码块语法高亮要求，避免生成纯色纯文本代码块
- promotion-project-polish: 调整为更通用的 project-summary，用于项目、需求、Bug 修复或阶段性工作的总结沉淀

## [0.3.0] - 2026-05-20
### Added
- session-rename: Claude Code 会话自动命名助手，推荐通过 UserPromptSubmit hook 返回 sessionTitle 自动生成可检索标题

## [0.2.0] - 2026-04-19
### Added
- mgit: 百度 MGIT 多仓库管理工具助手，覆盖状态诊断、同步、分支、批量提交/推送和中间态处理

## [0.1.0] - 2026-04-17
### Added
- code-reading: 代码阅读与执行链路追踪
- html-report: HTML 报告生成
- sql-exp-replace: SQL 实验号与日期批量替换
