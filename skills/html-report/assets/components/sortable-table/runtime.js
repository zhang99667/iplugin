/* HTML_REPORT_SORTABLE_TABLE_RUNTIME_START */
(() => {
  function numericValue(text) {
    const normalized = text.replace(/[,，\s￥¥$€£%]/g, '');
    return /^[-+]?\d+(\.\d+)?$/.test(normalized) ? Number(normalized) : null;
  }

  function compareValues(left, right, type, locale) {
    if (type === 'number' || type === 'auto') {
      const leftNumber = numericValue(left);
      const rightNumber = numericValue(right);
      if (leftNumber !== null && rightNumber !== null) return leftNumber - rightNumber;
    }
    if (type === 'date') {
      const leftDate = Date.parse(left);
      const rightDate = Date.parse(right);
      if (!Number.isNaN(leftDate) && !Number.isNaN(rightDate)) return leftDate - rightDate;
    }
    return left.localeCompare(right, locale, { numeric: true, sensitivity: 'base' });
  }

  document.querySelectorAll('table.sortable').forEach(table => {
    if (table.dataset.sortableReady === 'true') return;
    table.dataset.sortableReady = 'true';
    const body = table.tBodies[0];
    if (!body) return;

    table.querySelectorAll('thead .sort-button').forEach(button => {
      button.addEventListener('click', () => {
        const header = button.closest('th');
        if (!header) return;
        const column = Array.from(header.parentElement.children).indexOf(header);
        const ascending = header.getAttribute('aria-sort') !== 'ascending';
        const type = button.dataset.sortType || 'auto';
        const locale = document.documentElement.lang || undefined;

        const rows = Array.from(body.rows).map((row, index) => ({ row, index }));
        rows.sort((left, right) => {
          const leftText = left.row.cells[column]?.innerText.trim() || '';
          const rightText = right.row.cells[column]?.innerText.trim() || '';
          const compared = compareValues(leftText, rightText, type, locale);
          return (ascending ? compared : -compared) || left.index - right.index;
        });

        table.querySelectorAll('thead th').forEach(item => {
          item.removeAttribute('aria-sort');
          const arrow = item.querySelector('.sort-arrow');
          if (arrow) arrow.textContent = '';
        });
        header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        const arrow = button.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = ascending ? '▲' : '▼';
        rows.forEach(item => body.appendChild(item.row));
      });
    });
  });
})();
/* HTML_REPORT_SORTABLE_TABLE_RUNTIME_END */
