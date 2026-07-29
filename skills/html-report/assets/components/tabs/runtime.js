/* HTML_REPORT_TABS_RUNTIME_START */
(() => {
  document.querySelectorAll('.report-tabs[data-tabs]').forEach(component => {
    if (component.dataset.tabsReady === 'true') return;
    const tabs = Array.from(component.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;
    component.dataset.tabsReady = 'true';

    const activate = nextTab => {
      tabs.forEach(tab => {
        const selected = tab === nextTab;
        const controlledId = tab.getAttribute('aria-controls') || '';
        // 用精确 id 比较定位面板，避免 file:// 环境依赖 CSS.escape 的浏览器实现版本。
        const panel = Array.from(component.querySelectorAll('[role="tabpanel"]'))
          .find(item => item.id === controlledId);
        tab.setAttribute('aria-selected', String(selected));
        tab.tabIndex = selected ? 0 : -1;
        if (panel) panel.hidden = !selected;
      });
    };

    const initial = tabs.find(tab => tab.getAttribute('aria-selected') === 'true') || tabs[0];
    activate(initial);
    component.classList.add('tabs-ready');

    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activate(tab));
      tab.addEventListener('keydown', event => {
        let nextIndex = index;
        if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
        else if (event.key === 'Home') nextIndex = 0;
        else if (event.key === 'End') nextIndex = tabs.length - 1;
        else return;
        event.preventDefault();
        activate(tabs[nextIndex]);
        tabs[nextIndex].focus();
      });
    });
  });
})();
/* HTML_REPORT_TABS_RUNTIME_END */
