# CE-1C3a — Approved PDF and Issuer Listing Capture (Private Staging)

**Checkpoint:** 2026-11-05  
**Status:** Engineering prototype, offline mock-tested. No real external fetch has been authorized or run.  
**Code:** `src/company_os/approved_pdf_capture.py`, plus `src/company_os/approved_source_fetch.py` PDF transport extension.  
**Tests:** `tests/test_approved_pdf_capture.py`.  
**Owner controls:** `PAUSE_AUTONOMY`, company `policy.enforce_action`, and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` are mandatory and unchanged.  
**Upstream:** [CE-1C2 receipt verifier](CE1C2_SIGNED_CAPTURE_BINDING.md), [CE-1B HTTPS transport](CE1B_PROTECTED_SOURCE_FETCH.md), [Master roadmap](../ventures/market-intelligence/BUILD_PLAN.md).

## Purpose

CE-1C2 can verify cryptographically signed receipt metadata against local PDFs but could not acquire original PDFs itself. CE-1C3a adds an **explicit, permissioned single-GET retrieval and private staging path** for text/HTML issuer listings and actual PDF attachments.

The old **V2 Ed25519 source permit** remains **text/HTML only**, maximum 512 KB; it is not silently upgraded to PDF access. A new **V3 Ed25519 permit** explicitly includes `media_type=application/pdf` and a per-file limit up to 4 MiB. All permissions remain bound to an exact canonical HTTPS URL, an independently configured exact hostname allowlist, unexpired source-governance signer and the existing company external-action approval.

The downloader uses the existing checked public DNS/IP pinning, original-host TLS and hostname verification, no redirects, no unapproved content-type, no compression, and a hard response byte cap. It refuses compressed or ambiguous headers. PDF bytes must begin with a PDF header, then the PDF goes through the already-bounded child-process text/page inspector **before** any private file is created. Scanned, encrypted, unreadable or interactive PDFs still fail closed. An actual capture of scanned or image-only documents needs a protected separate review flow later; this feature does not silently treat OCR as verified.

The worker checks the company pause and exact permit again after network retrieval, and once more before private persistence. Files are written into `state/competitive_engine/capture_staging/<package-id>/`; the entire `state/` tree is Git-ignored, with restrictive POSIX permissions, symlink path refusal and no-overwrite file creation.

`stage_issuer_listing` saves a UTF-8 original HTML listing only when it contains supported approved-host PDF anchors. `stage_pdf` writes one exact named PDF only after permitted retrieval and parsing. Neither operation enumerates or automatically follows links. Every PDF URL needs its own signed permit and separate company approval.

## IMPORTANT: not independently signed capture evidence

The output is a `StagedSource` status `UNSIGNED_CAPTURE_REQUIRES_SEPARATE_ATTESTATION`, with file hash, URL, issuer-transport fingerprint, observed timestamp, byte length, reviewed PDF page count and claimed source permit ID.

**This data is NOT a signed CE-1C2 receipt**, cannot be added directly as a trusted `capture_receipts.json`, and must never be represented as independent original-source verification. An **authentic separately protected receipt signer** must compare raw secure transport logs, verify issuer authorization, attach a trusted actor identity, sign the final capture record under a separately protected private key and retain an audit trail before the CE-1C2 signed-bundle gate can operate. Signers are not implemented here.

Even an eventual valid signature can prove only the configured signer attested the capture, not that the issuer has no unlisted addenda, no hidden portal attachments, no updated mandatory site visits or that a customer is eligible. Genuine independent critic review remains required.

## Internal example (not authorized to execute live)

A prepared caller would supply `repo_root`, `package_id`, `document_id`, an actual **signed V3 PDF permit**, and a separate current company `call_approved_api` approval to `stage_pdf`. For an issuer HTML listing, use `stage_issuer_listing` and a separate V2 permit. Both are ordinary Python library calls; there is deliberately no unauthenticated URL CLI or scheduler, and the company pause blocks execution in the repository today.

For tests only: network and TLS responses are mocked with synthetic PDF files. Never put actual issuer originals or client private data into GitHub, CI logs, or this public documentation.

## Acceptance for this increment

- Validate V2 text-only vs V3 PDF-only signed permits, maximum body size, wrong MIME/redirect/invalid PDF rejection, and exact-host approval **before DNS/network**.
- Demonstrate an emergency stop prevents both initial fetch and post-download persistence.
- Demonstrate no overwrites, no path traversal, rejected symlink destinations, and private ignored state.
- Confirm the PDF inspector sees real synthetic PDF bytes and rejects scanned/invalid PDFs.
- Verify that every returned result is still marked unsigned, unauthenticated, independent-critic-unapproved and publication-blocked.
- Run all repository Python tests, Node ImportScope tests, and document-quality workflow without code changes or client data side effects.

**CE-1C3b follows:** [Signed staging-only attestation and root-governed revocation/replay](CE1C3B_CAPTURE_TRUST.md). This is not a production signer or a genuine issuer TLS capture receipt.

## Remaining launch blockers

1. **CE-1C3b:** Capture worker and protected signer identity boundary plus genuine immutable receipts, revocation/replay prevention, external issuer policy/rights verification and realistic end-to-end **authorized** original-source integration.
2. **CE-1C3c:** Full issuer portal listing and addenda discovery, JS/dynamic and multiple-host attachment handling with separately approved adapters; pinned individual PDF/source receipts and periodic change detection where explicitly authorized.
3. **CE-1D/CE-3:** A genuine authenticated independent reviewer verifying real PDF pages, bidder eligibility, competition strengths/weaknesses and all mandatory 12 critic criteria; output must be digest-bound.
4. **CE-2/4/5:** Protected host, durable queue, monitoring, actual release-controller enforcement across **every** business and connector, incident recovery and explicit CEO approval. GitHub Actions is not a continuously running service.

**Reviewer declaration:** Internal review only. No separate critic runtime is available. Do not score the overall engine above 9 or claim CE-1 complete based on synthetic acceptance tests.
