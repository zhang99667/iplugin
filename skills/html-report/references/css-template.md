# HTML 报告 CSS 模板

生成报告时使用以下 CSS。可根据内容微调，但整体风格保持一致。

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
    --code-bg: #111827;
    --code: #e5e7eb;
  }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.65;
  }
  main {
    max-width: 1180px;
    margin: 0 auto;
    padding: 32px 24px 56px;
  }
  h1 {
    margin: 0 0 8px;
    font-size: 30px;
    line-height: 1.25;
  }
  h2 {
    margin: 30px 0 14px;
    font-size: 22px;
    border-left: 5px solid #3b82f6;
    padding-left: 10px;
  }
  h3 {
    margin: 0 0 10px;
    font-size: 18px;
  }
  p { margin: 8px 0; }
  .summary, .issue {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
    padding: 18px 20px;
    margin: 16px 0;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0 12px;
  }
  .tag {
    display: inline-block;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
    color: #fff;
  }
  .p0 { background: var(--p0); }
  .p1 { background: var(--p1); }
  .p2 { background: var(--p2); }
  .path {
    display: inline-block;
    background: #eef2ff;
    color: #3730a3;
    border-radius: 8px;
    padding: 2px 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    word-break: break-all;
  }
  .line {
    display: inline-block;
    background: #ecfeff;
    color: #155e75;
    border-radius: 8px;
    padding: 2px 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
  }
  .muted { color: var(--muted); }
  ul { margin: 8px 0 8px 22px; padding: 0; }
  li { margin: 4px 0; }
  pre {
    margin: 10px 0 14px;
    padding: 14px 16px;
    overflow: auto;
    background: var(--code-bg);
    color: var(--code);
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.5;
    tab-size: 4;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 1px 5px;
    font-size: .92em;
    white-space: nowrap;
  }
  pre code {
    background: transparent;
    color: inherit;
    border: 0;
    border-radius: 0;
    padding: 0;
    font-size: inherit;
    white-space: pre;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
  }
  .mini {
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    background: #fbfdff;
  }
  .ok { color: #047857; font-weight: 700; }
  .warn { color: #b45309; font-weight: 700; }
</style>
```

## HTML 骨架

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>报告标题</title>
  <style>...</style>
</head>
<body>

<main>
  <h1>报告标题</h1>
  <p class="muted">整理时间：YYYY-MM-DD。行号基于当前本地源码定位，若评审系统行号有偏移，以文件路径和代码上下文为准。</p>

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
      <span class="path">/absolute/or/repo/path/File.kt</span>
      <span class="line">123-145</span>
    </div>
    <p><b>问题：</b>说明当前代码行为，例如 <code>WebPanelAction.kt</code> 没有解析某个字段。</p>
    <p><b>影响：</b>说明业务、稳定性、性能或转化影响。</p>
    <p><b>当前代码：</b></p>
    <pre><code>// code snippet</code></pre>
    <p><b>修复方案：</b>说明最小、安全、可编译的改法。</p>
    <pre><code>// fixed code snippet</code></pre>
  </section>

  <h2>建议修复顺序</h2>
  <section class="summary">
    <ol>
      <li><b>P0 先修：</b>...</li>
    </ol>
  </section>
</main>
</body>
</html>
```