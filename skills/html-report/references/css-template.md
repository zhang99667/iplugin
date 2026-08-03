# HTML 报告组件装配

本文件只定义从语义 HTML 到离线单文件报告的装配流程。组件结构和依赖见
`references/component-contracts.md`，真实 CSS/JS 资产由
`assets/components/registry.json` 统一登记；不要手工复制资产或在文档里维护第二份 runtime。

## 1. 生成顺序

1. 先写语义化 HTML 正文，不手写组件 `<style>` 或 `<script>`。
2. 代码、日志和 diff 先用 `scripts/highlight_code.py` 生成片段。
3. 多版本完整源码审阅先用 `scripts/build_review_workspace.py` 生成片段。
4. 运行统一装配器，让它根据稳定 class/attribute 自动识别组件、展开依赖并内联资产：

   ```bash
   python3 skills/html-report/scripts/assemble_report.py report_source.html \
     -o report.html
   ```

5. 只有页面结构无法触发自动检测、但确实需要某个组件时才显式声明：

   ```bash
   python3 skills/html-report/scripts/assemble_report.py report_source.html \
     --component diagram \
     -o report.html
   ```

6. 完成后运行：

   ```bash
   python3 skills/html-report/scripts/check_html_report.py report.html
   ```

装配器默认加入 `base` 和 `interactions`，其余组件按内容加载。重复运行会替换自己管理的
CSS/JS 块并保持结果幂等。最终 HTML 仍只有内联 `<style>` / `<script>`，不依赖 CDN 或外部文件。

## 2. 语义骨架

正式技术、业务或分析报告在正文最前面使用 `.doc-header`。普通对话转 HTML 可以直接从
`<h1>` 开始。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>报告标题</title>
</head>
<body>
<main>
  <header class="doc-header">
    <h1>文档标题</h1>
    <p class="doc-subtitle">一句话说明主题、目的或核心结论。</p>
    <div class="doc-meta">
      <span class="doc-chip">文档类型</span>
      <span class="doc-chip">仓库/分支</span>
      <span class="doc-chip">更新时间</span>
    </div>
  </header>

  <section class="summary">
    <h2>最终结论</h2>
    <p>用一到两段概括结论和风险。</p>
  </section>

  <!-- 按内容插入 table、file-location、code-block、diff-viewer、media 等语义结构。 -->
</main>
</body>
</html>
```

不要编造任务号、负责人、仓库、分支或时间。没有可靠信息时省略相应 chip。

## 3. 自动检测与显式组件

装配器只根据注册表中的稳定 class/attribute 检测，不扫描正文关键词。例如：

- `.table-wrap` 触发 `table`。
- `.file-location` 触发 `file-location`。
- `.code-wrap` 触发 `code-block`。
- `.diff-viewer` 触发 `diff-viewer`，并自动带入 `code-block`。
- `.media-evidence` 触发 `media`；`.image-lightbox-trigger[data-image-lightbox]` 触发 `image-lightbox`。
- `.layout-with-toc` 触发 `toc`。
- `.report-tabs[data-tabs]` 触发 `tabs`。
- `table.sortable` 触发 `sortable-table`，并自动带入 `table`。
- `.review-workspace` 触发 `review-workspace`。

查看当前注册表：

```bash
python3 skills/html-report/scripts/assemble_report.py --list-components
```

`data-html-report-components` 和 `data-html-report-runtime` 是装配产物，不要手写。需要新增或
修改组件时按 `references/component-contracts.md` 的维护门禁同时更新注册表、资产和测试。

## 4. 复合模块顺序

Review Workspace 由自己的构建脚本输出正文结构、数据和唯一 runtime；统一装配器只补它的
依赖样式。多个 Workspace 时，第一个保留 runtime，后续使用 `--no-runtime`。

批注模式是报告完成后的后处理模块。先装配并通过基础校验，再运行
`scripts/inject_annotation_mode.py`；不要把批注模式拆成普通内容组件，也不要把它的资产登记到
页面组件注册表。

## 5. 完成前检查

- 普通表格使用 `.table-wrap > table`，所有 `th` / `td` 都有完整 1px 网格线。
- IDE 跳转使用 `.file-location.file-link`，短标签只显示文件名和行范围。
- 媒体证据图片包在原图链接中并启用 `data-image-lightbox`。
- 代码和真实 diff 由 `highlight_code.py` 生成，不手写高亮 token 或 diff 表格。
- Tabs、TOC、排序、灯箱在无 JS 时仍保留可读内容或原生链接回退。
- 最终运行 `check_html_report.py`；失败后修正并重跑。
