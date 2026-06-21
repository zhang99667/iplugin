---
name: html-report
version: 0.3.0
tags:
  - report
  - html
  - output
description: 生成独立 HTML 报告文件，支持离线批注审核模式和可导出给 Agent 的 Markdown/JSON 提问包。用户明确要求 HTML 输出（如“生成 HTML”“HTML 报告”“写成 HTML”“放到桌面”）、HTML 内批注/审核/提问，或调用 `/html-report` 时必须触发；用户未明说 HTML，但任务明显更适合独立可视化交付物时，也应自动触发或由其他 skill 调用，例如多章节长报告、代码评审报告、问题排查/修复方案、技术方案、方案对比、包含 diff/表格/时间线/证据链的归档材料。普通简短的“总结一下”“整理一下”“直接给结论”默认用 Markdown，不触发。
---

# HTML 报告

当用户希望把分析结论、代码评审意见、问题清单、修复方案、技术方案或排查结果整理成一个独立 HTML 文件时，使用这个技能。默认生成一个可直接在浏览器打开的 `.html` 文件，通常放到桌面。

## Progressive Disclosure

SKILL.md 只保留触发、决策和执行路线。生成报告时按需要读取：

- `references/content-rules.md`：HTML vs Markdown 决策、文档类型、正式抬头、输出要求、写作规范、完成前检查。
- `references/artifact-patterns.md`：按报告类型选择结构模板。当前覆盖技术方案、技术调研、问题排查/修复方案三个高频场景，其他场景先按通用报告规则处理。
- `references/visual-rules.md`：视觉原则、变更标识、文件定位链接、目录导航、ASCII/代码块、交互组件、场景速查。
- `references/css-template.md`：CSS 模板、交互组件样式、可整体收起的浮动目录侧栏、复制按钮 JS 和 HTML 骨架。只有开始写 HTML 文件时再读取。
- `references/annotation-mode.md`：当用户要求离线批注、审核模式、Agent 提问包、HTML 内选中文本提问/批注或发布版导出时读取。
- `../svg-tech-diagram/SKILL.md`：当报告需要复杂技术架构图、流程图、状态图或模块关系图时读取；由它负责 SVG 图的信息结构、绘制、PNG 渲染自审和可内联交付。
- `scripts/highlight_code.py`：代码片段 HTML 转义和基础高亮脚本。报告包含代码、SQL、XML、JSON、配置片段、shell 命令或 diff 时必须用它生成可嵌入的 `.code-wrap` 片段；默认使用零依赖 `builtin` 引擎，复杂代码可用 `--engine auto` 尝试本机 Pygments 静态预渲染，不能静默安装依赖；展示 unified diff 修改点时使用 `--diff-view`。
- `scripts/inject_annotation_mode.py`：当需要审核批注模式时，在基础 HTML 通过常规校验后运行它注入稳定的离线批注 UI、Markdown/JSON 提问包导出和“导出发布版”能力；不要手写批注 JS。
- `scripts/check_html_report.py`：生成后校验脚本。写完 HTML 后运行它检查外部 CSS/JS、未渲染的 Markdown 行内代码、裸 `<pre><code>`、`.code-wrap`、静态高亮 token/inline style、token CSS 样式、复制按钮、viewport、响应式/打印样式、稳定 diff viewer 和可整体收起的目录侧栏结构。

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
   - 明确要求终端输出或不用 HTML：直接输出 Markdown。
   - 模糊请求：内容简单用 Markdown；内容明显是复杂交付物时自动生成 HTML；无法判断时先确认。
2. 决定要生成 HTML 后，读取 `references/content-rules.md`，判断正式技术/业务文档、分析报告或普通对话转 HTML。
3. 如果报告属于技术方案、技术调研、问题排查或修复方案，读取 `references/artifact-patterns.md`，选择对应结构。
4. 读取 `references/visual-rules.md`，选择必要的视觉结构和交互。保持克制，不为装饰添加复杂交互。
5. 报告需要复杂技术架构图、流程图、状态图或模块关系图时，读取 `../svg-tech-diagram/SKILL.md` 及其相关 references，生成可内联 SVG；该图必须先渲染 PNG 并完成自审，再嵌入 HTML。
6. 报告包含代码、SQL、XML、JSON、配置片段、shell 命令或 diff 时，先用 `scripts/highlight_code.py` 生成高亮 HTML 片段，再嵌入报告；不要手写裸 `<pre><code>`。
7. 写 HTML 文件前读取 `references/css-template.md`，使用内嵌 CSS/JS 生成单文件 HTML；长文档目录必须默认展开，并能点击按钮收起/展开整个目录侧栏。
8. 如果用户要求离线批注、审核模式或希望把 HTML 中的疑问导出给 Agent，先运行基础校验，再读取 `references/annotation-mode.md`，执行 `python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>` 注入审核模式。
9. 完成前运行 `python3 skills/html-report/scripts/check_html_report.py <html-file>`；若失败，修正 HTML 后重跑直到通过。
10. 完成后只回复文件路径和一句话概要，不复述报告全文。

## 输出契约

- 生成单文件 `.html`，CSS 和 JS 内嵌在 `<style>` / `<script>` 中，不依赖外部 CSS、JS 或 CDN；图表优先使用表格、内联 SVG 或生成期静态内容。复杂技术图优先由 `svg-tech-diagram` 生成并自审后内联。
- 用户没有指定路径时，默认输出到桌面。
- 文件名表意，例如 `review_report.html`、`rate_limiter_explainer.html`。
- 批注审核模式只在用户明确需要时加入。审核版 HTML 必须内置“导出发布版”，发布版要物理剥离批注 UI、批注 JS、批注高亮和本地批注数据入口。
- 批注导出的 Markdown/JSON 必须包含原 HTML 的文件名、绝对路径和 `file://` URL，避免交给 Agent 或子 Agent 后丢失上下文。
- 判断为正式技术/业务文档或分析报告时，必须加文档抬头；普通对话转 HTML 不强制加。
- 报告内容必须来自用户内容或可靠上下文，不编造仓库、负责人、日期、卡片号、上线计划或收益数据。
- 代码高亮、长文档目录、响应式和打印样式的细节按 `references/visual-rules.md` 与 `references/css-template.md` 执行；最终必须通过 `scripts/check_html_report.py`。

## 核心原则

- HTML 的价值是可视化表达力，不是花哨交互。
- 首屏给结论，详情和证据往下排。
- 颜色、卡片、表格、目录、折叠都服务于阅读和定位。
- 代码块必须先转义再高亮，使用 `scripts/highlight_code.py` 生成静态 HTML；如果脚本语言参数不匹配，先换用受支持语言或修正脚本，不要降级成交付未高亮代码块。
- 使用 `tok-*` class 的 builtin 高亮时，最终 HTML 的 `<style>` 必须包含对应 `.tok-*` 样式；缺少 token CSS 会导致代码实际无高亮。
- Markdown 来源中的反引号行内代码必须渲染成 `<code>...</code>`，例如 `` `d` `` 或 `` `support_full_screen` `` 不能作为原始反引号文本留在 HTML 正文里。
- 涉及代码新增、删除或修改时，必须用清晰的变更标识说明每处是新增、删除、修改还是上下文；真实 unified diff 必须用 `scripts/highlight_code.py --lang diff --diff-view` 生成 `.diff-card.diff-viewer`，不要手写 diff 表格或使用普通 `language-diff` 代码块。
- 宽表格、代码块、ASCII 图和长路径必须在窄屏/分屏下可横向滚动或换行，不允许把正文撑出视口。
- 如果用户指定其他视觉风格，以用户的新要求为准。
