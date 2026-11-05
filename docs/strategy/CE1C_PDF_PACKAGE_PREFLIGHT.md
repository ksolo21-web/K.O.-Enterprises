# CE-1C — Original PDF Package / Addenda Preflight

**Milestone:** CE-1C first offline implementation · **2026-11-05**  
**Status:** Internal engineering prototype only — **NOT issuer authenticated, NOT independent critic-approved, NOT live**.  
**Files:** `src/company_os/pdf_evidence.py`, `src/company_os/procurement_package.py`, `tests/test_procurement_package.py`.  
**Dependency:** [CE-1A provenance ledger](CE1_SOURCE_PROVENANCE.md), [CE-1B approved source transport](CE1B_PROTECTED_SOURCE_FETCH.md), [company-wide launch requirement](COMPETITIVE_ENGINE_LAUNCH_PREREQUISITE.md).  
**Critical blockers:** [Issues #32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32) and [#38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38).

## What this checks

A local private `package.json` describes one issuer, each required PDF, the declared complete issuer inventory, contiguous addenda, per-file hash, a recent observation date, page-specific quotations and structured claim values. The preflight:

- Rejects missing files, hash mismatches, symlinks, path traversal, duplicate document IDs, missing attachments, missing or out-of-order addenda, stale issuer listings and source documents.
- Parses *real PDFs* with pinned optional `pypdf==6.21.4` inside a separate subprocess with input size, page, extracted-text, timeout and POSIX resource limits. Rejects encrypted/blank/scanned PDFs, forms, interactive actions, annotations, embedded attachments, broken or very large PDFs. This is **not a production-grade hostile-file isolation container**.
- Requires each evidence quote to occur **exactly once** on the specified original PDF page. Detects two different operator-supplied values for a single topic and blocks them unless an exact cited resolution is recorded. A resolution is **not independently validated**.
- Requires evidence for the submission deadline and flags an elapsed deadline. Requires PDF citations for mandatory site visits and blocks elapsed events with missing/unconfirmed attendance. A claimed waiver without a cited original-page passage is rejected, but even a cited waiver remains on HOLD.
- Returns only **BLOCK** or **HOLD_INDEPENDENT_ISSUER_AND_CLIENT_REVIEW**. There is NO approval or client release state. Even the strongest accepted package only establishes that the *given local PDF files and human assertions* are mutually consistent.

## Invocation (local authorized files only)

```bash
# The package folder contains package.json and original lawfully acquired PDFs.
# Never store client originals in the PUBLIC repository or GitHub Actions logs.
python -m company_os.procurement_package /approved/private/package-folder
```

Required root manifest keys (schema_version `1.0`): `package_id`, `issuer_url`, `issuer_name`, `discovery`, `documents`, `required_document_ids`, `expected_addenda`, `evidence`, `resolutions`, `mandatory_events`, and `client_eligibility`.

Each `documents` record contains `id`, `filename`, `sha256`, `kind`, `source_url`, `observed_at`, `issuer_reference`, `sequence` (an integer for addenda, otherwise null). Each `evidence` item provides `id`, `topic`, `value`, `document_id`, `page` (1-based), and an actual `quote`. `resolutions` are explicit topic → selected evidence IDs plus a reviewer-needed rationale. Every addendum must have cited source text. `mandatory_events` use source evidence IDs and an explicitly stated attendance status. The issuer discovery record retains checked date, reference, operator-asserted completeness and any known missing records.

**Deliberately strict date policy:** For this first automated preflight, a deadline or mandatory event timestamp must appear **verbatim in ISO-8601 with timezone** in its page-specific quoted PDF text. Dates written only in natural language therefore **block automated acceptance** until we build and independently verify a safe date-interpretation protocol. A conflicting value cannot be resolved by selecting an older notice over a later numbered addendum. Waiver claims need a separate cited issuer waiver statement. These checks prevent a typed value from being mistaken for original-source proof.

**Mandatory-event omission check:** A conservative text-pattern check blocks a completely empty event inventory when an original PDF refers to a mandatory or required site walk, visit, walkthrough, meeting, or conference. It is a safeguard, **not** complete semantic recognition of every kind of issuer requirement. The independent critic must still review the entire package for omitted conditions.

## Critical residual gaps

1. **Issuer completeness is not authenticatable from the local manifest.** An operator can omit an addendum and also incorrectly assert the number expected. Real monitored issuer portal discovery, original signatures, changes/addenda enumeration, procurement-number/contract-scope verification and independent cross-check remain future work.
2. **PDF page text extraction does not establish understanding.** It may miss diagrams, scanned pages, signatures, tables, maps, charts, embedded links or visually misleading composition. Every page still needs actual human/independent critic visual review. There is no OCR acceptance path in this increment.
3. **Hash integrity is local, not attested issuer origin.** A malicious operator may alter a PDF and its hash. Real signed receipt provenance, protected archive storage, secure reviewer identity and immutable external anchoring remain blocked.
4. **No claim of live procurement eligibility.** Attendance, waiver and client-qualification fields are operator assertions. This implementation cannot certify participation eligibility or make a bid recommendation.
5. **No scheduled network activity or production hosting.** `PAUSE_AUTONOMY` is active, and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` blocks all company launches. CE-1 is still incomplete.

## Acceptance requirements and next executable work

- Run the full repository Python/Node CI plus synthetic PDF adverse scenarios with actual parsed documents, including missing addendum, conflicting deadline, late site visit, unreadable/scanned PDF, malformed package, source hash alteration and interactive PDF.
- Independent internal review must check that the output never implies release approval, that source labels cannot be treated as independent verification, and that test failures remain fail-closed.
- Future CE-1C2: issuer-file retrieval integration and per-attachment provenance (signed authorized source permits), complete changes/addenda enumeration and independent source-page review; verify at least one genuinely lawfully acquired full tender packet with true original issuer attachments.
- Future CE-1D/CE-3: reconcile original-record evidence with competitor battlecards and genuine independently authenticated critic; render and review every PDF page, not text-only.
- Keep Issues #32/#38 open and document test evidence on merge. This document alone is not a production approval.
