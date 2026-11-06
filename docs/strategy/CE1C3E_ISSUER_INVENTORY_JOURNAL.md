# CE-1C3e — Permit-Bound Issuer Inventory and Source-Change Journal

**Checkpoint:** 2026-11-05 · **Status:** Internal/offline evidence reconciliation prototype only. **No real issuer capture, production attestation, independent critic or live business launch.**

**Source:** `src/company_os/issuer_inventory_journal.py`  
**Tests:** `tests/test_issuer_inventory_journal.py`, using locally generated original PDFs, synthetic issuer listing HTML, ephemeral Ed25519 source permits and staging-only signing keys.

**Prerequisites:** [CE-1C3a permitted PDF staging](CE1C3A_APPROVED_PDF_CAPTURE.md), [CE-1C3b staging trust](CE1C3B_CAPTURE_TRUST.md), [CE-1C3d separate-UID signing tests](CE1C3D_CROSS_UID_SIGNER.md).  
**Company launch protections:** `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` remain in force.

## Gap addressed

The approved downloader retained separate locally staged files, and the signer could attest local bytes, but there was **no integrated inventory journal** comparing consecutive issuer listings, detecting source additions/removals, blocking missing attachments at the session boundary, or connecting a source's original signed access permit with a trusted *staging-only* receipt.

This increment implements those checks as **offline, human/agent-invoked methods**, not as automatically operating source monitoring. It is not a genuine original-issuer transport attestation and cannot prove that a scraped HTML listing shows all documents in a bid portal.

## New checks

1. **Exact signed source scope.** `IssuerInventoryJournal.record(issuer_id, staged, permit)` verifies the real original local bytes, per-file SHA-256, size, TLS metadata assertions, timestamp and original signed permit. V2 permits authorize HTML listings; V3 PDF permits authorize PDFs. The unsigned metadata cannot claim authentication or publication permission. PDF files are re-parsed in the bounded subprocess before journaling; original listing anchors are extracted and checked against independently allowed HTTPS hosts.
2. **Issuer-to-document continuity.** The journal binds package ID to exactly one issuer, requires the listing to be recorded first, and prevents a document from being attached to a different original URL/issuer identity. For now all PDFs must use the listing's host; cross-host publisher/adapters require separate explicit provenance design.
3. **Version and change detection.** Each new package captures an issuer listing and its attachments; successive issuer-listing snapshots flag newly linked or removed PDF URLs, and successive captures of the same document ID flag changed original content hashes. Older package listings are blocked once superseded by a newer observation, even if still within the usual freshness window.
4. **Completeness before internal review.** `inspect_session` compares the recorded PDF URLs with all original PDF anchor links in the current listing, rechecks stored file bytes/paths and freshness, and blocks missing or extra files or disappearing links pending a separate issuer review. Changed/additional documents are explicitly surfaced, never silently accepted as unchanged.
5. **Optional root-governed staging-attestation bridge.** When a staging-only signed receipt has already been recorded by the separate local signer/replay ledger, `record` verifies the current root policy, signer/receipt status and complete source-metadata match. Strict `inspect_session(require_staging_attestations=True, policy_envelope=..., trust_ledger=...)` blocks absent or subsequently revoked signatures. **Staging signatures cannot certify authentic source transport**.
6. **Private append-only history.** Events are kept in a private local SQLite journal under Git-ignored `state/competitive_engine/issuer_inventory/` with an SHA-256-linked integrity chain, no-update/delete triggers and a finite event budget. This is **not a tamperproof external ledger**, and privileged deletion/rewrite remains possible.

## Offline usage boundary

```python
from company_os.issuer_inventory_journal import IssuerInventoryJournal

# Use already-authorized and locally staged originals; no network call here.
with IssuerInventoryJournal(repo_root) as journal:
    journal.record(
        issuer_id="issuer-001",
        staged=previously_staged_listing,
        permit=signed_exact_url_v2_listing_permit,
    )
    journal.record(
        issuer_id="issuer-001",
        staged=previously_staged_pdf,
        permit=signed_exact_url_v3_pdf_permit,
    )
    report = journal.inspect_session("issuer-001", "pkg-one")
    # report remains BLOCK or HOLD. NEVER customer or launch approval.
```

A full session requires all original listed PDF URLs. With a genuinely root-verified local signing record, the optional strict mode can require a trusted, currently unrevoked staging receipt for every listing and PDF. Both modes still return **HOLD**, never APPROVED.

This journal is not yet automatically connected to an approved real source-capture scheduler, always-on monitoring or any customer-facing decision. It has no network access, signer secrets, outreach, spending or release capability.

## Residual critical blockers

- **Original issuer identity remains unverified.** A source permit and TLS metadata assert permissioned acquisition properties, but an operator could fabricate local files and matching metadata. Production must independently bind exact protected transport/response bytes to a remotely authenticated issuer and sealed fetch-worker evidence without handing that worker signing authority.
- **Issuer package completeness is unproved.** A listing's HTML anchors can omit linked documents inside dynamic JavaScript, pagination, authenticated bid portals, PDFs with referenced attachments, notices on another host and amendments issued after observation. A changed/removed link must be independently reconciled, not inferred to be cancellation.
- **Local audit is not externally anchored.** Protected signing and monitoring, privileged immutable audit sinks, replay across workers, source recovery after failures, key rotation and secure storage are still needed.
- **Independent human or genuinely separate agent critique is absent.** Actual full-page PDF visual review, issuer eligibility and addenda interpretation, adversarial comparison, client fit and the company's 12 mandatory critic gates are not accepted.
- **Production deployment and company release controller are not ready.** GitHub Actions is a finite test runner. No K.O. business launch is allowed, and the mandatory strictly greater-than-9/10 acceptance threshold has not been achieved.

## Acceptance checks for this increment

Run all Python/Node CI, disposable Linux distinct-UID signer checks, document-quality workflow, and the new synthetic issuer/link/change/adversarial tests. Explicitly test unsigned/signed modes, expired or revoked receipts, compromised PDF bytes, missing addenda, removals, changes across versions, cross-issuer ID collision, permit drift, superseded snapshots, and SQL/symlink tampering. Preserve emergency pause, hard launch lock and existing safety tests.

**Next executable critical path:** CE-1C3f verifiable protected original HTTPS response handoff/receipt (without trusting only operator metadata), dynamic/adaptive issuer inventory adapters with exact permissions, externally anchored audit; CE-1D genuine independent source critic; CE-2/4/5 supervised always-on company-wide release gate.

**Resume:** Read current main, this checkpoint, Issues #32/#38, and latest merged PR/CI evidence. Do not describe source authentic or CE-1 accepted solely because all synthetic tests pass.
