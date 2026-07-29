/* HTML_REPORT_CODE_BLOCK_RUNTIME_START */
(() => {
  const root = document.documentElement;
  if (root.dataset.htmlReportCodeBlockReady === 'true') return;
  root.dataset.htmlReportCodeBlockReady = 'true';

  let toastTimer = 0;

  function showToast(message) {
    let toast = document.querySelector('.toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove('show'), 1500);
  }

  function fallbackCopy(text) {
    const input = document.createElement('textarea');
    input.value = text;
    input.setAttribute('readonly', '');
    input.style.position = 'fixed';
    input.style.opacity = '0';
    document.body.appendChild(input);
    input.select();
    const copied = document.execCommand('copy');
    input.remove();
    return copied;
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (_) {
        // file:// 和受限浏览器可能拒绝 Clipboard API，继续走兼容回退。
      }
    }
    return fallbackCopy(text);
  }

  document.addEventListener('click', async event => {
    const button = event.target.closest('.copy-btn');
    if (!button) return;
    const code = button.closest('.code-wrap')?.querySelector('pre');
    if (!code) return;

    const originalLabel = button.dataset.copyLabel || button.textContent.trim() || '复制';
    button.dataset.copyLabel = originalLabel;
    const copied = await copyText(code.innerText);
    button.textContent = copied ? '已复制' : '复制失败';
    button.classList.toggle('copied', copied);
    showToast(copied ? '已复制到剪贴板' : '复制失败，请手动选择代码');
    window.setTimeout(() => {
      button.textContent = originalLabel;
      button.classList.remove('copied');
    }, 1500);
  });
})();
/* HTML_REPORT_CODE_BLOCK_RUNTIME_END */
