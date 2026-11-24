(function () {
  'use strict';
  const Lite = window.ImportScopeLite;
  if (!Lite) return;

  const $ = (id) => document.getElementById(id);
  const proposedCsv = $('proposed-csv');
  const currentCsv = $('current-csv');
  const proposedName = $('proposed-name');
  const currentName = $('current-name');
  const thresholdInput = $('threshold');
  const errorEl = $('check-error');
  const capEl = $('cap-banner');
  const emptyEl = $('results-empty');
  const clearEl = $('results-clear');
  const listEl = $('results-findings');
  const titleEl = $('results-title');
  const countsEl = $('results-counts');
  const header = document.querySelector('.site-header');
  const menuBtn = $('menu-btn');
  const navLinks = $('nav-links');

  function setHidden(el, hidden) {
    if (!el) return;
    el.hidden = hidden;
  }

  function clearChildren(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function addCount(label, kind) {
    const span = document.createElement('span');
    span.className = kind ? 'count ' + kind : 'count';
    span.textContent = label;
    countsEl.appendChild(span);
  }

  function render(result) {
    setHidden(errorEl, true);
    errorEl.textContent = '';
    clearChildren(countsEl);
    clearChildren(listEl);

    const s = result.stats;
    const high = s.high;
    const medium = s.medium;
    const findings = result.findings;
    titleEl.textContent =
      findings.length === 0
        ? 'Pre-flight results'
        : findings.length === 1
          ? '1 finding'
          : findings.length + ' findings';

    addCount(s.rowsChecked + (s.capped ? ' of ' + s.rowsTotal : '') + ' rows', '');
    if (high) addCount(high + (high === 1 ? ' error' : ' errors'), 'err');
    if (medium) addCount(medium + (medium === 1 ? ' warning' : ' warnings'), 'warn');
    if (!findings.length) addCount('All clear', 'ok');
    if (s.hasCurrent) addCount(s.matched + ' matched', '');

    if (s.capped) {
      capEl.textContent = '';
      capEl.appendChild(
        document.createTextNode(
          'This free checker reviewed the first ' +
            Lite.FREE_ROW_CAP +
            ' of ' +
            s.rowsTotal +
            ' data rows. The full ImportScope tool in OAKX Seller Suite handles 10,000+ rows, reports, and exports. '
        )
      );
      const a = document.createElement('a');
      a.href = '#pricing';
      a.textContent = 'See Founding Pricing';
      capEl.appendChild(a);
      setHidden(capEl, false);
    } else {
      capEl.textContent = '';
      setHidden(capEl, true);
    }

    setHidden(emptyEl, true);
    if (!findings.length) {
      setHidden(clearEl, false);
      setHidden(listEl, true);
      return;
    }
    setHidden(clearEl, true);
    setHidden(listEl, false);

    for (const f of findings) {
      const li = document.createElement('li');
      li.className = 'finding';

      const sev = document.createElement('span');
      sev.className = 'sev ' + (f.severity === 'high' ? 'error' : 'warn');
      sev.textContent = f.severity === 'high' ? 'Error' : 'Review';
      li.appendChild(sev);

      const body = document.createElement('div');
      const t = document.createElement('div');
      t.className = 't';
      t.textContent = f.title;
      const loc = document.createElement('span');
      loc.className = 'loc';
      const locParts = [];
      if (f.line) locParts.push('line ' + f.line);
      if (f.handle) locParts.push(f.handle);
      if (f.variant) locParts.push(f.variant);
      if (f.sku) locParts.push('SKU ' + f.sku);
      loc.textContent = locParts.join(' · ');
      t.appendChild(loc);
      body.appendChild(t);

      const fix = document.createElement('div');
      fix.className = 'fix';
      fix.textContent = f.detail;
      if (f.oldValue !== null || f.newValue !== null) {
        const values = document.createElement('div');
        values.className = 'fix';
        const b = document.createElement('b');
        b.textContent = (f.oldValue == null ? '—' : String(f.oldValue)) + ' → ' + (f.newValue == null ? '—' : String(f.newValue));
        values.appendChild(b);
        body.appendChild(fix);
        body.appendChild(values);
      } else {
        body.appendChild(fix);
      }
      li.appendChild(body);
      listEl.appendChild(li);
    }
  }

  function renderError(message) {
    clearChildren(countsEl);
    clearChildren(listEl);
    titleEl.textContent = 'Could not read this CSV';
    errorEl.textContent = message;
    setHidden(errorEl, false);
    setHidden(capEl, true);
    setHidden(emptyEl, true);
    setHidden(clearEl, true);
    setHidden(listEl, true);
  }

  function run() {
    const proposed = proposedCsv.value;
    const current = currentCsv.value;
    const threshold = Number(thresholdInput.value);
    try {
      if (!proposed.trim()) {
        renderError('Paste or drop a proposed Shopify product CSV first.');
        return;
      }
      render(Lite.check(proposed, current, { threshold: threshold }));
    } catch (err) {
      renderError(err && err.message ? String(err.message) : 'Could not check this file.');
    }
  }

  function loadSample() {
    proposedCsv.value = Lite.SAMPLE_PROPOSED;
    currentCsv.value = Lite.SAMPLE_CURRENT;
    proposedName.textContent = 'Sample proposed import (planted errors)';
    currentName.textContent = 'Sample current export';
    thresholdInput.value = String(Lite.DEFAULT_THRESHOLD);
    run();
  }

  function resetAll() {
    proposedCsv.value = '';
    currentCsv.value = '';
    proposedName.textContent = 'No file chosen — paste is fine';
    currentName.textContent = 'No file chosen';
    thresholdInput.value = String(Lite.DEFAULT_THRESHOLD);
    clearChildren(countsEl);
    clearChildren(listEl);
    titleEl.textContent = 'Pre-flight results';
    errorEl.textContent = '';
    capEl.textContent = '';
    setHidden(errorEl, true);
    setHidden(capEl, true);
    setHidden(emptyEl, false);
    setHidden(clearEl, true);
    setHidden(listEl, true);
  }

  function readFile(file, textarea, label) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function () {
      textarea.value = typeof reader.result === 'string' ? reader.result : '';
      label.textContent = file.name + ' · ' + file.size + ' bytes on this device';
    };
    reader.onerror = function () {
      renderError('Could not read ' + file.name + ' on this device.');
    };
    reader.readAsText(file);
  }

  function bindDrop(zone, input, textarea, label) {
    zone.addEventListener('dragenter', (e) => {
      e.preventDefault();
      zone.classList.add('drag');
    });
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag');
    });
    zone.addEventListener('dragleave', (e) => {
      if (!zone.contains(e.relatedTarget)) zone.classList.remove('drag');
    });
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag');
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      readFile(file, textarea, label);
    });
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      readFile(file, textarea, label);
      input.value = '';
    });
  }

  bindDrop($('proposed-drop'), $('proposed-file'), proposedCsv, proposedName);
  bindDrop($('current-drop'), $('current-file'), currentCsv, currentName);
  $('proposed-browse').addEventListener('click', () => $('proposed-file').click());
  $('current-browse').addEventListener('click', () => $('current-file').click());
  $('run-btn').addEventListener('click', run);
  $('sample-btn').addEventListener('click', loadSample);
  $('reset-btn').addEventListener('click', resetAll);

  if (menuBtn && header && navLinks) {
    menuBtn.addEventListener('click', () => {
      const open = header.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    navLinks.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', () => {
        header.classList.remove('open');
        menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.setAttribute('aria-label', 'Open menu');
      });
    });
  }
  if (header) {
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  loadSample();
})();
