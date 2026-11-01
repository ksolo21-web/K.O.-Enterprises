# M3 v5 recovery checkpoint — reading order and private offline viewer

Date: 2026-11-01 (America/Detroit). Target branch `home-inspection-development`; parent at start `968f8bf2d82b7d0f53c4834fa2338a6d73d7f448`. Root `PAUSE_AUTONOMY` and `main` must remain untouched.

## Delivered source files

- `inspection_engine/report_reading_order.py` — bounded OCR word-lossless candidate column order.
- `inspection_engine/report_study_viewer.py` — local offline source-backed private HTML/PNG viewer and CLI.
- `tests/test_m3_reading_viewer_v5.py` — synthetic tests, private-output security, no premature approval.
- `docs/M3_READING_ORDER_AND_PRIVATE_VIEWER_V5.md` — data contract, CLI and limitations.
- This checkpoint.

## Validation gates

- New v5 test suite: 24 passing.
- Prior v4 PDFium layout tests: 15 passing.
- Total targeted: 39 successful, run in separate processes. Full GitHub suite **not run**.
- Visual inspection: printed HTML preview after overlay and contrast fixes; no external browser runtime/interaction certification.
- Test harness uses locally reconstructed source and stubbed authority validators for the new viewer tests. **Do not describe this as full upstream integration acceptance.** Production viewer code calls authoritative validation functions.
- Verified omissions: no automatic OCR interpretation, table classification, cross-page inference, credential verification, training, customer release or real accuracy.

## Execution boundary / next task

Before integrating with a real case: validate all original PDF and PNG sources using the latest repo's v1.6+ registration and v2–v4 render/audit stack. Exercise a full held private synthetic 3+ page test with OCR, table columns, alternating images and page breaks; inspect in a real desktop browser. Then run latest-branch regression. Do not start remote Ollama/GitHub CPU trials or change company autonomy controls absent fresh authorization.

Potential upcoming work **within deferred constraints**: multi-page navigation batches, safe inspector selections export, offline UI search/highlight, and PDF text/geometry reconciliation. Qualified adjudication, field benchmarks and verified learning remain deferred.
