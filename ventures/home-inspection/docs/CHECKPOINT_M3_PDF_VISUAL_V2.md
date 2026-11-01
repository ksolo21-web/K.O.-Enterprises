# K.O. Enterprises Home Inspection — Milestone 3 PDF visual review v2 checkpoint

Date: 2026-10-31 America/Detroit. Development parent commit at start: `93be1d67a20909a973947da94f6f6d24f4db993a`.

## Preserved scope

Continue Milestone 3 after the existing report-study foundation and 20/20-text-triage checkpoint. Preserve national SOP/Michigan knowledge, complete observation/evidence custody, M00/T01–T08/Q01/Q02/Q03, controlled report learning, Option 2 report, holdouts, human approval and root pause. Do not send real customer report media to public GitHub or remote providers. M2 live acceptance remains blocked after A10 timeout.

## This change

New bounded PDF page-image renderer and source-custody manifest, manual visual annotation record, second-reviewer spatial conflict and unmatched queue, private no-overwrite CLIs and synthetic regression tests. Fixed first focused failure due to the test helper interpreting `[]` as default pages, not a renderer defect. Hardened output creation to exclusive mkdir and 0600 files; re-render validation stops forged PNG-with-recomputed-hash attempts. Rotated pages preserve displayed orientation. Documented file/CPU/memory/pixel bounds and no OCR/AI/training semantics.

## Checks and evidence

- 40/40 focused synthetic checks passed (12 original page renderer checks, 7 reconciliation tests, 1 full CLI integration test, 20 earlier text-triage tests). Exact local full-suite log retained.
- Three synthetic PDF page renders were opened and visually inspected: text page, image-only page, rotated page. Correct orientations and content presence observed. Contact sheet saved in the local validation package.
- The existing imported-report and private-registry validators were represented in the isolated test harness. The actual GitHub implementations remain authoritative and are imported at runtime; **full checkout regression is pending**.
- No real-inspection findings, live inference, OCR, field validation, training promotion, authenticated reviewer or customer release was exercised.

## Blockers

1. Validate declared `pypdfium2>=5.8,<6` alongside existing PDF dependencies in the actual runtime and validate supported versions, licenses and PDF sandbox resource budgets.
2. Complete real-source integration testing against `report_learning`, `study_registry`, imported PDF/registry payload and the existing text-review queue.
3. Implement per-case whole-report page/batch coverage ledger; never claim a sampled subset is the full report.
4. Add limited, source-bound OCR only where no extractable text exists and only with explicit authorization and verified quotations; evaluate scan/table/figure extraction with professional review.
5. Implement authenticated, qualified inspector adjudication of independently selected visual marks with professional-labeled real cases, holdout segregation, serious-miss statistics and rollback.
6. Retest latest complete repository suite and actual model runtime before seeking Milestone 3 or customer acceptance.

Next executable step: reconcile visual page selections into the existing human correction workflow without treating geometric overlap as proof of matching defects, and add full-report page coverage ledger.
