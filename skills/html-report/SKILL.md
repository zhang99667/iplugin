---
name: html-report
version: 0.2.8
tags:
  - report
  - html
  - output
description: HTML 报告生成助手，仅当用户明确要求“生成 HTML/HTML 报告/写成 HTML 放到桌面”或调用 /htmlreport 时触发。不要因普通“总结一下”“整理一下”“直接给我结论”触发；这类默认用 Markdown，除非内容复杂且用户确认要 HTML。
---

# HTML 报告

当用户希望把分析结论、代码评审意见、问题清单、修复方案、技术方案或排查结果整理成一个独立 HTML 文件时，使用这个技能。默认生成一个可直接在浏览器打开的 `.html` 文件，通常放到桌面。

## Progressive Disclosure

SKILL.md 只保留触发、决策和执行路线。生成报告时按需要读取：

- `references/content-rules.md`：HTML vs Markdown 决策、文档类型、正式抬头、输出要求、写作规范、完成前检查。
- `references/visual-rules.md`：视觉原则、变更标识、文件定位链接、目录导航、ASCII/代码块、交互组件、场景速查。
- `references/css-template.md`：CSS 模板、交互组件样式、复制按钮 JS 和 HTML 骨架。只有开始写 HTML 文件时再读取。

## 触发边界

### 适用

用户明确要求 HTML 输出、HTML 报告、写成 HTML 放到桌面，或调用 `/htmlreport`。适合代码评审报告、问题排查报告、技术方案、方案对比、长结论归档等需要可视化层级的内容。

### 不适用

用户只是要求“总结一下”“整理一下”“直接给我”“不用 HTML”“输出结论”，且内容较短或适合在对话里阅读时，不使用本技能，直接输出 Markdown。

### 需要确认

用户表达模糊但内容复杂、包含多章节/代码块/表格/多问题时，先问一句“需要生成 HTML 报告还是直接输出 Markdown？”除非调用方已经明确要求 HTML。

## 最短执行流程

1. 判断用户是否明确要求 HTML。
   - 明确要求 HTML 或调用 `/htmlreport`：直接生成 HTML。
   - 明确要求终端输出或不用 HTML：直接输出 Markdown。
   - 模糊请求：内容简单用 Markdown；内容复杂先确认输出格式。
2. 决定要生成 HTML 后，读取 `references/content-rules.md`，判断正式技术/业务文档、分析报告或普通对话转 HTML。
3. 读取 `references/visual-rules.md`，选择必要的视觉结构和交互。保持克制，不为装饰添加复杂交互。
4. 写 HTML 文件前读取 `references/css-template.md`，使用内嵌 CSS/JS 生成单文件 HTML。
5. 完成后只回复文件路径和一句话概要，不复述报告全文。

## 输出契约

- 生成单文件 `.html`，CSS 和 JS 内嵌在 `<style>` / `<script>` 中，不依赖外部文件（CDN 图表库除外）。
- 用户没有指定路径时，默认输出到桌面。
- 文件名表意，例如 `review_report.html`、`rate_limiter_explainer.html`。
- 判断为正式技术/业务文档或分析报告时，必须加文档抬头；普通对话转 HTML 不强制加。
- 报告内容必须来自用户内容或可靠上下文，不编造仓库、负责人、日期、卡片号、上线计划或收益数据。

## 核心原则

- HTML 的价值是可视化表达力，不是花哨交互。
- 首屏给结论，详情和证据往下排。
- 颜色、卡片、表格、目录、折叠都服务于阅读和定位。
- 代码块必须有可读层次；文件位置必须尽量可跳转。
- 涉及代码新增、删除或修改时，必须用清晰的变更标识说明每处是新增、删除、修改还是上下文。
- 如果用户指定其他视觉风格，以用户的新要求为准。
