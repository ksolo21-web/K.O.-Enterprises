# M3 v6 — active requirements and recovery checkpoint

Base: `6b8bfeb5abc38169b4891e6b8a66731943b14af8`, branch `home-inspection-development`.

Scope: private offline review aids, not verified table interpretation or semantic understanding.

## Dependency-aware acceptance checklist

1. [x] Recover exact latest branch and read repository rules.
2. [x] Run full home-inspection regression with generated synthetic media: independent 777/777 passed; company 229/229 also passed.
3. [x] Add bounded candidate table rows/cell groups preserving original OCR word IDs, text and boxes, with explicit uncertainty and all unassigned words accounted for.
4. [x] Add consecutive source-page boundary panels from exact PDF spans. Never infer continuation, merge findings, or skip missing pages.
5. [x] Integrate candidates/context into the existing offline viewer; preserve escaping, privacy, page coverage and no-release gates. Bound total assets and metadata.
6. [x] Exercise real import, registry, queue, PDFium rendering/layout, local Tesseract and viewer without substituting source validators, using synthetic 3+ page input and multiple batches. New v6 tests: 22/22.
7. [x] Independent critic checks actual code, regression and output evidence; fix and retest. **9.7/10 scoped PASS**, no blocking findings. Review in `evidence/m3-v6/independent-critic.md`.
8. [x] Commit only source, tests, docs and synthetic evidence. Verified **24/24 GitHub file blobs** at `c4e59b66659591a13aeb8af49e5b35fb530c155c`, plus unchanged main/pause. Delivery receipt in `evidence/m3-v6/github-delivery.json`.

No live model trial, customer report, external scheduled operation, professional adjudication, learning promotion or field benchmark is included. Overall M3 remains unapproved. Unsigned OCR receipts do not authenticate text; OCR remains untrusted even with a matching receipt.

## Evidence and repair record

See `M3_STRUCTURE_CONTEXT_V6.md` and `evidence/m3-v6/acceptance-evidence.json`. Desktop/mobile Chromium screenshots include candidate groups, boundary panels and missing-page navigation; no remote page requests or page errors. The first mobile overflow was repaired and retested. The independent critic additionally tested widths 360/390/768/1280 and keyboard operation.

26 preexisting failed/error cases were reproduced independently from the untouched base. Placeholder registry fixtures were replaced with real import/registration, and the consumed A10 workflow was restored solely as a historical record under `docs/workflows/`, byte-for-byte from `93c8593`. No production authority validator was weakened. One parent regression stalled at an existing loopback transport test; root cause remains unresolved, but the isolated 16-test module and the independent full 777-test suite passed.

The v6 increment passed all eight scoped gates. Final delivery/checkpoint documentation is a follow-up to the verified source commit above; all executable source and visual evidence remain identical to that tested commit.

Next: continue M3 with geometric PDF/OCR text reconciliation and more robust ragged/multiline table proposals, preserving original evidence and uncertainty. Reliable semantics and deferred professional work remain outside this completed increment. Use `M3_STRUCTURE_CONTEXT_V6.md` for reproduction, limitations and exact acceptance evidence. No approval is inherited for new remote model trials or changes to company autonomy.
