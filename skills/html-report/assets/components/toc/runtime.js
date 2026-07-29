/* HTML_REPORT_TOC_RUNTIME_START */
(() => {
  document.querySelectorAll('.layout-with-toc').forEach(layout => {
    if (layout.dataset.tocReady === 'true') return;
    const button = layout.querySelector('.toc-toggle');
    if (!button) return;
    layout.dataset.tocReady = 'true';
    const icon = button.querySelector('.toc-toggle-icon');

    const setCollapsed = collapsed => {
      layout.classList.toggle('toc-collapsed', collapsed);
      button.setAttribute('aria-expanded', String(!collapsed));
      button.setAttribute('aria-label', collapsed ? '展开目录' : '收起目录');
      button.title = collapsed ? '展开目录' : '收起目录';
      if (icon) icon.textContent = collapsed ? '›' : '‹';
    };

    setCollapsed(layout.classList.contains('toc-collapsed'));
    button.addEventListener('click', () => {
      setCollapsed(!layout.classList.contains('toc-collapsed'));
    });
  });
})();
/* HTML_REPORT_TOC_RUNTIME_END */
