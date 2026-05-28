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
