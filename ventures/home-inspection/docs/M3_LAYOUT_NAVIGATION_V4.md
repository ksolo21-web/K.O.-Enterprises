# Milestone 3 — PDF layout and evidence navigation v4

**Status: development-only.** This is a bounded engineering step before qualified-inspector adjudication, automatic learning, and field accuracy validation. It does not establish table semantics, recognize defects, or authorize customer reports.

## Purpose

The existing v1–v3 report study can import text, render and hash PDF pages, extract untrusted OCR words, and preserve separate visual reviewer marks. This increment makes the PDF *navigable* at the object and geometry level without conflating those data types.

- Use the previously verified `report_page_evidence` render manifest, original PDF bytes, registered imported report, and exact `report_review_queue` to construct a **source-bound per-page index**.
- In an isolated, bounded PDFium child process, enumerate top-level PDF raster image objects and normalize their display-space bounding boxes, including rotated pages. Match counts against the existing renderer to catch omitted or mutated inventories.
- Preserve all previously reported PDF text rectangle navigation hints, with the number of rectangles that could not be localized. These rectangles are **not** mapped to exact `pypdf` text offsets.
- When an existing validated OCR review is supplied, group its word positions into **provisional visual rows** and flag repeated horizontal alignments as possible tables. Preserve every OCR word index and keep table cells, header meaning, reading order, and technical interpretation unverified.
- Pages without OCR, inaccessible images, vector-drawn figures and ambiguity remain human review tasks. PDF raster objects must not be mistaken for a complete inventory of all photographic or diagrammatic content (nested forms/vector drawings may not appear as top-level images).
- Every page links to source PDF SHA-256, render PNG SHA-256, imported page text SHA-256, text span identities, and optional OCR record SHA-256. A stale index must be regenerated against the original case, not accepted through a recomputed checksum.

## Local usage (private report files only)

After the already-approved private `report_learning import`, `report_review_queue triage`, `report_page_evidence render` and optionally `report_ocr_review` steps:

```bash
python -m inspection_engine.report_layout_navigation \
  --reference private_case/reference_bundle.json \
  --registry private_study/registry.json \
  --pdf private_case/original_report.pdf \
  --manifest private_case/render_batch/manifest.json \
  --render-dir private_case/render_batch \
  --text-queue private_case/text_review_queue.json \
  --ocr private_case/ocr_review.json \
  --out private_case/layout_navigation.json
```

Omit `--ocr` when it has not been run. The output is a new private file, never overwritten. The command prints only status and page counts, not report contents.

## Acceptance and bounds

- Parent validators must confirm original PDF, reference bundle, registry, page images, text queue and OCR receipt before new indexing. There is no shortcut to attest these values inside the model.
- At most eight page images per batch, 96 top-level raster objects per page, 3,500 existing PDF text rectangles per page, 6,000 OCR words and 600 visual OCR rows per page. Excess explicitly blocks; data is not dropped to report artificial completeness.
- PDF source bytes only are supplied through subprocess stdin. A child has a 20-second CPU/25-second wall and 1-GiB address-space allowance where supported, and produces at most 350KB JSON. The parent output is capped at 4MB.
- All source geometry requires finite, in-bounds, positive normalized rectangles. Bool, NaN, inverted, and out-of-bounds coordinates are invalid.
- Every output is expressly unverified. There is no model call, training update, code-compliance determination, physical inspection claim, or customer release action.

## Evidence

15 synthetic offline tests, including actual PDFium raster object inventory, 90-degree rotated PDF, repeatable OCR row/group geometry, tampered original, invalid worker pages, forged raster counts, absent OCR, unrecognized coordinates and revalidation. `15/15` passed locally in 23.443 seconds.

**Integration limitation:** The isolated local checkout reconstructed from archived early files does not include the current remote `report_learning.py` and `study_registry.py` dependencies. The isolated tests use explicit mocks for existing source-custody validator calls. Production code calls the real authoritative validators. No current-branch full regression, live customer PDF, qualified review or genuine separate critic passed in this increment. The new source remains unapproved for field use.

## Next engineering stage, without professional or learning gates

1. Add explicit page-to-page section navigation with ambiguous multi-column reading order and page-figure cross-reference links.
2. Improve synthetic table/diagram reconstruction *as review suggestions only*, with no fabricated cells or observation truth.
3. Integrate the index into an inspector-facing private report-study viewer once the validation path has a complete current-branch regression.
