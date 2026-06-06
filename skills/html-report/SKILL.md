---
name: html-report
version: 0.2.17
tags:
  - report
  - html
  - output
description: 生成独立 HTML 报告文件。用户明确要求 HTML 输出（如“生成 HTML”“HTML 报告”“写成 HTML”“放到桌面”）或调用 `/htmlreport` 时必须触发；用户未明说 HTML，但任务明显更适合独立可视化交付物时，也应自动触发或由其他 skill 调用，例如多章节长报告、代码评审报告、问题排查/修复方案、技术方案、方案对比、包含 diff/表格/时间线/证据链的归档材料。普通简短的“总结一下”“整理一下”“直接给结论”默认用 Markdown，不触发。
---

# HTML 报告

当用户希望把分析结论、代码评审意见、问题清单、修复方案、技术方案或排查结果整理成一个独立 HTML 文件时，使用这个技能。默认生成一个可直接在浏览器打开的 `.html` 文件，通常放到桌面。

## Progressive Disclosure

SKILL.md 只保留触发、决策和执行路线。生成报告时按需要读取：

- `references/content-rules.md`：HTML vs Markdown 决策、文档类型、正式抬头、输出要求、写作规范、完成前检查。
- `references/artifact-patterns.md`：按报告类型选择结构模板。当前只覆盖技术方案和技术调研两个高频场景，其他场景先按通用报告规则处理。
- `references/visual-rules.md`：视觉原则、变更标识、文件定位链接、目录导航、ASCII/代码块、交互组件、场景速查。
- `references/css-template.md`：CSS 模板、交互组件样式、可整体收起的浮动目录侧栏、复制按钮 JS 和 HTML 骨架。只有开始写 HTML 文件时再读取。
- `scripts/highlight_code.py`：代码片段 HTML 转义和基础高亮脚本。报告包含代码、SQL、XML、JSON、配置片段、shell 命令或 diff 时必须用它生成可嵌入的 `.code-wrap` 片段；默认使用零依赖 `builtin` 引擎，需要更好语法覆盖时可用 `--engine auto` 尝试本机 Pygments 静态预渲染；Pygments 缺失时不要自动安装，只有用户明确要求增强高亮/安装依赖时才征得确认后安装；展示 unified diff 修改点时使用 `--diff-view`。
- `scripts/check_html_report.py`：生成后校验脚本。写完 HTML 后运行它检查外部 CSS/JS、裸 `<pre><code>`、`.code-wrap`、静态高亮 token/inline style、复制按钮、viewport、响应式/打印样式和可整体收起的目录侧栏结构。

## 触发边界

### 适用

- 用户明确要求 HTML 输出、HTML 报告、写成 HTML 放到桌面，或调用 `/htmlreport`。
- 用户虽然没有说 HTML，但任务明显更适合独立可视化交付物：多章节长报告、代码评审报告、问题排查/修复方案、技术方案、方案对比、长结论归档，或包含 diff、表格、时间线、证据链等结构化内容。
- 其他 skill 已完成分析，并且用户或上游任务要求“报告文件”“交付物”“归档材料”，或上游判断 HTML 比对话 Markdown 更适合承载复杂结构。

### 不适用

- 用户只是要求“总结一下”“整理一下”“直接给我”“输出结论”，且内容较短或适合在对话里阅读。
- 用户明确要求不用 HTML、直接在对话里输出、只要 Markdown、只要命令行结果或只要简短结论。

### 需要确认

用户表达模糊，且无法判断他是要对话内阅读还是独立交付物时，先问一句“需要生成 HTML 报告还是直接输出 Markdown？”如果复杂度已经明显偏向交付物，或调用方已经明确要求 HTML，直接生成 HTML。

## 最短执行流程

1. 判断用户是否明确要求 HTML。
   - 明确要求 HTML 或调用 `/htmlreport`：直接生成 HTML。
   - 明确要求终端输出或不用 HTML：直接输出 Markdown。
   - 模糊请求：内容简单用 Markdown；内容明显是复杂交付物时自动生成 HTML；无法判断时先确认。
2. 决定要生成 HTML 后，读取 `references/content-rules.md`，判断正式技术/业务文档、分析报告或普通对话转 HTML。
3. 如果报告属于技术方案、技术调研、问题排查或修复方案，读取 `references/artifact-patterns.md`，选择对应结构。
4. 读取 `references/visual-rules.md`，选择必要的视觉结构和交互。保持克制，不为装饰添加复杂交互。
5. 报告包含代码、SQL、XML、JSON、配置片段、shell 命令或 diff 时，先用 `scripts/highlight_code.py` 生成高亮 HTML 片段，再嵌入报告；不要手写裸 `<pre><code>`。
6. 写 HTML 文件前读取 `references/css-template.md`，使用内嵌 CSS/JS 生成单文件 HTML；长文档目录必须默认展开，并能点击按钮收起/展开整个目录侧栏。
7. 完成前运行 `python3 skills/html-report/scripts/check_html_report.py <html-file>`；若失败，修正 HTML 后重跑直到通过。
8. 完成后只回复文件路径和一句话概要，不复述报告全文。

## 可选依赖策略

- 保持轻量优先：生成报告时默认使用 `--engine builtin`，不联网、不安装依赖。
- `--engine auto` 只探测当前环境已有的 Pygments 模块或 `pygmentize` CLI；没有就自动回退 builtin。
- 不要在报告生成流程里静默安装依赖。只有用户明确要求“安装 Pygments”“启用增强高亮”或同意安装时，才执行安装命令。
- Homebrew Python 遇到 PEP 668 时，优先使用用户级安装：`python3 -m pip install --user --break-system-packages Pygments`；不要用会修改系统 Python 或全局 site-packages 的安装方式。

## 输出契约

- 生成单文件 `.html`，CSS 和 JS 内嵌在 `<style>` / `<script>` 中，不依赖外部文件（CDN 图表库除外）。
- 用户没有指定路径时，默认输出到桌面。
- 文件名表意，例如 `review_report.html`、`rate_limiter_explainer.html`。
- 判断为正式技术/业务文档或分析报告时，必须加文档抬头；普通对话转 HTML 不强制加。
- 报告内容必须来自用户内容或可靠上下文，不编造仓库、负责人、日期、卡片号、上线计划或收益数据。
- 代码高亮必须是离线单文件方案：默认使用 `scripts/highlight_code.py` 的 `builtin` 引擎做静态预高亮；如果本机安装了 Pygments，可用 `--engine auto` 或 `--engine pygments` 生成更准确的静态 HTML；如果没有安装，保持 builtin 回退，除非用户明确要求安装；最终报告不得引入 highlight.js、Prism、Shiki CDN 或外部 CSS/JS 文件。
- 长文档目录沿用旧版浮动侧栏样式：使用 `.layout-with-toc` + `<aside class="toc">` + `.toc-title` + 直接锚点链接，并额外加入 `.toc-toggle` 按钮；默认展开，点击按钮切换 `.toc-collapsed` 来收起/展开整个目录侧栏，不要用 `<details class="toc-details">` 只折叠目录内部链接。窄屏/分屏下目录不能遮挡或挤出正文。

## 核心原则

- HTML 的价值是可视化表达力，不是花哨交互。
- 首屏给结论，详情和证据往下排。
- 颜色、卡片、表格、目录、折叠都服务于阅读和定位。
- 代码块必须先转义再高亮，使用 `scripts/highlight_code.py` 生成静态 HTML；如果脚本语言参数不匹配，先换用受支持语言或修正脚本，不要降级成交付未高亮代码块。
- 涉及代码新增、删除或修改时，必须用清晰的变更标识说明每处是新增、删除、修改还是上下文。
- 宽表格、代码块、ASCII 图和长路径必须在窄屏/分屏下可横向滚动或换行，不允许把正文撑出视口。
- 如果用户指定其他视觉风格，以用户的新要求为准。
