# HTML 报告 CSS 组件装配

本文件只维护生成 HTML 时的装配规则、脚本片段和骨架。CSS 源码按组件拆在 `references/css/` 下，生成最终报告时必须把需要的 CSS 内容复制进同一个 `<style>`，不要在交付 HTML 里使用 `<link>`、CDN 或外部 CSS 文件。

---

## 1. CSS 组件清单

默认内联顺序：

1. `references/css/base.css`：所有报告必选。提供页面、卡片、正式抬头、路径 chip、行内 `<code>`、基础响应式和打印兜底。
2. `references/css/interactions.css`：默认加入。提供 `<details>` 折叠区和 toast 反馈。
3. `references/css/code-diff.css`：报告包含多行代码、日志、SQL、XML、JSON、配置、shell、ASCII 图或真实 unified diff 时加入。它提供 `.code-wrap`、复制按钮、`tok-*`、`.ascii-diagram` 和 `.diff-card.diff-viewer`。
4. `references/css/media.css`：报告展示截图、录屏、关键帧或证据图片时加入。
5. `references/css/diagram.css`：报告内联 SVG 技术图，或使用 `.diagram-block` 承载宽架构图时加入。
6. `references/css/toc.css`：长文档需要左侧目录并支持整体收起时加入。
7. `references/css/tabs.css`：只有 2 到 3 个并列视角需要标签页时加入。
8. `references/css/sortable-table.css`：5 行以上数据表需要点击表头排序时加入。

选择组件时保持按需：不要因为组件存在就全部塞进报告。`base.css` 与 `interactions.css` 是默认组合；其他组件由内容决定。

## 2. 代码与 diff 组件规则

多行代码、日志和真实 diff 的 HTML 片段必须由 `scripts/highlight_code.py` 生成：

```bash
python3 skills/html-report/scripts/highlight_code.py --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang objc view_controller.m
python3 skills/html-report/scripts/highlight_code.py --lang swift view_model.swift
python3 skills/html-report/scripts/highlight_code.py --lang sql query.sql
python3 skills/html-report/scripts/highlight_code.py --lang json payload.json
python3 skills/html-report/scripts/highlight_code.py --engine auto --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang diff --diff-view patch.diff
```

脚本默认输出可直接嵌入正文的 `.code-wrap` 片段，并使用 `tok-*` class 做基础语法高亮。真实 unified diff 必须使用 `--diff-view` 输出 `.diff-card.diff-viewer`，把脚本输出的 `<section class="diff-card diff-viewer">...</section>` 原样嵌入正文，不要再包成 `.code-wrap`。

如果使用 `tok-*` class，最终 `<style>` 必须包含 `references/css/code-diff.css`；缺失时 `check_html_report.py` 会报 token CSS 或 diff viewer CSS 错误。

## 3. HTML 骨架

正式技术/业务文档或分析报告需要在 `<main>` 最前面加入 `.doc-header`。普通对话转 HTML 可以省略 `.doc-header`，直接使用 `<h1>` 和整理时间。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>报告标题</title>
  <style>
    {{ inline references/css/base.css }}
    {{ inline references/css/interactions.css }}
    {{ inline references/css/code-diff.css when report has code/log/diff/ascii }}
    {{ inline references/css/media.css when report has image/video evidence }}
    {{ inline references/css/diagram.css when report has SVG diagram block }}
    {{ inline references/css/toc.css when report has left TOC }}
    {{ inline references/css/tabs.css when report has tabs }}
    {{ inline references/css/sortable-table.css when report has sortable table }}
  </style>
</head>
<body>

<div id="toast" class="toast">已复制到剪贴板</div>

<main>
  <header class="doc-header">
    <h1>文档标题</h1>
    <p class="doc-subtitle">一句话说明文档主题、交付目的或核心结论。</p>
    <div class="doc-meta">
      <span class="doc-chip">文档类型</span>
      <span class="doc-chip">任务号</span>
      <span class="doc-chip">仓库/分支</span>
      <span class="doc-chip">负责人</span>
      <span class="doc-chip">更新时间</span>
    </div>
  </header>

  <p class="muted">整理时间：YYYY-MM-DD。行号基于当前本地源码定位，若行号有偏移以文件路径和代码上下文为准。</p>

  <section class="summary">
    <h2>最终结论</h2>
    <p>用 1-2 段概括根因、结论或整体风险。</p>
    <div class="grid">
      <div class="mini"><span class="tag p0">P0</span> <b>问题标题</b><br/>一句话说明影响。</div>
    </div>
  </section>

  <h2>问题 1：问题标题</h2>
  <section class="issue">
    <h3><span class="tag p0">P0</span> 问题说明</h3>
    <div class="meta">
      <a class="path file-link" href="idea://open?file=/absolute/or/repo/path/File.kt&amp;line=123" title="/absolute/or/repo/path/File.kt:123-145">repo/path/File.kt:123-145</a>
    </div>
    <p><b>问题：</b>说明当前代码行为。</p>
    <p><b>影响：</b>说明业务、稳定性或性能影响。</p>
    <p><b>当前代码：</b></p>
    {{ insert output from highlight_code.py }}
    <p><b>修复方案：</b>说明最小、安全的改法。</p>
  </section>

  <details>
    <summary>相关日志（点击展开）</summary>
    <div class="details-body">
      {{ insert output from highlight_code.py --lang text log.txt }}
    </div>
  </details>

  <h2>建议修复顺序</h2>
  <section class="summary">
    <ol>
      <li><b>P0 先修：</b>...</li>
    </ol>
  </section>
</main>

<script>
  {{ include copy button JS when code-diff.css is used }}
  {{ include TOC toggle JS when toc.css is used }}
  {{ include sortable table JS when sortable-table.css is used }}
</script>
</body>
</html>
```

## 4. 媒体证据结构

当报告需要展示截图、录屏或关键帧时，加入 `references/css/media.css`。默认使用相对路径引用同目录证据资源，例如 `evidence_20260625/login_case.png`。小图可以按需使用 `data:image/...;base64,...` 内嵌，大图和 MP4 不建议 base64。

```html
<figure class="media-evidence" data-case="case-01" data-conclusion="修复后按钮不再遮挡正文">
  <div class="media-frame">
    <img src="evidence_20260625/case_01_after.png" alt="case-01 修复后按钮不再遮挡正文的截图">
  </div>
  <figcaption class="media-caption">
    <span class="media-caption-title">case-01 修复后截图</span>
    <span>说明：按钮、正文和底部操作区在窄屏下保持单列布局。</span>
    <span class="media-meta">
      <span>case: case-01</span>
      <span>结论: 通过</span>
    </span>
  </figcaption>
</figure>
```

录屏保留可播放预览和原文件链接；同时建议放一张关键帧截图，让读者不播放也能理解证据内容：

```html
<figure class="media-evidence" data-case="case-02" data-conclusion="录屏显示横竖屏切换无布局溢出">
  <div class="media-frame">
    <img src="evidence_20260625/case_02_keyframe.png" alt="case-02 录屏关键帧截图">
  </div>
  <div class="media-frame">
    <video controls preload="metadata" poster="evidence_20260625/case_02_keyframe.png">
      <source src="evidence_20260625/case_02_recording.mp4" type="video/mp4">
    </video>
  </div>
  <figcaption class="media-caption">
    <span class="media-caption-title">case-02 横竖屏切换录屏</span>
    <span>说明：关键帧用于快速扫读，视频用于复核完整操作过程。</span>
    <span class="media-meta">
      <span>case: case-02</span>
      <span>结论: 无横向撑破</span>
      <a class="media-link" href="evidence_20260625/case_02_recording.mp4">打开原始录屏</a>
    </span>
  </figcaption>
</figure>
```

## 5. 左侧目录结构

长文档加入 `references/css/toc.css`。目录必须默认展开，读者点击按钮时切换 `.toc-collapsed`，收起/展开整个目录侧栏。不要把目录包进 `<details>`。

```html
<div class="layout-with-toc">
  <aside class="toc" aria-label="目录">
    <div class="toc-header">
      <p class="toc-title">目录</p>
      <button class="toc-toggle" type="button" aria-label="收起目录" aria-expanded="true" title="收起目录">
        <span class="toc-toggle-icon" aria-hidden="true">‹</span>
      </button>
    </div>
    <a href="#summary">最终结论</a>
    <a href="#issue-1">问题 1：问题标题</a>
    <a href="#fix-order">建议修复顺序</a>
  </aside>
  <main>
    <section id="summary" class="summary">...</section>
    <h2 id="issue-1">问题 1：问题标题</h2>
    <h2 id="fix-order">建议修复顺序</h2>
  </main>
</div>
```

## 6. 标签页结构

只有报告天然有 2 到 3 个并列视角时加入 `references/css/tabs.css`。一个视角不要用标签页。

```html
<input type="radio" name="tab" class="tab-radio" id="tab1" checked />
<input type="radio" name="tab" class="tab-radio" id="tab2" />
<div class="tabs">
  <label for="tab1" class="tab-label">问题清单</label>
  <label for="tab2" class="tab-label">修复方案</label>
</div>
<div class="tab-content">
  <div class="tab-panel" id="panel1">...</div>
  <div class="tab-panel" id="panel2">...</div>
</div>
```

## 7. 脚本片段

### 7.1 复制按钮

仅当报告使用 `references/css/code-diff.css` 且存在 `.copy-btn` 时加入。

```html
<script>
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.closest('.code-wrap').querySelector('pre').innerText;
      navigator.clipboard.writeText(code).then(() => {
        btn.textContent = '已复制';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '复制'; btn.classList.remove('copied'); }, 1500);
      });
    });
  });
</script>
```

### 7.2 目录侧栏收起

仅当报告使用 `references/css/toc.css` 时加入。

```html
<script>
  document.querySelectorAll('.layout-with-toc').forEach(layout => {
    const btn = layout.querySelector('.toc-toggle');
    if (!btn) return;
    const icon = btn.querySelector('.toc-toggle-icon');
    const setCollapsed = collapsed => {
      layout.classList.toggle('toc-collapsed', collapsed);
      btn.setAttribute('aria-expanded', String(!collapsed));
      btn.setAttribute('aria-label', collapsed ? '展开目录' : '收起目录');
      btn.title = collapsed ? '展开目录' : '收起目录';
      if (icon) icon.textContent = collapsed ? '›' : '‹';
    };
    btn.addEventListener('click', () => {
      setCollapsed(!layout.classList.contains('toc-collapsed'));
    });
  });
</script>
```

### 7.3 可排序表格

5 行以上数据表才加入 `references/css/sortable-table.css` 和这段 JS。3 到 4 行的迷你表不需要排序。

```html
<script>
  document.querySelectorAll('.sortable th').forEach((th, colIdx) => {
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const tbody = table.querySelector('tbody');
      const rows = [...tbody.querySelectorAll('tr')];
      const asc = th.dataset.sort !== 'asc';
      table.querySelectorAll('th').forEach(h => { delete h.dataset.sort; });
      th.dataset.sort = asc ? 'asc' : 'desc';
      rows.sort((a, b) => {
        const va = a.children[colIdx].innerText.trim();
        const vb = b.children[colIdx].innerText.trim();
        const na = parseFloat(va), nb = parseFloat(vb);
        if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      });
      th.querySelector('.sort-arrow').textContent = asc ? ' ▲' : ' ▼';
      rows.forEach(r => tbody.appendChild(r));
    });
  });
</script>
```

## 8. 完成前检查

- 最终 HTML 只有内联 `<style>` / `<script>`，没有外部 CSS、JS 或 CDN。
- 只内联内容实际需要的组件 CSS；不要把 `references/css/` 整包复制进所有报告。
- 代码、日志、ASCII 图或 diff 出现时，必须内联 `references/css/code-diff.css` 并使用 `scripts/highlight_code.py` 生成片段。
- 长文档目录必须使用 `references/css/toc.css` 的 `.layout-with-toc` / `.toc` / `.toc-toggle` 结构，默认展开，可整体收起。
- 完成后运行 `python3 skills/html-report/scripts/check_html_report.py <html-file>`，失败则修正后重跑。
