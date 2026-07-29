/* HTML_REPORT_IMAGE_LIGHTBOX_RUNTIME_START */
(() => {
  if (!('HTMLDialogElement' in window) || !HTMLDialogElement.prototype.showModal) return;
  const root = document.documentElement;
  if (root.dataset.htmlReportLightboxReady === 'true') return;
  root.dataset.htmlReportLightboxReady = 'true';

  const dialog = document.createElement('dialog');
  dialog.className = 'image-lightbox';
  dialog.setAttribute('aria-label', '图片预览');
  dialog.innerHTML = [
    '<button class="image-lightbox-close" type="button" aria-label="关闭图片预览" title="关闭">×</button>',
    '<div class="image-lightbox-inner">',
    '  <div class="image-lightbox-stage"><img class="image-lightbox-image" alt=""></div>',
    '  <p class="image-lightbox-caption"></p>',
    '</div>'
  ].join('');
  document.body.appendChild(dialog);

  const preview = dialog.querySelector('.image-lightbox-image');
  const caption = dialog.querySelector('.image-lightbox-caption');
  const closeButton = dialog.querySelector('.image-lightbox-close');
  let opener = null;

  function closeDialog() {
    if (dialog.open) dialog.close();
  }

  document.addEventListener('click', event => {
    const trigger = event.target.closest('a.image-lightbox-trigger[data-image-lightbox]');
    if (!trigger) return;
    event.preventDefault();
    const sourceImage = trigger.querySelector('img');
    preview.src = trigger.dataset.lightboxSrc || trigger.href;
    preview.alt = sourceImage?.alt || '';
    caption.textContent = trigger.dataset.lightboxCaption
      || trigger.closest('figure')?.querySelector('figcaption')?.innerText.trim()
      || sourceImage?.alt
      || '图片预览';
    opener = trigger;
    dialog.showModal();
    closeButton.focus();
  });

  closeButton.addEventListener('click', closeDialog);
  dialog.addEventListener('click', event => {
    if (event.target === dialog) closeDialog();
  });
  dialog.addEventListener('close', () => {
    preview.removeAttribute('src');
    opener?.focus();
    opener = null;
  });
})();
/* HTML_REPORT_IMAGE_LIGHTBOX_RUNTIME_END */
