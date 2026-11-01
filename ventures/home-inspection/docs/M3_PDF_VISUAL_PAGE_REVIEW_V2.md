# Milestone 3 — PDF page-image provenance and independent visual review (v2)

**Scope:** local, consent-declared, previously imported professional reference reports. This is a **private review preparation stage**, not an OCR engine, autonomous defect detection, code-compliance determination, qualified inspector approval, report release, or model training pipeline.

## Work completed

1. `report_page_evidence.py` consumes the existing registered PDF reference bundle, private registry, and the **exact source PDF**. It verifies source byte length and SHA-256, refuses symlinks/FIFOs, and renders explicitly selected pages as private PNGs at 105 DPI inside a bounded child process. Process guardrails include a 1 GiB address space, CPU budget, 40-second wall cap, a max of eight pages per batch, 3 million raster pixels per page, max 8 MB PNG bytes, and a 4 MB metadata response. Missing/large pages **block**, never silently disappear.
2. Each original-page image stores a SHA-256, page number, pixel geometry, source SHA-256, untrusted text-line rectangles, source/registry bundle identities and explicitly unreviewed status. Rotated geometry is normalized to the displayed page. Renderer words are untrusted and are **not** confused with the existing `pypdf` text-character offsets. Table / diagram / photo contents are not read as verified findings.
3. A qualified reviewer can later open these PNGs and **manually select normalized visual rectangles** with a declared building system, category, note and location. These marks are intentionally **not** fake text annotations. They cannot activate existing `report_learning` lessons. A declaration is not an authenticated reviewer or professional license.
4. Before accepting a visual mark, the validator **re-renders the original registered PDF bytes** and compares the full per-page image/line-rectangle metadata, not just hashes copied from a mutable JSON file. Recomputed hashes for a forged PNG are not sufficient to bypass source binding.
5. `report_visual_reconciliation.py` consumes two distinct reviewer-declared records and preserves **all** marks. It suggests spatial overlap using intersection-over-union, holds disagreement/unmatched marks for further review, and deliberately does not merge similar locations, establish semantic agreement, declare root causes, or treat the two declarations as independently authenticated professionals.
6. The reconciliation CLI always first verifies source, registry, original PDF and rendered page provenance. All outputs are new files in a private directory, mode 0600; page-output directories are mode 0700. Nothing modifies the source report or public company repository data.

## Local commands

Use an authorized, consent-declared imported PDF reference and the **same immutable private registry** from the M3 foundation. Keep all original PDFs and JSONs out of public GitHub. The output-parent directory must already exist.

```bash
python -m inspection_engine.report_page_evidence render \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --source-pdf private_case/reference.pdf \
  --pages 1,2,3 --out-dir private_case/pdf_pages_1_3
```

Inspect the rendered page PNGs and original PDF. Page numbers are 1-indexed. The report's existing text review queue remains separate and available. Visual mark files must contain only the reviewer-selected exact rectangles and *unverified* descriptions, for example:

```json
[{"id":"review-01","page":1,"bbox":[0.1,0.1,0.5,0.5],
  "system":"roof","kind":"potential_concern","feature_code":null,
  "location":"Roof view in report","description":"Reviewer-selected area requiring further inspection",
  "reviewer_id":"DECLARED-REVIEWER-A"}]
```

```bash
python -m inspection_engine.report_page_evidence mark \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --source-pdf private_case/reference.pdf \
  --manifest private_case/pdf_pages_1_3/manifest.json \
  --marks private_case/reviewer_a.json \
  --out private_case/reviewer_a_bound.json
```

Repeat with a separately declared reviewer and distinct reviewer_id. Then compare:

```bash
python -m inspection_engine.report_visual_reconciliation \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --source-pdf private_case/reference.pdf \
  --manifest private_case/pdf_pages_1_3/manifest.json \
  --first private_case/reviewer_a_bound.json \
  --second private_case/reviewer_b_bound.json \
  --out private_case/visual_reconciliation.json
```

**Privacy/security:** These commands generate page images containing whatever private images and addresses exist in the original report. Never commit generated case images, extracted text, reviewer statements, or reports to public GitHub. No network/model/OCR services are called. Rights/consent flags are preexisting operator declarations, not authenticated documentation.

## Tested acceptance for this increment

- [x] Bounded exact-source PDF rendering, including raster-image pages and rotated-page geometry
- [x] Output set and source custody: every selected page, all image hashes, no overwrite, private permissions
- [x] Re-render check prevents forged PNG or tampered manifest from becoming trusted evidence
- [x] Invalid source/path/FIFO/symlink/page selections/regions/category/code rejected
- [x] Two reviewer declarations retained; overlapping, conflicting and unmatched marks held without merge
- [x] CLI refuses existing output and does not print extracted customer text
- [x] Synthetic multi-page visual contact sheet manually inspected for page orientation and content retention
- [x] No claims of OCR, qualified review, defect detection, approved labels or customer release
- [ ] Full latest GitHub repository regression (not run)
- [ ] Real consented report with qualified independent inspection labels
- [ ] Authenticated inspector credentials and real adjudication/release governance
- [ ] OCR and evaluated recognition of textless scans, photographs, diagrams, tables and reading order
- [ ] Field-accuracy benchmark and approved feedback/promotion/rollback system

## Known limits and next action

Rendering is a **preparation stage**. The renderer does not infer missing words from pixels, recover scanned text, interpret a photo, determine significance, or judge whether a prior report was correct. Every page remains unreviewed regardless of rendering success. Batches are explicitly 1–8 pages. To cover a 200-page source, batch orchestration must be built with a durable, non-overlapping coverage ledger and case-level completion checks. The PDF text and visual annotation formats are deliberately separate until qualified adjudication can establish evidence alignment. pypdfium2 is a new local dependency, to be added alongside the existing PDF inspection libraries.

**Internal review only.** No separate critic runtime was available. The test suite used an isolated harness for the existing imported-reference and registry validators, so the complete latest-repository integration and field accuracy are unverified. No change to `main`, root `PAUSE_AUTONOMY` or remote runners is approved by this work.

## Renderer licensing choice

This integration uses `pypdfium2` (tested 5.8.0), **not** PyMuPDF/MuPDF. The public pypdfium2 project identifies its Python bindings as Apache-2.0/BSD-3-Clause and PDFium as BSD-style, with third-party license notices required when distributing its binary dependencies. This improves compatibility with proprietary business software but remains subject to legal/license review of the actual distributed wheel and notices. Sources: https://github.com/pypdfium2-team/pypdfium2#licensing and https://pymupdf.io/licensing. No publisher-protected ICC/NFPA/ASTM full texts are ingested by this subsystem.
