---
name: html-report
version: 0.6.4
tags:
  - report
  - html
  - output
  - review
  - workspace
description: 生成独立 HTML 报告文件，支持图片/视频证据预览、多文件多版本 Review Workspace、离线评论模式、将评论结果内嵌回 HTML 供 Agent 直接读取，以及发布版导出。用户明确要求 HTML 输出（如“生成 HTML”“HTML 报告”“写成 HTML”“放到桌面”）、HTML 内评论/批注/审核/提问、复用两方/三方 Review Workspace，调用 `/html-report`，或说“我已在 HTML 里完成批注”“按 HTML 内嵌评论更新报告”时必须触发；用户未明说 HTML，但任务明显更适合独立可视化交付物时，也应自动触发或由其他 skill 调用，例如多章节长报告、代码评审报告、验收报告、问题排查/修复方案、技术方案、方案对比、项目总结、包含 diff/表格/时间线/图片/视频证据链的归档材料。普通简短的“总结一下”“整理一下”“直接给结论”默认用 Markdown，不触发。
---

# HTML 报告

当用户希望把分析结论、代码评审意见、问题清单、修复方案、技术方案或排查结果整理成一个独立 HTML 文件时，使用这个技能。默认生成一个可直接在浏览器打开的 `.html` 文件，通常放到桌面。

## Progressive Disclosure

SKILL.md 只保留触发、决策和执行路线。生成报告时按需要读取：

- `references/content-rules.md`：HTML vs Markdown 决策、文档类型、内容编排、正式抬头、输出要求、写作规范、完成前检查。
- `references/artifact-patterns.md`：按报告类型检查必要内容覆盖。当前覆盖技术方案、技术调研、问题排查/修复方案、代码评审、验收报告、选型对比、项目总结七个高频场景；它是覆盖清单，不是固定章节模板。
- `references/visual-rules.md`：视觉原则、变更标识、文件定位链接、超长路径省略展示、目录导航、ASCII/代码块、交互组件、场景速查。
- `references/css-template.md`：统一装配流程和最小 HTML 骨架。开始写 HTML 文件时读取；不再从 reference 手工复制 CSS/JS。
- `references/component-contracts.md`：组件分层、依赖、语义结构、无 JS 回退和维护门禁。报告使用表格、IDE 跳转、代码、Diff、图片灯箱、目录、Tabs、排序表格或 Workspace 时读取对应章节。
- `assets/components/registry.json`：页面组件、依赖和资产的机器可读单一真源；由装配器和校验器共同使用，普通生成时不手工修改。
- `references/review-workspace.md`：代码评审需要多个文件的 2 到 3 份完整源码并排审阅，或用户要求复用“三方 Review Workspace / 审阅台”时读取；它定义适用边界、JSON 规格、构建流程和与真实 diff 的分工。
- `assets/review-workspace/workspace.css`：Review Workspace 的布局、源码窗格、响应式和打印资产；由统一装配器按注册表内联。
- `assets/review-workspace/workspace.js`：Review Workspace 离线交互 runtime；通常由 `build_review_workspace.py` 自动内联，不要手写或业务化复制。
- `references/annotation-mode.md`：当用户要求离线评论模式（兼容旧称“审核模式”）、把评论结果写回 HTML、按内嵌批注更新报告或导出无批注发布版时读取。
- `assets/annotation-mode/`：评论模式的 CSS、HTML 容器和 JS 资产。普通生成报告时不要读取；维护评论 UI 或发布版剥离逻辑时再修改这些文件，最终仍由 `inject_annotation_mode.py` 内联成单文件 HTML。
- `../svg-tech-diagram/SKILL.md`：当报告需要复杂技术架构图、流程图、状态图或模块关系图时读取；由它负责 SVG 图的信息结构、绘制、PNG 渲染自审和可内联交付。
- `scripts/highlight_code.py`：代码片段 HTML 转义和基础高亮脚本。报告包含代码、SQL、XML、JSON、配置片段、Objective-C / Swift / C-family 等语言片段、shell 命令或 diff 时必须用它生成可嵌入的 `.code-wrap` 片段；默认使用零依赖 `builtin` 引擎，复杂代码可用 `--engine auto` 尝试本机 Pygments 静态预渲染，不能静默安装依赖；展示 unified diff 修改点时使用 `--diff-view`，多文件 patch 会自动输出每文件一个 `.diff-card`。
- `scripts/build_review_workspace.py`：按 JSON 规格读取 2 到 3 份源码快照，生成安全静态高亮并输出可内联 Workspace 片段；不要手工拼含源码的 JSON `<script>`。
- `scripts/assemble_report.py`：统一组件装配器。语义 HTML 和脚本生成片段准备完成后，用它自动检测组件、递归解析依赖并幂等内联 CSS/JS；不要手贴组件资产。
- `scripts/inject_annotation_mode.py`：当需要评论模式时，在基础 HTML 通过常规校验后运行它注入稳定的离线评论 UI、评论结果内嵌交接、Markdown 兜底和无批注发布版导出能力；不要手写批注 JS。
- `scripts/check_html_report.py`：生成后校验脚本。写完 HTML 后运行它检查外部 CSS/JS、普通表格圆角滚动容器与完整网格线、状态标签默认前景/背景、未渲染的 Markdown 行内代码、裸 `<pre><code>`、`.code-wrap`、静态高亮 token/inline style、token CSS 样式、复制按钮、viewport、响应式/打印样式、每文件独立 diff viewer 结构/CSS、可整体收起的目录侧栏结构，以及已出现图片/视频的相对路径、alt、controls 和响应式保护。
- `evals/evals.json`：html-report 的回归用例清单。只有评估或维护 skill 质量时读取，不参与普通报告生成；当前覆盖代码评审、问题排查、技术方案、聚焦 diff、多版本 Review Workspace、Android mock 验收、评论模式、既有知识文档结构保真和基础组件稳定性。

## 触发边界

### 适用

- 用户明确要求 HTML 输出、HTML 报告、写成 HTML 放到桌面，或调用 `/html-report`。
- 用户虽然没有说 HTML，但任务明显更适合独立可视化交付物：多章节长报告、代码评审报告、问题排查/修复方案、技术方案、方案对比、长结论归档，或包含 diff、表格、时间线、证据链等结构化内容。
- 其他 skill 已完成分析，并且用户或上游任务要求“报告文件”“交付物”“归档材料”，或上游判断 HTML 比对话 Markdown 更适合承载复杂结构。

### 不适用

- 用户只是要求“总结一下”“整理一下”“直接给我”“输出结论”，且内容较短或适合在对话里阅读。
- 用户明确要求不用 HTML、直接在对话里输出、只要 Markdown、只要命令行结果或只要简短结论。

### 需要确认

用户表达模糊，且无法判断他是要对话内阅读还是独立交付物时，先问一句“需要生成 HTML 报告还是直接输出 Markdown？”如果复杂度已经明显偏向交付物，或调用方已经明确要求 HTML，直接生成 HTML。

## 最短执行流程

1. 判断用户是否明确要求 HTML。
   - 明确要求 HTML 或调用 `/html-report`：直接生成 HTML。
   - 用户说已在 HTML 里完成批注、要求按批注更新：先读取 `references/annotation-mode.md` 并用 `--require-review-pack` 校验目标 HTML；通过后解析 `QA_EMBEDDED_REVIEW_START/END` 与 `#qaEmbeddedReviewData`，逐条处理 `annotations`。详细边界以该 reference 为准。
   - 明确要求终端输出或不用 HTML：直接输出 Markdown。
   - 模糊请求：内容简单用 Markdown；内容明显是复杂交付物时自动生成 HTML；无法判断时先确认。
2. 决定要生成 HTML 后，读取 `references/content-rules.md`，判断文档类型、目标读者和阅读任务，先拟一条适合材料的叙事主线与提纲。转换已有文档时优先保留已经清晰的宏观结构。
3. 如果报告属于技术方案、技术调研、问题排查/修复方案、代码评审、验收报告、选型对比或项目总结，读取 `references/artifact-patterns.md`，用对应清单检查必要内容是否齐全；不要逐项复制为章节，可以改名、排序、合并或省略不适用项。
4. 读取 `references/visual-rules.md`，选择必要的视觉结构和交互。保持克制，不为装饰添加复杂交互。
5. 报告需要复杂技术架构图、流程图、状态图或模块关系图时，读取 `../svg-tech-diagram/SKILL.md` 及其相关 references，生成可内联 SVG；该图必须先渲染 PNG 并完成自审，再嵌入 HTML。
6. 代码评审需要多文件、2 到 3 版本完整源码审阅，或用户明确要求 Workspace / 审阅台时，读取 `references/review-workspace.md`，准备源码快照和 JSON 规格，再用 `scripts/build_review_workspace.py` 生成组件；Workspace 放在 Findings / 改动概览之后，不能替代真实 unified diff。
7. 报告包含代码、SQL、XML、JSON、配置片段、shell 命令或 diff 时，先用 `scripts/highlight_code.py` 生成高亮 HTML 片段，再嵌入报告；不要手写裸 `<pre><code>`。多文件 unified diff 直接把完整 patch 交给 `--diff-view`，由脚本自动拆成每文件一张卡片，不要把脚本输出重新合并。
8. 写 HTML 时读取 `references/css-template.md` 和实际使用组件在 `references/component-contracts.md` 中的章节。先完成语义正文，再执行 `python3 skills/html-report/scripts/assemble_report.py <source-html> -o <final-html>`；普通表格、IDE 跳转、图片灯箱、目录、Tabs 和排序结构必须遵守组件契约。
9. 如果用户要求离线评论模式（包括旧称“审核模式”）或希望把 HTML 中的意见交给 Agent，先装配并运行基础校验，再读取 `references/annotation-mode.md`，执行 `python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>` 注入评论模式。评论完成后由页面的 `保存评论结果到 HTML` 把结构化批注直接内嵌回单文件。
   - 如果用户说已经在 HTML 中完成批注并要求更新，先执行 `check_html_report.py <html-file> --require-review-pack`；缺包、坏包或多包时停止修改并请用户重新保存正确评论版，不能静默当作零批注。
10. 完成前运行 `python3 skills/html-report/scripts/check_html_report.py <html-file>`；若失败，修正 HTML 后重跑直到通过。
11. 完成后只回复文件路径和一句话概要，不复述报告全文。

## 输出契约

- 生成单文件 `.html`，CSS 和 JS 内嵌在 `<style>` / `<script>` 中，不依赖外部 CSS、JS 或 CDN；图表优先使用表格、内联 SVG 或生成期静态内容。复杂技术图优先由 `svg-tech-diagram` 生成并自审后内联。
- 图片/视频证据是可选能力，不是所有报告的强制结构；需要展示截图、录屏或关键帧时，默认用相对路径引用同目录 `evidence_YYYYMMDD/` 资源，小图可选 base64，视频不建议 base64。
- 用户没有指定路径时，默认输出到桌面。
- 文件名表意，例如 `review_report.html`、`rate_limiter_explainer.html`。
- 评论模式只在用户明确需要时加入。评论版 HTML 必须以内嵌 `AgentQuestionPack` 的 `保存评论结果到 HTML` 为主操作，并保留 Markdown 兜底；独立 `下载 JSON` 不再作为用户入口。
- 评论版内嵌包必须包含原 HTML 的文件名、绝对路径和 `file://` URL，使用唯一 `#qaEmbeddedReviewData[data-qa-review-data]` 节点和 `QA_EMBEDDED_REVIEW_START/END` 标记，避免 Agent 或子 Agent 丢失上下文。
- 用户声明已完成批注时，必须用 `--require-review-pack` 校验交接文件；合法空数组表示明确的空评论结果，缺少、损坏或重复的包则是阻塞错误。
- 评论版必须内置 `导出无批注版`；对外发布版要物理剥离批注 UI、批注 JS、批注高亮、`data-block-id` 和内嵌评论包，不能泄露内部意见或本地路径。
- 判断为正式技术/业务文档或分析报告时，必须加文档抬头；普通对话转 HTML 不强制加。
- 报告内容必须来自用户内容或可靠上下文，不编造仓库、负责人、日期、卡片号、上线计划或收益数据。
- 代码高亮、长文档目录、响应式和打印细节按 `references/visual-rules.md`、`references/css-template.md` 和 `references/component-contracts.md` 执行；最终必须通过 `scripts/check_html_report.py`。
- 多版本 Review Workspace 只在完整源码关系确实影响判断时加入，限制为 2 到 3 个版本；数据必须由 `build_review_workspace.py` 做行号校验、静态高亮和 raw-text 安全转义。
- 普通表格必须放进带统一圆角裁切的 `.table-wrap`，表头和单元格显示完整 1px 网格线；只画横向底线不算合格。Diff viewer 自带 `.diff-table` 专用样式，不继承普通表格网格线。
- 源码定位链接默认只显示 `文件名:起始行-结束行`；同名文件最多增加一级父目录。`href` 和 `title` 保留完整路径及起始行，禁止把完整仓库路径直接铺在正文中。
- 媒体证据图片必须以原图链接作为无 JS 回退，并通过 `image-lightbox` 组件支持点击放大；视频继续使用原生 controls，不进入图片灯箱。

## 核心原则

- HTML 的价值是可视化表达力，不是花哨交互。
- Review Workspace 服务于跨文件、跨版本审阅；Findings、真实 patch 和测试结论仍然是代码评审报告的主线。
- 评论交接的默认载体仍是同一个 HTML 文件；`localStorage` 只负责编辑期暂存，不能作为 Agent 看不到的唯一数据源。
- 先保证内容完整和阅读主线清晰，再选择页面组件；不要让模板反过来决定文章结构。
- 首屏要让读者知道文档解决什么问题、该如何阅读。决策、评审、排查和验收类优先给结论；教程、前序知识和概念讲解可先给阅读地图，不强插重复的 TL;DR。
- 颜色、卡片、表格、目录、折叠都服务于阅读和定位；状态标签必须同时定义可读的默认前景与背景，不能只依赖可选变体类提供背景色。
- 代码块必须先转义再高亮，使用 `scripts/highlight_code.py` 生成静态 HTML；如果脚本语言参数不匹配，先换用受支持语言或修正脚本，不要降级成交付未高亮代码块。
- 支持语言和常见别名以 `python3 skills/html-report/scripts/highlight_code.py --list-langs` 输出为准；不要在 references 或校验脚本里维护第二份完整语言清单。
- 使用 `tok-*` class 的 builtin 高亮时，最终 HTML 必须由装配器加入 `code-block` 组件的 `.tok-*` 样式；缺少 token CSS 会导致代码实际无高亮。
- Markdown 来源中的反引号行内代码必须渲染成 `<code>...</code>`，例如 `` `d` `` 或 `` `support_full_screen` `` 不能作为原始反引号文本留在 HTML 正文里。
- 涉及代码新增、删除或修改时，必须用清晰的变更标识说明每处是新增、删除、修改还是上下文；真实 unified diff 必须用 `scripts/highlight_code.py --lang diff --diff-view` 生成 `.diff-card.diff-viewer`，并原样嵌入输出片段，不要手写 diff 表格、不要拆成普通 `<pre>`、不要把 diff 降级成 `language-diff` 或 `language-text` 代码块。输入包含多个文件时，脚本必须输出每文件一个带 `.diff-file` 标题的卡片。
- 宽表格、代码块、ASCII 图和长路径必须在窄屏/分屏下可横向滚动或换行，不允许把正文撑出视口。
- IDE 文件定位链接使用短标签，完整路径只放在 `href` 和 `title`；没有绝对路径时保留不可点击的短路径文本，不编造跳转。
- 如果用户指定其他视觉风格，以用户的新要求为准。
