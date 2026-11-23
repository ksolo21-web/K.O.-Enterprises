/* OAKX Seller Suite — public site script.
 * Drop the two LIVE Stripe Payment Links in here once live checkout is activated.
 * While a value is null, that plan's buttons open the Founding Access email modal instead. */
const CHECKOUT_CONFIG = {
  monthlyUrl: null, // e.g. 'https://buy.stripe.com/xxxxxxxx'
  annualUrl: null,  // e.g. 'https://buy.stripe.com/yyyyyyyy'
  supportEmail: 'ksolo21@gmail.com'
};

(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const usd = (n) => (n < 0 ? '−$' : '$') + Math.abs(n).toFixed(2);

  /* ---------- Header ---------- */
  const header = document.querySelector('.site-header');
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  const menuBtn = $('menu-btn');
  menuBtn.addEventListener('click', () => {
    const open = header.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('#nav-links a').forEach((a) => a.addEventListener('click', () => {
    header.classList.remove('open'); menuBtn.setAttribute('aria-expanded', 'false');
  }));
  $('year').textContent = String(new Date().getFullYear());

  /* ---------- Tabs ---------- */
  const tabs = [$('tab-truenet'), $('tab-importscope')];
  function selectTab(tab) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      $(t.getAttribute('aria-controls')).hidden = !on;
    });
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => selectTab(t));
    t.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        selectTab(next); next.focus();
      }
    });
  });

  /* ---------- TrueNet preview ---------- */
  // Planning defaults, mirroring the full TrueNet kit's documented presets.
  const CHANNELS = {
    tiktok:  { label: 'TikTok Shop', short: 'TikTok' },
    shopify: { label: 'Shopify',     short: 'Shopify' },
    amazon:  { label: 'Amazon',      short: 'Amazon' },
    etsy:    { label: 'Etsy',        short: 'Etsy' }
  };
  let channel = 'tiktok';
  const num = (id) => { const v = parseFloat($(id).value); return Number.isFinite(v) && v >= 0 ? v : 0; };

  function fees(ch, price, opts) {
    // returns { pct, fixed, lines:[[name, amount]] }
    if (ch === 'tiktok') {
      const lines = [['Referral fee (6%)', price * 0.06]];
      let pct = 0.06;
      if (opts.campaign) { lines.push(['Campaign service fee (1%)', price * 0.01]); pct += 0.01; }
      return { pct, fixed: 0, lines };
    }
    if (ch === 'shopify') return { pct: 0.029, fixed: 0.30, lines: [['Payment processing (2.9% + $0.30)', price * 0.029 + 0.30]] };
    if (ch === 'amazon') {
      const lines = [['Referral fee (15%)', price * 0.15]];
      if (opts.fba > 0) lines.push(['FBA / fulfillment fee', opts.fba]);
      return { pct: 0.15, fixed: opts.fba, lines };
    }
    // etsy
    return { pct: 0.065 + 0.03, fixed: 0.25 + 0.20, lines: [
      ['Transaction fee (6.5%)', price * 0.065],
      ['Payment processing (3% + $0.25)', price * 0.03 + 0.25],
      ['Listing fee', 0.20]
    ] };
  }

  function compute(ch, inp) {
    const landed = inp.cogs * (1 + inp.tariff / 100);
    const tariffAmt = landed - inp.cogs;
    const f = fees(ch, inp.price, inp);
    const feeTotal = f.lines.reduce((s, l) => s + l[1], 0);
    const reserve = (inp.returnRate / 100) * inp.retCost;
    const net = inp.price - landed - feeTotal - inp.ship - reserve;
    const fixedCosts = landed + inp.ship + reserve + f.fixed;
    const be = f.pct < 1 ? fixedCosts / (1 - f.pct) : Infinity;
    return { landed, tariffAmt, f, feeTotal, reserve, net, margin: inp.price > 0 ? net / inp.price * 100 : 0, be };
  }

  function readInputs() {
    return {
      price: num('tn-price'), cogs: num('tn-cogs'), tariff: num('tn-tariff'), ship: num('tn-ship'),
      returnRate: Math.min(num('tn-return'), 100), retCost: num('tn-retcost'),
      campaign: $('tn-campaign').checked, fba: num('tn-fba')
    };
  }

  function setSigned(el, value, text) {
    el.textContent = text;
    el.classList.toggle('pos', value > 0.004);
    el.classList.toggle('neg', value < -0.004);
  }

  function renderTrueNet() {
    const inp = readInputs();
    const r = compute(channel, inp);
    const paper = inp.price - inp.cogs;
    setSigned($('kpi-paper'), paper, usd(paper));
    setSigned($('kpi-net'), r.net, usd(r.net));
    setSigned($('kpi-margin'), r.margin, r.margin.toFixed(1) + '%');
    $('kpi-be').textContent = Number.isFinite(r.be) ? usd(r.be) : '—';
    $('kpi-be-s').textContent = 'on ' + CHANNELS[channel].label;
    $('kpi-net-s').textContent = 'per order on ' + CHANNELS[channel].short;
    const gap = paper - r.net;
    $('tn-gap-text').textContent = gap > 0.004
      ? usd(gap) + ' of your “paper profit” disappears into tariffs, channel fees, shipping, and expected returns on every ' + CHANNELS[channel].label + ' order.'
      : 'True net profit matches or beats paper profit at these inputs.';
    $('tn-ch-label').textContent = CHANNELS[channel].label;

    const rows = [['Sale price', inp.price], ['Unit COGS', -inp.cogs]];
    if (r.tariffAmt > 0) rows.push(['Tariff / landed-cost adj. (' + inp.tariff + '%)', -r.tariffAmt]);
    r.f.lines.forEach((l) => rows.push([l[0], -l[1]]));
    rows.push(['Shipping', -inp.ship]);
    rows.push(['Return reserve (' + inp.returnRate + '% × ' + usd(inp.retCost) + ')', -r.reserve]);
    const tbody = $('tn-ledger').tBodies[0];
    tbody.textContent = '';
    rows.forEach(([name, v]) => {
      const tr = tbody.insertRow();
      tr.insertCell().textContent = name;
      tr.insertCell().textContent = usd(v);
    });
    const tot = tbody.insertRow(); tot.className = 'total';
    tot.insertCell().textContent = 'True net profit';
    const tc = tot.insertCell(); setSigned(tc, r.net, usd(r.net));

    // channel comparison
    const all = Object.keys(CHANNELS).map((k) => ({ k, net: compute(k, inp).net }));
    const max = Math.max(...all.map((a) => Math.abs(a.net)), 0.01);
    const best = all.reduce((a, b) => (b.net > a.net ? b : a));
    const bars = $('tn-bars'); bars.textContent = '';
    all.forEach((a) => {
      const row = document.createElement('div');
      row.className = 'bar-row' + (a.k === channel ? ' active' : '') + (a.k === best.k && best.net > 0 ? ' best' : '');
      row.dataset.channel = a.k;
      row.innerHTML = '<span class="name"></span><span class="bar-track"><span class="bar-fill"></span></span><span class="amt"></span>';
      row.querySelector('.name').textContent = CHANNELS[a.k].short;
      const fill = row.querySelector('.bar-fill');
      fill.style.width = Math.max(2, Math.abs(a.net) / max * 100).toFixed(1) + '%';
      if (a.net < 0) fill.classList.add('neg-fill');
      const amt = row.querySelector('.amt'); setSigned(amt, a.net, usd(a.net));
      bars.appendChild(row);
    });
  }

  document.querySelectorAll('#tn-channel button').forEach((b) => b.addEventListener('click', () => {
    channel = b.dataset.ch;
    document.querySelectorAll('#tn-channel button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    $('tn-campaign-row').hidden = channel !== 'tiktok';
    $('tn-fba-row').hidden = channel !== 'amazon';
    renderTrueNet();
  }));
  $('tn-form').addEventListener('input', renderTrueNet);
  renderTrueNet();

  /* ---------- ImportScope preview ---------- */
  const SAMPLE_CSV = [
    'Handle,Title,Option1 Name,Option1 Value,Variant SKU,Variant Price,Varient Compare At Price,Variant Barcode,Variant Inventory Qty',
    'holiday-gift-bundle,Holiday Gift Bundle,Size,Standard,HGB-STD,40.00,48.00,012345678905,25',
    'holiday-gift-bundle,,Size,Deluxe,HGB-DLX,,58.00,012345678912,10',
    'holiday-gift-bundle,,Size,Deluxe,HGB-DLX2,52.00,,012345678929,8',
    'soy-holiday-candle,Soy Holiday Candle,Scent,Pine,CND-PINE,16.00,,8901234AB,40',
    'soy-holiday-candle,,Scent,Cedar,CND-PINE,16.00,,890123456781,35',
    'wool-mittens,Wool Mittens,Color,Charcoal,MIT-CHR,$24.99,,,12.5',
    'Linen Apron,Linen Apron,Color,Natural,APR-NAT,29.00,,,18'
  ].join('\n');
  const KNOWN = ['Handle','Title','Body (HTML)','Vendor','Product Category','Type','Tags','Published','Option1 Name','Option1 Value','Option2 Name','Option2 Value','Option3 Name','Option3 Value','Variant SKU','Variant Grams','Variant Inventory Tracker','Variant Inventory Qty','Variant Inventory Policy','Variant Fulfillment Service','Variant Price','Variant Compare At Price','Variant Requires Shipping','Variant Taxable','Variant Barcode','Image Src','Image Position','Image Alt Text','Gift Card','SEO Title','SEO Description','Variant Image','Variant Weight Unit','Variant Tax Code','Cost per item','Status'];
  const csvEl = $('is-csv');
  csvEl.value = SAMPLE_CSV;

  function parseCSV(text) {
    const rows = []; let row = [], field = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; }
        else field += c;
      } else if (c === '"') q = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(field); rows.push(row); row = []; field = '';
      } else field += c;
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }
    return rows.filter((r) => r.some((v) => v.trim() !== ''));
  }
  function lev(a, b) {
    a = a.toLowerCase(); b = b.toLowerCase();
    const d = Array.from({ length: a.length + 1 }, (_, i) => [i]);
    for (let j = 1; j <= b.length; j++) d[0][j] = j;
    for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[a.length][b.length];
  }
  function gtinValid(code) {
    if (!/^\d+$/.test(code) || ![8, 12, 13, 14].includes(code.length)) return false;
    const digits = code.split('').map(Number); const check = digits.pop();
    const sum = digits.reverse().reduce((s, d, i) => s + d * (i % 2 === 0 ? 3 : 1), 0);
    return (10 - (sum % 10)) % 10 === check;
  }

  function audit(text) {
    const out = [];
    const add = (sev, title, loc, fix) => out.push({ sev, title, loc, fix });
    const rows = parseCSV(text);
    if (!rows.length) { add('error', 'File is empty', 'File', 'Paste a Shopify product CSV export, starting with the header row.'); return { out, n: 0 }; }
    const header = rows[0].map((h) => h.trim());
    const idx = {};
    header.forEach((h, i) => {
      if (h in idx) add('error', 'Duplicate column "' + h + '"', 'Header', 'Delete one of the two <b>' + h + '</b> columns so Shopify knows which value to use.');
      idx[h] = i;
      if (!KNOWN.includes(h) && !/^Metafield|\(product\.metafields|^Google Shopping/i.test(h)) {
        const near = KNOWN.map((k) => [k, lev(h, k)]).sort((a, b) => a[1] - b[1])[0];
        if (near && near[1] <= 3) add('error', 'Unrecognized column "' + h + '"', 'Header, column ' + (i + 1), 'Rename it to <b>' + near[0] + '</b>. Shopify won’t recognize a misspelled column, so its data won’t import.');
        else add('warn', 'Unknown column "' + h + '"', 'Header, column ' + (i + 1), 'Shopify will ignore this column. Remove it or map it to a standard Shopify header.');
      }
    });
    ['Handle', 'Title', 'Variant Price'].forEach((req) => {
      if (!(req in idx)) add('error', 'Missing required column "' + req + '"', 'Header', 'Add a <b>' + req + '</b> column. Shopify needs it to create or update products.');
    });
    const get = (r, k) => (k in idx ? (r[idx[k]] || '').trim() : '');
    const seenTitle = {}, combos = {}, skus = {};
    for (let i = 1; i < rows.length; i++) {
      const r = rows[i]; const line = i + 1; const loc = 'Row ' + line;
      if (r.length !== header.length) add('warn', 'Row has ' + r.length + ' cells, header has ' + header.length, loc, 'Check for a stray or missing comma. Misaligned cells shift values into the wrong columns.');
      const h = get(r, 'Handle');
      if (!h) { add('error', 'Missing Handle', loc, 'Every row needs a <b>Handle</b> so Shopify knows which product it belongs to.'); continue; }
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(h)) {
        const fixed = h.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        add('error', 'Invalid Handle "' + h + '"', loc, 'Handles must be lowercase letters, numbers, and hyphens. Use <b>' + fixed + '</b>.');
      }
      if (!(h in seenTitle)) {
        seenTitle[h] = line;
        if ('Title' in idx && !get(r, 'Title')) add('error', 'First row of "' + h + '" has no Title', loc, 'Put the product <b>Title</b> on the first row for each handle.');
      }
      const combo = h + '|' + ['Option1 Value', 'Option2 Value', 'Option3 Value'].map((k) => get(r, k)).join('|');
      if (combo in combos) add('error', 'Duplicate Handle + option combination', loc + ' (same as row ' + combos[combo] + ')', 'Handle <b>' + h + '</b> already has a variant "' + get(r, 'Option1 Value') + '". Give this row a unique option value or delete it.');
      else combos[combo] = line;
      if ('Variant Price' in idx) {
        const p = get(r, 'Variant Price');
        if (!p) add('error', 'Missing Variant Price', loc, 'Add a price for this variant. A blank price may import as $0.00.');
        else if (!/^\d+(\.\d{1,2})?$/.test(p)) add('error', 'Invalid Variant Price "' + p + '"', loc, 'Use a plain number like <b>' + (p.replace(/[^0-9.]/g, '') || '0.00') + '</b>, with no currency symbol or commas.');
      }
      const sku = get(r, 'Variant SKU');
      if (sku) { if (sku in skus) add('warn', 'Duplicate Variant SKU "' + sku + '"', loc + ' (same as row ' + skus[sku] + ')', 'Each variant should have its own SKU so inventory and reports stay accurate.'); else skus[sku] = line; }
      const bc = get(r, 'Variant Barcode');
      if (bc && !gtinValid(bc)) add('error', 'Malformed Variant Barcode "' + bc + '"', loc, /^\d+$/.test(bc) && [8, 12, 13, 14].includes(bc.length) ? 'The check digit is wrong. Re-copy the UPC/EAN from your supplier.' : 'Barcodes must be 8, 12, 13, or 14 digits (UPC/EAN/GTIN) with no letters or spaces.');
      const qty = get(r, 'Variant Inventory Qty');
      if (qty && !/^-?\d+$/.test(qty)) add('error', 'Invalid Variant Inventory Qty "' + qty + '"', loc, 'Inventory must be a whole number, e.g. <b>' + Math.floor(parseFloat(qty) || 0) + '</b>.');
    }
    return { out, n: rows.length - 1 };
  }

  function runAudit() {
    const t0 = performance.now();
    const { out, n } = audit(csvEl.value);
    const ms = performance.now() - t0;
    const errs = out.filter((f) => f.sev === 'error').length, warns = out.length - errs;
    $('is-empty').hidden = true;
    const list = $('is-findings'); list.hidden = false; list.textContent = '';
    $('is-title').textContent = out.length ? out.length + ' issue' + (out.length === 1 ? '' : 's') + ' found' : 'Ready to upload';
    $('is-counts').innerHTML = '<span class="count err" id="is-err-count">' + errs + ' error' + (errs === 1 ? '' : 's') + '</span><span class="count warn" id="is-warn-count">' + warns + ' warning' + (warns === 1 ? '' : 's') + '</span><span class="count">' + n + ' rows</span>';
    if (!out.length) { const li = document.createElement('li'); li.className = 'allclear'; li.textContent = 'No issues found. This CSV passed every preview check.'; list.appendChild(li); }
    out.forEach((f) => {
      const li = document.createElement('li'); li.className = 'finding';
      li.innerHTML = '<span class="sev ' + f.sev + '">' + (f.sev === 'error' ? 'Error' : 'Warn') + '</span><div><span class="t"></span><span class="loc"></span><div class="fix"></div></div>';
      li.querySelector('.t').textContent = f.title;
      li.querySelector('.loc').textContent = f.loc;
      li.querySelector('.fix').innerHTML = f.fix.replace(/<(?!\/?b>)/g, '&lt;');
      list.appendChild(li);
    });
    $('is-meta').textContent = 'Checked ' + n + ' rows in ' + Math.max(ms, 0.1).toFixed(1) + ' ms · in your browser';
  }
  $('is-run').addEventListener('click', runAudit);
  $('is-reset').addEventListener('click', () => { csvEl.value = SAMPLE_CSV; runAudit(); });
  $('is-meta').textContent = SAMPLE_CSV.split('\n').length - 1 + ' sample rows · edit anything, then run';

  /* ---------- Checkout / Founding Access ---------- */
  const modal = $('modal'); let lastFocus = null;
  const PLANS = { monthly: 'Monthly · $9/month', annual: 'Annual · $79/year' };
  function openModal(plan) {
    lastFocus = document.activeElement;
    $('modal-plan').textContent = PLANS[plan];
    const subject = 'OAKX Founding Access — ' + (plan === 'annual' ? 'Annual ($79/year)' : 'Monthly ($9/month)');
    const body = 'Hi OAKX,\n\nPlease reserve a Founding Membership for me on the ' + PLANS[plan] + ' plan and send my checkout link when it opens.\n\nName:\nStore / channels (Shopify, TikTok Shop, Amazon, Etsy):\n\nThanks!';
    $('modal-mail').href = 'mailto:' + CHECKOUT_CONFIG.supportEmail + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    modal.hidden = false; document.body.style.overflow = 'hidden';
    modal.querySelector('.modal-close').focus();
  }
  function closeModal() { modal.hidden = true; document.body.style.overflow = ''; if (lastFocus) lastFocus.focus(); }
  modal.querySelectorAll('[data-close]').forEach((el) => el.addEventListener('click', closeModal));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !modal.hidden) closeModal(); });
  document.querySelectorAll('[data-plan]').forEach((b) => b.addEventListener('click', () => {
    const plan = b.dataset.plan;
    const url = plan === 'annual' ? CHECKOUT_CONFIG.annualUrl : CHECKOUT_CONFIG.monthlyUrl;
    if (url) window.location.href = url; else openModal(plan);
  }));
})();
