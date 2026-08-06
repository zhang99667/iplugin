/* HTML_REPORT_INTERACTIONS_RUNTIME_START */
(() => {
  if (window.__HTML_REPORT_INTERACTIONS_READY__ === true) return;
  window.__HTML_REPORT_INTERACTIONS_READY__ = true;

  // 导出的 HTML 会保留动态按钮但不会保留事件监听，因此重新打开时必须复用并重新绑定
  const button = document.querySelector('.back-to-top') || document.createElement('button');
  button.className = 'back-to-top';
  button.type = 'button';
  button.tabIndex = -1;
  button.setAttribute('aria-label', '回到顶部');
  button.setAttribute('aria-hidden', 'true');
  button.title = '回到顶部';
  button.innerHTML = [
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">',
    '  <path d="M6 10.5 12 4.5l6 6M12 5v14"></path>',
    '</svg>'
  ].join('');
  if (!button.isConnected) document.body.appendChild(button);

  let framePending = false;

  function syncVisibility() {
    framePending = false;
    const visible = window.scrollY > 360;
    button.classList.toggle('is-visible', visible);
    button.tabIndex = visible ? 0 : -1;
    button.setAttribute('aria-hidden', String(!visible));
    if (!visible && document.activeElement === button) button.blur();
  }

  function scheduleVisibilitySync() {
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(syncVisibility);
  }

  button.addEventListener('click', () => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reducedMotion ? 'auto' : 'smooth' });
  });
  window.addEventListener('scroll', scheduleVisibilitySync, { passive: true });
  window.addEventListener('resize', scheduleVisibilitySync);
  syncVisibility();
})();
/* HTML_REPORT_INTERACTIONS_RUNTIME_END */
