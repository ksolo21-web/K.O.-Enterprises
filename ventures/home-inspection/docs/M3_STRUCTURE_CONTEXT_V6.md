# Milestone 3 v6 — positional table candidates and page-boundary context

This increment improves private offline navigation. It does **not** establish reliable table interpretation, semantic understanding, defect recognition, professional approval or learning. Original OCR and PDF text stay separate. Overall M3 remains unapproved.

## Implemented behavior

`inspection_engine/report_structure_candidates.py` builds bounded table-like groups from repeated aligned OCR rows. At least three consecutive rows with 2–8 positional groups are required. Groups split at horizontal whitespace; their left anchors must remain within 0.025 normalized page width and row centers within 0.09 normalized page height. Large breaks and inconsistent group counts split candidates. These fixed heuristics are review aids, not validated detection thresholds.

Each candidate retains source row IDs, original word indices, exact supplied OCR word records, text and boxes. Every OCR word appears exactly once in a candidate or the explicit unassigned-word list. No headers, blank cells, multiline cells, row meanings or defects are inferred. Aligned prose and multiple text columns can mimic a table and remain explicitly ambiguous. Ragged and wrapped content may be left unassigned. Missing OCR produces no invented table.

Page-boundary panels display up to two complete source PDF text chunks from each side of every adjacent physical page break. Original page/span IDs, offsets, hashes and text are preserved in `boundary-context.json`; no text is truncated inside a chunk, joined or carried across a missing page. An image-only page stays textless in this panel even when a separate OCR record exists. PDF page ordinals are not assumed to equal printed page labels. The panels provide context for the reviewer; they do not determine whether the paragraphs continue or refer to the same finding.

The existing `report_study_viewer` command now includes these panels and table candidates. Missing rendered pages have explicit navigation placeholders. The output receipt kind advances to `M3_PRIVATE_OFFLINE_VIEWER_V6`; the CLI arguments are unchanged. New private sidecars are `structure-candidates.json` and `boundary-context.json`, with file hashes in `receipt.json`. The viewer retains no scripts, external links, fonts or requests; source text is escaped. All outputs remain pending review with training/release disabled.

Total PNG payloads are limited to 96,000,000 bytes per viewer, each PNG to 8,000,000 bytes, HTML to 9,000,000 bytes, and each new metadata sidecar to 8,000,000 bytes. Oversized construction fails before creating output. Fewer render batches can reduce asset/structure size; boundary context still covers the whole source, so very large text-only context may require another review workflow. Output ancestors containing symlinks are rejected. These checks do not provide filesystem race isolation or a sandbox for the host browser.

Source validation rechecks original PDF bytes, registry, queue, manifests, PNGs and layout through the existing production validators. Candidate validation reconstructs the expected groups instead of trusting a rehashed candidate. OCR receipts remain **unsigned integrity references, not authentication**: a party who edits and recomputes an OCR receipt can supply altered untrusted OCR text. The original PDF pixels remain essential.

## Reproduction

From `ventures/home-inspection`, with the documented Python/PDF dependencies, FFmpeg, local English Tesseract and DejaVu Sans available:

```bash
python -m scripts.generate_public_fixtures
python -m unittest discover -s tests -v
python -m scripts.build_m3_study_demo --out-dir /absolute/new/private-synthetic-demo
```

The demonstration creates its own synthetic three-page PDF: text/table candidates, a scanned image-only middle page, and a third text/table page. It imports into a locked holdout registry, builds a full text queue, renders two batches, runs actual local Tesseract, indexes the layouts and creates `viewer/index.html`. It never invokes models or networking. Keep any real private-case output outside the public repository.

The optional browser QA driver requires a local Playwright installation and Chromium:

```bash
M3_PLAYWRIGHT_MODULE=/absolute/path/to/playwright \
M3_CHROMIUM_EXECUTABLE=/absolute/path/to/chromium \
node scripts/review_m3_viewer.cjs /absolute/demo/viewer/index.html /absolute/new/evidence-dir
```

A third argument can name a partial synthetic viewer with the middle page omitted. The driver tests the 3-page demonstration, details controls, page anchors, image sizes, mobile layout, and missing-page placeholders. It blocks and records attempted remote page requests. This is browser behavior evidence for the synthetic case, not a browser privacy certification or deployment-device acceptance.

## Actual acceptance evidence

- **22/22 new v6 tests passed**, including unpatched real import/registry/queue/PDFium/Tesseract/viewer integration over two batches. Actual OCR word counts: 28, 16 and 20; table candidates on pages 1 and 3, none on scanned page 2.
- **777/777 home-inspection tests passed**, no skips, independently run by the critic in 61.497 seconds. **229/229 company tests passed**, independently repeated by the critic as well.
- The first full v5 regression exposed **26 preexisting failed/error cases**: 10 page-evidence cases and 15 OCR/document-audit cases using placeholder registries, plus one missing retired A10 workflow file. The critic reproduced those failures from an untouched archive of base `6b8bfeb`. Test fixtures now use real imported/registered sources, including an actual 200-page planning fixture. Production authorization checks were preserved. The A10 record was restored byte-for-byte from commit `93c8593` under `docs/workflows/`; no active workflow was added.
- One parent full-suite attempt stalled at an existing loopback transport test. That module passed independently (16/16), and the independent full 777-test run passed. The isolated stall's root cause is **unresolved**; no claim of a transport repair is made.
- Chromium **153.0.8010.0** loaded all three original local PNGs. Parent checks passed at 1280×960 and 390×844; critic additionally checked widths 360/390/768/1280 and keyboard Enter behavior. All 12 first-page candidate cells were present, image/overlay container dimensions agreed, page anchors/details/missing-page placeholders worked, and no page errors or remote requests were recorded. Headless browser OS sandboxing was unavailable in this container; web-security/CSP checks stayed enabled.
- The first mobile browser check caught overflow from a long unbroken status label. `overflow-wrap:anywhere` fixed it; the browser checks and screenshots were repeated successfully. Actual desktop/mobile screenshots and browser measurements are under `docs/evidence/m3-v6/` and were inspected by parent and critic.

## Remaining milestone work

Reliable cell/header interpretation, robust diagram/photo semantics, semantic cross-page relationships and paragraph-to-image attribution remain unfinished. Live M2 inference, professional adjudication, validated learning/promotion, field benchmarks and customer release remain unapproved or deferred. Do not expand this scoped engineering acceptance into an overall M3 approval. No remote inference trial was launched; `main` and the root pause are preserved.
