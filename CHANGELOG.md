## [0.22.39] - 2026-08-10
### Fixed
- nad-acx-pivot-table: `styles.xml` 补齐 Excel 内建 Normal 命名样式、差异样式和默认表格/透视样式声明，避免 Mac Excel 打开时修复工作簿样式
- nad-acx-pivot-table: OOXML 闸门新增 styles 关系、Content Type、集合计数、样式索引边界和子元素顺序校验

### Changed
- nad-acx-pivot-table: 增加样式损坏故障注入测试，skill 从 `0.1.6` 升级到 `0.1.7`，插件从 `0.22.38` 升级到 `0.22.39`

## [0.22.38] - 2026-08-10
### Changed
- nad-acx-pivot-table: 多业务合并与单透视生成统一字段别名和计算字段冲突处理，补充 `clk` / `asp_charge` 常见别名
- nad-acx-pivot-table: `merge_pivots` 支持可选隐藏明细 sheet，并改为同目录临时写入、全量多透视 OOXML 校验通过后原子替换目标文件
- nad-acx-pivot-table: skill 从 `0.1.5` 升级到 `0.1.6`，插件从 `0.22.37` 升级到 `0.22.38`

## [0.22.37] - 2026-08-10
### Changed
- html-report: 代码块右上角让语言标签与复制按钮共用同一槽位，默认显示语言，悬停或键盘聚焦时切换为复制，触摸设备默认保留复制入口
- html-report: 同步更新 code-block CSS 门禁、组件测试、Gallery、视觉契约和版本记录，skill 从 `0.7.15` 升级到 `0.7.16`，插件升级到 `0.22.37`

## [0.22.36] - 2026-08-07
### Changed
- html-report: 源码定位链接改为按技术方案平台统一选择 IDE，Android 方案内所有文件使用 IDEA，iOS 方案内所有文件使用 Xcode，不再按源码语言或扩展名切换
- html-report: Review Workspace 使用通用 `ideKind` / `ideLabel` / `ideHref` 数据，工具栏按当前文件动态显示 IDEA 或 Xcode；输入继续兼容旧 `idea_line`，新版 runtime 与校验器继续读取历史 `ideaHref`
- html-report: 校验器逐文件核对 IDE 协议、绝对路径、起始行和定位元数据，组件测试与 Gallery 同步覆盖跨语言平台默认、`idea://open` 和 `xcode://open`；skill 从 `0.7.14` 升级到 `0.7.15`，插件升级到 `0.22.36`

## [0.22.35] - 2026-08-06
### Added
- html-report: 默认 `interactions` 组件新增右下角回到顶部按钮，滚动超过 360px 后显示，支持键盘焦点、移动端安全区和减少动态效果

### Changed
- html-report: 批注侧栏桌面展开时回顶按钮自动避让，移动端侧栏展开时隐藏；打印版不输出按钮
- html-report: runtime 可复用导出 HTML 中已有的动态按钮并重新绑定事件，避免批注版或发布版重新打开后按钮失效
- html-report: 同步更新组件注册表、Gallery、组件测试、插件门禁和交互契约，skill 从 `0.7.13` 升级到 `0.7.14`，插件升级到 `0.22.35`

## [0.22.34] - 2026-08-05
### Fixed
- html-report: 修复 `--no-copy` 代码块被校验器误报缺少复制按钮的问题，使用显式 `data-copy="false"` 保留无复制输出契约
- html-report: 旧工具栏初始化时统一把语言标签放到最右侧，打印和窄屏场景补充对比度、收缩与不换行保护
- html-report: 同步更新运行时顺序校正、结构门禁、组件测试、Gallery 和版本记录，skill 从 `0.7.12` 升级到 `0.7.13`，插件升级到 `0.22.34`

## [0.22.33] - 2026-08-05
### Changed
- html-report: 代码块右上角显示规范化语言标签，复制按钮改为默认隐藏并在悬停、键盘聚焦时显示，触摸设备保留可操作状态
- html-report: 运行时兼容旧 `.code-wrap`，自动补齐工具栏和语言标签；同步更新校验器、组件测试、Gallery、视觉契约和版本记录
- html-report: skill 从 `0.7.11` 升级到 `0.7.12`，插件升级到 `0.22.33`

## [0.22.32] - 2026-08-04
### Changed
- html-report: 保存批注版的文件选择和下载兜底统一沿用当前 HTML 原始文件名，不再自动追加 `_reviewed` 或 `_copy`
- html-report: 发布版继续使用 `_public` 后缀，保持内部批注交接文件与公开交付物语义分离
- html-report: 组件门禁、Gallery 和批注契约同步更新，skill 从 `0.7.10` 升级到 `0.7.11`，插件升级到 `0.22.32`

## [0.22.31] - 2026-08-04
### Fixed
- html-report: 零批注时复制主按钮保留禁用视觉与语义，但点击会明确提示先添加问题或评论，不再表现为完全无响应
- html-report: 批注提示可自动复用或创建稳定 toast，避免报告未预置 `#toast` 时静默吞掉复制、定位和校验反馈
- html-report: `file://` 报告移动或重命名后优先使用当前实际路径生成 Agent 交接包，避免继续回写旧临时副本
- html-report: 运行时测试、组件门禁和批注契约同步更新，skill 从 `0.7.9` 升级到 `0.7.10`，插件升级到 `0.22.31`

## [0.22.30] - 2026-08-04
### Changed
- html-report: 选区气泡恢复“问题 / 评论”两个直接入口，右键菜单在选中内容、本段和本节三个范围下同步支持两类
- html-report: 旧 `提问` 映射为问题，旧 `注释 / 批注` 映射为评论；新建、编辑、卡片徽标和 Agent 交接包保留类型语义，但侧栏不恢复类型筛选
- html-report: 校验器、运行时测试、组件 Gallery、eval 与交互契约同步更新，skill 从 `0.7.8` 升级到 `0.7.9`，插件升级到 `0.22.30`

## [0.22.29] - 2026-08-04
### Changed
- html-report: 批注卡片基础字号和批注正文从偏大的继承值收敛到 12px，提升侧栏长列表的扫描密度
- html-report: 移除重复的复制/下载 Markdown 按钮和“更多操作”折叠层；保存批注版与导出发布版并排展示，清空本轮改为直接可见的危险操作
- html-report: 校验器、组件回归、Gallery、eval 与交互契约同步更新，skill 从 `0.7.7` 升级到 `0.7.8`，插件升级到 `0.22.29`

## [0.22.28] - 2026-08-04
### Added
- nad-acx-pivot-table: 新增 `merge_pivots` 多业务合并能力，同一实验号多个业务方可合并为一个多 sheet 原生透视表工作簿
- nad-acx-pivot-table: 多业务工作簿支持空数据业务占位，0 行 CSV 不再生成可能触发 Excel 修复提示的空 pivotTable/cache

### Fixed
- nad-acx-pivot-table: 修复多业务合并时所有 pivotTable 的 `cacheId` 均为 0、与 workbook `pivotCaches` 不一致导致 Excel 报内容损坏的问题
- nad-acx-pivot-table: 修复多级行字段（`exp_id` + `event_day`）的 `rowItems` 生成，避免相对差列 `#N/A`
- nad-acx-pivot-table: `merge_pivots` 仅声明实际存在的 cache/pivotTable 部件，消除 `[Content_Types].xml` 悬空引用

## [0.22.27] - 2026-08-03
### Changed
- html-report: 批注模式的可见术语统一为“批注”，移除提问/注释类型筛选和分流；选区、右键、侧栏、空态与发布操作使用同一套命名
- html-report: 默认交接从“完成批注并保存 HTML”改为“复制批注给 Agent”，零批注时主操作明确禁用；`保存批注版 HTML` 降为备用，次级 Markdown/发布/清空操作收进更多菜单
- html-report: 新增轮次状态和 `AgentReviewReceipt`；Agent 可通过 `inject_annotation_mode.py --processed` 或 `--processed-round` 写回处理条数、正文是否修改、时间与章节，并用 `check_html_report.py --require-review-receipt` 验证
- html-report: 发布版同步物理剥离待处理包、处理回执和本地路径；运行时、校验器、组件测试、Gallery、eval 与文档契约同步更新，skill 从 `0.7.6` 升级到 `0.7.7`，插件升级到 `0.22.27`

## [0.22.26] - 2026-08-03
### Changed
- html-report: 自动定位失败的批注增加手动“重新关联”闭环；用户在 `<main>` 正文中选择新原文后可复用原批注完成锚点迁移，保留 `id`、内容、类型和创建时间，不再要求删除重建
- html-report: 重新关联模式支持 Esc/取消和正文选区安全校验；校验器、组件回归、运行时测试、Gallery 与 annotation eval 同步更新，skill 从 `0.7.5` 升级到 `0.7.6`，插件升级到 `0.22.26`

## [0.22.25] - 2026-08-03
### Changed
- html-report: 批注侧栏新增 `全部 / 提问 / 注释` 分段筛选和数量徽标，长批注列表可以按工作视图快速收敛
- html-report: 批注原文摘录支持直接定位正文，保留显式“定位”按钮；筛选状态只存在于当前编辑会话，不进入 AgentQuestionPack
- html-report: 校验器、组件回归、运行时测试、Gallery 和 eval 同步更新；skill 版本从 `0.7.4` 升级到 `0.7.5`，插件升级到 `0.22.25`

## [0.22.24] - 2026-08-03
### Changed
- html-report: 右上角固定为批注侧栏入口，零条显示“批注”、有内容时显示数量徽标，不再与“导出无批注版”切换职责
- html-report: 侧栏主操作改为“完成批注”，明确将当前批注写回 HTML 供 Agent 处理；发布版导出继续留在侧栏并物理剥离批注数据
- html-report: 校验器、组件回归和 eval 同步新增稳定入口门禁；skill 版本从 `0.7.3` 升级到 `0.7.4`，插件升级到 `0.22.24`

## [0.22.23] - 2026-07-30
### Changed
- html-report: Diff Viewer 最左侧红绿变更指示条从 5px 收窄到 2px，`+/-` gutter 继续保持 25px，兼顾细状态标识与符号对齐
- html-report: 校验器、组件回归和 Gallery 新增 2px 指示条门禁；skill 版本从 `0.7.2` 升级到 `0.7.3`，插件升级到 `0.22.23`

## [0.22.22] - 2026-07-30
### Changed
- html-report: Diff Viewer 的 old/new 行号列取消 40px 固定最小宽度，改为按当前 diff 的最长行号自然收缩，减少空白占宽
- html-report: 移除 old/new 行号之间的内部竖线，仅保留行号区与代码区边界；校验器、组件测试和 Gallery 同步更新，skill 版本从 `0.7.1` 升级到 `0.7.2`，插件升级到 `0.22.22`

## [0.22.21] - 2026-07-30
### Added
- html-report: 新增可重建的标准组件 Gallery，集中展示全部 13 个注册组件、评论模式及默认、长内容、空状态和交互状态

### Changed
- html-report: Gallery 的代码、Diff 和 Review Workspace 复用正式生成器，并增加组件覆盖、产物新鲜度和最终 HTML 校验；skill 版本从 `0.7.0` 升级到 `0.7.1`，插件升级到 `0.22.21`

## [0.22.20] - 2026-07-29
### Added
- html-report: 新增隔离 Eval Runner，支持独立任务 Agent 与 grader 自动执行、确定性 HTML 校验、逐项证据评分和多轮通过率汇总

### Changed
- html-report: 评测任务完成后才生成 grader rubric，并用输入、skill 快照和提交物哈希阻止 expectations 泄露与跨轮污染；skill 版本从 `0.6.5` 升级到 `0.7.0`，插件升级到 `0.22.20`

## [0.22.19] - 2026-07-29
### Changed
- html-report: 评论卡片的提问/注释徽标禁止 flex 收缩和换行，长章节标题承担换行，避免窄卡片中两个字被挤成竖排
- html-report: 评论模式校验器、组件回归和 eval 新增类型徽标稳定布局门禁；skill 版本从 `0.6.4` 升级到 `0.6.5`，插件升级到 `0.22.19`

## [0.22.18] - 2026-07-29
### Changed
- html-report: 为 `.tag` 增加中性深色默认背景，漏写 P0/P1/P2 变体类时仍保持可读；打印模式统一退化为浅底深字
- html-report: 校验器、组件回归和 eval 新增标签默认前景/背景门禁；skill 版本从 `0.6.3` 升级到 `0.6.4`，插件升级到 `0.22.18`

## [0.22.17] - 2026-07-29
### Changed
- html-report: 普通表格的 `.table-wrap` 新增统一 12px 圆角裁切，与目录和内容卡片保持一致，同时保留完整 1px 网格线和宽表横向滚动
- html-report: 组件契约、校验器和 eval 新增表格圆角门禁；skill 版本从 `0.6.2` 升级到 `0.6.3`，插件升级到 `0.22.17`

## [0.22.16] - 2026-07-29
### Changed
- html-report: 选中文本后的评论气泡从“提问 / 批注”双入口收敛为单一“注释”入口，问题和修改建议不再要求用户预先分类
- html-report: 右键菜单继续保留提问和注释细分操作，并兼容旧评论包中的“批注”类型；skill 版本从 `0.6.1` 升级到 `0.6.2`，插件升级到 `0.22.16`

## [0.22.15] - 2026-07-29
### Changed
- html-report: 批注输入浮层的提交按钮新增可见 `Ctrl/⌘ + Enter` 快捷键标识，并保留 `aria-keyshortcuts` 与原有键盘提交行为
- html-report: 校验器和 eval 新增快捷键提示可见性门禁；skill 版本从 `0.6.0` 升级到 `0.6.1`，插件升级到 `0.22.15`

## [0.22.14] - 2026-07-29
### Added
- html-report: 新增统一组件注册表和 `assemble_report.py`，自动检测页面组件、递归解析依赖并幂等内联 CSS/JS
- html-report: 新增 `file-location` 短标签 IDE 跳转与 `image-lightbox` 图片点击放大组件，完整路径保留在链接和悬停信息中
- docs: 新增 HTML Report 组件化架构设计，记录分层、外部案例、迁移策略、版本规则和扩展门槛

### Changed
- html-report: 将 CSS/JS 从 `references/css/` 迁入 `assets/components/`，拆分 base、table、code-block、diff-viewer、media、目录、Tabs、排序等可组合组件
- html-report: Review Workspace standalone 预览接入统一装配器，静态与 runtime IDE 定位统一使用短标签和完整目标
- html-report: 校验器新增组件声明、依赖、runtime 完整性、Tabs/排序结构、灯箱和 IDE 定位一致性门禁，组件回归扩展到 23 项
- html-report: skill 版本从 `0.5.3` 升级到 `0.6.0`；未新增 skill，插件按累计数量规则升级到 `0.22.14`

## [0.22.13] - 2026-07-28
### Changed
- html-report: 普通表格收敛到 `base.css` 的 `.table-wrap` 组件，默认提供完整 1px 网格线、表头样式和窄屏横向滚动，不再依赖报告临时补边框
- html-report: `highlight_code.py --lang diff --diff-view` 自动按 Git 或标准 unified 文件头拆分多文件 patch，为每个文件输出独立且带文件名的 Diff 卡片
- html-report: 校验器新增普通表格容器、完整网格线、Diff 文件标题和单卡片多文件混装门禁，并增加 7 项组件级回归测试与专门 eval
- html-report: skill 版本升级到 `0.5.3`，插件版本升级到 `0.22.13`

## [0.22.12] - 2026-07-27
### Changed
- html-report: 将七类报告的固定章节模板改为内容覆盖清单，先按读者任务和材料依赖自主设计叙事主线，再检查必要内容，允许章节改名、排序、合并和省略不适用项
- html-report: 转换已有文档时优先保留清晰的宏观结构与教学提示；结论型报告继续给首屏摘要，知识手册可改用阅读地图，避免重复 TL;DR 和通用报告章节
- html-report: 保留技术内容完整性护栏；涉及真实代码或配置改动时仍需文件定位和聚焦 diff，建议代码与原理说明不得伪造 diff
- html-report: 新增知识手册结构保真回归用例，skill 版本升级到 `0.5.2`，插件版本升级到 `0.22.12`

## [0.22.11] - 2026-07-20
### Removed
- skills: 将零调用且仅适用于 Claude Code 的 `session-rename` 从活跃 `skills/` 移出，不再由 Claude Code / Codex 插件发现、注册或自动触发
- README / manifest: 移除 `session-rename` 的活跃清单和关键词；`html2md` 继续保留为活跃 skill

### Added
- repository: 新增顶层 `deprecated-skills/` 历史归档目录，保留退役 skill 的完整目录内容，并用 frontmatter 记录退役版本与原因
- validation: 新增退役 skill 隔离检查，校验归档元数据、README 归档表、活跃/退役重名、manifest 关键词泄漏及 Codex 扫描根
- validation: 新增插件版本结构检查，要求第一位保持 `0`，第二位等于活跃与退役 skill 总数

### Changed
- repository: 重写 skill 目录规范和退役流程，明确 `skills/` 只承载当前启用能力，历史 CHANGELOG / 版本记录保持不变
- manifest: 退役不改变累计新增 skill 数，按插件版本规则仅增加优化次数，版本升级到 `0.22.11`

## [0.22.10] - 2026-07-19
### Changed
- html-report: 修复同一路径报告重新生成后旧评论仍从 `localStorage` 恢复、但顺序型 `blockId` 已失效，导致保存出的评论版无法定位正文的问题
- html-report: 初始化、点击定位和保存前按完整原文、上下文与章节做唯一匹配迁移；无法安全迁移的评论明确标黄并阻止保存，避免生成无效 `AgentQuestionPack`
- html-report: 校验脚本新增旧定位迁移、失效提示和保存前门禁契约；skill 版本升级到 `0.5.1`，插件版本升级到 `0.22.10`

## [0.22.9] - 2026-07-16
### Added
- html-report: 新增可复用的多文件 2-3 版本 Review Workspace，支持文件筛选、同步滚动、只看差异、参考行跳转、全文复制、IDEA 打开和本地已审阅进度
- html-report: 新增 `build_review_workspace.py`，按 JSON 规格读取源码快照、校验标记行号、生成逐行静态高亮，并对内嵌 JSON 做 raw-text 安全转义
- html-report: 新增 Workspace CSS、离线 runtime、使用规范和回归 fixture，校验脚本同步检查组件结构、唯一 runtime、数据 schema、安全标签与响应式样式

### Changed
- html-report: 明确 Review Workspace 只用于多文件完整源码关系判断，Findings、测试缺口和真实 `.diff-card.diff-viewer` 仍是代码评审主线
- html-report: skill 版本升级到 `0.5.0`
- README / manifest: 同步多版本 Review Workspace 能力，插件版本升级到 `0.22.9`

## [0.22.8] - 2026-07-15
### Changed
- nad-acx-pivot-table: 修正页面筛选字段与透视主体重叠的问题，按筛选字段数量下移 `location`，并补齐 `rowPageCount` / `colPageCount`
- nad-acx-pivot-table: 修正有页面筛选时的 `firstDataRow` 与主体高度计算，避免 Microsoft Excel 打开文件时提示修复
- nad-acx-pivot-table: OOXML guard 改为校验页面区、主体范围和行项数量的一致性，新增 0/1/2 个筛选字段的回归测试
- nad-acx-pivot-table: skill 版本升级到 `0.1.4`，插件版本升级到 `0.22.8`

## [0.22.7] - 2026-07-14
### Changed
- html-report: 将离线批注功能的正式名称从“审核模式”统一为“评论模式”，同步页面标签、保存提示、skill 指引、回归用例和插件说明
- html-report: 保留“审核模式”旧称触发兼容，并保持 `AgentQuestionPack`、`--require-review-pack`、DOM id 和 `review` 数据字段不变，已有评论结果可继续读取
- html-report: skill 版本升级到 `0.4.1`
- README / manifest: 同步评论模式定位，插件版本升级到 `0.22.7`

## [0.22.6] - 2026-07-13
### Changed
- obsidian: 将工作模式与文档类型拆开，新增完整技术指南的概念依赖和知识点唯一主章节门禁
- obsidian: 用户指定参考文章时，强制在提纲前提取标题、章节、段落、列表/表格、配图、语气及借鉴边界的 style profile
- obsidian: 新增专业标题风险规则、结构与文风两轮全篇审查，以及用户反馈后的同类缺陷全文与 SVG 回归
- obsidian: validator 新增 front matter 子集、正文收尾、本地图片断链和 SVG 根元素校验；行为 eval 新增三组故障注入场景与可重复任务/评分 harness
- obsidian: 技术链路模板改用名词性标题，skill 保持未发布的 `0.3.0` 版本
- README / manifest: 同步 Obsidian 编辑工作流说明，插件版本升级到 `0.22.6`

## [0.22.5] - 2026-07-13
### Changed
- xbuild-open-source: 在代码阅读、调用链追踪、排障或修改中发现 EasyBox/xbuild 目标源码缺失时自动触发，唯一映射下最小补个人 local 配置并精确同步缺失仓
- xbuild-open-source: 新增 effective 配置/本地仓状态决策表，已存在源码时直接继续原任务，多候选、公共 overlay、全量同步和已有仓更新仍保留确认边界
- xbuild-open-source: 新增 5 个行为回归场景，覆盖隐式补开、精确同步、已有源码 no-op、多候选和同步失败不扩大范围
- xbuild-open-source: skill 版本升级到 `0.1.1`
- code-reading / mgit: 增加 xbuild 源码缺失协作路由与唯一缺失仓精确同步例外；skill 版本分别升级到 `0.1.3`、`0.1.6`
- README / manifest: 同步 xbuild 源码自动补开能力，插件版本升级到 `0.22.5`

## [0.22.4] - 2026-07-13
### Added
- html-report: 审核侧栏新增 `保存审核结果到 HTML`，将唯一、安全转义的 `AgentQuestionPack` 内嵌回单文件，Agent 可直接读取并更新报告
- html-report: 重新打开含批注审核版时可从内嵌包恢复批注；发布版显式剥离内嵌审核数据，避免内部意见和本地路径泄漏
- html-report: 兼容迁移旧版本地草稿键，并允许把清空后的空审核包保存回 HTML，避免旧批注复活

### Changed
- html-report: 批注审核模式的输入浮层新增 `⌘ + Enter` 提交，并兼容 Windows/Linux 的 `Ctrl + Enter`
- html-report: 用 HTML 内嵌交接替换独立 `下载 JSON`，并把对外产物明确为 `导出无批注版`
- html-report: 普通 Enter 继续换行，输入法组字阶段不触发提交；校验脚本新增快捷键、内嵌包 schema、安全转义与发布版剥离检查
- html-report: 新增 `--require-review-pack` 审核交接门禁，修复正文标记误判、清空态“批注 0”、增段定位 ID 冲突；下载兜底保留原页草稿，避免取消下载造成批注丢失
- html-report: 明确当前承载审核包的 HTML 是 Agent 回写目标，另存后的来源路径只用于回查
- html-report: skill 版本升级到 `0.4.0`
- README / manifest: 同步可编辑、可内嵌交接的离线批注审核定位，插件版本升级到 `0.22.4`

## [0.22.3] - 2026-07-08
### Changed
- datapilot-sql-runner: 将定位调整为 DataPilot MCP 跑数结果闭环，默认覆盖提交 SQL、查状态、等待下载、下载结果和可选透视表产出
- datapilot-sql-runner: 大幅瘦身 `SKILL.md`，把 Chrome/Monaco 页面操作经验迁移到 `references/chrome_fallback.md`，仅 MCP 不可用或能力不覆盖时按需读取
- datapilot-sql-runner: 补充下载结果后联动 `nad-acx-pivot-table` 生成商业 AB 实验透视表的交付流程
- datapilot-sql-runner: skill 版本升级到 `0.1.3`
- README / manifest: 同步 DataPilot 跑数结果闭环说明，插件版本升级到 `0.22.3`

## [0.22.2] - 2026-07-08
### Changed
- datapilot-sql-runner: 默认优先使用 DataPilot MCP 提交 SQL、查询任务状态、下载或转储结果，MCP 不可用或能力不覆盖时再回退 Chrome/Monaco 页面流程
- datapilot-sql-runner: 补充 MCP 已返回 `task_id` 后的重复提交保护，后续查询失败时优先按任务 ID 跟进或打开 Chrome 运行中心定位
- datapilot-sql-runner: skill 版本升级到 `0.1.2`
- README / manifest: 同步 DataPilot MCP 优先说明，插件版本升级到 `0.22.2`

## [0.22.1] - 2026-07-07
### Changed
- obsidian: 引入任务定义、范围计划、证据包、内容规格、大纲、初稿、改写、配图计划、质检和写入交付的 10 步写作闭环，减少空泛模板化笔记
- obsidian: 新增概念解释、技术链路、问题复盘和资料整理四类常用笔记结构，并补充“烂笔记模式”反向检查
- obsidian: skill 版本升级到 `0.2.0`
- README / manifest: 同步 Obsidian 写作流程说明，插件版本升级到 `0.22.1`

## [0.22.0] - 2026-07-07
### Added
- xbuild-open-source: 新增 EasyBox/xbuild 源码模式打开 skill，支持从崩溃栈、类名、包名、模块名或远端仓库反查 `xbuild/modules/default` 映射，并在 local/overlay 覆盖文件中最小开启 `syncSource true`
- xbuild-open-source: 新增 `references/xbuild-source-mode.md`，沉淀 local/overlay 选择、default 映射查找、TalosPro/bba_talospro/广告仓判断和 MGIT 同步确认边界

### Changed
- README / manifest: 同步新增 xbuild 源码模式打开能力，插件版本升级到 `0.22.0`

## [0.21.21] - 2026-07-06
### Changed
- html-report: 将批注审核模式的 CSS、HTML 容器和 JS 从 `inject_annotation_mode.py` 抽到 `assets/annotation-mode/`
- html-report: `inject_annotation_mode.py` 改为读取批注资产、校验剥离 marker 和 `__QA_REPORT_META__` 占位符后再内联注入，脚本从 1341 行降到约 120 行
- validation: `scripts/validate-plugin.py` 新增批注资产完整性检查，避免发布版剥离标记或路径元数据占位符丢失
- html-report: skill 版本升级到 `0.3.14`
- manifest: 插件版本升级到 `0.21.21`

## [0.21.20] - 2026-07-06
### Added
- html-report: 新增 `evals/evals.json` 和 fixtures，覆盖代码评审、问题排查、技术方案、聚焦 diff、Android mock 验收和批注审核模式六类回归 prompt
- validation: `scripts/validate-plugin.py` 新增 skill eval schema 与 fixture 路径检查，避免回归用例断链

### Changed
- html-report: skill 版本升级到 `0.3.13`
- manifest: 插件版本升级到 `0.21.20`

## [0.21.19] - 2026-07-06
### Changed
- html-report: `artifact-patterns.md` 新增代码评审、验收报告、选型对比、项目总结四类专门模板
- html-report: 报告类型选择规则补齐 review、验收、选型、总结的触发边界，减少高频报告落回通用规则
- html-report: README 同步报告类型模板能力说明，skill 版本升级到 `0.3.12`
- manifest: 插件版本升级到 `0.21.19`

## [0.21.18] - 2026-07-06
### Changed
- html-report: `highlight_code.py` 新增 `--list-langs`，以 JSON 输出支持语言和常见别名，作为代码语言清单单一真源
- html-report: `check_html_report.py` 改为从 `highlight_code.py` 读取支持语言，移除校验脚本内重复白名单
- html-report: references 改为引用 `--list-langs`，避免文档里维护第二份完整语言清单
- html-report: skill 版本升级到 `0.3.11`
- manifest: 插件版本升级到 `0.21.18`

## [0.21.17] - 2026-07-04
### Changed
- html-report: 将 `css-template.md` 从整块 CSS 模板改为 CSS 组件装配说明，行数从 1120 行降到 291 行
- html-report: 新增 `references/css/` 组件 CSS 源文件，按 base、code-diff、interactions、media、diagram、toc、tabs、sortable-table 拆分维护
- html-report: 明确生成报告时按需读取组件 CSS，并把需要的 CSS 内联进最终单文件 HTML，避免交付物依赖外部 CSS
- html-report: skill 版本升级到 `0.3.10`
- manifest: 插件版本升级到 `0.21.17`

## [0.21.16] - 2026-07-03
### Changed
- html-report: `highlight_code.py` 新增 Objective-C、Swift、C/C++、Go、Rust、TypeScript、Ruby、PHP、Markdown、TOML、INI 等语言和常见后缀/别名支持
- html-report: `check_html_report.py` 同步扩展代码块语言白名单，避免新增语言生成后在报告校验阶段被误报
- html-report: skill 版本升级到 `0.3.9`
- README / manifest: 同步多语言离线高亮说明，插件版本升级到 `0.21.16`

## [0.21.15] - 2026-07-02
### Changed
- generate-image: 客户端新增 `--candidates` 并发候选生成能力，支持默认三路并发请求后视觉筛选最佳图
- generate-image: skill 版本升级到 `0.1.5`，执行流程改为并发生成 3 张候选图、检查后只保留最佳候选
- README / manifest: 同步三候选并发筛选说明，插件版本升级到 `0.21.15`

## [0.21.14] - 2026-07-02
### Changed
- generate-image: 客户端脚本补齐中文 docstring，说明生成结果、鉴权错误、密钥缓存、后端分发和输出路径去重等关键边界
- manifest: 插件版本升级到 `0.21.14`

## [0.21.13] - 2026-07-01
### Changed
- 维护指南: 新增代码编写注释规则，要求方法、类、脚本入口以及方法内关键逻辑、分支条件、边界处理都补充清晰中文注释
- manifest: 插件版本升级到 `0.21.13`

## [0.21.12] - 2026-07-01
### Changed
- generate-image: 客户端新增默认本地私有缓存 `~/.config/iplugin/generate-image-api-key`，首次提供令牌后后续生成可自动复用
- generate-image: CLI 新增 `--save-api-key-stdin` / `--save-api-key-only`，避免令牌出现在命令行或日志里
- generate-image: skill 版本升级到 `0.1.4`
- README / manifest: 同步 API key 缓存说明，插件版本升级到 `0.21.12`

## [0.21.11] - 2026-06-30
### Fixed
- generate-image: 明确用户指定 `gptimage` / `gptimg2` / `gpt-image-2` / `banana2` 等接口链路时必须走本地 API 客户端，避免被平台内置出图路径误接走
- generate-image: skill 版本升级到 `0.1.3`
- README / manifest: 同步图片生成路由说明，插件版本升级到 `0.21.11`

## [0.21.10] - 2026-06-30
### Changed
- html-report: 离线批注审核模式的右侧栏新增编辑已有批注能力，复用单按钮输入浮层，避免只能删除重加
- html-report: 校验脚本新增批注编辑能力检查，防止后续生成的审核版 HTML 回退到不可编辑
- html-report: skill 版本升级到 `0.3.8`
- svg-tech-diagram: 收紧自适应画布规则，要求按内容包围盒反推 `viewBox` 和背景尺寸，限制无意义留白
- svg-tech-diagram: 新增几何闸门脚本，检查多箭头终点聚集、连线穿节点和背景 `rect` 覆盖范围
- svg-tech-diagram: 新增 PNG 像素闸门脚本，检查渲染空白、裁切、四周留白过大和上下留白失衡
- svg-tech-diagram: 补充多来源汇聚图规则，要求先抽象变量池/汇聚层，再用单箭头指向失败现象或目标
- svg-tech-diagram: 自审清单新增外边距阈值和非零 `viewBox` 背景覆盖检查，避免继续交付大留白 SVG
- svg-tech-diagram: skill 版本升级到 `0.1.4`
- README / manifest: 将批注审核能力描述同步为可编辑，插件版本升级到 `0.21.10`

## [0.21.9] - 2026-06-26
### Changed
- delegated-search: 增加主线程上下文预算约束，避免委派后重复宽搜和全链路重跑
- delegated-search: 明确主线程搜索应优先使用精确标识符、`rg -l` 和少量证据抽查
- delegated-search: skill 版本升级到 `0.1.5`
- manifest: 插件版本升级到 `0.21.9`

## [0.21.8] - 2026-06-26
### Changed
- android-mock: 固化录屏抽帧流程，要求 toast/loading/无 toast 等时序证据生成关键帧或 contact sheet 并在报告中展示
- android-mock: 补充 `ffmpeg` contact sheet 推荐命令、缺失工具时的安装确认和工具补充记录要求
- android-mock: skill 版本升级到 `0.1.3`
- manifest: 插件版本升级到 `0.21.8`

## [0.21.7] - 2026-06-26
### Changed
- android-mock: 验收报告优先使用逐 case 卡片，并在卡片内嵌截图或录屏预览
- android-mock: 明确纯汇总表格和超链接只能作为补充，mock 日志、logcat 等原始文件链接不替代主证据
- android-mock: skill 版本升级到 `0.1.2`
- manifest: 插件版本升级到 `0.21.7`

## [0.21.6] - 2026-06-26
### Changed
- delegated-search: 将“强阈值”改为“委派信号”，明确数字只作为复杂度参考，不作为子 Agent 委派硬门槛
- delegated-search: 强调判断重点是子任务是否独立、自包含，以及是否能减少主线程大量中间输出
- delegated-search: skill 版本升级到 `0.1.4`
- manifest: 插件版本升级到 `0.21.6`

## [0.21.5] - 2026-06-26
### Changed
- delegated-search: 从“广域检索委派”调整为“复杂任务委派”，覆盖复杂排查、调用链找全、影响面分析、跨模块实现和并行验证
- delegated-search: 增加强阈值、explorer/worker/verifier 角色映射、子 Agent 不可用 fallback 和命中阈值但不委派时的可见说明要求
- delegated-search: skill 版本升级到 `0.1.3`
- README / manifest: 将能力描述、关键词和默认提示同步为复杂任务委派
- manifest: 插件版本升级到 `0.21.5`

## [0.21.4] - 2026-06-26
### Changed
- android-mock: 收紧验收报告规范，要求报告新增或版本化输出，避免覆盖历史报告
- android-mock: 强制每个 case 下直接放截图、录屏或 mock/logcat/dumpsys 链接，证据附录不能替代 case 级证据块
- android-mock: skill 版本升级到 `0.1.1`
- manifest: 插件版本升级到 `0.21.4`

## [0.21.3] - 2026-06-26
### Changed
- 维护指南: 明确只有新增 skill 才升级 minor 版本；改名、修复、文档和 manifest 等非新增变更统一升级 patch 版本
- manifest: 插件版本升级到 `0.21.3`

## [0.21.2] - 2026-06-26
### Changed
- generate-image: 将 `comate-image` 重命名为 `generate-image`，skill 定位改为通用图片生成，不再以 Comate 作为能力名称
- generate-image: 客户端脚本改名为 `generate_image_client.py`，API key 主变量改为 `GENERATE_IMAGE_API_KEY` / `GENERATE_IMAGE_API_KEY_FILE`，旧 `COMATE_*` 变量仅保留兼容读取
- README / manifest: 将插件描述、关键词和默认提示中的 Comate 图片生成入口改为通用图片生成入口
- manifest: 插件版本升级到 `0.21.2`

## [0.21.1] - 2026-06-25
### Changed
- comate-image: 将 `Comate`、`banana2`、`gptimg2`、`生成图片` 等触发/选路词明确从最终图片 prompt 中剥离
- comate-image: CLI 支持 `gptimg2`、`banana2` 等 backend 别名，并提供 `--raw-prompt` 兜底保留原始 prompt
- manifest: 插件版本升级到 `0.21.1`

## [0.21.0] - 2026-06-25
### Added
- comate-image: 新增 Comate 图片生成 skill，内置标准库客户端，支持 Images、Responses image_generation 和 Banana/Gemini 三条链路

### Changed
- comate-image: 默认按 prompt 语义判断输出图片文件名，缺少或过期 API key 时通过 ask-user-question 询问用户设置或刷新方式
- svg-tech-diagram: 补充垂直分区预算和上下留白阈值，把“上挤下空、文字堆叠”列为 A 级自审失败项
- svg-tech-diagram: skill 版本升级到 `0.1.3`
- README / manifest: 补充 Comate 图片生成能力入口、关键词和默认提示
- manifest: 插件版本升级到 `0.21.0`

## [0.20.0] - 2026-06-25
### Added
- android-mock: 新增 Android mock 自测验收 skill，覆盖真机 adb 执行、mockserver 请求核验、多链路分别验收、逐 case 证据留存、截图/录屏/logcat 采证和验收报告归档

### Changed
- README / manifest: 补充 Android mock 自测验收能力入口、关键词和默认提示
- manifest: 插件版本升级到 `0.20.0`

## [0.19.18] - 2026-06-25
### Added
- git-hooks: 新增版本化 `pre-push` hook，push 前转发到版本防撞检查脚本
- scripts: 新增 `pre_push_version_check.py`，push 前 fetch 远端并检查本地是否包含远端最新提交、manifest 版本是否大于远端、远端是否已有同版本 CHANGELOG / versions 记录

### Changed
- README / 维护指南: 补充 `git config core.hooksPath git-hooks` 启用方式和版本冲突处理说明
- 维护指南: 补充提交时只暂存并提交自己改动的边界规则，同一文件混合修改时必须按 hunk 控制
- validate-plugin.py: 将 `git-hooks/` 纳入 README 顶层目录结构检查
- manifest: 插件版本升级到 `0.19.18`

## [0.19.17] - 2026-06-25
### Added
- html-report: 新增可选图片/视频证据块支持，提供截图、录屏、关键帧和原文件链接的推荐结构与响应式样式
- html-report: `check_html_report.py` 在报告实际使用媒体时检查本地相对路径、图片 `alt`、视频 `controls` 和图片/视频响应式保护

### Changed
- html-report: 媒体证据的标题、说明、对应 case 和证据结论作为推荐结构输出 warning，不作为所有报告的强制失败条件
- html-report: skill 版本升级到 `0.3.7`
- manifest: 插件版本升级到 `0.19.17`

## [0.19.16] - 2026-06-25
### Fixed
- nad-acx-pivot-table: 为筛选字段生成的 `<pageField>` 补齐 `hier="-1"`，避免 Mac Excel 对含 `filter_fields` 的原生透视表继续提示修复
- nad-acx-pivot-table: 更新 OOXML 踩坑记录，明确 `axisPage`、`pageFields` 与 `hier="-1"` 需要成套出现

### Changed
- nad-acx-pivot-table: 新增 `pivot_tool.ooxml_guard` 兼容性闸门，生成 xlsx 后自动检查 PivotTable OOXML 高风险结构
- nad-acx-pivot-table: skill 版本升级到 `0.1.3`
- manifest: 插件版本升级到 `0.19.16`

## [0.19.15] - 2026-06-25
### Changed
- nad-acx-pivot-table: 有实验名时自动输出文件名改为 `【MMdd-MMdd】实验名.xlsx`，例如 `【0621-0624】健康竞胜率.xlsx`
- nad-acx-pivot-table: 同步更新 CLI 帮助、skill 文档和配置 schema 中的命名规则说明
- nad-acx-pivot-table: skill 版本升级到 `0.1.2`
- manifest: 插件版本升级到 `0.19.15`

## [0.19.14] - 2026-06-25
### Changed
- commercial-sql-writer: 补充 `fc_nad.nativeads_als_every_log` 落地页性能日志口径，沉淀 `category_id = '1029'` 下 `f*` / `ef*` 字段映射
- commercial-sql-writer: 新增落地页抵达率场景路由和自查项，明确 `f7=cmatch`、`f2=lp_real_url`、`ef2=clickTime`、`ef3=isbrowser`
- commercial-sql-writer: skill 版本升级到 `0.1.1`
- README / manifest: 插件版本升级到 `0.19.14`，补充落地页性能检索关键词

## [0.19.13] - 2026-06-24
### Fixed
- nad-acx-pivot-table: 修复自定义配置使用 `filter_fields` 时只生成 `axisPage`、未生成 `pageFields` 导致 Excel 打开提示修复的问题
- nad-acx-pivot-table: 补充 OOXML 筛选字段兼容性记录，说明 `pageFields` 必须位于 `colItems` 与 `dataFields` 之间

### Changed
- nad-acx-pivot-table: skill 版本升级到 `0.1.1`
- manifest: 插件版本升级到 `0.19.13`

## [0.19.12] - 2026-06-24
### Changed
- html-report: diff viewer 的 `+/-` 轨道收敛为 25px，old/new 行号列改为 `width: 1%; min-width: 40px` 自适应宽度，减少窄屏下左侧指示器挤占代码区
- html-report: `check_html_report.py` 增加自适应行号列宽度检查，避免后续回退到固定 54px 宽列
- html-report: skill 版本升级到 `0.3.6`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.12`

## [0.19.11] - 2026-06-24
### Changed
- html-report: 收紧真实 unified diff 的生成规则，要求脚本输出的 `.diff-card.diff-viewer` 原样嵌入，禁止降级成 `language-diff` 或 `language-text` 普通代码块
- html-report: `check_html_report.py` 新增 diff viewer 结构和 CSS 闸门，检查 header、scroll、table、old/new 行号列、hunk、增删行和左侧红绿变更轨道，拦截样式漂移
- html-report: skill 版本升级到 `0.3.5`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.11`

## [0.19.10] - 2026-06-23
### Changed
- obsidian: 增加个人技术笔记写作风格规则，强调先定规模、先定位再展开、用段落解释并用列表收束
- obsidian: 强化配图克制原则，要求每张图解决明确理解问题，并在图前交代用途、图后点明结论
- obsidian: skill 版本升级到 `0.1.3`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.10`

## [0.19.9] - 2026-06-23
### Changed
- svg-tech-diagram: 增加文字块、箭头标签、图例和底部说明的占位预算规则，避免说明文字贴边或压到节点卡片
- svg-tech-diagram: 自审清单新增“文字遮挡 / 压线 / 贴到卡片上”的失败映射，要求自由文字必须有独立说明区
- svg-tech-diagram: skill 版本升级到 `0.1.2`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.9`

## [0.19.8] - 2026-06-23
### Changed
- html-report: 明确没有行号的超长文件路径也不能完整塞进普通 `<code>`，应使用 `.path` chip 和 `...` 省略中间目录，同时保留仓库/模块、文件名和必要的方法指向
- html-report: 完成前检查增加“长文件路径块截断展示”要求，避免证据来源、表格或摘要卡片被完整目录撑破
- html-report: skill 版本升级到 `0.3.4`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.8`

## [0.19.7] - 2026-06-23
### Changed
- svg-tech-diagram: 补充内容驱动的 `viewBox` 规则，单行流程图和横向生命周期图不再默认套用 `1200x675`
- svg-tech-diagram: 自审清单增加“大面积空白”检查，要求画布高度与内容匹配并同步背景 rect 尺寸
- svg-tech-diagram: skill 版本升级到 `0.1.1`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.7`

## [0.19.6] - 2026-06-23
### Changed
- html-report: 普通行内 `<code>` 默认允许换行和断词，避免长命令、路径、Gradle task 或参数串撑破摘要卡片、证据列表和表格单元格
- html-report: skill 版本升级到 `0.3.3`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.6`

## [0.19.5] - 2026-06-23
### Changed
- html-report: 文件定位链接支持用 `...` 省略展示文本中的中间目录，保留仓库/模块语义、完整文件名和行号，同时通过 `href` 与 `title` 保持完整跳转定位
- html-report: 路径 chip 样式增加宽度约束和 `overflow-wrap:anywhere`，降低超长链接在窄屏或分屏下撑破正文的风险
- html-report: skill 版本升级到 `0.3.2`
- manifest: 插件版本按现有 skill 规则优化递增到 `0.19.5`

## [0.19.4] - 2026-06-23
### Changed
- datapilot-sql-runner: 新增运行中心跳检查规则，任务处于排队中、执行中或运行中时可按默认 3 分钟间隔复查状态
- datapilot-sql-runner: 明确心跳终止边界，终态停止，无明确长时间等待时最多 10 次或 30 分钟
- datapilot-sql-runner: skill 版本升级到 `0.1.1`
- README / manifest: 插件版本升级到 `0.19.4`

## [0.19.3] - 2026-06-21
### Changed
- html-report: 优化离线批注审核模式的发布入口；0 条批注时右上角不再显示“批注 0”，改为更明确的“导出发布版”并直接导出发布版 HTML
- html-report: 右侧栏将“导出发布版”提升为首个全宽主按钮，避免发布版导出入口被 Markdown/JSON 导出按钮淹没
- html-report: skill 版本升级到 `0.3.1`
- manifest: 插件版本按现有 skill 功能优化规则递增到 `0.19.3`

### Fixed
- html-report: 修正导出发布版确认框语义，点击取消时不再下载 `_public` 文件；确认后优先选择覆盖保存，不支持直接保存时才下载当前文件名作为兜底
- html-report: 修正 0 条批注时“导出发布版”右侧残留蓝色计数圆点的问题

## [0.19.2] - 2026-06-21
### Added
- html-report: 新增离线批注审核模式注入脚本，支持选区提问/批注、右侧批注栏、Markdown/JSON 提问包导出和导出发布版 HTML
- html-report: 新增批注模式 reference，明确轻量浮层、单按钮提交、点击外侧关闭、发布版物理剥离和 Agent 提问包路径字段契约

### Changed
- html-report: 校验脚本新增批注模式结构检查，确保提问包包含原 HTML 文件名、绝对路径和 `file://` URL，并避免批注 UI 交互漂移
- html-report: 批注注入脚本在生成阶段写入输出 HTML 的绝对路径和 `file://` URL，避免本地 HTTP 预览时提问包丢失文件上下文
- html-report: skill 版本升级到 `0.3.0`
- README / manifest: 插件版本按现有 skill 功能升级规则递增到 `0.19.2`

### Fixed
- html-report: 删除或清空批注后同步清理正文高亮、块级边框和浏览器选区，避免右侧栏已删除但正文仍显示选中状态

## [0.19.1] - 2026-06-21
### Changed
- html-report: 增加与 `svg-tech-diagram` 的软依赖协作规则，复杂技术图由 SVG 绘图 skill 生成、渲染自审后内联到 HTML 报告
- html-report: CSS 模板新增 `.diagram-block` / `.tech-diagram` 图块样式，支持响应式横向滚动和打印降级
- README / manifest: 插件版本升级到 `0.19.1`

## [0.19.0] - 2026-06-21
### Added
- svg-tech-diagram: 新增 SVG 技术绘图 skill，用于为技术长文、HTML 报告、架构说明和代码链路生成统一风格的矢量图
- svg-tech-diagram: 沉淀朴素浅色优先的视觉规范、少量强调色建议、SVG 组件骨架、布局模式、渲染 PNG 自审清单和用户反馈映射
- svg-tech-diagram: 新增 `render_svg.py`，优先通过本机 `rsvg-convert` 将 SVG 渲染为 PNG，辅助交付前视觉自审

### Changed
- README / manifest: 插件能力清单加入 SVG 技术图生成，版本升级到 `0.19.0`

## [0.18.3] - 2026-06-17
### Fixed
- README: 将目录树改为仓库顶层结构，补充 `tools/`，并将 `skills/` 改为目录模板，避免手写 skill 清单与 Skills 表重复漂移
- validate-plugin.py: 将 `tools/` 纳入 README 目录树闸门
- manifest: 插件版本升级到 `0.18.3`

## [0.18.2] - 2026-06-17
### Fixed
- html-report: 将当前触发命令文案统一为 `/html-report`
- best-of-web: 移除已不存在 command 文件的触发说明，并将 Codex 默认示例改为显式 `/best-of-web`
- AGENTS.md / CLAUDE.md: 将 `commands/` 描述收敛为可选目录，强调不要和同名 skill 重复注册
- validate-plugin.py: 新增当前命令触发文案和 Codex defaultPrompt 一致性闸门
- manifest: 插件版本升级到 `0.18.2`

## [0.18.1] - 2026-06-17
### Fixed
- README: 将目录结构改为插件核心结构，移除已删除的 `commands/` 目录引用，并说明 slash command 触发语义由同名 skill 承载
- validate-plugin.py: 新增 README 目录树闸门，拒绝目录结构代码块列出不存在的顶层路径
- manifest: 插件版本升级到 `0.18.1`

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
