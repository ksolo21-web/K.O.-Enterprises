# Milestone 4 — Private Option 2 assembly V1 checkpoint (2026-11-02)

**Scope**: authorized engineering of the private end-to-end reporting stage; not a milestone release or model-accuracy approval. Repository `ksolo21-web/K.O.-Enterprises`, branch `home-inspection-development`. Parent `main` and `PAUSE_AUTONOMY` are unchanged.

## Implemented

- `inspection_engine/m4_assembly.py`: opt-in `assemble_private_draft` starts from an existing source-validated private case JSON (including specialist-staged cases), runs strict project validation, independent SHA-256 custody checks and M4 specialist preflight, then assembles the existing approved Option 2 editorial PDF. It does not invoke a model.
- Every original media ID, hash, area, video-parent/timestamp when supplied, zoom provenance, observation/finding/equipment/limitation ID, citation and conservative evidence classification is preserved in a companion JSON receipt. Unrouted or unreviewed videos remain listed, not silently dropped.
- Receipt stores the exact optional Q02/Q03 decision objects, binds their SHA-256, validates supplied Q03 against the current project and corresponding Q02 record, and labels unvalidated standalone Q02 honestly. Q01 source custody is deterministic; **no separate reviewer is claimed to have run as part of this assembler**.
- Release flags are always false. A qualified human decision is not inferred from any model, finding review flag or formatted PDF. No automatic customer delivery.
- Output directory and PDF/JSON are private by default (700 directory / 600 files). Repeated same-source assembly is idempotent; altered input/source evidence cannot overwrite a prior report. Recheck after PDF generation rejects mid-render evidence changes.
- `report.py` uses ReportLab invariant mode to make otherwise identical PDF generation byte-reproducible. Original five-page editorial opening and complete-record appendix logic are retained.
- `scripts/build_m4_private_draft.py` is an explicit local CLI wrapper; `tests/test_m4_private_assembly.py` contains 11 synthetic-only checks of source integrity, PDF content, identical bytes, Q02 and Q03 safety, video gaps, and review holds.

## Run manually (PRIVATE local project; no customer release)

From `ventures/home-inspection`:

```bash
python -m scripts.build_m4_private_draft /path/to/private/case.json --out-dir /path/to/private/m4_drafts
```

For saved Q02/Q03 records, optionally add `--q02-json /path/private/q02.json --q03-json /path/private/q03.json`. Without those, status remains explicitly unreviewed. Never commit local output, customer media, private report receipts or credentials to public GitHub.

## Gate status

- Engineering code: committed to the dedicated branch.
- Unit suite: **CI result must be confirmed from GitHub run attached to latest source SHA**. Earlier unrelated successful CI cannot be counted as the M4 result.
- Synthetic fixture PDF visual review, full live model inspection, separate Q02/Q03 runtime independence, professional adjudication, authenticated inspector sign-off and client release: **NOT APPROVED / NOT EXECUTED**.
- Milestone 3 deferred professional/model gates remain deferred; V8 baseline and autonomy pause remain protected.

## Required next implementation increments

1. Integrate the existing M2 specialist run, Q02 challenge and Q03 reconciliation with this assembler under an opt-in resumable case workflow, while preserving source-bound stage receipts and recovery from partial failures. Do not re-run paid/downloaded models without authorization.
2. Add a professionally usable private inspector approval UI with authenticated identity, scoped decisions, auditability and no self-authorization; require explicit field inspector approval for any future release path.
3. Add exhaustive PDF appendix coverage for every raw/derived evidence item, verified equipment-date evidence, complete photo galleries and accessible-page acceptance; do not let editorial preview truncation imply a complete inspection.
4. Build a licensed, professionally annotated holdout benchmark on real inspections **only when authorized**, measure serious-defect misses/false alarms and qualify model performance before any production claim.

**Next action**: read the current CI run for the M4 test and full regression, fix every actual failure, and inspect a rendered five-page Option 2 PDF plus appendix before claiming private-renderer acceptance. Never equate a passed synthetic unit test with real-property inspection reliability.
