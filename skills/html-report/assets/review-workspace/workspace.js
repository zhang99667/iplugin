/* HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_START */
(() => {
  "use strict";

  const RUNTIME_NAME = "HtmlReportReviewWorkspace";

  function createElement(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function lineSet(values) {
    return new Set(Array.isArray(values) ? values : []);
  }

  function htmlToText(value) {
    const container = document.createElement("div");
    container.innerHTML = value || "";
    return container.textContent || "";
  }

  async function copyText(value) {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(value);
        return;
      } catch (_error) {
        // file:// 页面可能没有 Clipboard API 权限，下面回退到同步复制。
      }
    }

    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("浏览器拒绝复制");
  }

  class ReviewWorkspace {
    constructor(shell) {
      this.shell = shell;
      this.mountPoint = shell.querySelector("[data-review-workspace-root]");
      this.dataNode = shell.querySelector("[data-review-workspace-data]");
      this.config = this.parseConfig();
      this.filesById = new Map(this.config.files.map(file => [file.id, file]));
      this.currentId = this.config.files[0]?.id || "";
      this.syncScroll = true;
      this.diffOnly = false;
      this.syncing = false;
      this.reviewed = this.loadReviewed();
      this.elements = {};
    }

    parseConfig() {
      if (!this.mountPoint || !this.dataNode) {
        throw new Error("Review Workspace 缺少挂载点或数据节点");
      }
      const config = JSON.parse(this.dataNode.textContent || "{}");
      if (!Array.isArray(config.versions) || config.versions.length < 2 || config.versions.length > 3) {
        throw new Error("Review Workspace 只支持 2 到 3 个版本");
      }
      if (!Array.isArray(config.files) || !config.files.length) {
        throw new Error("Review Workspace 至少需要一个文件");
      }
      return config;
    }

    loadReviewed() {
      try {
        const value = JSON.parse(localStorage.getItem(this.config.storageKey) || "[]");
        const validIds = Array.isArray(value) ? value.filter(id => this.filesById.has(id)) : [];
        return new Set(validIds);
      } catch (_error) {
        return new Set();
      }
    }

    saveReviewed() {
      try {
        localStorage.setItem(this.config.storageKey, JSON.stringify([...this.reviewed]));
      } catch (_error) {
        // 隐私模式或 file:// 策略可能禁用持久化；当前页面仍保留内存状态。
      }
    }

    mount() {
      this.renderFrame();
      this.cacheElements();
      this.populateFilters();
      this.renderPanes();
      this.bindEvents();
      this.renderFile(this.currentId);
      this.shell.dataset.reviewWorkspaceReady = "true";
    }

    renderFrame() {
      this.mountPoint.innerHTML = `
        <div class="rw-toolbar">
          <input class="rw-input rw-search" data-rw-role="search" type="search"
            placeholder="筛选文件名、结论或路径" aria-label="筛选文件" />
          <select class="rw-input" data-rw-role="status-filter" aria-label="按结论筛选"></select>
          <button class="rw-button is-active" data-rw-role="sync" type="button">同步滚动：开</button>
          <button class="rw-button" data-rw-role="diff" type="button">只看差异：关</button>
          <button class="rw-button" data-rw-role="focus" type="button">跳到参考行</button>
          <select class="rw-input" data-rw-role="jump-version" aria-label="跳转版本"></select>
          <input class="rw-input rw-line-input" data-rw-role="jump-line" type="number"
            min="1" placeholder="行号" aria-label="跳转行号" />
          <button class="rw-button" data-rw-role="jump" type="button">跳转</button>
          <button class="rw-button" data-rw-role="idea" type="button">IDEA 打开</button>
          <button class="rw-button" data-rw-role="reviewed" type="button">标记已审阅</button>
          <span class="rw-toolbar-spacer"></span>
          <span class="rw-progress" data-rw-role="progress"></span>
        </div>
        <div class="rw-body">
          <nav class="rw-file-nav" data-rw-role="file-nav" aria-label="文件列表"></nav>
          <div class="rw-stage">
            <div class="rw-overview" data-rw-role="overview"></div>
            <div class="rw-panes" data-rw-role="panes"></div>
            <div class="rw-legend" data-rw-role="legend"></div>
            <p class="rw-live-status" data-rw-role="live-status" aria-live="polite"></p>
          </div>
        </div>`;
    }

    cacheElements() {
      this.mountPoint.querySelectorAll("[data-rw-role]").forEach(element => {
        this.elements[element.dataset.rwRole] = element;
      });
    }

    populateFilters() {
      const allOption = createElement("option", "", "全部结论");
      allOption.value = "all";
      this.elements["status-filter"].appendChild(allOption);

      const seen = new Set();
      this.config.files.forEach(file => {
        const status = file.status || {};
        if (!status.id || seen.has(status.id)) return;
        seen.add(status.id);
        const option = createElement("option", "", status.label || status.id);
        option.value = status.id;
        this.elements["status-filter"].appendChild(option);
      });

      this.config.versions.forEach(version => {
        const option = createElement("option", "", version.jumpLabel || version.label);
        option.value = version.id;
        this.elements["jump-version"].appendChild(option);
      });
    }

    renderPanes() {
      const panes = this.elements.panes;
      panes.style.setProperty("--rw-pane-count", String(this.config.versions.length));
      this.config.versions.forEach(version => {
        const pane = createElement("section", "rw-code-pane");
        pane.dataset.rwVersion = version.id;

        const header = createElement("header", "rw-pane-header");
        const titleWrap = createElement("div");
        titleWrap.appendChild(createElement("span", "rw-pane-title", version.label));
        const ref = createElement("span", "rw-pane-ref");
        ref.dataset.rwRef = version.id;
        titleWrap.appendChild(ref);

        const copy = createElement("button", "rw-pane-copy", "复制");
        copy.type = "button";
        copy.dataset.rwCopyVersion = version.id;
        copy.setAttribute("aria-label", `复制 ${version.label} 全文`);

        header.append(titleWrap, copy);
        const scroll = createElement("div", "rw-code-scroll");
        scroll.dataset.rwScrollVersion = version.id;
        const lines = createElement("div", "rw-code-lines");
        scroll.appendChild(lines);
        pane.append(header, scroll);
        panes.appendChild(pane);
      });

      this.renderLegend();
    }

    renderLegend() {
      const legend = this.config.legend || {};
      const items = [
        ["rw-dot-focus", legend.focus || "参考行 / 修复聚焦行"],
        ["rw-dot-primary", legend.primary || "主要版本差异"],
        ["rw-dot-secondary", legend.secondary || "次要版本差异"],
      ];
      items.forEach(([dotClass, label]) => {
        const item = createElement("span", "rw-legend-item");
        item.append(createElement("i", `rw-legend-dot ${dotClass}`), document.createTextNode(label));
        this.elements.legend.appendChild(item);
      });
    }

    bindEvents() {
      this.elements.search.addEventListener("input", () => this.renderNav());
      this.elements["status-filter"].addEventListener("change", () => this.renderNav());
      this.elements.sync.addEventListener("click", () => this.toggleSync());
      this.elements.diff.addEventListener("click", () => this.toggleDiff());
      this.elements.focus.addEventListener("click", () => this.jumpToFocus());
      this.elements.jump.addEventListener("click", () => this.jumpFromToolbar());
      this.elements["jump-line"].addEventListener("keydown", event => {
        if (event.key === "Enter") this.jumpFromToolbar();
      });
      this.elements.idea.addEventListener("click", () => this.openInIdea());
      this.elements.reviewed.addEventListener("click", () => this.toggleReviewed());

      this.mountPoint.querySelectorAll("[data-rw-copy-version]").forEach(button => {
        button.addEventListener("click", () => this.copyVersion(button.dataset.rwCopyVersion));
      });

      this.scrollElements().forEach(source => {
        source.addEventListener("scroll", () => this.syncOtherScrolls(source));
      });
    }

    scrollElements() {
      return [...this.mountPoint.querySelectorAll("[data-rw-scroll-version]")];
    }

    renderFile(id, jump = true) {
      const file = this.filesById.get(id);
      if (!file) return;
      this.currentId = id;
      this.renderOverview(file);
      this.config.versions.forEach(version => this.renderLines(file, version));
      this.renderNav();
      this.updateReviewed();
      this.updateIdeaButton(file);
      if (jump) requestAnimationFrame(() => this.jumpToFocus());
    }

    renderOverview(file) {
      const overview = this.elements.overview;
      overview.replaceChildren();

      const top = createElement("div", "rw-overview-top");
      const titleGroup = createElement("div");
      titleGroup.appendChild(createElement("h3", "", file.filename));

      const meta = createElement("div", "rw-meta");
      const path = createElement(file.ideaHref ? "a" : "span", "path rw-path", file.displayPath || file.path);
      path.title = file.absolutePath || file.path || "";
      if (file.ideaHref) {
        path.classList.add("file-link");
        path.href = file.ideaHref;
      }
      meta.appendChild(path);

      const status = file.status || {};
      const statusChip = createElement("span", `rw-status rw-tone-${status.tone || "neutral"}`, status.label || "未分类");
      const relation = createElement("span", "rw-relation", file.relation || "版本关系未标注");
      meta.append(statusChip, relation);
      titleGroup.appendChild(meta);

      const reference = createElement("div", "rw-reference", file.reference || "");
      top.append(titleGroup, reference);

      const conclusion = createElement("p");
      conclusion.append(createElement("b", "", "结论："), document.createTextNode(file.conclusion || "未提供"));
      const action = createElement("p");
      action.append(createElement("b", "", "处理："), document.createTextNode(file.action || "未提供"));
      overview.append(top, conclusion, action);
    }

    renderLines(file, version) {
      const source = file.versions[version.id];
      const pane = this.mountPoint.querySelector(`[data-rw-version="${CSS.escape(version.id)}"]`);
      const lines = pane.querySelector(".rw-code-lines");
      const marks = source.marks || {};
      const primary = lineSet(marks.primary);
      const secondary = lineSet(marks.secondary);
      const focus = lineSet(marks.focus);
      const context = lineSet(marks.context);
      const fragment = document.createDocumentFragment();

      source.lines.forEach((sourceHtml, index) => {
        const lineNumber = index + 1;
        const row = createElement("div", "rw-code-line");
        row.dataset.line = String(lineNumber);
        if (primary.has(lineNumber)) row.classList.add("rw-mark-primary");
        if (secondary.has(lineNumber)) row.classList.add("rw-mark-secondary");
        if (focus.has(lineNumber)) row.classList.add("rw-focus-line");
        if (context.has(lineNumber)) row.classList.add("rw-keep-line");

        const number = createElement("span", "rw-ln", String(lineNumber));
        const code = createElement("span", "rw-src");
        // sourceHtml 只来自 build_review_workspace.py 的安全静态高亮结果。
        code.innerHTML = sourceHtml || "&nbsp;";
        row.append(number, code);
        fragment.appendChild(row);
      });
      lines.replaceChildren(fragment);

      const ref = pane.querySelector(`[data-rw-ref="${CSS.escape(version.id)}"]`);
      ref.textContent = `${source.ref || version.ref || ""} · ${source.lines.length} 行`;
    }

    renderNav() {
      const query = this.elements.search.value.trim().toLowerCase();
      const statusFilter = this.elements["status-filter"].value;
      const matched = this.config.files.filter(file => {
        const status = file.status || {};
        const searchable = [
          file.filename,
          file.path,
          file.displayPath,
          status.label,
          file.relation,
          file.conclusion,
          file.action,
        ].filter(Boolean).join(" ").toLowerCase();
        return (statusFilter === "all" || status.id === statusFilter) && (!query || searchable.includes(query));
      });

      const nav = this.elements["file-nav"];
      nav.replaceChildren();
      if (!matched.length) {
        nav.appendChild(createElement("div", "rw-file-nav-empty", "没有匹配文件"));
        return;
      }

      matched.forEach(file => {
        const status = file.status || {};
        const button = createElement("button", "rw-file-item");
        button.type = "button";
        button.dataset.fileId = file.id;
        button.classList.toggle("is-active", file.id === this.currentId);
        button.classList.toggle("is-reviewed", this.reviewed.has(file.id));

        button.appendChild(createElement("span", "rw-file-name", file.filename));
        const sub = createElement("span", "rw-file-sub");
        sub.append(
          createElement("span", `rw-status rw-tone-${status.tone || "neutral"}`, status.label || "未分类"),
          createElement("span", "", file.group || file.repo || "")
        );
        button.appendChild(sub);
        button.addEventListener("click", () => this.renderFile(file.id));
        nav.appendChild(button);
      });
    }

    toggleSync() {
      this.syncScroll = !this.syncScroll;
      this.elements.sync.textContent = `同步滚动：${this.syncScroll ? "开" : "关"}`;
      this.elements.sync.classList.toggle("is-active", this.syncScroll);
    }

    toggleDiff() {
      this.diffOnly = !this.diffOnly;
      this.shell.classList.toggle("rw-diff-only", this.diffOnly);
      this.elements.diff.textContent = `只看差异：${this.diffOnly ? "开" : "关"}`;
      this.elements.diff.classList.toggle("is-active", this.diffOnly);
      requestAnimationFrame(() => this.jumpToFocus());
    }

    syncOtherScrolls(source) {
      if (!this.syncScroll || this.syncing) return;
      this.syncing = true;
      const max = source.scrollHeight - source.clientHeight;
      const ratio = max > 0 ? source.scrollTop / max : 0;
      this.scrollElements().forEach(target => {
        if (target === source) return;
        const targetMax = target.scrollHeight - target.clientHeight;
        target.scrollTop = targetMax * ratio;
        target.scrollLeft = source.scrollLeft;
      });
      requestAnimationFrame(() => {
        this.syncing = false;
      });
    }

    jumpFromToolbar() {
      const line = Number(this.elements["jump-line"].value);
      if (line > 0) this.jumpTo(this.elements["jump-version"].value, line);
    }

    jumpTo(versionId, line) {
      const scroll = this.mountPoint.querySelector(`[data-rw-scroll-version="${CSS.escape(versionId)}"]`);
      const row = scroll?.querySelector(`.rw-code-line[data-line="${line}"]`);
      if (!scroll || !row) {
        this.notify(`${versionId} 没有第 ${line} 行`);
        return;
      }

      const scrollRect = scroll.getBoundingClientRect();
      const rowRect = row.getBoundingClientRect();
      scroll.scrollTop += rowRect.top - scrollRect.top - (scroll.clientHeight - row.clientHeight) / 2;
      scroll.scrollLeft = 0;
      row.classList.add("rw-search-hit");
      setTimeout(() => row.classList.remove("rw-search-hit"), 1400);
    }

    jumpToFocus() {
      const file = this.filesById.get(this.currentId);
      if (!file) return;
      for (const version of [...this.config.versions].reverse()) {
        const focus = file.versions[version.id]?.marks?.focus || [];
        if (!focus.length) continue;
        this.elements["jump-version"].value = version.id;
        this.elements["jump-line"].value = String(focus[0]);
        this.jumpTo(version.id, focus[0]);
        return;
      }
      this.notify("当前文件没有参考行");
    }

    async copyVersion(versionId) {
      const file = this.filesById.get(this.currentId);
      const source = file?.versions?.[versionId];
      if (!source) return;
      const text = source.lines.map(htmlToText).join("\n");
      try {
        await copyText(text);
        this.notify(`已复制 ${versionId} 全文`);
      } catch (_error) {
        this.notify("复制失败，请手动选择代码");
      }
    }

    updateIdeaButton(file) {
      this.elements.idea.disabled = !file.ideaHref;
      this.elements.idea.title = file.ideaHref ? "在 IDEA 中打开当前文件" : "当前文件没有绝对路径";
    }

    openInIdea() {
      const file = this.filesById.get(this.currentId);
      if (file?.ideaHref) window.location.href = file.ideaHref;
    }

    toggleReviewed() {
      if (this.reviewed.has(this.currentId)) this.reviewed.delete(this.currentId);
      else this.reviewed.add(this.currentId);
      this.saveReviewed();
      this.renderNav();
      this.updateReviewed();
    }

    updateReviewed() {
      const isReviewed = this.reviewed.has(this.currentId);
      this.elements.reviewed.textContent = isReviewed ? "取消已审阅" : "标记已审阅";
      this.elements.reviewed.classList.toggle("is-active", isReviewed);
      this.elements.progress.textContent = `已审阅 ${this.reviewed.size} / ${this.config.files.length}`;
    }

    notify(message) {
      const toast = document.querySelector(".toast");
      if (toast) {
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(toast.__rwTimer);
        toast.__rwTimer = setTimeout(() => toast.classList.remove("show"), 1500);
      }
      this.elements["live-status"].textContent = message;
    }
  }

  function initAll() {
    document.querySelectorAll("[data-review-workspace]").forEach(shell => {
      if (shell.dataset.reviewWorkspaceReady === "true") return;
      try {
        new ReviewWorkspace(shell).mount();
      } catch (error) {
        shell.classList.add("rw-load-error");
        const mountPoint = shell.querySelector("[data-review-workspace-root]") || shell;
        mountPoint.textContent = `Review Workspace 加载失败：${error.message}`;
        console.error(error);
      }
    });
  }

  window[RUNTIME_NAME] = { initAll };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll, { once: true });
  } else {
    initAll();
  }
})();
/* HTML_REPORT_REVIEW_WORKSPACE_RUNTIME_END */
