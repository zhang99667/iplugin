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
      let editingAnnotationId = null;
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

      function openComposer(target, kind, options = {}) {
        if (!target) return;
        draftTarget = target;
        draftKind = kind || '提问';
        editingAnnotationId = options.editingId || null;
        const titlePrefix = editingAnnotationId ? '编辑' : '';
        composerTitle.innerHTML = (draftKind === '批注' ? iconNote : iconQuestion) + '<span>' + titlePrefix + draftKind + '</span>';
        composerExcerpt.textContent = truncate(target.selectedText || target.blockText || '', 84);
        composerText.value = options.initialText || '';
        composerText.placeholder = draftKind === '批注' ? '写下这段内容需要注意或修改的地方' : '写下你想让 Agent 回答的问题';
        positionComposer(target);
        composer.classList.add('show');
        setTimeout(() => composerText.focus(), 0);
      }

      function closeComposer() {
        composer.classList.remove('show');
        draftTarget = null;
        editingAnnotationId = null;
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
        if (editingAnnotationId) {
          const index = annotations.findIndex(item => item.id === editingAnnotationId);
          if (index < 0) {
            closeComposer();
            return;
          }
          annotations[index] = {
            ...annotations[index],
            kind: draftKind,
            text,
            updatedAt: new Date().toISOString()
          };
          saveAnnotations();
          syncAnnotatedState();
          renderAnnotations();
          closeComposer();
          setSidebarOpen(true);
          showToast('已更新' + draftKind);
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
              <button class="qa-mini-btn" type="button" data-qa-card-action="edit">编辑</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="copy">复制此条</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="delete">删除</button>
            </div>
          </article>
        `).join('');
        list.querySelectorAll('[data-qa-card-action]').forEach(btn => {
          btn.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const card = event.target.closest('.qa-card');
            const item = annotations.find(x => x.id === card.dataset.qaId);
            if (!item) return;
            const action = event.target.dataset.qaCardAction;
            if (action === 'locate') locateAnnotation(item);
            if (action === 'edit') openEditAnnotation(item, card);
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

      function openEditAnnotation(item, anchor) {
        const el = main.querySelector('[data-block-id="' + cssEscape(item.blockId) + '"]') || anchor;
        openComposer({
          mode: 'edit',
          element: el,
          blockId: item.blockId,
          sectionId: item.sectionId,
          sectionTitle: item.sectionTitle,
          selectedText: item.selectedText,
          blockText: item.blockText,
          contextBefore: item.contextBefore,
          contextAfter: item.contextAfter
        }, item.kind || '提问', {
          editingId: item.id,
          initialText: item.text || item.question || ''
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
