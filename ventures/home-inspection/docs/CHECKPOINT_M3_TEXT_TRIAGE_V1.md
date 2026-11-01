# Checkpoint — Milestone 3 text-source review queue

Task: continue M3 from existing private report import/comparison/quarantined corrections; add exhaustive page-based review queue with quote-to-annotation bridge and fail-closed privacy/holdout guards. Do **not** close M2 or M3, authorize a remote model run, remove `PAUSE_AUTONOMY` or change `main`.

## Implemented

- `inspection_engine/report_review_queue.py`: source-bound registered-bundle review queue, exhaustive extracted-page text spans, image/OCR warnings, privacy-local CLI, manual quote-to-existing annotation export, unchanged human and release gates.
- `tests/test_report_review_queue.py`: isolated synthetic checks for exact textual coverage, false/negated cue handling, quote geometry, missing pages, feature ownership, tampering, stale sources, registry changes, duplicate claims, symlinks/FIFO, private output, CLI no-content output, and absence of automated promotion.
- `docs/M3_TEXT_TRIAGE_V1.md`: usage and limits.

## Tested

**20/20 focused local code tests passed.** Focused local code tests are synthetic. The tests use current-looking source bundles and explicit stubs for `validate_bundle` and `require_registered`, as the available archived project source predates Milestone 3. Production code calls the actual v1.6 validators. Do not equate isolated unit tests with a full application regression or real report understanding.

## Mandatory next steps

1. Re-run `python -m unittest discover -s tests -q` on a clean checkout of the exact current dev branch, with the actual M3 registry/import modules; fix any compatibility failures without relaxing scope or release gates.
2. Add provenance-preserving OCR and page rendering to bridge scanned/graphical pages; evaluate table reading order and hand-written disclosures on consented reference reports.
3. Develop independently labeled, case-isolated real-report extraction and serious-defect recall evaluation. Report actual misses and false positives; do not approve a model on synthetic fixtures alone.
4. Develop authenticated inspector adjudication, staged versioned lesson promotion/rollback, and holdout anti-leakage; keep all customer data private.
5. Verify latest branch readback, unchanged `main`/pause, and do not start remote CPU trials without new explicit scoped consent.
