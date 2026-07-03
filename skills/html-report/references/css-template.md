# HTML 报告 CSS 模板

生成报告时使用以下样式和 JS。**默认只用基础样式 + 折叠 + 复制按钮**，其他组件仅在内容确实需要时才选入。本文件只提供样式和示例；代码片段由 `scripts/highlight_code.py` 生成，并由 `scripts/check_html_report.py` 校验。

---

## 1. 基础样式（所有报告必备）

```html
<style>
  :root {
    --bg: #f6f8fb;
    --card: #ffffff;
    --text: #1f2937;
    --muted: #6b7280;
    --border: #e5e7eb;
    --p0: #dc2626;
    --p1: #ea580c;
    --p2: #2563eb;
    --code-bg: #10231f;
    --code: #a9b5af;
    --accent: #3b82f6;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.65;
    overflow-x: hidden;
  }
  img, svg, canvas, video { max-width: 100%; height: auto; }
  main {
    width: min(100%, 1180px);
    max-width: 1180px;
    margin: 0 auto;
    padding: 32px 24px 56px;
  }
  h1 { margin: 0 0 8px; font-size: 30px; line-height: 1.25; }
  h2 {
    margin: 30px 0 14px; font-size: 22px;
    border-left: 5px solid var(--accent); padding-left: 10px;
  }
  h3 { margin: 0 0 10px; font-size: 18px; }
  p { margin: 8px 0; }
  .summary, .issue {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
    padding: 18px 20px;
    margin: 16px 0;
    min-width: 0;
  }
  .meta {
    display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px;
  }
  .tag {
    display: inline-block; border-radius: 999px; padding: 2px 10px;
    font-size: 12px; font-weight: 700; color: #fff;
  }
  .p0 { background: var(--p0); }
  .p1 { background: var(--p1); }
  .p2 { background: var(--p2); }
  .path {
    display: inline-block; background: #eef2ff; color: #3730a3;
    border-radius: 8px; padding: 2px 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px; max-width: 100%; box-sizing: border-box;
    word-break: normal; overflow-wrap: anywhere;
    text-decoration: none;
  }
  a.path.file-link {
    cursor: pointer;
    transition: background .15s, color .15s, box-shadow .15s;
  }
  a.path.file-link:hover {
    background: #e0e7ff;
    color: #312e81;
    box-shadow: inset 0 0 0 1px rgba(67, 56, 202, .18);
  }
  .muted { color: var(--muted); }
  .doc-header {
    margin-bottom: 18px;
    padding: 28px 30px;
    border-radius: 16px;
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 58%, #60a5fa 100%);
    color: #ffffff;
    box-shadow: 0 14px 32px rgba(37, 99, 235, .22);
  }
  .doc-header h1 {
    margin: 0 0 12px;
    font-size: 30px;
    line-height: 1.28;
  }
  .doc-subtitle {
    margin: 0 0 18px;
    color: rgba(255, 255, 255, .86);
    font-size: 15px;
  }
  .doc-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .doc-chip {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-height: 30px;
    padding: 3px 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, .15);
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.35;
    word-break: break-word;
  }
  ul { margin: 8px 0 8px 22px; padding: 0; }
  li { margin: 4px 0; }
  pre {
    max-width: 100%;
    margin: 10px 0 14px; padding: 14px 16px; overflow: auto;
    background: var(--code-bg); color: var(--code);
    border-radius: 12px; font-size: 13px; line-height: 1.5; tab-size: 4;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: #f1f5f9; color: #334155;
    border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 1px 5px; font-size: .92em; max-width: 100%;
    white-space: normal; overflow-wrap: anywhere; word-break: break-word;
    box-decoration-break: clone; -webkit-box-decoration-break: clone;
  }
  pre code {
    background: transparent; color: inherit; border: 0;
    border-radius: 0; padding: 0; font-size: inherit; white-space: pre;
    overflow-wrap: normal; word-break: normal;
  }
  .ascii-diagram {
    background: #f8fafc; color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre;
    overflow-x: auto;
  }
  .diagram-block {
    margin: 16px 0 18px;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #ffffff;
    overflow-x: auto;
    box-shadow: 0 6px 18px rgba(15, 23, 42, .04);
  }
  .diagram-block .tech-diagram {
    display: block;
    width: 100%;
    min-width: 720px;
    height: auto;
  }
  .diagram-block figcaption {
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
  }
  .media-evidence {
    margin: 16px 0 18px;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(15, 23, 42, .04);
  }
  .media-frame {
    overflow-x: auto;
    border: 1px solid #dbe3ef;
    border-radius: 12px;
    background: #0f172a;
  }
  .media-frame + .media-frame {
    margin-top: 10px;
  }
  .media-frame img,
  .media-frame video {
    display: block;
    width: 100%;
    max-width: 100%;
    height: auto;
    max-height: 72vh;
    object-fit: contain;
    background: #0f172a;
  }
  .media-caption {
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
  }
  .media-caption-title {
    display: block;
    margin-bottom: 4px;
    color: var(--text);
    font-weight: 800;
  }
  .media-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
  }
  .media-meta span,
  .media-link {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-height: 24px;
    padding: 2px 8px;
    border-radius: 8px;
    background: #f1f5f9;
    color: #475569;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }
  .media-link {
    color: #1d4ed8;
    text-decoration: none;
  }
  .media-link:hover {
    background: #dbeafe;
    color: #1e40af;
  }
  .code-wrap {
    position: relative;
    max-width: 100%;
    min-width: 0;
  }
  .code-wrap pre {
    padding-top: 38px;
    overflow-x: auto;
  }
  .tok-key { color: #d955a2; font-weight: 700; }
  .tok-str { color: #83b986; }
  .tok-num { color: #d7c96f; }
  .tok-cmt { color: #5f947d; font-style: italic; }
  .tok-fn { color: #6fa0ff; }
  .tok-var { color: #8f79bd; }
  .tok-type { color: #d2d66f; font-weight: 700; }
  .tok-add { color: #83b986; background: rgba(90, 137, 75, .18); display: inline-block; width: 100%; }
  .tok-del { color: #d955a2; background: rgba(139, 66, 86, .20); display: inline-block; width: 100%; }
  .change-chip {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.2;
    border: 1px solid transparent;
  }
  .change-add { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
  .change-del { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
  .change-mod { background: #fef3c7; color: #92400e; border-color: #fde68a; }
  .change-ctx { background: #e0f2fe; color: #075985; border-color: #bae6fd; }
  .diff-card {
    margin: 14px 0;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 6px 18px rgba(15, 23, 42, .05);
  }
  .diff-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: #f8fafc;
    border-bottom: 1px solid var(--border);
  }
  .diff-table {
    width: 100%;
    border-collapse: collapse;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    line-height: 1.45;
  }
  .diff-table td {
    padding: 0;
    border: 0;
    vertical-align: top;
  }
  .diff-gutter, .diff-num {
    width: 40px;
    min-width: 40px;
    user-select: none;
    text-align: right;
    color: #64748b;
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
  }
  .diff-gutter {
    width: 25px;
    min-width: 25px;
    text-align: center;
    font-weight: 800;
  }
  .diff-code {
    padding: 1px 12px;
    white-space: pre;
    overflow-x: auto;
  }
  .diff-add .diff-gutter, .diff-add .diff-code { background: #ecfdf5; color: #166534; }
  .diff-del .diff-gutter, .diff-del .diff-code { background: #fef2f2; color: #991b1b; }
  .diff-mod .diff-gutter, .diff-mod .diff-code { background: #fffbeb; color: #92400e; }
  .diff-context .diff-code { background: #ffffff; color: #334155; }
  .diff-scroll {
    overflow-x: auto;
  }
  .diff-viewer .diff-table {
    min-width: 100%;
  }
  .diff-viewer .diff-gutter {
    width: 25px;
    min-width: 25px;
    padding: 1px 0;
  }
  .diff-viewer .diff-num {
    width: 1%;
    min-width: 40px;
    padding: 1px 6px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .diff-viewer .diff-code {
    min-width: 0;
    padding: 2px 12px;
    color: #1e293b;
  }
  .diff-viewer .tok-key { color: #7c3aed; font-weight: 700; }
  .diff-viewer .tok-str { color: #047857; }
  .diff-viewer .tok-num { color: #a16207; }
  .diff-viewer .tok-cmt { color: #64748b; font-style: italic; }
  .diff-viewer .tok-fn { color: #2563eb; }
  .diff-viewer .tok-var { color: #6d28d9; }
  .diff-viewer .tok-type { color: #b45309; font-weight: 700; }
  .diff-viewer .diff-add .diff-gutter {
    border-left: 5px solid #16a34a;
  }
  .diff-viewer .diff-del .diff-gutter {
    border-left: 5px solid #dc2626;
  }
  .diff-viewer .diff-context .diff-gutter {
    border-left: 5px solid transparent;
  }
  .diff-viewer .diff-add .diff-num,
  .diff-viewer .diff-add .diff-code {
    background: #ecfdf3;
  }
  .diff-viewer .diff-del .diff-num,
  .diff-viewer .diff-del .diff-code {
    background: #fff1f2;
  }
  .diff-viewer .diff-hunk .diff-code,
  .diff-viewer .diff-meta .diff-code {
    background: #f8fafc;
    color: #64748b;
    font-weight: 700;
  }
  .diff-mark-add, ins {
    background: #bbf7d0;
    color: #14532d;
    text-decoration: none;
    border-radius: 3px;
    padding: 0 2px;
  }
  .diff-mark-del, del {
    background: #fecaca;
    color: #7f1d1d;
    text-decoration: line-through;
    border-radius: 3px;
    padding: 0 2px;
  }
  .change-block {
    margin: 12px 0;
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-left: 5px solid #38bdf8;
    border-radius: 12px;
    background: #ffffff;
  }
  .change-block.add { border-left-color: #22c55e; background: #f0fdf4; }
  .change-block.del { border-left-color: #ef4444; background: #fef2f2; }
  .change-block.mod { border-left-color: #f59e0b; background: #fffbeb; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
  }
  .grid > * { min-width: 0; }
  .mini {
    border: 1px solid var(--border); border-radius: 12px;
    padding: 12px 14px; background: #fbfdff;
  }
  .ok { color: #047857; font-weight: 700; }
  .warn { color: #b45309; font-weight: 700; }

  @media (max-width: 720px) {
    main { padding: 20px 14px 42px; }
    h1 { font-size: 24px; }
    h2 { font-size: 19px; }
    .summary, .issue { padding: 14px 14px; border-radius: 12px; }
    .doc-header { padding: 22px 18px; border-radius: 14px; }
    .doc-header h1 { font-size: 23px; }
    .doc-chip { font-size: 12px; }
    .diagram-block { padding: 10px; border-radius: 12px; }
    .diagram-block .tech-diagram { min-width: 640px; }
    .media-evidence { padding: 10px; border-radius: 12px; }
    .media-frame img,
    .media-frame video { max-height: 62vh; }
    .grid { grid-template-columns: 1fr; }
    .copy-btn { opacity: 1; }
  }

  @media print {
    body { background: #ffffff; color: #111827; }
    main, .layout-with-toc { width: 100%; max-width: none; padding: 0; }
    .summary, .issue, .toc, .doc-header {
      box-shadow: none;
      break-inside: avoid;
    }
    .doc-header {
      background: #ffffff;
      color: #111827;
      border: 1px solid #d1d5db;
    }
    .doc-subtitle, .muted { color: #374151; }
    .doc-chip {
      background: #f3f4f6;
      color: #111827;
      border: 1px solid #d1d5db;
    }
    .toc { position: static; max-height: none; }
    .copy-btn, .toast { display: none !important; }
    .diagram-block {
      box-shadow: none;
      break-inside: avoid;
    }
    .media-evidence {
      box-shadow: none;
      break-inside: avoid;
    }
    .diagram-block .tech-diagram {
      min-width: 0;
    }
    pre, .ascii-diagram {
      white-space: pre-wrap;
      overflow: visible;
      color: #111827;
      background: #f9fafb;
      border: 1px solid #d1d5db;
    }
    a { color: #111827; text-decoration: underline; }
  }
</style>
```

文件定位 chip 优先使用可跳转 IDEA 的链接，展示文本遵循 `{displayPath}:{line}`、`{displayPath}:{start}-{end}` 或 `{displayPath}:{line}:{column}`。这里由 HTML 结构驱动：先生成单个 `<a class="path file-link">`，CSS 只负责样式。必须把路径和行号放在同一个链接中，不要拆成 `.path` + `.line` 两个 chip，也不要把行号范围另起一行：

```html
<a class="path file-link" href="idea://open?file=/abs/path/File.java&amp;line=82&amp;column=7">/abs/path/File.java:82:7</a>
```

行号范围链接跳到起始行，展示保留完整范围；可用 `title` 放完整绝对路径，正文展示更短的仓库相对路径。超长路径可以在展示文本里用 `...` 省略中间目录，例如 `lib-ad-feed/.../UnitedSchemeADDispatcher.java:1350-1351`，但不能省略仓库/模块线索、文件名、行号或行号范围；同名文件可能混淆时，保留更多父级目录。不要额外生成独立的 `43-50` 或 `106-111` 行号 badge：

```html
<a class="path file-link" href="idea://open?file=/Users/markz/code/baidu/browser-android/searchbox-lite/repos/business/ad_business/flowvideo/src/main/java/com/baidu/searchbox/video/feedflow/ad/position/FlowVideoLandscapeHelper.kt&amp;line=43" title="/Users/markz/code/baidu/browser-android/searchbox-lite/repos/business/ad_business/flowvideo/src/main/java/com/baidu/searchbox/video/feedflow/ad/position/FlowVideoLandscapeHelper.kt:43-50">browser-android/searchbox-lite/.../FlowVideoLandscapeHelper.kt:43-50</a>
```

### 1.1 可选媒体证据块

当报告需要展示截图、录屏或关键帧时，可以使用 `.media-evidence`。这不是所有报告的必选结构；只在证据确实需要图片或视频时加入。默认使用相对路径引用同目录证据资源，例如 `evidence_20260625/login_case.png`。小图可以按需使用 `data:image/...;base64,...` 内嵌，大图和 MP4 不建议 base64，避免 HTML 膨胀。

截图示例：

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

录屏示例。视频保留可播放预览和原文件链接；同时建议放一张关键帧截图，让读者不播放也能理解证据内容：

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

---

## 2. 必备交互：折叠 + 复制（所有报告默认加入）

代码块必须通过脚本生成：

```bash
python3 skills/html-report/scripts/highlight_code.py --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang objc view_controller.m
python3 skills/html-report/scripts/highlight_code.py --lang swift view_model.swift
python3 skills/html-report/scripts/highlight_code.py --lang sql query.sql
python3 skills/html-report/scripts/highlight_code.py --lang json payload.json
python3 skills/html-report/scripts/highlight_code.py --engine auto --lang kotlin snippet.kt
python3 skills/html-report/scripts/highlight_code.py --lang diff --diff-view patch.diff
```

脚本默认输出可直接嵌入正文的 `.code-wrap` 片段，并使用上面的 `tok-*` class 做基础语法高亮。支持 `kotlin`、`java`、`objc`、`swift`、`c`、`cpp`、`go`、`rust`、`js`、`ts`、`python`、`ruby`、`php`、`xml`、`sql`、`json`、`yaml`、`toml`、`ini`、`markdown`、`bash`、`diff`、`text`，常见后缀/别名会映射到这些语言。Objective-C 可用 `objc`、`objective-c`、`.m`、`.mm`、`.h`，TypeScript 可用 `ts` / `typescript` / `.tsx`。常用映射：关键字 `tok-key`，字符串 `tok-str`，数字 `tok-num`，注释 `tok-cmt`，函数名 `tok-fn`，变量名 `tok-var`，类型名 `tok-type`。真实 unified diff 不使用普通 `.code-wrap language-diff`，必须走 `--diff-view`。

需要更准确语法覆盖时，使用 `--engine auto` 尝试本机 Pygments 静态预渲染；如果 Pygments 不可用，脚本会回退到 `builtin`。最终报告仍然只包含静态 HTML/CSS/JS，不引入 highlight.js、Prism、Shiki CDN 或外部文件。

展示修改点时必须使用 `--diff-view`，它会把 unified diff 渲染成 `.diff-card.diff-viewer`：带 old/new 行号、红绿整行背景、左侧变更轨道、hunk header，并根据 `---` / `+++` 文件路径后缀复用普通代码高亮逻辑给代码列生成 `tok-*` token。把脚本输出的 `<section class="diff-card diff-viewer">...</section>` 原样嵌入正文，不要再包成 `.code-wrap`、不要把行号列拆到外层，也不要把真实 diff 改成 `language-text` 代码块。脚本不可用时先修复并重试；确实无法运行时，才按本模板的 `.diff-card.diff-viewer` 结构手工补齐，且必须先转义 HTML。

涉及代码变更时，真实 diff 统一使用 `.diff-card.diff-viewer` + `.diff-table` 展示聚焦 diff。新增、删除、修改、上下文必须有不同视觉状态；行内 token 变化可使用 `<ins>` / `<del>` 或 `.diff-mark-add` / `.diff-mark-del`。不要生成没有 `.diff-viewer` 的手写 `.diff-card`。最终 HTML 的 `<style>` 必须保留上方完整 diff viewer CSS，尤其是 `.diff-header`、`.diff-scroll`、`.diff-viewer .diff-table`、`.diff-viewer .diff-gutter`、`.diff-viewer .diff-num`、`.diff-viewer .diff-code`、`.diff-viewer .diff-add/.diff-del` 和左侧红绿 `border-left` 轨道；行号列使用 `width: 1%; min-width: 40px; white-space: nowrap` 自适应内容宽度，`+/-` 轨道保持 25px，避免固定宽列挤占代码区。这些选择器或关键宽度缺失时 `check_html_report.py` 会失败。

### 2.1 可折叠区域

```html
<style>
  details {
    margin: 12px 0;
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  summary {
    padding: 10px 16px;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    background: #f8fafc;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  summary::-webkit-details-marker { display: none; }
  summary::before {
    content: "▸";
    display: inline-block;
    font-size: 10px;
    transition: transform .2s;
    color: var(--muted);
  }
  details[open] summary::before { transform: rotate(90deg); }
  .details-body { padding: 12px 16px; }
</style>
```

### 2.2 复制按钮

所有多行代码块都使用 `.code-wrap` 包裹，并放置复制按钮。ASCII 架构图如果需要复制，也可以同样放入 `.code-wrap`；如果只是展示结构，可以只用 `.ascii-diagram`。

```html
<style>
  .code-wrap {
    position: relative;
    max-width: 100%;
    min-width: 0;
  }
  .copy-btn {
    position: absolute;
    top: 8px; right: 8px;
    padding: 4px 10px;
    font-size: 12px;
    background: rgba(255,255,255,.10);
    color: #8fa59c;
    border: 1px solid rgba(143,165,156,.22);
    border-radius: 6px;
    cursor: pointer;
    opacity: 0;
    transition: opacity .15s;
  }
  .code-wrap:hover .copy-btn,
  .code-wrap:focus-within .copy-btn { opacity: 1; }
  .copy-btn.copied { color: #83b986; border-color: #83b986; }
  @media (hover: none) {
    .copy-btn { opacity: 1; }
  }
</style>
```

### 2.3 Toast 通知

```html
<style>
  .toast {
    position: fixed;
    bottom: 24px; left: 50%; transform: translateX(-50%);
    background: #1f2937; color: #fff;
    padding: 10px 22px;
    border-radius: 999px;
    font-size: 14px;
    opacity: 0;
    pointer-events: none;
    transition: opacity .25s;
    z-index: 999;
  }
  .toast.show { opacity: 1; }
</style>
```

### JavaScript（复制按钮 + 目录侧栏收起）

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

---

## 3. 可选交互（仅在内容确实需要时选入）

### 3.0 离线批注审核模式 —— 用户明确需要批注/提问包时使用

不要在报告里手写批注相关 CSS/JS。先按本模板生成普通单文件 HTML 并通过校验，再运行确定性注入脚本：

```bash
python3 skills/html-report/scripts/check_html_report.py <html-file>
python3 skills/html-report/scripts/inject_annotation_mode.py <html-file>
python3 skills/html-report/scripts/check_html_report.py <html-file>
```

注入后的审核版 HTML 会提供选区 `提问` / `批注` 气泡、单按钮 `提交` 输入浮层、可编辑的右侧批注栏、Markdown/JSON 提问包导出和 `导出发布版`。Markdown/JSON 会写入原 HTML 的文件名、绝对路径和 `file://` URL。发布版导出会物理剥离批注 UI、批注 JS、批注样式和批注高亮。

详细契约见 `references/annotation-mode.md`。

### 3.1 左侧目录 —— 长文档使用，浮动侧栏，可整体收起

当报告章节超过 5 个、内容包含多组问题/方案/链路/验证结果，或读者需要频繁跨章节查阅时使用。目录沿用旧版浮动卡片样式：固定在左侧，正文放在右侧；默认展开，读者点击按钮时收起/展开整个目录侧栏。不要把目录包进 `<details>`，那只会隐藏目录里的链接，不是侧栏级收起。小屏幕下目录退化为顶部卡片，不遮挡正文。

```html
<style>
  .layout-with-toc {
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
    gap: 24px;
    max-width: 1360px;
    margin: 0 auto;
    padding: 32px 24px 56px;
    transition: grid-template-columns .2s ease;
  }
  .layout-with-toc.toc-collapsed {
    grid-template-columns: 52px minmax(0, 1fr);
  }
  .layout-with-toc main {
    max-width: none;
    margin: 0;
    padding: 0;
  }
  .toc {
    position: sticky;
    top: 24px;
    align-self: start;
    max-height: calc(100vh - 48px);
    overflow: auto;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
    padding: 16px;
  }
  .toc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin: 0 0 10px;
  }
  .toc-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--muted);
  }
  .toc-toggle {
    width: 28px;
    height: 28px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #f8fafc;
    color: #64748b;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-weight: 700;
    line-height: 1;
    transition: background .15s, color .15s, border-color .15s;
  }
  .toc-toggle:hover {
    background: #eef2ff;
    border-color: #c7d2fe;
    color: var(--accent);
  }
  .toc-toggle-icon { font-size: 18px; line-height: 1; }
  .toc a {
    display: block;
    padding: 7px 10px;
    border-radius: 8px;
    color: #334155;
    text-decoration: none;
    font-size: 14px;
    line-height: 1.35;
  }
  .toc a:hover { background: #f1f5f9; color: var(--accent); }
  .layout-with-toc.toc-collapsed .toc {
    padding: 10px;
    overflow: visible;
  }
  .layout-with-toc.toc-collapsed .toc-header {
    justify-content: center;
    margin-bottom: 0;
  }
  .layout-with-toc.toc-collapsed .toc-title,
  .layout-with-toc.toc-collapsed .toc a {
    display: none;
  }
  .layout-with-toc.toc-collapsed .toc-toggle {
    width: 32px;
    height: 32px;
  }
  section[id], h2[id] { scroll-margin-top: 24px; }

  @media (max-width: 900px) {
    .layout-with-toc {
      display: block;
      padding: 20px 16px 44px;
    }
    .toc {
      position: static;
      max-height: none;
      margin-bottom: 16px;
      overflow: visible;
    }
    .layout-with-toc.toc-collapsed .toc {
      padding: 16px;
    }
    .layout-with-toc.toc-collapsed .toc-header {
      justify-content: space-between;
      margin-bottom: 0;
    }
    .layout-with-toc.toc-collapsed .toc-title {
      display: block;
    }
    .doc-header {
      padding: 22px 20px;
      border-radius: 14px;
    }
    .doc-header h1 { font-size: 24px; }
  }
</style>
```

目录结构示例：

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
    <a href="#architecture">架构视图</a>
    <a href="#fix-order">建议修复顺序</a>
  </aside>
  <main>
    <section id="summary" class="summary">...</section>
    <h2 id="issue-1">问题 1：问题标题</h2>
    <h2 id="architecture">架构视图</h2>
    <h2 id="fix-order">建议修复顺序</h2>
  </main>
</div>
```

### 3.2 标签页 —— 纯 CSS，不需要 JS

当报告天然有 2-3 个并列视角时使用。只有一个视角不要用。

```html
<style>
  .tabs {
    display: flex; flex-wrap: wrap; gap: 4px;
    margin-bottom: 16px;
    border-bottom: 2px solid var(--border);
  }
  .tab-label {
    padding: 8px 18px; font-size: 14px; font-weight: 600;
    cursor: pointer; color: var(--muted);
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: color .15s, border-color .15s;
    user-select: none;
  }
  .tab-radio { display: none; }
  .tab-panel { display: none; }

  #tab1:checked ~ .tab-content #panel1,
  #tab2:checked ~ .tab-content #panel2,
  #tab3:checked ~ .tab-content #panel3 { display: block; }

  #tab1:checked ~ .tabs .tab-label[for="tab1"],
  #tab2:checked ~ .tabs .tab-label[for="tab2"],
  #tab3:checked ~ .tabs .tab-label[for="tab3"] {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
</style>
```

### 3.3 可排序表格

5 行以上的数据表才加。3-4 行的迷你表不需要。

```html
<style>
  .tbl-wrap { overflow-x: auto; margin: 12px 0; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th {
    cursor: pointer; user-select: none;
    padding: 10px 14px; text-align: left;
    background: #f1f5f9; border-bottom: 2px solid var(--border);
    white-space: nowrap;
  }
  th:hover { background: #e2e8f0; }
  th .sort-arrow { font-size: 10px; margin-left: 4px; }
  td { padding: 8px 14px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: #f8fafc; }
</style>

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

---

## 4. HTML 骨架（默认版：折叠 + 复制）

正式技术/业务文档或分析报告需要在 `<main>` 最前面加入 `.doc-header`。普通对话转 HTML 可以省略 `.doc-header`，直接使用 `<h1>` 和整理时间。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>报告标题</title>
  <style>
    {{ 基础样式 + 折叠样式 + 复制按钮样式 + Toast 样式 }}
  </style>
</head>
<body>

<div id="toast" class="toast">已复制到剪贴板</div>

<main>
  <!-- 正式技术/业务文档或分析报告使用；普通对话转 HTML 可省略 -->
  <header class="doc-header">
    <h1>文档标题</h1>
    <p class="doc-subtitle">一句话说明文档主题、交付目的或核心结论。</p>
    <div class="doc-meta">
      <span class="doc-chip">技术详设</span>
      <span class="doc-chip">FEEDADS-23545</span>
      <span class="doc-chip">baidu/channel/im-android-sdk · master</span>
      <span class="doc-chip">Android 端</span>
      <span class="doc-chip">zhangzhen40</span>
      <span class="doc-chip">2026-05-20 更新</span>
    </div>
  </header>

  <p class="muted">整理时间：YYYY-MM-DD。行号基于当前本地源码定位，若行号有偏移以文件路径和代码上下文为准。</p>

  <!-- 总结区 -->
  <section class="summary">
    <h2>最终结论</h2>
    <p>用 1-2 段概括根因、结论或整体风险。</p>
    <div class="grid">
      <div class="mini"><span class="tag p0">P0</span> <b>问题标题</b><br/>一句话说明影响。</div>
    </div>
  </section>

  <!-- 问题卡片 -->
  <h2>问题 1：问题标题</h2>
  <section class="issue">
    <h3><span class="tag p0">P0</span> 问题说明</h3>
    <div class="meta">
      <a class="path file-link" href="idea://open?file=/absolute/or/repo/path/File.kt&amp;line=123" title="/absolute/or/repo/path/File.kt:123-145">repo/path/File.kt:123-145</a>
    </div>
    <p><b>问题：</b>说明当前代码行为。</p>
    <p><b>影响：</b>说明业务、稳定性或性能影响。</p>
    <p><b>当前代码：</b></p>
    <div class="code-wrap">
      <pre><code class="language-kotlin"><span class="tok-key">fun</span> <span class="tok-fn">loadUser</span>(<span class="tok-var">id</span>: <span class="tok-type">String</span>): <span class="tok-type">User</span> {
  <span class="tok-cmt">// code snippet</span>
  <span class="tok-key">return</span> <span class="tok-fn">repository.find</span>(<span class="tok-var">id</span>)
}</code></pre>
      <button class="copy-btn" type="button" aria-label="复制代码">复制</button>
    </div>
    <p><b>修复方案：</b>说明最小、安全的改法。</p>
    <div class="code-wrap">
      <pre><code class="language-kotlin"><span class="tok-key">fun</span> <span class="tok-fn">loadUser</span>(<span class="tok-var">id</span>: <span class="tok-type">String</span>): <span class="tok-type">User?</span> {
  <span class="tok-key">return</span> <span class="tok-fn">repository.findOrNull</span>(<span class="tok-var">id</span>)
}</code></pre>
      <button class="copy-btn" type="button" aria-label="复制代码">复制</button>
    </div>
  </section>

  <!-- ASCII 架构图：保持原始缩进和连线 -->
  <h2>架构视图</h2>
  <section class="summary">
    <pre class="ascii-diagram">入口
 └─ 分支 A
    ├─ 子节点 1
    └─ 子节点 2</pre>
  </section>

  <!-- 折叠区 -->
  <details>
    <summary>相关日志（点击展开）</summary>
    <div class="details-body">
      <div class="code-wrap">
        <pre><code class="language-text"><span class="tok-cmt">// 日志内容</span></code></pre>
        <button class="copy-btn" type="button" aria-label="复制代码">复制</button>
      </div>
    </div>
  </details>

  <!-- 建议修复顺序 -->
  <h2>建议修复顺序</h2>
  <section class="summary">
    <ol>
      <li><b>P0 先修：</b>...</li>
    </ol>
  </section>
</main>

<script>{{ 复制按钮 JS；使用左侧目录时同时加入目录侧栏收起 JS }}</script>
</body>
</html>
```

---

## 5. 按需扩展：当报告内容较长时加入左侧目录

在默认骨架的基础上：

1. 在 `<style>` 中追加左侧目录 CSS
2. 用 `.layout-with-toc` 包裹目录和正文，目录结构沿用旧版浮动 `<aside class="toc">`，只额外加入 `.toc-toggle`
3. 为主要章节设置稳定 `id`
4. 目录链接只放主要章节，不要把每个小标题都塞进去

```html
<body>
<div id="toast" class="toast">已复制到剪贴板</div>

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
    <a href="#architecture">架构视图</a>
    <a href="#fix-order">建议修复顺序</a>
  </aside>

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

    <section id="summary" class="summary">
      <h2>最终结论</h2>
      <p>...</p>
    </section>

    <h2 id="issue-1">问题 1：问题标题</h2>
    <section class="issue">...</section>

    <h2 id="architecture">架构视图</h2>
    <section class="summary">...</section>

    <h2 id="fix-order">建议修复顺序</h2>
    <section class="summary">...</section>
  </main>
</div>
</body>
```

---

## 6. 按需扩展：当报告内容需要标签页时

在默认骨架的基础上：

1. 在 `<style>` 中追加标签页 CSS
2. 在 `<main>` 中用以下结构替换问题列表：

```html
<input type="radio" name="tab" class="tab-radio" id="tab1" checked />
<input type="radio" name="tab" class="tab-radio" id="tab2" />
<div class="tabs">
  <label for="tab1" class="tab-label">问题清单</label>
  <label for="tab2" class="tab-label">修复方案</label>
</div>
<div class="tab-content">
  <div class="tab-panel" id="panel1">
    <!-- 问题卡片 -->
  </div>
  <div class="tab-panel" id="panel2">
    <!-- 修复内容 -->
  </div>
</div>
```
