---
name: html2md
version: 0.1.0
tags: [html, markdown, conversion]
description: HTML 转 Markdown 助手。当用户要求“HTML 转 MD/Markdown”“html2md”“把 .html 输出成 .md”“file://... 输出成 md”“网页/HTML 报告转 Markdown”时触发；优先使用 bundled script 做确定性转换并抽样校验结构，不要手工整篇重写。
user_invocable: true
---

# HTML2MD

把本地 HTML 文件或用户提供的 HTML 内容转换成 Markdown。适合把技术方案页、HTML 报告、浏览器保存的页面、单文件 HTML 文档转成可编辑的 `.md`。

## 触发边界

### 适用

- 用户给出 `.html` 路径、`file://` URL，或粘贴 HTML，并要求输出 Markdown / `.md`。
- 用户说“html2md”“HTML 转 MD”“输出成 md”“把这个 HTML 报告转 Markdown”。
- 需要保留标题、段落、列表、表格、链接、代码块、diff 表格等结构。

### 不适用

- 用户要求生成 HTML 报告：使用 `html-report`。
- 用户只是总结 HTML 内容，而不是要求转换格式：直接总结即可。
- 远程网页抓取需要登录态或浏览器交互：先按浏览器/Chrome 相关能力获取页面内容，再把保存后的本地 HTML 交给本 skill。

### 需要确认

- 用户没有给输入文件，也没有粘贴 HTML 内容。
- 输出文件已存在且用户没有明确表示可以覆盖；若是“把 X 转成 md”这类直接转换请求，可默认覆盖同名 `.md`。

## 默认流程

1. 定位输入：
   - `file://...` 先解码成绝对路径。
   - 普通路径按当前工作目录或用户提供的绝对路径解析。
   - 粘贴 HTML 时，先保存到 `/private/tmp/<meaningful-name>.html`。
2. 决定输出路径：
   - 用户指定输出路径时按指定路径。
   - 未指定时输出到输入文件同目录，文件名改为 `.md`。
3. 运行脚本：

```bash
python3 skills/html2md/scripts/html2md.py input.html output.md
```

4. 抽样校验：
   - `head -80 output.md` 看标题、正文和表格是否可读。
   - `rg -n '<(html|body|div|span|table|tr|td|th|pre|code|script|style)[ >]' output.md` 确认没有明显 HTML 结构标签残留。
   - `rg -n '^#|^```|^\|' output.md` 快速检查标题、代码块和表格。
5. 回复用户输出文件路径和校验结论，不复述全文。

## 转换原则

- 脚本优先，避免模型手工重排导致漏内容。
- 只做格式转换，不改写技术结论、字段名、代码和表格内容。
- 保留原文链接；`idea://open?...`、`file://...` 等本地链接不要改成普通文本。
- 对 HTML diff 表格，尽量转成 fenced `diff` 代码块。
- 对普通表格，使用 GitHub Flavored Markdown 表格。
- 如果脚本输出不理想，优先修脚本或做局部后处理，再重新跑转换。
