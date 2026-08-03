  <!-- QA_ANNOTATION_SCRIPT_START -->
  <script data-qa-script>
    (() => {
      const iconQuestion = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M9.8 9a2.4 2.4 0 0 1 4.4 1.35c0 1.65-2.2 1.85-2.2 3.35"></path><path d="M12 17h.01"></path></svg>';
      const iconNote = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>';
      const annotationTargetSelector = 'p, li, tr, table, pre, .panel, .mini, .check, .flow-svg, h2, h3, section';
      const embeddedReviewStartMarker = 'QA_' + 'EMBEDDED_REVIEW_START';
      const embeddedReviewEndMarker = 'QA_' + 'EMBEDDED_REVIEW_END';
      const injectedReportMeta = __QA_REPORT_META__;
      const reportTitle = (document.querySelector('.doc-header h1')?.innerText || document.title || 'HTML 报告').trim();
      const reportFileName = injectedReportMeta.fileName || currentFileName();
      const runtimePath = decodeURIComponent(location.pathname || '');
      const reportAbsolutePath = injectedReportMeta.absolutePath || runtimePath;
      const reportFileUrl = injectedReportMeta.fileUrl || location.href || '';
      // 另存的评论版用运行时路径隔离 localStorage，同时继续把生成期绝对路径保留给 Agent 回查来源。
      const storageKeyPrefix = 'agent-report-annotations:';
      const storageKey = storageKeyPrefix + (runtimePath || reportAbsolutePath) + ':' + reportTitle;
      // 旧版优先使用生成期绝对路径；保留迁移键，避免 HTTP 预览和 Windows file URL 升级后找不到草稿。
      const legacyStorageKey = storageKeyPrefix + (reportAbsolutePath || location.pathname) + ':' + reportTitle;
      const storageKeys = Array.from(new Set([storageKey, legacyStorageKey]));
      const main = document.querySelector('main');
      const launcher = document.getElementById('qaLauncher');
      const launcherLabel = document.getElementById('qaLauncherLabel');
      const launcherCount = document.getElementById('qaLauncherCount');
      const sidebar = document.getElementById('qaSidebar');
      const closeBtn = document.getElementById('qaClose');
      const list = document.getElementById('qaList');
      const filterBar = document.getElementById('qaFilterBar');
      const selectionPopover = document.getElementById('qaSelectionPopover');
      const selectionAction = document.getElementById('qaSelectionAction');
      const selectionActionLabel = document.getElementById('qaSelectionActionLabel');
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
      // 重新关联只存在于当前页面会话；用户确认新选区前不修改任何批注数据。
      let rebindAnnotationId = null;
      let blockSeq = 0;
      // 筛选是当前浏览会话的 UI 状态，不写入 AgentQuestionPack，避免改变交接语义。
      let annotationFilter = 'all';

      if (!main) return;

      // 评论版会保留既有定位 ID；先恢复最大序号，保护 Agent 增段后新 ID 不与旧批注冲突。
      main.querySelectorAll('[data-block-id]').forEach(el => {
        const match = el.dataset.blockId.match(/-b(\d+)$/);
        if (match) blockSeq = Math.max(blockSeq, Number(match[1]));
      });
      main.querySelectorAll('h2, h3, p, li, table, pre, .panel, .mini, .check, .flow-svg, section').forEach(el => {
        if (!el.dataset.blockId) {
          blockSeq += 1;
          const section = nearestSectionId(el) || 'root';
          el.dataset.blockId = section + '-b' + String(blockSeq).padStart(3, '0');
        }
      });

      // 同一路径的报告被重新生成后，localStorage 可能仍保存旧的顺序型 blockId。
      // 先按原文做唯一匹配迁移；找不到或命中不唯一时保留评论，但禁止生成无法定位的交接文件。
      const initialReconciliation = reconcileAnnotationTargets();
      if (initialReconciliation.relocated.length) saveAnnotations();
      renderAnnotations();
      syncAnnotatedState();
      if (initialReconciliation.unresolved.length) {
        setTimeout(() => showToast('有 ' + initialReconciliation.unresolved.length + ' 条评论的原文已变化，请重新关联'), 0);
      }

      launcher?.addEventListener('click', () => {
        // 右上角始终是批注工作区入口，发布动作只从侧栏触发，避免零批注时按钮职责突变。
        setSidebarOpen(!sidebar.classList.contains('open'));
      });
      closeBtn?.addEventListener('click', () => setSidebarOpen(false));
      filterBar?.addEventListener('click', event => {
        const button = event.target.closest('[data-qa-filter]');
        if (!button || !filterBar.contains(button)) return;
        const nextFilter = button.dataset.qaFilter;
        if (!['all', 'question', 'note'].includes(nextFilter)) return;
        annotationFilter = nextFilter;
        renderAnnotations();
      });
      composerSave?.addEventListener('click', saveDraftAnnotation);
      composerText?.addEventListener('keydown', event => {
        if (!isComposerSubmitShortcut(event)) return;
        // 组合键提交与按钮复用同一入口；IME 组字阶段仍由输入法消费 Enter，避免误提交。
        event.preventDefault();
        event.stopPropagation();
        saveDraftAnnotation();
      });
      copyClose?.addEventListener('click', () => copyBackdrop.classList.remove('show'));
      document.getElementById('qaCopyMarkdown')?.addEventListener('click', () => copyText(buildMarkdownPack()));
      document.getElementById('qaDownloadMarkdown')?.addEventListener('click', () => downloadText(safeFileName(reportTitle) + '_questions.md', buildMarkdownPack(), 'text/markdown'));
      document.getElementById('qaSaveReviewHtml')?.addEventListener('click', saveReviewHtml);
      document.getElementById('qaExportPublic')?.addEventListener('click', exportPublicHtml);
      document.getElementById('qaClearAll')?.addEventListener('click', () => {
        if (!annotations.length) return;
        if (!confirm('确定清空本页所有批注吗？')) return;
        annotations = [];
        rebindAnnotationId = null;
        updateSelectionActionMode();
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
          if (cancelAnnotationRebind()) {
            renderAnnotations();
            setSidebarOpen(true);
            showToast('已取消重新关联');
            return;
          }
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
          // 正文拖选会保留合法选区；普通点击造成选区折叠时退出临时模式，且不触碰批注数组。
          if (rebindAnnotationId && !event.target.closest('[data-qa-ui]') && !buildTargetFromSelection() && cancelAnnotationRebind()) {
            renderAnnotations();
            setSidebarOpen(true);
            showToast('已取消重新关联');
          }
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
        if (action === 'rebind-selection') {
          finishAnnotationRebind(selectionTarget);
          return;
        }
        if (action === 'ask-selection' || action === 'note-selection') {
          const target = selectionTarget || buildTargetFromElement(lastContextTarget);
          openComposer(target, action === 'ask-selection' ? '提问' : '注释');
          return;
        }
        if (action === 'ask-block' || action === 'note-block') {
          openComposer(buildTargetFromElement(lastContextTarget), action === 'ask-block' ? '提问' : '注释');
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
        composerTitle.innerHTML = (isNoteKind(draftKind) ? iconNote : iconQuestion) + '<span>' + titlePrefix + draftKind + '</span>';
        composerExcerpt.textContent = truncate(target.selectedText || target.blockText || '', 84);
        composerText.value = options.initialText || '';
        composerText.placeholder = isNoteKind(draftKind) ? '写下这段内容需要注意或修改的地方' : '写下你想让 Agent 回答的问题';
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

      // 只接受跨平台提交组合键，普通 Enter 继续服务多行输入。
      function isComposerSubmitShortcut(event) {
        return event.key === 'Enter'
          && !event.isComposing
          && (event.metaKey || event.ctrlKey);
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
        updateSelectionActionMode();
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

      function findAnnotationElementById(item) {
        if (!item?.blockId) return null;
        return main.querySelector('[data-block-id="' + cssEscape(item.blockId) + '"]');
      }

      // 只把旧定位迁移到唯一命中的当前正文节点；宁可提示用户重新确认，也不把评论猜到错误位置。
      function findAnnotationElementByText(item, candidates) {
        const pool = candidates || buildAnnotationCandidates();
        const blockText = normalizeText(item?.blockText || '');
        const selectedText = normalizeText(item?.selectedText || '');
        const contextWindow = normalizeText(
          String(item?.contextBefore || '').slice(-120)
          + String(item?.selectedText || item?.blockText || '')
          + String(item?.contextAfter || '').slice(0, 120)
        );

        const exactBlock = chooseUniqueAnnotationCandidate(pool, candidate => {
          return Boolean(blockText) && candidate.text === blockText;
        }, item);
        if (exactBlock) return exactBlock;

        if (contextWindow.length >= 12) {
          const contextual = chooseUniqueAnnotationCandidate(pool, candidate => {
            return candidate.text.includes(contextWindow);
          }, item);
          if (contextual) return contextual;
        }

        if (selectedText.length >= 12) {
          return chooseUniqueAnnotationCandidate(pool, candidate => {
            return candidate.text.includes(selectedText);
          }, item);
        }
        return chooseUniqueAnnotationCandidate(pool, candidate => {
          return Boolean(selectedText) && candidate.text === selectedText;
        }, item);
      }

      function buildAnnotationCandidates() {
        return Array.from(main.querySelectorAll(annotationTargetSelector))
          .map(element => ({
            element,
            text: normalizeText(element.innerText || element.textContent || ''),
            sectionTitle: normalizeText(nearestSectionTitle(element))
          }))
          .filter(candidate => candidate.text);
      }

      function chooseUniqueAnnotationCandidate(candidates, predicate, item) {
        let matches = candidates.filter(predicate);
        if (!matches.length) return null;

        const expectedSection = normalizeText(item?.sectionTitle || '');
        const sameSection = matches.filter(candidate => expectedSection && candidate.sectionTitle === expectedSection);
        if (sameSection.length) matches = sameSection;

        // 父级 section/panel 也会包含同一段文字；只保留没有更深命中节点的候选，避免迁移到过大的容器。
        const deepestMatches = matches.filter(candidate => {
          return !matches.some(other => candidate !== other && candidate.element.contains(other.element));
        });
        return deepestMatches.length === 1 ? deepestMatches[0].element : null;
      }

      function reconcileAnnotationTargets() {
        const candidates = buildAnnotationCandidates();
        const relocated = [];
        const unresolved = [];
        annotations.forEach(item => {
          let element = findAnnotationElementById(item);
          if (!element) element = findAnnotationElementByText(item, candidates);
          if (!element) {
            unresolved.push(item);
            return;
          }

          const blockId = ensureBlockId(element);
          if (item.blockId === blockId) return;
          item.blockId = blockId;
          item.sectionId = nearestSectionId(element);
          item.sectionTitle = nearestSectionTitle(element);
          relocated.push(item);
        });
        return { relocated, unresolved };
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
        updateAnnotationFilterControls();
        if (!list) return;
        if (!annotations.length) {
          list.innerHTML = '<div class="qa-empty">还没有批注。选中文本后点击小气泡，或在正文中右键，对段落、表格、图表发起提问。</div>';
          return;
        }
        const visibleAnnotations = annotations.filter(item => matchesAnnotationFilter(item, annotationFilter));
        if (!visibleAnnotations.length) {
          list.innerHTML = '<div class="qa-empty">当前筛选下没有批注。切换“全部”查看其他批注。</div>';
          return;
        }
        list.innerHTML = visibleAnnotations.map(item => {
          const locationMissing = !findAnnotationElementById(item);
          const rebinding = locationMissing && rebindAnnotationId === item.id;
          return `
          <article class="qa-card ${isNoteKind(item.kind) ? 'kind-note' : ''} ${locationMissing ? 'location-missing' : ''} ${rebinding ? 'rebinding' : ''}" data-qa-id="${escapeAttr(item.id)}">
            <div class="qa-card-head">
              <span class="qa-kind">${escapeHtml(item.kind || '提问')}</span>
              <span class="qa-section">${escapeHtml(item.sectionTitle || '未命名章节')}</span>
            </div>
            <button class="qa-quote qa-quote-link" type="button" data-qa-card-action="locate" title="点击原文定位到正文">${escapeHtml(truncate(item.selectedText || item.blockText || '', 520))}</button>
            <div class="qa-question">${escapeHtml(item.text || item.question || '')}</div>
            ${locationMissing ? '<div class="qa-location-warning">' + (rebinding
              ? '正在重新关联：请在正文选中新位置，再点击选区气泡中的“重新关联”；按 Esc 取消。'
              : '原文已变化，当前报告中无法安全定位；可以手动重新关联到当前选区。') + '</div>' : ''}
            <div class="qa-card-actions">
              <button class="qa-mini-btn ${locationMissing ? 'rebind' : ''}" type="button" data-qa-card-action="${locationMissing ? 'rebind' : 'locate'}">${rebinding ? '取消重新关联' : (locationMissing ? '重新关联' : '定位')}</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="edit">编辑</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="copy">复制此条</button>
              <button class="qa-mini-btn" type="button" data-qa-card-action="delete">删除</button>
            </div>
          </article>
        `;
        }).join('');
        list.querySelectorAll('[data-qa-card-action]').forEach(btn => {
          btn.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const card = event.target.closest('.qa-card');
            const item = annotations.find(x => x.id === card.dataset.qaId);
            if (!item) return;
            const action = event.target.closest('[data-qa-card-action]')?.dataset.qaCardAction;
            if (action === 'locate') locateAnnotation(item);
            if (action === 'rebind') {
              if (rebindAnnotationId === item.id) {
                cancelAnnotationRebind();
                renderAnnotations();
                showToast('已取消重新关联');
              } else {
                startAnnotationRebind(item);
              }
            }
            if (action === 'edit') {
              if (cancelAnnotationRebind()) renderAnnotations();
              openEditAnnotation(item, card);
            }
            if (action === 'copy') copyText(buildSinglePrompt(item));
            if (action === 'delete') {
              if (rebindAnnotationId === item.id) {
                rebindAnnotationId = null;
                updateSelectionActionMode();
              }
              annotations = annotations.filter(x => x.id !== item.id);
              saveAnnotations();
              syncAnnotatedState();
              renderAnnotations();
            }
          });
        });
      }

      function matchesAnnotationFilter(item, filter) {
        if (filter === 'note') return isNoteKind(item?.kind);
        if (filter === 'question') return !isNoteKind(item?.kind);
        return true;
      }

      function updateAnnotationFilterControls() {
        if (!filterBar) return;
        const counts = {
          all: annotations.length,
          question: annotations.filter(item => matchesAnnotationFilter(item, 'question')).length,
          note: annotations.filter(item => matchesAnnotationFilter(item, 'note')).length
        };
        filterBar.querySelectorAll('[data-qa-filter]').forEach(button => {
          const filter = button.dataset.qaFilter || 'all';
          const active = filter === annotationFilter;
          button.classList.toggle('active', active);
          button.setAttribute('aria-pressed', String(active));
          const count = button.querySelector('[data-qa-filter-count]');
          if (count) count.textContent = String(counts[filter] ?? 0);
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

      // 失效批注才允许进入手动模式；正常批注继续使用定位，避免同一动作承担两种职责。
      function startAnnotationRebind(item) {
        if (!item || findAnnotationElementById(item)) return;
        rebindAnnotationId = item.id;
        cachedSelectionTarget = null;
        window.getSelection()?.removeAllRanges();
        closeComposer();
        hideFloatingUi();
        updateSelectionActionMode();
        renderAnnotations();
        // 收起侧栏后正文才能在桌面和窄屏上完整参与拖选；右上角入口仍可重新打开并取消。
        setSidebarOpen(false);
        showToast('请在正文选中新位置，再点击“重新关联”；Esc 可取消');
      }

      // 临时模式退出只清理 UI 状态；批注内容与旧锚点必须保持原样，直到用户确认合法新选区。
      function cancelAnnotationRebind() {
        if (!rebindAnnotationId) return false;
        rebindAnnotationId = null;
        cachedSelectionTarget = null;
        updateSelectionActionMode();
        hideSelectionPopover();
        window.getSelection()?.removeAllRanges();
        return true;
      }

      function updateSelectionActionMode() {
        if (!selectionAction || !selectionActionLabel) return;
        const rebinding = Boolean(rebindAnnotationId);
        selectionAction.dataset.qaAction = rebinding ? 'rebind-selection' : 'note-selection';
        selectionAction.title = rebinding ? '将批注关联到当前选区' : '添加注释';
        selectionActionLabel.textContent = rebinding ? '重新关联' : '注释';
      }

      // 只替换定位字段，保留 id、批注正文、类型、创建时间和来源路径，避免手动迁移变成删除重建。
      function buildReboundAnnotation(item, target) {
        return {
          ...item,
          blockId: target.blockId,
          sectionId: target.sectionId,
          sectionTitle: target.sectionTitle,
          selectedText: target.selectedText,
          blockText: target.blockText,
          contextBefore: target.contextBefore,
          contextAfter: target.contextAfter
        };
      }

      function finishAnnotationRebind(target) {
        const index = annotations.findIndex(item => item.id === rebindAnnotationId);
        // 缓存选区也必须仍属于正文；无效选择安全退出，不对原批注做部分更新。
        if (index < 0 || !target?.element || !main.contains(target.element)) {
          cancelAnnotationRebind();
          renderAnnotations();
          setSidebarOpen(true);
          showToast('未找到有效正文选区，已取消重新关联');
          return;
        }
        annotations[index] = buildReboundAnnotation(annotations[index], target);
        rebindAnnotationId = null;
        cachedSelectionTarget = null;
        updateSelectionActionMode();
        hideSelectionPopover();
        saveAnnotations();
        syncAnnotatedState();
        renderAnnotations();
        setSidebarOpen(true);
        showToast('已重新关联到当前选区');
      }

      function updateLauncherMode() {
        const count = annotations.length;
        // 文案保持稳定，数量只表达当前工作状态；零条也必须能进入侧栏并写回合法空包。
        if (launcherLabel) launcherLabel.textContent = '批注';
        if (launcherCount) {
          launcherCount.textContent = count > 0 ? String(count) : '';
          launcherCount.hidden = count === 0;
        }
        launcher?.setAttribute('aria-label', count > 0
          ? '打开报告批注，当前 ' + count + ' 条'
          : '打开报告批注');
      }

      function locateAnnotation(item) {
        const reconciliation = reconcileAnnotationTargets();
        if (reconciliation.relocated.length) {
          saveAnnotations();
          syncAnnotatedState();
          renderAnnotations();
        }
        const el = findAnnotationElementById(item);
        if (!el) {
          showToast('无法定位：报告内容已变化，请使用“重新关联”选择新原文');
          return;
        }
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

      // 把当前批注包直接写入 HTML，成功覆盖或另存后即可把该文件交给 Agent。
      async function saveReviewHtml() {
        const reconciliation = reconcileAnnotationTargets();
        if (reconciliation.relocated.length) {
          saveAnnotations();
          syncAnnotatedState();
          renderAnnotations();
        }
        if (reconciliation.unresolved.length) {
          setSidebarOpen(true);
          showToast('有 ' + reconciliation.unresolved.length + ' 条评论无法定位，请先重新关联');
          return;
        }
        const currentName = currentFileName();
        const result = await saveHtmlFile({
          suggestedName: currentName,
          fallbackName: reviewFallbackFileName(currentName),
          buildHtml: buildReviewedHtml
        });
        if (result === 'saved') {
          clearStoredAnnotations();
        }
        if (result === 'saved') {
          showToast('批注已写入 HTML，可将该文件交给 Agent');
        }
        if (result === 'downloaded') {
          showToast('已发起批注版下载，原页草稿仍保留');
        }
      }

      // 发布版只保留正文；默认另存，避免覆盖唯一的评论版。
      async function exportPublicHtml() {
        const shouldExport = confirm('导出不含批注的发布版 HTML。\n\n确定：选择保存位置，建议另存，避免覆盖评论版。\n取消：取消导出。');
        if (!shouldExport) return;
        const currentName = currentFileName();
        const publicName = fileNameWithSuffix(currentName, '_public');
        const result = await saveHtmlFile({
          suggestedName: publicName,
          fallbackName: publicName,
          buildHtml: buildPublicHtml
        });
        if (result === 'saved') showToast('已导出无批注版');
        if (result === 'downloaded') showToast('浏览器不支持直接保存，已下载无批注版');
      }

      // 先取得文件句柄再构建大 HTML，保护浏览器要求的用户激活；不支持时退化为下载。
      async function saveHtmlFile({ suggestedName, fallbackName, buildHtml }) {
        if (window.showSaveFilePicker) {
          try {
            const handle = await window.showSaveFilePicker({
              suggestedName,
              types: [{ description: 'HTML 文件', accept: { 'text/html': ['.html'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(buildHtml());
            await writable.close();
            return 'saved';
          } catch (error) {
            if (error && error.name === 'AbortError') return 'cancelled';
          }
        }
        // 不支持 File System Access API 的浏览器无法静默覆盖本地文件，只能下载当前文件名作为兜底。
        downloadText(fallbackName, buildHtml(), 'text/html');
        return 'downloaded';
      }

      // 保存评论版时清理瞬时 UI，正文高亮会在重新打开后由内嵌批注重新生成。
      function buildReviewedHtml() {
        const clone = document.documentElement.cloneNode(true);
        clone.querySelectorAll('[data-qa-review-data]').forEach(el => el.remove());
        clone.querySelectorAll('.qa-sidebar.open').forEach(el => el.classList.remove('open'));
        clone.querySelectorAll('.qa-selection-popover.show, .qa-context-menu.show, .qa-composer.show, .qa-copy-backdrop.show').forEach(el => el.classList.remove('show'));
        clone.querySelectorAll('mark.qa-highlight').forEach(unwrapElement);
        clone.querySelectorAll('.qa-annotated-block, .qa-focus-pulse').forEach(el => {
          el.classList.remove('qa-annotated-block', 'qa-focus-pulse');
        });
        clone.querySelector('body')?.classList.remove('qa-panel-open');
        clone.querySelector('#qaLauncher')?.setAttribute('aria-expanded', 'false');
        const clonedList = clone.querySelector('#qaList');
        if (clonedList) clonedList.innerHTML = '';
        ['#qaComposerTitle', '#qaComposerExcerpt'].forEach(selector => {
          const element = clone.querySelector(selector);
          if (element) element.textContent = '';
        });
        ['#qaComposerText', '#qaCopyTextarea'].forEach(selector => {
          const textarea = clone.querySelector(selector);
          if (!textarea) return;
          textarea.value = '';
          textarea.textContent = '';
        });

        let result = '<!doctype html>\n' + clone.outerHTML;
        result = stripEmbeddedReviewBlock(result);
        const reviewBlock = buildEmbeddedReviewBlock();
        result = result.includes('</head>')
          ? result.replace('</head>', reviewBlock + '\n</head>')
          : result.replace('</body>', reviewBlock + '\n</body>');
        return result.replace(/\n{3,}/g, '\n\n');
      }

      // 标记名在源码中拆开拼接，避免清理整页 HTML 时误匹配批注脚本自身。
      function buildEmbeddedReviewBlock() {
        const json = serializeReviewPack(buildJsonPack());
        return [
          '  <!' + '-- ' + embeddedReviewStartMarker + ': Agent 读取并逐条处理以下评论结果。 --' + '>',
          '  <' + 'script type="application/json" id="qaEmbeddedReviewData" data-qa-review-data>',
          json.split('\n').map(line => '  ' + line).join('\n'),
          '  </' + 'script>',
          '  <!' + '-- ' + embeddedReviewEndMarker + ' --' + '>'
        ].join('\n');
      }

      // script 是 raw-text 元素，必须使用 JSON Unicode 转义阻断结束标签和 HTML 注入。
      function serializeReviewPack(pack) {
        const escapes = {
          '<': '\\u003c',
          '>': '\\u003e',
          '&': '\\u0026',
          '\u2028': '\\u2028',
          '\u2029': '\\u2029'
        };
        return JSON.stringify(pack, null, 2).replace(/[<>&\u2028\u2029]/g, char => escapes[char]);
      }

      // 删除已有内嵌包后再写入，保证连续保存始终只有一份 AgentQuestionPack。
      function stripEmbeddedReviewBlock(html) {
        let result = String(html || '');
        const startToken = '<!' + '-- ' + embeddedReviewStartMarker;
        const endToken = embeddedReviewEndMarker + ' --' + '>';
        let start = result.indexOf(startToken);
        while (start >= 0) {
          const end = result.indexOf(endToken, start);
          if (end < 0) break;
          result = result.slice(0, start) + result.slice(end + endToken.length);
          start = result.indexOf(startToken);
        }
        return result;
      }

      function buildPublicHtml() {
        const clone = document.documentElement.cloneNode(true);
        clone.querySelectorAll('[data-qa-ui], [data-qa-script], [data-qa-review-data]').forEach(el => el.remove());
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
        result = stripEmbeddedReviewBlock(result);
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
          lines.push((isNoteKind(item.kind) ? '我的注释：' : '我的问题：'));
          lines.push('');
          lines.push(item.text || item.question || '');
          lines.push('');
          lines.push('请 Agent 处理：');
          lines.push('');
          lines.push(isNoteKind(item.kind)
            ? '请结合原文和上下文判断这条注释是否合理，并给出报告修改建议。'
            : '请结合原文、上下文和报告结论解释这个问题。如果原报告存在表达不清、逻辑跳跃、证据不足或结论错误，请指出并给出修改建议。');
          lines.push('');
        });
        return lines.join('\n');
      }

      function buildJsonPack() {
        return {
          type: 'AgentQuestionPack',
          version: '0.3.0',
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
          delivery: {
            mode: 'embedded-html',
            status: 'ready-for-agent',
            instruction: '以当前承载此包的 HTML 为回写目标；逐条处理 annotations；完成后删除评论区块，重新运行 inject_annotation_mode.py，再运行不带 --require-review-pack 的 check_html_report.py。'
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
        lines.push('', isNoteKind(kind) ? '我的注释：' : '我的问题：', '', item.text || item.question || '', '', '请结合上下文处理。');
        return lines.join('\n');
      }

      function isNoteKind(kind) {
        // 兼容旧评论包中的“批注”，新建内容统一使用更简洁的“注释”。
        return kind === '注释' || kind === '批注';
      }

      function quoteMarkdown(text) {
        const normalized = normalizeText(text || '');
        if (!normalized) return ['> （无原文）'];
        return normalized.split('\n').map(line => '> ' + line);
      }

      function loadAnnotations() {
        for (const key of storageKeys) {
          try {
            const stored = localStorage.getItem(key);
            if (stored !== null) {
              const parsed = JSON.parse(stored);
              if (Array.isArray(parsed)) {
                // 读取旧键时迁移，读取新键时也清掉残留旧值；清理失败不影响返回已成功解析的草稿。
                try {
                  if (key !== storageKey) {
                    localStorage.setItem(storageKey, stored);
                  }
                  storageKeys.filter(candidate => candidate !== storageKey).forEach(candidate => localStorage.removeItem(candidate));
                } catch (error) {
                  // 迁移失败仍返回已成功读取的草稿，后续保存会再次尝试收敛到新键。
                }
                return normalizeAnnotations(parsed);
              }
            }
          } catch (error) {
            // 单个 localStorage 键不可用或损坏时继续尝试兼容键和 HTML 内嵌评论包。
          }
        }
        return normalizeAnnotations(readEmbeddedReviewPack()?.annotations);
      }

      // 内嵌包只作为无本地更新时的持久化来源，显式清空的 [] 不会被旧批注复活。
      function readEmbeddedReviewPack() {
        const node = document.getElementById('qaEmbeddedReviewData');
        if (!node?.textContent) return null;
        try {
          const pack = JSON.parse(node.textContent);
          if (pack?.type !== 'AgentQuestionPack' || !Array.isArray(pack.annotations)) return null;
          return pack;
        } catch (error) {
          return null;
        }
      }

      // 丢弃损坏的非对象条目，避免侧栏渲染读取无效字段。
      function normalizeAnnotations(items) {
        return Array.isArray(items) ? items.filter(item => item && typeof item === 'object') : [];
      }

      function saveAnnotations() {
        try {
          localStorage.setItem(storageKey, JSON.stringify(annotations));
          storageKeys.filter(key => key !== storageKey).forEach(key => localStorage.removeItem(key));
        } catch (error) {
          // file:// 下 localStorage 行为因浏览器而异，内嵌评论版和 Markdown 是可靠兜底。
        }
      }

      // 直接保存成功后让磁盘内嵌包成为下次打开的基线，Agent 清除该区块后不会残留旧批注。
      function clearStoredAnnotations() {
        storageKeys.forEach(key => {
          try {
            localStorage.removeItem(key);
          } catch (error) {
            // localStorage 不可用不影响已经写入磁盘的评论结果。
          }
        });
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

      // 下载兜底使用区分评论版/发布版的文件名，避免浏览器静默覆盖错误文件。
      function fileNameWithSuffix(fileName, suffix) {
        const match = String(fileName || 'report.html').match(/^(.*?)(\.html?)$/i);
        const base = match ? match[1] : 'report';
        const extension = match ? match[2] : '.html';
        return (base.endsWith(suffix) ? base : base + suffix) + extension;
      }

      // 已是 _reviewed 的页面再次走下载兜底时改用 _copy，避免默认文件名与当前草稿路径碰撞。
      function reviewFallbackFileName(fileName) {
        const reviewedName = fileNameWithSuffix(fileName, '_reviewed');
        return reviewedName === fileName ? fileNameWithSuffix(fileName, '_copy') : reviewedName;
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
