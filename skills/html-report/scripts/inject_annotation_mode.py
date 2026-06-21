#!/usr/bin/env python3
"""给 html-report 单文件 HTML 注入离线批注审核模式。

这个脚本用于把已经生成好的普通 HTML 报告升级成“审核版”：
- 选中文本后显示轻量气泡，可选择“提问”或“批注”。
- 输入浮层只有一个“提交”按钮，点击外侧自动关闭。
- 右侧栏可以复制/下载 Markdown、JSON，并导出物理剥离批注能力的发布版 HTML。

脚本只依赖 Python 标准库，输出仍是单文件 HTML。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CSS_MARKER_START = "/* QA_ANNOTATION_CSS_START:"
CSS_MARKER_END = "QA_ANNOTATION_CSS_END */"
HTML_MARKER_START = "<!-- QA_ANNOTATION_HTML_START:"
HTML_MARKER_END = "QA_ANNOTATION_HTML_END -->"
SCRIPT_MARKER_START = "<!-- QA_ANNOTATION_SCRIPT_START -->"
SCRIPT_MARKER_END = "<!-- QA_ANNOTATION_SCRIPT_END -->"


ANNOTATION_CSS = r'''

    /* QA_ANNOTATION_CSS_START: 离线批注审核模式，导出发布版时会被移除。 */
    :root {
      --qa-accent: #2563eb;
      --qa-accent-soft: #eff6ff;
      --qa-border: #dbe3ef;
      --qa-text: #172033;
      --qa-muted: #64748b;
      --qa-panel: #ffffff;
    }
    body.qa-panel-open { padding-right: 380px; }
    .qa-launcher {
      position: fixed;
      right: 18px;
      top: 18px;
      z-index: 1400;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 38px;
      padding: 8px 12px;
      border: 1px solid rgba(37, 99, 235, .22);
      border-radius: 999px;
      background: #ffffff;
      color: #1d4ed8;
      box-shadow: 0 10px 28px rgba(15, 23, 42, .14);
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
    }
    .qa-launcher:hover { background: var(--qa-accent-soft); }
    .qa-launcher.publish-mode {
      border-color: rgba(37, 99, 235, .34);
      background: #ffffff;
      color: #1d4ed8;
      box-shadow: 0 10px 26px rgba(15, 23, 42, .14);
    }
    .qa-launcher.publish-mode:hover { background: var(--qa-accent-soft); }
    .qa-launcher-icon {
      display: none;
      width: 15px;
      height: 15px;
      stroke-width: 2.4;
    }
    .qa-launcher.publish-mode .qa-launcher-icon { display: block; }
    .qa-launcher-label { line-height: 1; }
    .qa-launcher-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 22px;
      height: 22px;
      padding: 0 6px;
      border-radius: 999px;
      background: #1d4ed8;
      color: #ffffff;
      font-size: 12px;
      line-height: 1;
    }
    .qa-launcher-count[hidden],
    .qa-launcher.publish-mode .qa-launcher-count {
      display: none !important;
    }
    .qa-selection-popover,
    .qa-context-menu,
    .qa-composer {
      position: fixed;
      z-index: 1700;
      display: none;
      border: 1px solid var(--qa-border);
      background: #ffffff;
      box-shadow: 0 16px 42px rgba(15, 23, 42, .18);
    }
    .qa-selection-popover {
      gap: 4px;
      padding: 5px;
      border-radius: 999px;
    }
    .qa-selection-popover.show { display: inline-flex; }
    .qa-bubble-btn {
      appearance: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 34px;
      padding: 7px 12px;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: #1f2937;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      font-weight: 900;
      white-space: nowrap;
    }
    .qa-bubble-btn svg {
      width: 15px;
      height: 15px;
      stroke-width: 2.4;
    }
    .qa-bubble-btn:hover,
    .qa-bubble-btn.primary {
      background: var(--qa-accent-soft);
      color: #1d4ed8;
    }
    .qa-context-menu.show {
      display: block;
      min-width: 190px;
      padding: 6px;
      border-radius: 10px;
    }
    .qa-menu-item {
      appearance: none;
      display: block;
      width: 100%;
      padding: 9px 10px;
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: #1f2937;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      line-height: 1.25;
      text-align: left;
    }
    .qa-menu-item:hover { background: #f1f5f9; color: var(--qa-accent); }
    .qa-menu-sep { height: 1px; margin: 5px 4px; background: #e2e8f0; }
    .qa-composer {
      width: min(360px, calc(100vw - 28px));
      padding: 10px;
      border-radius: 14px;
    }
    .qa-composer.show { display: block; }
    .qa-composer-title {
      display: flex;
      align-items: center;
      gap: 7px;
      margin: 0 0 7px;
      color: var(--qa-text);
      font-size: 13px;
      font-weight: 900;
    }
    .qa-composer-title svg {
      width: 15px;
      height: 15px;
      color: #1d4ed8;
      stroke-width: 2.4;
    }
    .qa-composer-excerpt {
      margin: 0 0 8px;
      padding: 6px 8px;
      border-radius: 8px;
      background: #f8fafc;
      color: var(--qa-muted);
      font-size: 12px;
      line-height: 1.45;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .qa-composer textarea {
      width: 100%;
      min-height: 86px;
      padding: 9px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      background: #ffffff;
      color: #111827;
      font: inherit;
      font-size: 13px;
      line-height: 1.55;
      resize: vertical;
    }
    .qa-composer textarea:focus {
      border-color: #93c5fd;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, .12);
      outline: 0;
    }
    .qa-composer-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 8px;
    }
    .qa-small-btn,
    .qa-secondary-btn,
    .qa-primary-btn,
    .qa-danger-btn {
      appearance: none;
      border-radius: 9px;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      font-weight: 800;
    }
    .qa-small-btn { min-height: 32px; padding: 6px 12px; }
    .qa-primary-btn,
    .qa-secondary-btn,
    .qa-danger-btn { min-height: 34px; padding: 7px 10px; }
    .qa-primary-btn,
    .qa-small-btn.primary { border: 1px solid #1d4ed8; background: #1d4ed8; color: #ffffff; }
    .qa-secondary-btn,
    .qa-small-btn { border: 1px solid var(--qa-border); background: #ffffff; color: #1f2937; }
    .qa-danger-btn { border: 1px solid #fecaca; background: #fff1f2; color: #b91c1c; }
    .qa-primary-btn:hover,
    .qa-small-btn.primary:hover { background: #1e40af; }
    .qa-secondary-btn:hover,
    .qa-small-btn:hover { background: #f8fafc; color: var(--qa-accent); }
    .qa-danger-btn:hover { background: #fee2e2; }
    .qa-sidebar {
      position: fixed;
      top: 0;
      right: 0;
      z-index: 1500;
      width: 380px;
      max-width: calc(100vw - 18px);
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--qa-panel);
      border-left: 1px solid var(--qa-border);
      box-shadow: -18px 0 42px rgba(15, 23, 42, .16);
      transform: translateX(105%);
      transition: transform .2s ease;
    }
    .qa-sidebar.open { transform: translateX(0); }
    .qa-sidebar-header {
      padding: 16px 16px 12px;
      border-bottom: 1px solid var(--qa-border);
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
    .qa-title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }
    .qa-sidebar h2 {
      margin: 0;
      padding: 0;
      border: 0;
      color: var(--qa-text);
      font-size: 17px;
      line-height: 1.3;
    }
    .qa-mode-chip {
      display: inline-flex;
      align-items: center;
      min-height: 23px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e0f2fe;
      color: #075985;
      font-size: 12px;
      font-weight: 900;
    }
    .qa-close {
      width: 32px;
      height: 32px;
      border: 1px solid var(--qa-border);
      border-radius: 9px;
      background: #ffffff;
      color: #475569;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      font-weight: 900;
    }
    .qa-help { margin: 0; color: var(--qa-muted); font-size: 12px; line-height: 1.55; }
    .qa-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 12px;
    }
    .qa-actions .qa-wide { grid-column: 1 / -1; }
    .qa-publish-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      min-height: 42px;
      box-shadow: 0 10px 24px rgba(37, 99, 235, .18);
    }
    .qa-publish-btn svg {
      width: 16px;
      height: 16px;
      stroke-width: 2.4;
    }
    .qa-list {
      flex: 1;
      overflow: auto;
      padding: 12px;
      background: #f8fafc;
    }
    .qa-empty {
      margin: 18px 4px;
      padding: 18px;
      border: 1px dashed #cbd5e1;
      border-radius: 12px;
      background: #ffffff;
      color: var(--qa-muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .qa-card {
      margin: 0 0 10px;
      padding: 12px;
      border: 1px solid var(--qa-border);
      border-left: 4px solid var(--qa-accent);
      border-radius: 12px;
      background: #ffffff;
      box-shadow: 0 6px 18px rgba(15, 23, 42, .05);
    }
    .qa-card.kind-note { border-left-color: #0f766e; }
    .qa-card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }
    .qa-kind {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e0f2fe;
      color: #075985;
      font-size: 12px;
      font-weight: 900;
    }
    .qa-card.kind-note .qa-kind { background: #ccfbf1; color: #115e59; }
    .qa-section { color: var(--qa-muted); font-size: 12px; line-height: 1.4; }
    .qa-quote {
      margin: 8px 0;
      padding: 8px 10px;
      border-left: 3px solid #cbd5e1;
      background: #f8fafc;
      color: #334155;
      font-size: 12px;
      line-height: 1.55;
      max-height: 120px;
      overflow: auto;
      white-space: pre-wrap;
    }
    .qa-question { margin: 8px 0; color: #111827; font-size: 13px; line-height: 1.55; white-space: pre-wrap; }
    .qa-card-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .qa-mini-btn {
      appearance: none;
      border: 1px solid var(--qa-border);
      border-radius: 8px;
      background: #ffffff;
      color: #334155;
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
      padding: 5px 8px;
    }
    .qa-mini-btn:hover { background: #f1f5f9; color: var(--qa-accent); }
    .qa-annotated-block {
      outline: 2px solid rgba(37, 99, 235, .30);
      outline-offset: 3px;
      border-radius: 8px;
      background-image: linear-gradient(rgba(239, 246, 255, .62), rgba(239, 246, 255, .62));
    }
    .qa-highlight {
      background: #fef3c7;
      box-shadow: 0 0 0 2px rgba(251, 191, 36, .18);
      border-radius: 4px;
    }
    .qa-focus-pulse { animation: qaPulse 1.2s ease; }
    @keyframes qaPulse {
      0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, .42); }
      70% { box-shadow: 0 0 0 12px rgba(37, 99, 235, 0); }
      100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
    }
    .qa-copy-backdrop {
      position: fixed;
      inset: 0;
      z-index: 1800;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: rgba(15, 23, 42, .38);
    }
    .qa-copy-backdrop.show { display: flex; }
    .qa-copy-dialog {
      width: min(640px, 100%);
      max-height: min(760px, 92vh);
      display: flex;
      flex-direction: column;
      border-radius: 16px;
      background: #ffffff;
      box-shadow: 0 26px 72px rgba(15, 23, 42, .30);
      overflow: hidden;
    }
    .qa-dialog-head {
      padding: 16px 18px;
      border-bottom: 1px solid var(--qa-border);
      background: #f8fafc;
    }
    .qa-dialog-head h2 {
      margin: 0;
      padding: 0;
      border: 0;
      color: var(--qa-text);
      font-size: 18px;
    }
    .qa-dialog-body { padding: 16px 18px; overflow: auto; }
    .qa-dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding: 12px 18px 16px;
      border-top: 1px solid var(--qa-border);
    }
    .qa-copy-textarea {
      width: 100%;
      min-height: 260px;
      border: 1px solid var(--qa-border);
      border-radius: 10px;
      padding: 10px 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      line-height: 1.55;
      resize: vertical;
    }
    @media (max-width: 960px) {
      body.qa-panel-open { padding-right: 0; }
      .qa-sidebar { width: min(100vw, 420px); }
      .qa-launcher { right: 12px; top: 12px; }
    }
    @media print {
      body.qa-panel-open { padding-right: 0; }
      .qa-launcher,
      .qa-selection-popover,
      .qa-context-menu,
      .qa-composer,
      .qa-sidebar,
      .qa-copy-backdrop { display: none !important; }
      .qa-annotated-block { outline: 0; background: transparent; }
    }
    /* QA_ANNOTATION_CSS_END */
'''


ANNOTATION_HTML = r'''
  <!-- QA_ANNOTATION_HTML_START: 离线批注审核模式，导出发布版时会被移除。 -->
  <button class="qa-launcher" type="button" id="qaLauncher" aria-controls="qaSidebar" aria-expanded="false" data-qa-ui>
    <svg class="qa-launcher-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 3v12"></path><path d="m7 8 5-5 5 5"></path><path d="M5 15v4h14v-4"></path></svg>
    <span class="qa-launcher-label" id="qaLauncherLabel">导出发布版</span>
    <span class="qa-launcher-count" id="qaLauncherCount" hidden>0</span>
  </button>

  <div class="qa-selection-popover" id="qaSelectionPopover" role="menu" aria-label="选中文本操作" data-qa-ui>
    <button class="qa-bubble-btn primary" type="button" data-qa-action="ask-selection" title="向 Agent 提问">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M9.8 9a2.4 2.4 0 0 1 4.4 1.35c0 1.65-2.2 1.85-2.2 3.35"></path><path d="M12 17h.01"></path></svg>
      提问
    </button>
    <button class="qa-bubble-btn" type="button" data-qa-action="note-selection" title="添加批注">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>
      批注
    </button>
  </div>

  <div class="qa-composer" id="qaComposer" role="dialog" aria-label="添加批注" data-qa-ui>
    <p class="qa-composer-title" id="qaComposerTitle"></p>
    <p class="qa-composer-excerpt" id="qaComposerExcerpt"></p>
    <textarea id="qaComposerText" placeholder="写下你想让 Agent 回答或修改的点"></textarea>
    <div class="qa-composer-actions">
      <button class="qa-small-btn primary" type="button" id="qaComposerSave">提交</button>
    </div>
  </div>

  <div class="qa-context-menu" id="qaContextMenu" role="menu" aria-label="批注右键菜单" data-qa-ui>
    <button class="qa-menu-item" type="button" data-qa-action="ask-selection">对选中内容提问</button>
    <button class="qa-menu-item" type="button" data-qa-action="note-selection">对选中内容批注</button>
    <div class="qa-menu-sep"></div>
    <button class="qa-menu-item" type="button" data-qa-action="ask-block">对本段提问</button>
    <button class="qa-menu-item" type="button" data-qa-action="note-block">对本段批注</button>
    <button class="qa-menu-item" type="button" data-qa-action="ask-section">对本节提问</button>
  </div>

  <aside class="qa-sidebar" id="qaSidebar" aria-label="报告批注" data-qa-ui>
    <div class="qa-sidebar-header">
      <div class="qa-title-row">
        <h2>报告批注</h2>
        <span class="qa-mode-chip">审核模式</span>
        <button class="qa-close" type="button" id="qaClose" aria-label="关闭批注栏">×</button>
      </div>
      <p class="qa-help">选中文本后点小气泡提问/批注。发布给外部前，可导出物理剥离批注能力的发布版 HTML。</p>
      <div class="qa-actions">
        <button class="qa-primary-btn qa-publish-btn qa-wide" type="button" id="qaExportPublic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 3v12"></path><path d="m7 8 5-5 5 5"></path><path d="M5 15v4h14v-4"></path></svg>
          导出发布版
        </button>
        <button class="qa-secondary-btn" type="button" id="qaCopyMarkdown">复制 Markdown</button>
        <button class="qa-secondary-btn" type="button" id="qaDownloadMarkdown">下载 Markdown</button>
        <button class="qa-secondary-btn" type="button" id="qaDownloadJson">下载 JSON</button>
        <button class="qa-danger-btn qa-wide" type="button" id="qaClearAll">清空批注</button>
      </div>
    </div>
    <div class="qa-list" id="qaList"></div>
  </aside>

  <div class="qa-copy-backdrop" id="qaCopyBackdrop" role="dialog" aria-modal="true" aria-labelledby="qaCopyTitle" data-qa-ui>
    <div class="qa-copy-dialog">
      <div class="qa-dialog-head"><h2 id="qaCopyTitle">手动复制</h2></div>
      <div class="qa-dialog-body">
        <p class="qa-help">当前浏览器没有开放剪贴板权限。下面内容已选中，可以直接按 Cmd+C 复制。</p>
        <textarea class="qa-copy-textarea" id="qaCopyTextarea" readonly></textarea>
      </div>
      <div class="qa-dialog-actions">
        <button class="qa-primary-btn" type="button" id="qaCopyClose">完成</button>
      </div>
    </div>
  </div>
  <!-- QA_ANNOTATION_HTML_END -->
'''


ANNOTATION_JS = r'''
  <!-- QA_ANNOTATION_SCRIPT_START -->
  <script data-qa-script>
    (() => {
      const iconQuestion = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M9.8 9a2.4 2.4 0 0 1 4.4 1.35c0 1.65-2.2 1.85-2.2 3.35"></path><path d="M12 17h.01"></path></svg>';
      const iconNote = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>';
      const injectedReportMeta = __QA_REPORT_META__;
      const reportTitle = (document.querySelector('.doc-header h1')?.innerText || document.title || 'HTML 报告').trim();
      const reportFileName = injectedReportMeta.fileName || currentFileName();
      const reportAbsolutePath = injectedReportMeta.absolutePath || decodeURIComponent(location.pathname || '');
      const reportFileUrl = injectedReportMeta.fileUrl || location.href || '';
      const storageKey = 'agent-report-annotations:' + (reportAbsolutePath || location.pathname) + ':' + reportTitle;
      const main = document.querySelector('main');
      const launcher = document.getElementById('qaLauncher');
      const launcherLabel = document.getElementById('qaLauncherLabel');
      const launcherCount = document.getElementById('qaLauncherCount');
      const sidebar = document.getElementById('qaSidebar');
      const closeBtn = document.getElementById('qaClose');
      const list = document.getElementById('qaList');
      const selectionPopover = document.getElementById('qaSelectionPopover');
      const contextMenu = document.getElementById('qaContextMenu');
      const composer = document.getElementById('qaComposer');
      const composerTitle = document.getElementById('qaComposerTitle');
      const composerExcerpt = document.getElementById('qaComposerExcerpt');
      const composerText = document.getElementById('qaComposerText');
      const composerSave = document.getElementById('qaComposerSave');
      const copyBackdrop = document.getElementById('qaCopyBackdrop');
      const copyTextarea = document.getElementById('qaCopyTextarea');
      const copyClose = document.getElementById('qaCopyClose');
      let annotations = loadAnnotations();
      let draftTarget = null;
      let draftKind = '提问';
      let lastContextTarget = null;
      let cachedSelectionTarget = null;
      let blockSeq = 0;

      if (!main) return;

      main.querySelectorAll('h2, h3, p, li, table, pre, .panel, .mini, .check, .flow-svg, section').forEach(el => {
        if (!el.dataset.blockId) {
          blockSeq += 1;
          const section = nearestSectionId(el) || 'root';
          el.dataset.blockId = section + '-b' + String(blockSeq).padStart(3, '0');
        }
      });

      renderAnnotations();
      syncAnnotatedState();

      launcher?.addEventListener('click', () => {
        if (!annotations.length) {
          exportPublicHtml();
          return;
        }
        setSidebarOpen(!sidebar.classList.contains('open'));
      });
      closeBtn?.addEventListener('click', () => setSidebarOpen(false));
      composerSave?.addEventListener('click', saveDraftAnnotation);
      copyClose?.addEventListener('click', () => copyBackdrop.classList.remove('show'));
      document.getElementById('qaCopyMarkdown')?.addEventListener('click', () => copyText(buildMarkdownPack()));
      document.getElementById('qaDownloadMarkdown')?.addEventListener('click', () => downloadText(safeFileName(reportTitle) + '_questions.md', buildMarkdownPack(), 'text/markdown'));
      document.getElementById('qaDownloadJson')?.addEventListener('click', () => downloadText(safeFileName(reportTitle) + '_questions.json', JSON.stringify(buildJsonPack(), null, 2), 'application/json'));
      document.getElementById('qaExportPublic')?.addEventListener('click', exportPublicHtml);
      document.getElementById('qaClearAll')?.addEventListener('click', () => {
        if (!annotations.length) return;
        if (!confirm('确定清空本页所有批注吗？')) return;
        annotations = [];
        saveAnnotations();
        syncAnnotatedState();
        renderAnnotations();
      });

      document.addEventListener('mouseup', event => {
        if (event.target.closest('[data-qa-ui]')) return;
        setTimeout(showSelectionPopover, 0);
      });
      document.addEventListener('keyup', event => {
        if (event.key === 'Escape') {
          hideFloatingUi();
          closeComposer();
          setSidebarOpen(false);
          return;
        }
        showSelectionPopover();
      });
      document.addEventListener('click', event => {
        if (!event.target.closest('.qa-selection-popover') && !event.target.closest('.qa-context-menu') && !event.target.closest('.qa-composer')) {
          contextMenu.classList.remove('show');
          closeComposer();
        }
      });

      main.addEventListener('contextmenu', event => {
        const target = findQuestionTarget(event.target);
        if (!target) return;
        event.preventDefault();
        lastContextTarget = target;
        hideSelectionPopover();
        closeComposer();
        showContextMenu(event.clientX, event.clientY);
      });

      selectionPopover?.addEventListener('mousedown', event => {
        event.preventDefault();
      });
      selectionPopover?.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        const action = event.target.closest('[data-qa-action]')?.dataset.qaAction;
        if (action) handleAction(action, true);
      });
      contextMenu?.addEventListener('click', event => {
        const action = event.target.closest('[data-qa-action]')?.dataset.qaAction;
        if (action) handleAction(action, false);
      });

      function handleAction(action, preferCachedSelection = false) {
        contextMenu.classList.remove('show');
        hideSelectionPopover();
        const selectionTarget = preferCachedSelection ? (cachedSelectionTarget || buildTargetFromSelection()) : buildTargetFromSelection();
        if (action === 'ask-selection' || action === 'note-selection') {
          const target = selectionTarget || buildTargetFromElement(lastContextTarget);
          openComposer(target, action === 'ask-selection' ? '提问' : '批注');
          return;
        }
        if (action === 'ask-block' || action === 'note-block') {
          openComposer(buildTargetFromElement(lastContextTarget), action === 'ask-block' ? '提问' : '批注');
          return;
        }
        if (action === 'ask-section') {
          openComposer(buildTargetFromSection(lastContextTarget), '提问');
        }
      }

      function openComposer(target, kind) {
        if (!target) return;
        draftTarget = target;
        draftKind = kind || '提问';
        composerTitle.innerHTML = (draftKind === '批注' ? iconNote : iconQuestion) + '<span>' + draftKind + '</span>';
        composerExcerpt.textContent = truncate(target.selectedText || target.blockText || '', 84);
        composerText.value = '';
        composerText.placeholder = draftKind === '批注' ? '写下这段内容需要注意或修改的地方' : '写下你想让 Agent 回答的问题';
        positionComposer(target);
        composer.classList.add('show');
        setTimeout(() => composerText.focus(), 0);
      }

      function closeComposer() {
        composer.classList.remove('show');
        draftTarget = null;
      }

      function positionComposer(target) {
        const rect = target.range?.getBoundingClientRect?.() || target.element?.getBoundingClientRect?.();
        const width = 360;
        const height = 190;
        const top = Math.min(window.innerHeight - height - 10, Math.max(10, (rect?.bottom || 80) + 10));
        const left = Math.min(window.innerWidth - width - 10, Math.max(10, (rect?.left || 24)));
        composer.style.top = top + 'px';
        composer.style.left = left + 'px';
      }

      function saveDraftAnnotation() {
        if (!draftTarget) return;
        const text = composerText.value.trim();
        if (!text) {
          composerText.focus();
          return;
        }
        const item = {
          id: 'q-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7),
          reportTitle,
          reportFileName,
          reportAbsolutePath,
          reportFileUrl,
          reportPath: reportAbsolutePath,
          sectionId: draftTarget.sectionId,
          sectionTitle: draftTarget.sectionTitle,
          blockId: draftTarget.blockId,
          selectedText: draftTarget.selectedText,
          blockText: draftTarget.blockText,
          contextBefore: draftTarget.contextBefore,
          contextAfter: draftTarget.contextAfter,
          kind: draftKind,
          text,
          createdAt: new Date().toISOString()
        };
        annotations.unshift(item);
        saveAnnotations();
        syncAnnotatedState();
        renderAnnotations();
        closeComposer();
        setSidebarOpen(true);
        showToast('已保存' + draftKind);
      }

      function buildTargetFromSelection() {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null;
        const text = selection.toString().trim();
        if (!text || text.length < 1) return null;
        const range = selection.getRangeAt(0);
        const container = range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE ? range.commonAncestorContainer : range.commonAncestorContainer.parentElement;
        if (!container || !main.contains(container)) return null;
        const block = findQuestionTarget(container);
        if (!block) return null;
        const blockText = normalizeText(block.innerText || block.textContent || '');
        const idx = blockText.indexOf(text);
        return {
          mode: 'selection',
          range,
          element: block,
          blockId: ensureBlockId(block),
          sectionId: nearestSectionId(block),
          sectionTitle: nearestSectionTitle(block),
          selectedText: text,
          blockText,
          contextBefore: idx >= 0 ? blockText.slice(Math.max(0, idx - 120), idx) : '',
          contextAfter: idx >= 0 ? blockText.slice(idx + text.length, idx + text.length + 120) : ''
        };
      }

      function buildTargetFromElement(element) {
        const block = findQuestionTarget(element) || lastContextTarget;
        if (!block) return null;
        const text = normalizeText(block.innerText || block.textContent || '');
        return {
          mode: 'block',
          element: block,
          blockId: ensureBlockId(block),
          sectionId: nearestSectionId(block),
          sectionTitle: nearestSectionTitle(block),
          selectedText: text,
          blockText: text,
          contextBefore: '',
          contextAfter: ''
        };
      }

      function buildTargetFromSection(element) {
        const block = findQuestionTarget(element) || lastContextTarget;
        if (!block) return null;
        const section = block.closest('section') || block;
        const title = nearestSectionTitle(section);
        const text = normalizeText(section.innerText || section.textContent || '');
        return {
          mode: 'section',
          element: section,
          blockId: ensureBlockId(section),
          sectionId: nearestSectionId(section),
          sectionTitle: title,
          selectedText: text.slice(0, 2400),
          blockText: text,
          contextBefore: '',
          contextAfter: text.length > 2400 ? '本节内容较长，已截取前 2400 字。' : ''
        };
      }

      function findQuestionTarget(node) {
        if (!node) return null;
        const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
        if (!el || !main.contains(el)) return null;
        return el.closest('p, li, tr, table, pre, .panel, .mini, .check, .flow-svg, h2, h3, section');
      }

      function ensureBlockId(el) {
        if (!el.dataset.blockId) {
          blockSeq += 1;
          el.dataset.blockId = (nearestSectionId(el) || 'root') + '-b' + String(blockSeq).padStart(3, '0');
        }
        return el.dataset.blockId;
      }

      function nearestSectionId(el) {
        return el?.closest('section')?.id || previousHeading(el)?.id || 'summary';
      }

      function nearestSectionTitle(el) {
        const ownHeading = el?.matches?.('h2, h3') ? el : null;
        const sectionHeading = el?.closest('section')?.querySelector('h2, h3');
        const heading = ownHeading || sectionHeading || previousHeading(el);
        return normalizeText(heading?.innerText || '未命名章节');
      }

      function previousHeading(el) {
        let cur = el;
        while (cur && cur !== main) {
          let prev = cur.previousElementSibling;
          while (prev) {
            if (prev.matches('h2, h3')) return prev;
            const nested = prev.querySelector?.('h2, h3');
            if (nested) return nested;
            prev = prev.previousElementSibling;
          }
          cur = cur.parentElement;
        }
        return main.querySelector('h2, h3');
      }

      function showSelectionPopover() {
        const target = buildTargetFromSelection();
        if (!target) {
          cachedSelectionTarget = null;
          hideSelectionPopover();
          return;
        }
        const rect = target.range.getBoundingClientRect();
        if (!rect || rect.width === 0) return;
        cachedSelectionTarget = target;
        lastContextTarget = target.element;
        closeComposer();
        const top = Math.max(10, rect.top - 48);
        const left = Math.min(window.innerWidth - 190, Math.max(10, rect.left + rect.width / 2 - 88));
        selectionPopover.style.top = top + 'px';
        selectionPopover.style.left = left + 'px';
        selectionPopover.classList.add('show');
      }

      function hideSelectionPopover() {
        selectionPopover.classList.remove('show');
      }

      function showContextMenu(x, y) {
        const menuWidth = 210;
        const menuHeight = 230;
        contextMenu.style.left = Math.min(x, window.innerWidth - menuWidth - 8) + 'px';
        contextMenu.style.top = Math.min(y, window.innerHeight - menuHeight - 8) + 'px';
        contextMenu.classList.add('show');
      }

      function hideFloatingUi() {
        hideSelectionPopover();
        contextMenu.classList.remove('show');
      }

      function syncAnnotatedState() {
        window.getSelection()?.removeAllRanges();
        main.querySelectorAll('.qa-annotated-block').forEach(el => el.classList.remove('qa-annotated-block', 'qa-focus-pulse'));
        main.querySelectorAll('mark.qa-highlight').forEach(unwrapElement);
        annotations.forEach(item => {
          const el = main.querySelector('[data-block-id="' + cssEscape(item.blockId) + '"]');
          if (!el) return;
          el.classList.add('qa-annotated-block');
          if (item.selectedText && item.selectedText !== item.blockText) highlightTextInElement(el, item.selectedText, item.id);
        });
      }

      function highlightTextInElement(root, text, annotationId) {
        const needle = String(text || '').trim();
        if (!needle || needle.length > 500) return;
        try {
          const walker = document.createTreeWalker(root, 4);
          let node = walker.nextNode();
          while (node) {
            const parent = node.parentElement;
            if (parent && !parent.closest('mark.qa-highlight, [data-qa-ui], script, style')) {
              const index = node.nodeValue.indexOf(needle);
              if (index >= 0) {
                const range = document.createRange();
                range.setStart(node, index);
                range.setEnd(node, index + needle.length);
                const mark = document.createElement('mark');
                mark.className = 'qa-highlight';
                mark.dataset.qaId = annotationId || '';
                range.surroundContents(mark);
                return;
              }
            }
            node = walker.nextNode();
          }
        } catch (error) {
          // 文本跨多个节点时不强行包 mark，保留块级边框即可，避免破坏原 HTML 结构。
        }
      }

      function renderAnnotations() {
        updateLauncherMode();
        if (!list) return;
        if (!annotations.length) {
          list.innerHTML = '<div class="qa-empty">还没有批注。选中文本后点击小气泡，或在正文中右键，对段落、表格、图表发起提问。</div>';
          return;
        }
        list.innerHTML = annotations.map(item => `
          <article class="qa-card ${item.kind === '批注' ? 'kind-note' : ''}" data-qa-id="${escapeAttr(item.id)}">
            <div class="qa-card-head">
              <span class="qa-kind">${escapeHtml(item.kind || '提问')}</span>
              <span class="qa-section">${escapeHtml(item.sectionTitle || '未命名章节')}</span>
            </div>
            <div class="qa-quote">${escapeHtml(truncate(item.selectedText || item.blockText || '', 520))}</div>
            <div class="qa-question">${escapeHtml(item.text || item.question || '')}</div>
            <div class="qa-card-actions">
              <button class="qa-mini-btn" type="button" data-qa-card-action="locate">定位</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="copy">复制此条</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="delete">删除</button>
            </div>
          </article>
        `).join('');
        list.querySelectorAll('[data-qa-card-action]').forEach(btn => {
          btn.addEventListener('click', event => {
            const card = event.target.closest('.qa-card');
            const item = annotations.find(x => x.id === card.dataset.qaId);
            if (!item) return;
            const action = event.target.dataset.qaCardAction;
            if (action === 'locate') locateAnnotation(item);
            if (action === 'copy') copyText(buildSinglePrompt(item));
            if (action === 'delete') {
              annotations = annotations.filter(x => x.id !== item.id);
              saveAnnotations();
              syncAnnotatedState();
              renderAnnotations();
            }
          });
        });
      }

      function updateLauncherMode() {
        const count = annotations.length;
        const publishMode = count === 0;
        if (launcherLabel) launcherLabel.textContent = publishMode ? '导出发布版' : '批注';
        if (launcherCount) {
          launcherCount.textContent = publishMode ? '' : String(count);
          launcherCount.hidden = publishMode;
        }
        launcher?.classList.toggle('publish-mode', publishMode);
        launcher?.setAttribute('aria-label', publishMode ? '导出发布版 HTML' : '打开报告批注，当前 ' + count + ' 条');
      }

      function locateAnnotation(item) {
        const el = main.querySelector('[data-block-id="' + cssEscape(item.blockId) + '"]');
        if (!el) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('qa-focus-pulse');
        setTimeout(() => el.classList.remove('qa-focus-pulse'), 1300);
      }

      function setSidebarOpen(open) {
        sidebar.classList.toggle('open', open);
        document.body.classList.toggle('qa-panel-open', open);
        launcher?.setAttribute('aria-expanded', String(open));
      }

      async function copyText(text) {
        if (!text) return;
        try {
          if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
          await navigator.clipboard.writeText(text);
          showToast('已复制 Markdown');
        } catch (error) {
          copyTextarea.value = text;
          copyBackdrop.classList.add('show');
          setTimeout(() => {
            copyTextarea.focus();
            copyTextarea.select();
          }, 0);
        }
      }

      async function exportPublicHtml() {
        const shouldExport = confirm('导出发布版 HTML。\n\n确定：选择保存位置，建议使用当前文件名覆盖原审核版。\n取消：取消导出。');
        if (!shouldExport) return;
        const publicHtml = buildPublicHtml();
        const currentName = currentFileName();
        if (window.showSaveFilePicker) {
          try {
            const handle = await window.showSaveFilePicker({
              suggestedName: currentName,
              types: [{ description: 'HTML 文件', accept: { 'text/html': ['.html'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(publicHtml);
            await writable.close();
            showToast('已导出发布版');
            return;
          } catch (error) {
            if (error && error.name === 'AbortError') return;
          }
        }
        // 不支持 File System Access API 的浏览器无法静默覆盖本地文件，只能下载当前文件名作为兜底。
        downloadText(currentName, publicHtml, 'text/html');
        showToast('浏览器不支持直接覆盖，已下载发布版，请在保存时覆盖原文件');
      }

      function buildPublicHtml() {
        const clone = document.documentElement.cloneNode(true);
        clone.querySelectorAll('[data-qa-ui], [data-qa-script]').forEach(el => el.remove());
        clone.querySelectorAll('style').forEach(style => {
          style.textContent = style.textContent.replace(/\/\* QA_ANNOTATION_CSS_START:[\s\S]*?QA_ANNOTATION_CSS_END \*\//g, '');
        });
        clone.querySelectorAll('.qa-highlight').forEach(unwrapElement);
        clone.querySelectorAll('.qa-annotated-block, .qa-focus-pulse').forEach(el => {
          el.classList.remove('qa-annotated-block', 'qa-focus-pulse');
        });
        clone.querySelectorAll('[data-block-id]').forEach(el => el.removeAttribute('data-block-id'));
        clone.querySelector('body')?.classList.remove('qa-panel-open');
        let result = '<!doctype html>\n' + clone.outerHTML;
        result = result.replace(/\n?\s*<!-- QA_ANNOTATION_HTML_START:[\s\S]*?QA_ANNOTATION_HTML_END -->/g, '');
        result = result.replace(/\n?\s*<!-- QA_ANNOTATION_SCRIPT_START -->[\s\S]*?<!-- QA_ANNOTATION_SCRIPT_END -->/g, '');
        result = result.replace(/\n{3,}/g, '\n\n');
        return result;
      }

      function downloadText(fileName, text, type) {
        const blob = new Blob([text], { type: type + ';charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
      }

      function buildMarkdownPack() {
        const lines = [];
        lines.push('# HTML 报告批注提问包');
        lines.push('');
        lines.push('报告：' + reportTitle);
        lines.push('文件名：' + reportFileName);
        lines.push('绝对路径：' + (reportAbsolutePath || '无法从当前浏览器环境获取'));
        lines.push('File URL：' + (reportFileUrl || '无法从当前浏览器环境获取'));
        lines.push('导出时间：' + new Date().toLocaleString());
        lines.push('批注数量：' + annotations.length);
        lines.push('');
        if (!annotations.length) {
          lines.push('暂无批注。');
          return lines.join('\n');
        }
        annotations.slice().reverse().forEach((item, idx) => {
          lines.push('## ' + (item.kind || '提问') + ' ' + (idx + 1));
          lines.push('');
          lines.push('- 章节：' + (item.sectionTitle || '未命名章节'));
          lines.push('- 位置：' + (item.blockId || 'unknown'));
          lines.push('- 时间：' + (item.createdAt || ''));
          lines.push('');
          lines.push('原文：');
          lines.push('');
          quoteMarkdown(item.selectedText || item.blockText || '').forEach(line => lines.push(line));
          if (item.contextBefore || item.contextAfter) {
            lines.push('');
            lines.push('上下文：');
            if (item.contextBefore) lines.push('- 前文：' + item.contextBefore);
            if (item.contextAfter) lines.push('- 后文：' + item.contextAfter);
          }
          lines.push('');
          lines.push((item.kind === '批注' ? '我的批注：' : '我的问题：'));
          lines.push('');
          lines.push(item.text || item.question || '');
          lines.push('');
          lines.push('请 Agent 处理：');
          lines.push('');
          lines.push(item.kind === '批注'
            ? '请结合原文和上下文判断这条批注是否合理，并给出报告修改建议。'
            : '请结合原文、上下文和报告结论解释这个问题。如果原报告存在表达不清、逻辑跳跃、证据不足或结论错误，请指出并给出修改建议。');
          lines.push('');
        });
        return lines.join('\n');
      }

      function buildJsonPack() {
        return {
          type: 'AgentQuestionPack',
          version: '0.2.0',
          reportTitle,
          reportFileName,
          reportAbsolutePath,
          reportFileUrl,
          reportPath: reportAbsolutePath,
          source: {
            title: reportTitle,
            fileName: reportFileName,
            absolutePath: reportAbsolutePath,
            fileUrl: reportFileUrl
          },
          exportedAt: new Date().toISOString(),
          annotations
        };
      }

      function buildSinglePrompt(targetOrItem) {
        const item = targetOrItem || {};
        const selected = item.selectedText || item.blockText || '';
        const kind = item.kind || '提问';
        const lines = [
          '# HTML 报告单条' + kind,
          '',
          '报告：' + reportTitle,
          '文件名：' + reportFileName,
          '绝对路径：' + (item.reportAbsolutePath || reportAbsolutePath || '无法从当前浏览器环境获取'),
          'File URL：' + (item.reportFileUrl || reportFileUrl || '无法从当前浏览器环境获取'),
          '章节：' + (item.sectionTitle || '未命名章节'),
          '位置：' + (item.blockId || 'unknown'),
          '',
          '原文：',
          ''
        ];
        quoteMarkdown(selected).forEach(line => lines.push(line));
        lines.push('', kind === '批注' ? '我的批注：' : '我的问题：', '', item.text || item.question || '', '', '请结合上下文处理。');
        return lines.join('\n');
      }

      function quoteMarkdown(text) {
        const normalized = normalizeText(text || '');
        if (!normalized) return ['> （无原文）'];
        return normalized.split('\n').map(line => '> ' + line);
      }

      function loadAnnotations() {
        try {
          return JSON.parse(localStorage.getItem(storageKey) || '[]');
        } catch (error) {
          return [];
        }
      }

      function saveAnnotations() {
        try {
          localStorage.setItem(storageKey, JSON.stringify(annotations));
        } catch (error) {
          // file:// 下 localStorage 行为因浏览器而异，导出 Markdown/JSON 是可靠兜底。
        }
      }

      function showToast(message) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = message || '已复制';
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 1600);
      }

      function unwrapElement(el) {
        const parent = el.parentNode;
        if (!parent) return;
        while (el.firstChild) parent.insertBefore(el.firstChild, el);
        parent.removeChild(el);
        parent.normalize?.();
      }

      function currentFileName() {
        const name = decodeURIComponent(location.pathname.split('/').pop() || 'report.html');
        return /\.html?$/i.test(name) ? name : 'report.html';
      }

      function normalizeText(text) {
        return String(text || '').replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
      }

      function truncate(text, max) {
        const normalized = normalizeText(text);
        return normalized.length > max ? normalized.slice(0, max) + '…' : normalized;
      }

      function escapeHtml(text) {
        return String(text || '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
      }

      function escapeAttr(text) {
        return escapeHtml(text).replace(/`/g, '&#96;');
      }

      function cssEscape(value) {
        if (window.CSS && CSS.escape) return CSS.escape(value || '');
        return String(value || '').replace(/[^a-zA-Z0-9_-]/g, '\\$&');
      }

      function safeFileName(name) {
        return String(name || 'html_report').replace(/[\\/:*?"<>|\s]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 80) || 'html_report';
      }
    })();
  </script>
  <!-- QA_ANNOTATION_SCRIPT_END -->
'''


def strip_annotation_mode(html: str) -> str:
    """删除已经注入过的批注模式，保证脚本可重复运行。"""
    # 先删除整段批注脚本，避免脚本内部的正则文本被下面的标记清理误匹配。
    html = re.sub(r"\n?\s*<script\s+data-qa-script>[\s\S]*?</script>", "", html)
    html = re.sub(r"\n?\s*/\* QA_ANNOTATION_CSS_START:[\s\S]*?QA_ANNOTATION_CSS_END \*/", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_HTML_START:[\s\S]*?QA_ANNOTATION_HTML_END -->", "", html)
    html = re.sub(r"\n?\s*<!-- QA_ANNOTATION_SCRIPT_START -->[\s\S]*?<!-- QA_ANNOTATION_SCRIPT_END -->", "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


def build_annotation_js(output_path: Path | None = None) -> str:
    """生成带来源路径元数据的批注脚本。"""
    meta: dict[str, str] = {}
    if output_path is not None:
        # 在生成阶段写入绝对路径，避免通过 HTTP 预览时 location.pathname 退化为 URL 路径。
        absolute_path = output_path.expanduser().resolve()
        meta = {
            "fileName": absolute_path.name,
            "absolutePath": str(absolute_path),
            "fileUrl": absolute_path.as_uri(),
        }
    return ANNOTATION_JS.replace("__QA_REPORT_META__", json.dumps(meta, ensure_ascii=False))


def inject_annotation_mode(html: str, output_path: Path | None = None) -> str:
    """把 CSS、HTML 容器和 JS 批注逻辑插入到单文件 HTML 中。"""
    html = strip_annotation_mode(html)
    if "</style>" not in html:
        raise ValueError("找不到 </style>，无法注入批注样式")
    if "</body>" not in html:
        raise ValueError("找不到 </body>，无法注入批注脚本")

    html = html.replace("</style>", ANNOTATION_CSS + "\n  </style>", 1)

    # 优先放在现有 toast 后面，复用 html-report 的提示气泡。
    toast = '<div class="toast" id="toast">已复制</div>'
    if toast in html:
        html = html.replace(toast, toast + "\n" + ANNOTATION_HTML, 1)
    else:
        html = html.replace("</body>", ANNOTATION_HTML + "\n</body>", 1)

    return html.replace("</body>", build_annotation_js(output_path) + "\n</body>", 1)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="给 html-report 单文件 HTML 注入离线批注审核模式。")
    parser.add_argument("html", help="输入 HTML 文件。")
    parser.add_argument("-o", "--output", help="输出 HTML 文件；默认覆盖输入文件。")
    return parser.parse_args()


def main() -> None:
    """读取 HTML、注入批注模式并写回文件。"""
    args = parse_args()
    input_path = Path(args.html)
    output_path = Path(args.output) if args.output else input_path

    html = input_path.read_text(encoding="utf-8")
    output_path.write_text(inject_annotation_mode(html, output_path), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
