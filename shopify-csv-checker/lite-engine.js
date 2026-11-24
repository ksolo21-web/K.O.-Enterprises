/**
 * ImportScope Lite — in-browser Shopify CSV checks for the free
 * /shopify-csv-checker page. Reuses ImportScope's CSV tokenizer,
 * header aliases, HTML escaping, and decimal number parser.
 * Does not include the paid comparison report, exports, or 10,000-row kit.
 */
(function (root) {
  'use strict';

  const MAX_ROWS = 10000;
  const MAX_CHARS = 8 * 1024 * 1024;
  const FREE_ROW_CAP = 200;
  const DEFAULT_THRESHOLD = 20;

  const ALIASES = {
    handle: ['Handle', 'URL handle'],
    title: ['Title'],
    body: ['Body (HTML)', 'Description'],
    vendor: ['Vendor'],
    type: ['Type'],
    tags: ['Tags'],
    status: ['Status'],
    published: ['Published', 'Published on online store'],
    sku: ['Variant SKU', 'SKU'],
    barcode: ['Variant Barcode', 'Barcode', 'Barcodes'],
    price: ['Variant Price', 'Price'],
    compare: ['Variant Compare At Price', 'Compare-at price'],
    inventory: ['Variant Inventory Qty', 'Inventory quantity'],
    option1name: ['Option1 Name', 'Option1 name'],
    option1: ['Option1 Value', 'Option1 value'],
    option2name: ['Option2 Name', 'Option2 name'],
    option2: ['Option2 Value', 'Option2 value'],
    option3name: ['Option3 Name', 'Option3 name'],
    option3: ['Option3 Value', 'Option3 value'],
    image: ['Image Src', 'Product image URL'],
    variantImage: ['Variant Image', 'Variant image URL']
  };
  const LABELS = {
    handle: 'Handle',
    title: 'Title',
    sku: 'SKU',
    price: 'Price',
    compare: 'Compare-at price',
    option1name: 'Option 1 name',
    option2name: 'Option 2 name',
    option3name: 'Option 3 name'
  };

  const normalize = (s) => s.trim().toLowerCase();
  const MAP = new Map();
  for (const [k, aliases] of Object.entries(ALIASES)) {
    for (const a of aliases) MAP.set(normalize(a), k);
  }

  const escape = (s) =>
    String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));

  // Identical tokenizer to ImportScope engine.js: BOM, CRLF, quoted fields,
  // escaped quotes, line numbers through multiline cells, null-byte guard.
  function parseCSV(text) {
    if (typeof text !== 'string' || text.length > MAX_CHARS) {
      throw new Error('Use a UTF-8 CSV no larger than 8 MB.');
    }
    text = text.replace(/^\uFEFF/, '');
    if (text.includes('\0')) {
      throw new Error('The file contains null bytes. Export it as UTF-8 comma-separated CSV.');
    }
    const rows = [];
    const rowLines = [];
    let row = [];
    let cell = '';
    let quoted = false;
    let closed = false;
    let line = 1;
    let start = 1;
    const push = () => {
      row.push(cell);
      cell = '';
      if (row.some((x) => x.trim() !== '')) {
        rows.push(row);
        rowLines.push(start);
      }
      row = [];
      closed = false;
      if (rows.length > MAX_ROWS + 1) {
        throw new Error('Use at most 10,000 data rows per file.');
      }
    };
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') {
            cell += '"';
            i++;
          } else {
            quoted = false;
            closed = true;
          }
        } else {
          cell += c;
          if (c === '\n') line++;
          else if (c === '\r' && text[i + 1] !== '\n') line++;
        }
        continue;
      }
      if (closed && c !== ',' && c !== '\r' && c !== '\n') {
        throw new Error('Unexpected text after a quoted field at line ' + line + '.');
      }
      if (c === '"') {
        if (cell !== '') throw new Error('Unexpected quote at line ' + line + '.');
        quoted = true;
        continue;
      }
      if (c === ',') {
        row.push(cell);
        cell = '';
        closed = false;
        continue;
      }
      if (c === '\n' || c === '\r') {
        push();
        if (c === '\r' && text[i + 1] === '\n') i++;
        line++;
        start = line;
        continue;
      }
      cell += c;
    }
    if (quoted) {
      throw new Error('Unclosed quoted field beginning at or after line ' + start + '.');
    }
    if (cell !== '' || row.length || closed) push();
    if (rows.length < 2) {
      throw new Error('The CSV needs a header and at least one product row.');
    }
    const headers = rows.shift();
    const headerLine = rowLines.shift();
    if (headers.length < 2) {
      throw new Error('Expected comma-separated product CSV columns, not a tab- or semicolon-separated file.');
    }
    const seen = new Set();
    const columns = {};
    const unknown = [];
    headers.forEach((h, i) => {
      const norm = normalize(h);
      if (!norm) throw new Error('Column ' + (i + 1) + ' has no header.');
      if (seen.has(norm)) throw new Error('Duplicate header: ' + h);
      seen.add(norm);
      const k = MAP.get(norm);
      if (k) {
        if (k in columns) throw new Error('Two headers map to ' + (LABELS[k] || k) + '. Keep only one.');
        columns[k] = i;
      } else unknown.push(h);
    });
    // Lite accepts thin price-update files: Handle is required, Title is not.
    if (!('handle' in columns)) {
      throw new Error('The CSV needs a Handle (or URL handle) column.');
    }
    const records = rows.map((cells, i) => {
      if (cells.length !== headers.length) {
        throw new Error('Line ' + rowLines[i] + ' has ' + cells.length + ' fields; expected ' + headers.length + '.');
      }
      const values = {};
      for (const [k, j] of Object.entries(columns)) values[k] = cells[j];
      return { values, line: rowLines[i], cells };
    });
    return { headers, columns, unknown, records, headerLine };
  }

  // Same rule as ImportScope: non-negative decimal, no currency symbol or thousands separator, up to 6 places, cap 1e9.
  function number(s) {
    if (typeof s !== 'string' || !/^\d+(?:\.\d{1,6})?$/.test(s.trim())) return null;
    const n = Number(s);
    return Number.isFinite(n) && n <= 1e9 ? n : null;
  }

  function key(v) {
    return JSON.stringify([v.handle, v.option1 ?? '', v.option2 ?? '', v.option3 ?? '']);
  }

  function variantName(v) {
    return [v.option1, v.option2, v.option3].filter(Boolean).join(' / ') || 'Default / unspecified';
  }

  function isVariantData(v) {
    return ['option1', 'option2', 'option3', 'sku', 'price', 'barcode', 'inventory'].some(
      (k) => (v[k] ?? '') !== ''
    );
  }

  function indexCurrent(file) {
    const variants = new Map();
    const ambiguous = new Set();
    const products = new Map();
    for (const r of file.records) {
      const v = r.values;
      if (!v.handle) continue;
      let product = products.get(v.handle);
      if (!product) {
        product = { rows: [] };
        products.set(v.handle, product);
      }
      product.rows.push(r);
      const imageOnly = product.rows.length > 1 && v.image && !isVariantData(v);
      if (imageOnly) continue;
      const k = key(v);
      r.key = k;
      if (variants.has(k)) ambiguous.add(k);
      else variants.set(k, r);
    }
    return { variants, ambiguous, columns: file.columns };
  }

  function check(proposedText, currentText, options) {
    options = options || {};
    const threshold = Number(options.threshold ?? DEFAULT_THRESHOLD);
    if (!Number.isFinite(threshold) || threshold < 1 || threshold > 100) {
      throw new Error('Price-drop threshold must be 1–100%.');
    }
    const proposed = parseCSV(proposedText);
    const totalRows = proposed.records.length;
    const capped = totalRows > FREE_ROW_CAP;
    const records = capped ? proposed.records.slice(0, FREE_ROW_CAP) : proposed.records;
    const file = { columns: proposed.columns, records, headers: proposed.headers };

    let current = null;
    const hasCurrent = typeof currentText === 'string' && currentText.trim() !== '';
    if (hasCurrent) current = indexCurrent(parseCSV(currentText));

    const findings = [];
    let counter = 0;
    function add(severity, code, title, detail, record, oldValue, newValue) {
      findings.push({
        id: ++counter,
        severity,
        code,
        title,
        detail,
        handle: record?.values.handle ?? '',
        sku: record?.values.sku ?? '',
        line: record?.line ?? null,
        variant: record ? variantName(record.values) : '',
        oldValue: oldValue ?? null,
        newValue: newValue ?? null
      });
    }

    const variants = new Map();
    const skuKeys = new Map();
    const products = new Map();
    let matched = 0;

    if (!('price' in file.columns)) {
      add(
        'high',
        'missing_price_column',
        'No Variant Price column',
        'This free checker looks for Variant Price (or Price). Add that header to a thin price file, or use a Shopify product export.',
        null
      );
    }

    for (const r of file.records) {
      const v = r.values;
      const handle = v.handle;
      if (!handle) {
        add(
          'high',
          'missing_handle',
          'A row has no handle',
          'Rows without a handle cannot be matched to a product. Fill in the intended handle before you import.',
          r
        );
        continue;
      }
      if (/\s/.test(handle)) {
        add(
          'high',
          'handle_whitespace',
          'Handle contains whitespace',
          'Review the handle; Shopify product handles cannot contain spaces.',
          r
        );
      }

      let product = products.get(handle);
      if (!product) {
        product = { rows: [] };
        products.set(handle, product);
      }
      product.rows.push(r);

      const imageOnly = product.rows.length > 1 && v.image && !isVariantData(v);
      if (imageOnly) continue;

      const k = key(v);
      r.key = k;
      if (variants.has(k)) {
        add(
          'high',
          'duplicate_variant',
          'Variant identity is duplicated',
          'The same Handle and option combination appears more than once. Shopify cannot apply both rows reliably — keep one row per variant.',
          r
        );
      } else {
        variants.set(k, r);
      }

      if (v.sku) {
        const list = skuKeys.get(v.sku) || [];
        list.push(r);
        skuKeys.set(v.sku, list);
      }

      if ('price' in file.columns) {
        if (v.price === '') {
          add(
            'high',
            'blank_price',
            'A supplied price is blank',
            'Shopify can import an empty Variant Price as $0.00. Confirm the intended amount before you upload.',
            r,
            null,
            '(blank → 0)'
          );
        } else if (number(v.price) === null) {
          add(
            'high',
            'invalid_price',
            'Price is not a supported number',
            'Use a non-negative decimal without a currency symbol or thousands separator, for example 12.00 or 1299.99. Up to six decimal places are checked.',
            r,
            null,
            String(v.price).slice(0, 80)
          );
        }
      }

      if ('compare' in file.columns && v.compare !== '') {
        const price = 'price' in file.columns ? number(v.price) : null;
        const comp = number(v.compare);
        if (comp === null) {
          add(
            'high',
            'invalid_compare',
            'Compare-at price is not a supported number',
            'Use a non-negative decimal value without a currency symbol or thousands separator.',
            r,
            null,
            String(v.compare).slice(0, 80)
          );
        } else if (price !== null && comp <= price) {
          add(
            'medium',
            'compare_not_higher',
            'Compare-at price is not above the selling price',
            'A compare-at price at or below Variant Price will not show a meaningful markdown. Raise Compare At Price or clear it if you are not running a sale comparison.',
            r,
            v.price,
            v.compare
          );
        }
      }

      const uniqueFirst = variants.get(k) === r;
      if (
        uniqueFirst &&
        current &&
        'price' in file.columns &&
        current.columns &&
        'price' in current.columns &&
        !current.ambiguous.has(k)
      ) {
        const old = current.variants.get(k);
        if (old) {
          matched++;
          const left = old.values.price ?? '';
          const right = v.price;
          const oldPrice = number(left);
          const newPrice = right === '' ? null : number(right);
          if (oldPrice > 0 && newPrice !== null && left !== right) {
            const drop = (100 * (oldPrice - newPrice)) / oldPrice;
            if (drop >= threshold) {
              add(
                'high',
                'price_drop',
                'Price drops ' + drop.toFixed(1) + '%',
                'This exceeds the ' +
                  threshold +
                  '% review threshold. Check for a misplaced decimal or an unintended markdown before you import.',
                r,
                left,
                right
              );
            } else if (newPrice >= 2 * oldPrice) {
              const rise = (100 * (newPrice - oldPrice)) / oldPrice;
              add(
                'medium',
                'price_increase',
                'Price rises ' + rise.toFixed(1) + '%',
                'The proposed price is at least double the current price. Check for a misplaced decimal or an unintended markup.',
                r,
                left,
                right
              );
            }
          }
        }
      }
    }

    for (const list of skuKeys.values()) {
      if (list.length > 1) {
        add(
          'medium',
          'duplicate_sku',
          'SKU is reused',
          'This SKU belongs to ' +
            list.length +
            ' rows in the rows reviewed. Shopify may allow duplicate SKUs, but fulfillment and later matching can be ambiguous.',
          list[0]
        );
      }
    }

    findings.sort(
      (x, y) =>
        ({ high: 0, medium: 1, info: 2 }[x.severity] - { high: 0, medium: 1, info: 2 }[y.severity]) || x.id - y.id
    );

    const high = findings.filter((x) => x.severity === 'high').length;
    const medium = findings.filter((x) => x.severity === 'medium').length;

    return {
      findings,
      stats: {
        high,
        medium,
        rowsChecked: records.length,
        rowsTotal: totalRows,
        capped,
        products: products.size,
        matched,
        hasCurrent,
        threshold,
        hasPriceColumn: 'price' in file.columns
      },
      capped,
      cap: FREE_ROW_CAP
    };
  }

  const sampleHeaders =
    'Handle,Title,Option1 Name,Option1 Value,Variant SKU,Variant Price,Variant Compare At Price';
  const SAMPLE_CURRENT =
    sampleHeaders +
    '\n' +
    [
      'wool-coat,Wool Coat,Size,S,COAT-S,189.00,',
      'wool-coat,,Size,M,COAT-M,189.00,',
      'wool-coat,,Size,L,COAT-L,189.00,',
      'ceramic-mug,Ceramic Mug,Color,Ink,MUG-INK,24.00,30.00',
      'canvas-tote,Canvas Tote,Title,Default Title,TOTE-01,32.00,',
      'scarf,Wool Scarf,Color,Camel,SCARF-C,48.00,',
      'candle,Holiday Candle,Title,Default Title,CANDLE-01,16.00,20.00'
    ].join('\n') +
    '\n';
  const SAMPLE_PROPOSED =
    sampleHeaders +
    '\n' +
    [
      'wool-coat,Wool Coat,Size,S,COAT-S,18.90,189.00',
      'wool-coat,,Size,M,COAT-M,160.65,189.00',
      'wool-coat,,Size,L,COAT-L,1890.00,189.00',
      'ceramic-mug,Ceramic Mug,Color,Ink,MUG-INK,24.00,20.00',
      'canvas-tote,Canvas Tote,Title,Default Title,TOTE-01,,',
      'scarf,Wool Scarf,Color,Camel,SCARF-C,48.00,',
      'scarf,,Color,Camel,SCARF-CAMEL,42.00,',
      ',Ornament,Title,Default Title,ORN-01,8.00,',
      'candle,Holiday Candle,Title,Default Title,MUG-INK,16.00,20.00',
      'stocking,Stocking,Title,Default Title,STOCK-01,N/A,',
      'mug-set,Mug Set,Title,Default Title,MUG-SET,36.00,40.00'
    ].join('\n') +
    '\n';

  const api = {
    parseCSV,
    check,
    escape,
    number,
    SAMPLE_CURRENT,
    SAMPLE_PROPOSED,
    FREE_ROW_CAP,
    DEFAULT_THRESHOLD,
    MAX_ROWS,
    MAX_CHARS
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ImportScopeLite = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
