# Milestone 3 — private OCR and full-document evidence coverage v3

**Development-only:** This is a bounded, privacy-local document study workflow. It cannot certify defects, determine whether a building is safe, authenticate a home inspector, automatically correct a report, promote lessons, alter model weights, or release customer output. It extends the v1 text review and v2 PDF pixel evidence without modifying their source or control gates.

## What is implemented

- `inspection_engine.report_ocr_review`: actual offline Tesseract 5-compatible OCR over **original PDF-derived PNG bytes** from a verified v2 page manifest. Fixed English PSM3 TSV mode, normalized word rectangles, untrusted confidences, page/source SHA-256, bounded child execution and output. OCR is not merged into the imported `pypdf` text and is **not** a verified quote or diagnosis.
- `inspection_engine.report_document_coverage`: creates 8-page chunk plans up to the existing 200-page import limit; checks **every submitted render batch** against the original PDF and registered bundle, rejects duplicate pages, enumerates missing pages, remaining no-text OCR tasks, OCR attempts with no recognized words, and all pages pending professional visual review.
- Review pairs: binds the existing two-reviewer spatial reconciliation to each exact render batch, preserving disputes and unlinked marks. Reviewer ID strings are **declarations, not verified credentials**. A page image having been rendered, OCRed, or marked is never considered professionally inspected.
- Cross-modal case review: keeps source-text quote annotations, reviewer-selected visual rectangles, OCR word receipts, and model-generated observations separate. Existing `prepare_comparison` is invoked for any provided *text* annotations; **visual and OCR records are not converted into text-source annotations**. Every reference mark remains in the review queue.
- Optional `record_cross_modal_decisions`: human-declared possible correspondence, possible conflict, possible missed issue, or unresolved review action for every source mark. The result contains zero verified defect labels and zero promotable lessons. It **does not write into the existing learning registry**.

## Local private commands

Required prerequisites: Python 3.12+, existing local requirements (`pypdfium2`, Pillow, pypdf), and installed local **Tesseract** with English language data. `tesseract --version` must work; no cloud OCR is used. No new account or paid service is required. Tesseract licensing and binary distribution should be reviewed before shipping to customers.

Import the PDF under the existing `report_learning import`, then use the existing `report_review_queue triage` command.

```bash
python -m inspection_engine.report_document_coverage plan \
  --reference private/reference.json --registry private/registry.json \
  --out private/document_plan.json

# Render each sorted batch from document_plan.json using the existing M3 v2 renderer:
python -m inspection_engine.report_page_evidence render \
  --reference private/reference.json --registry private/registry.json \
  --source-pdf private/original.pdf --pages 1,2,3,4,5,6,7,8 \
  --out-dir private/pages-001

# Review OCR from the raster, for example, original PDF page 2:
python -m inspection_engine.report_ocr_review \
  --reference private/reference.json --registry private/registry.json \
  --source-pdf private/original.pdf --manifest private/pages-001/manifest.json \
  --pages 2 --out private/ocr-pages-001.json

# Create a private batches.json containing records like:
# [{"manifest":"private/pages-001/manifest.json","render_dir":"private/pages-001"}]
# Optionally create ocr_index.json: ["private/ocr-pages-001.json"]
python -m inspection_engine.report_document_coverage audit \
  --reference private/reference.json --registry private/registry.json \
  --text-queue private/review_queue.json --source-pdf private/original.pdf \
  --batches private/batches.json --ocr-records private/ocr_index.json \
  --out private/document_audit.json
```

Outputs use a new filename, mode `0600`; render directories and PNG files use owner-only permissions. The CLI returns only status and counters, not private report words. Source identity is checked **before OCR**. Text review and full PDF page review remain mandatory even if OCR returns legible words. There is no network call, API service, automatic code-violation allegation or customer release path.

The `cross_modal_queue` and `record_cross_modal_decisions` functions are internal APIs; the existing report-learning `compare` and `correct` commands remain authoritative for quote-bound human corrections. A verified visual-source correction pathway and credential verification are **not implemented**. Source checksums are integrity receipts, not authenticated authorship.

## Acceptance evidence and blockers

The new synthetic fixture is a three-page PDF (text, raster-only legible scan, text). When Tesseract is installed, tests run **real Tesseract OCR**; without it, they exercise controlled TSV behavior plus an explicit missing-binary blocker. Available real OCR verifies visible words against its image and reject forged source, altered hashes, invalid geometry, repeated pages, conflicting reviewer declarations, fabricated text quote annotations, and automatic approval flags. The previous v2 tests are also run separately. This is not a qualified inspector benchmark and has no real-property detection sensitivity result.

Still blocked: comprehensive scanned-page layout/table/handwriting recognition; real inspector credentials, source rights and consent authentication; two-reviewer adjudication decisions on genuine cases; semantic alignment to actual physical components; evidence-backed lesson promotion, rollback, held-out real case accuracy and full latest-branch CI regression. No end-to-end Milestone 2 live-model acceptance has passed. All customer releases stay blocked.
