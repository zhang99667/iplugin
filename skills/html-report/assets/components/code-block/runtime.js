/* HTML_REPORT_CODE_BLOCK_RUNTIME_START */
(() => {
  const root = document.documentElement;
  if (root.dataset.htmlReportCodeBlockReady === 'true') return;
  root.dataset.htmlReportCodeBlockReady = 'true';

  const languageLabels = {
    bash: 'Shell',
    c: 'C',
    cpp: 'C++',
    diff: 'Diff',
    go: 'Go',
    ini: 'INI',
    java: 'Java',
    js: 'JavaScript',
    json: 'JSON',
    kotlin: 'Kotlin',
    markdown: 'Markdown',
    objc: 'Objective-C',
    php: 'PHP',
    python: 'Python',
    ruby: 'Ruby',
    rust: 'Rust',
    sql: 'SQL',
    swift: 'Swift',
    toml: 'TOML',
    ts: 'TypeScript',
    text: 'Text',
    xml: 'XML',
    yaml: 'YAML'
  };
  const languageAliases = {
    kt: 'kotlin',
    kts: 'kotlin',
    cxx: 'cpp',
    javascript: 'js',
    jsx: 'js',
    typescript: 'ts',
    tsx: 'ts',
    'c++': 'cpp',
    cc: 'cpp',
    hpp: 'cpp',
    hh: 'cpp',
    hxx: 'cpp',
    'objective-c': 'objc',
    objectivec: 'objc',
    'obj-c': 'objc',
    m: 'objc',
    mm: 'objc',
    h: 'objc',
    'objective-c++': 'objc',
    'obj-c++': 'objc',
    rs: 'rust',
    rb: 'ruby',
    md: 'markdown',
    mkd: 'markdown',
    mdown: 'markdown',
    py: 'python',
    html: 'xml',
    xhtml: 'xml',
    svg: 'xml',
    plist: 'xml',
    yml: 'yaml',
    conf: 'yaml',
    config: 'yaml',
    properties: 'yaml',
    sh: 'bash',
    shell: 'bash',
    zsh: 'bash',
    txt: 'text',
    mysql: 'sql',
    hive: 'sql',
    spark: 'sql',
    jsonc: 'json',
    tml: 'toml',
    cfg: 'ini',
    patch: 'diff'
  };

  let toastTimer = 0;

  function languageFromCodeWrap(codeWrap) {
    const explicit = String(codeWrap.dataset.codeLang || '').trim().toLowerCase();
    if (explicit) return explicit;
    const code = codeWrap.querySelector('code[class*="language-"]');
    const match = String(code?.className || '').match(/\blanguage-([a-z0-9_+.-]+)/i);
    return match ? match[1].toLowerCase() : 'text';
  }

  function languageLabel(language) {
    const normalized = languageAliases[language] || language;
    return languageLabels[normalized] || normalized.toUpperCase();
  }

  function decorateCodeBlock(codeWrap) {
    const rawLanguage = languageFromCodeWrap(codeWrap);
    const language = languageAliases[rawLanguage] || rawLanguage;
    let toolbar = codeWrap.querySelector('.code-toolbar');
    if (!toolbar) {
      // 用 span 工具栏避免旧版代码块的非贪婪 div 解析边界被嵌套容器截断
      toolbar = document.createElement('span');
      toolbar.className = 'code-toolbar';
      toolbar.setAttribute('role', 'group');
      toolbar.setAttribute('aria-label', '代码工具栏');
      codeWrap.insertBefore(toolbar, codeWrap.firstChild);
    }

    let label = toolbar.querySelector('.code-lang');
    if (!label) {
      label = document.createElement('span');
      label.className = 'code-lang';
      toolbar.appendChild(label);
    }
    label.textContent = languageLabel(language);
    label.dataset.codeLang = language;
    label.setAttribute('aria-label', '代码语言：' + languageLabel(language));

    const copyButton = codeWrap.querySelector('.copy-btn');
    if (copyButton && copyButton.parentElement !== toolbar) {
      // 只迁移旧按钮，不覆盖报告作者可能放入工具栏的其他操作
      toolbar.insertBefore(copyButton, label);
    }
  }

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

  document.querySelectorAll('.code-wrap').forEach(decorateCodeBlock);

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
