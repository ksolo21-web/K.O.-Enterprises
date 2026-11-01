# Resumable checkpoint — M3 layout navigation v4

- User priority: keep engineering Milestone 3; defer real-field benchmark, authenticated qualified inspector adjudication and automatic learning/weight updates.
- Branch: `home-inspection-development` only; base remote head verified as `d3e8a2389007366bf0dbce3adb875930b7329c70` before source work. Always read current head before committing, and do not reset other changes.
- New files: `inspection_engine/report_layout_navigation.py`, `tests/test_report_layout_navigation.py`, `docs/M3_LAYOUT_NAVIGATION_V4.md`, this checkpoint.
- Synthetic PDFium geometry tests: 15 passed, 0 failed; run `python -m unittest tests.test_report_layout_navigation -q` from the repo's `ventures/home-inspection` directory with installed dependencies.
- Existing authoritative `validate_page_evidence`, `validate_review_queue`, `validate_ocr_record` are required by the new source. They were mocked in the isolated old archive test fixture (old package lacks current report-learning validators); read back actual remote source, then run latest-branch regression when practical.
- Unverified/blocked: full latest-branch tests, OCR language/quality, page-layout semantics, multi-column reading order, hidden/nested image object coverage, actual professional review, customer reports, field accuracy and training promotion.
- Must keep root `PAUSE_AUTONOMY` untouched, `main` unchanged, and avoid creating a workflow or deploying model inference.
- Next: page-layout navigation index linking to private review UI and cross-page sections, after validating full integration. Do not claim completion from a passing synthetic suite.
