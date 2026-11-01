# Milestone 3 v5 — OCR reading-order proposals and offline report-study viewer

**Scope:** private, synthetic-tested engineering; **not** defect detection, table interpretation, accredited inspector review, professional learning, or customer release. Earlier M3 import/compare/annotation/OCR/rendering and existing report format remain unchanged. Work stays on `home-inspection-development`; company pause remains active.

## Components

### `inspection_engine/report_reading_order.py`

- Consumes the existing M3 v4 layout index and optional M3 v3 OCR record, bound by their SHA-256 receipts. This stage must be called **after** source-bound layout and OCR validation, as the viewer does.
- Makes cautious candidate two-column groups only when repeated OCR row gutters support them. Sorts candidate lines within left and right columns while respecting an intervening full-width OCR heading.
- Preserves each OCR `word_index` exactly once; retaining original OCR text and boxes in the underlying record remains mandatory.
- Rejects missing/duplicate words, invalid geometry, changed hashes, absent OCR metadata, fabricated approval, or unsupported layout scope.
- When confidence is inadequate, returns row-major candidates with `COLUMN_BOUNDARY_NOT_ESTABLISHED` rather than guessing. Strong competing gutters explicitly require review. Repeated table-like rows **can mimic columns** and are never declared tables or cells.
- PDF extracted-text spans retain independent source IDs and **are not aligned to OCR words by assumption**. No OCR output becomes a verified PDF quote or property defect.
- New reading order does not cross page boundaries automatically; source pages stay in numeric order and transitions remain inspector review tasks.

### `inspection_engine/report_study_viewer.py`

- Builds an **offline, read-only** `index.html` and source-checked PNG copies under a **new local private directory**. It does not start a network server or include JavaScript, analytics, external fonts, remote images, or external links.
- Accepts 1–25 explicit render batches, each max eight pages, using existing source verification: actual PDF bytes, registered reference, full review queue, deterministic PDFium rerender, OCR record, v4 layout index, and the v5 reading-order receipt.
- Shows a page navigation panel, original page image, PDF text-region and embedded raster-object outlines, candidate OCR reading order, exact original PDF text spans, page hashes, and missing rendered page numbers. Original report text is HTML-escaped, never executed. Text marked as unverified; photo-versus-diagram identity and table structure are **not** inferred.
- Blocks duplicate or forged pages, bad source hash, missing/untrusted images, symlinked assets, existing output, unbounded HTML, and partial private writes. Outputs use mode 0700 directories and 0600 files; a `receipt.json` includes hashes for HTML/PNGs. Verification of the PDF is repeated after copying.
- Missing pages are explicitly `PARTIAL_SOURCE_COVERAGE`; completing rendering does **not** imply complete inspection or review.
- The HTML contains sensitive source text/images if a user processes a real authorized report. It **must stay outside public GitHub** and under local business-controlled access. Browsers, plugins, and the host device remain a separate privacy risk; do not claim a browser is guaranteed isolated.

## Command example

First prepare **private** reference import, source-bound text queue, verified PDF rendering, optional Tesseract OCR records, and PDFium layout indexes using the previous M3 tools. Create a private `batches.json`:

```json
[
  {
    "manifest": "private_case/render-01/manifest.json",
    "layout": "private_case/layout-01.json",
    "ocr_record": "private_case/ocr-01.json",
    "render_dir": "private_case/render-01"
  }
]
```

Omit `ocr_record` only when the corresponding layout was built with no OCR. Then run locally:

```bash
python -m inspection_engine.report_study_viewer \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --text-queue private_case/review_queue.json \
  --source-pdf private_case/source.pdf \
  --batches private_case/batches.json \
  --out-dir private_case/viewer
```

Open `private_case/viewer/index.html` on the local computer. Do not upload the viewer, its PNG assets or private report JSON to a public repository.

## Validation and acceptance (2026-11-01)

- 24 new synthetic tests passed; 15 prior v4 PDFium layout tests passed in an isolated, older-source reconstruction. Tests cover two-column/heading ordering, original OCR word coverage, source tampering, XSS escaping, missing pages, duplicate batches, PNG receipts, symlinks, file permissions, rollback and no remote script.
- A synthetic viewer preview was printed to PDF for **visual inspection**. First rendering exposed an overlay scale problem; this was repaired. Final print preview shows colored regions aligned to the source page and legible print colors. Chrome headless screenshot could not complete in this container; WeasyPrint was used for review instead. This is a presentation check, **not browser runtime certification**.
- The current checkout was reconstructed from previous M3 source archives and does not include every latest GitHub module. The earlier tests use fixture validators; full latest-branch regression and real report / OCR accuracy remain unverified.
- No new model calls, remote workflow, report uploads, credentials, licensing changes, or training/promotion are authorized.

## Deferred or still missing

1. Inspector-authenticated case adjudication, verified learning/promotion and field accuracy benchmarking: **explicitly deferred by owner**.
2. Multi-page semantic reading order, table-cell recognition, diagram/photo semantics and reliable paragraph-to-image linkage: **not solved**. This release provides candidate navigation only.
3. Full latest-branch regression, independent separate critic, and browser UX acceptance on the deployment device: **pending**.
4. Complete Milestone 2 live inference, qualified professional testing and customer release: **blocked**.

No automated learning, knowledge library rewriting, approval or client reporting occurs in this increment.
