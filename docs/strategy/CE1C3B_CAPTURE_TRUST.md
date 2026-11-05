# CE-1C3b — Capture Attestation Trust, Key Revocation and Replay Audit

**Checkpoint:** 2026-11-05 · **Status:** Offline engineering prototype. Genuine protected signing infrastructure **not deployed**.  
**Source:** `src/company_os/capture_trust.py` (public-only verifier + private replay ledger), `src/company_os/capture_staging_signer.py` (only a separately injectable, staging-only signing interface).  
**Tests:** `tests/test_capture_trust.py` using ephemeral synthetic signing keys and locally generated PDF files.  
**Previous step:** [CE-1C3a approved source staging](CE1C3A_APPROVED_PDF_CAPTURE.md).  
**Governance:** [mandatory company-wide launch prerequisite](COMPETITIVE_ENGINE_LAUNCH_PREREQUISITE.md), `PAUSE_AUTONOMY`, and the hard-coded production release lock.

## Why this matters

Earlier signed receipt checks trusted a configured public key but lacked an independently authenticated current key registry, signed revocations, monotonic policy revisions and a local receipt replay history. A single compromised or expired key could be difficult to contain, and repeated receipts could be reused without an explicit audit barrier.

This increment provides **two distinctly signed records**:

1. **Governance policy:** An independent trusted root public key (`KO_CAPTURE_GOV_ROOT_PUBLIC_KEY_B64`) validates the Ed25519-signed `policy` envelope, scoped to a policy ID, monotonic revision, short expiration (max seven days), exact approved HTTPS source hosts, authorized capture signer public keys and roles, signer-validity windows, revoked signer key IDs and revoked receipt IDs. The separate `KO_SOURCE_APPROVED_HOSTS` configuration must match the signed registry exactly. A reader cannot manufacture a new policy without the separate root private key.
2. **Unverified staging receipt:** A role-scoped capture signer signs a metadata record only after comparing the original **private local staged file bytes** with the source snapshot's SHA-256 and size. Every receipt explicitly says `capture_method=local_staged_bytes_unverified`, `original_issuer_authenticated=false`, and `publication_authorized=false`. A signed PDF metadata record does **not** assert it came from an original publisher.

The two signatures are domain separated to prevent treating a signed receipt as a signed policy or vice versa.

## Staging signer boundary

The signer interface accepts an injected `Ed25519PrivateKey` object. The approved source-fetch worker contains **no imported signing function**, no signer private key and no automatic publication ability. Production must run the signer in a separately authenticated and restricted process/security boundary with protected key custody and strictly approved handoffs. Merely importing these Python files in the same developer workspace **does not create real process isolation or trusted key custody**.

The signing function refuses mismatched or symlinked filenames, source URL outside the operator-approved exact-host registry, unsafe IP metadata, altered PDF bytes/hashes, unreviewed size mismatches, invalid timestamps and any claim of publisher authentication or release. This is a **local byte-attestation interface only**.

## Replay and policy registry

`StagingTrustLedger` keeps a private SQLite append-only SHA-256 chain beneath ignored `state/competitive_engine/trust/` with restrictive POSIX permissions and no-update/delete database triggers.

- Root-signed policy revisions must increase; an older revision or changed data under the same revision is blocked. Re-reading the same policy is idempotent. **Revoked key IDs and receipt IDs are retained as append-only hash-chained events, and no later signed policy revision may silently reinstate them.**
- The currently active policy revision/digest must match the policy used to accept any staging receipt.
- A receipt ID cannot be accepted twice. Each capture signer key's signing sequence must strictly increase, preventing stale sequence replay or rollback. Invalid signatures, revoked keys and revoked receipt IDs are rejected.
- The verifier **re-reads the original private staged bytes** before recording, so a valid signature for an earlier file cannot be used after a file replacement.
- Any successful local acceptance remains `LOCAL_STAGING_RECEIPT_RECORDED_UNVERIFIED_ORIGIN`, never a verified original-source retrieval, commercial finding, external delivery, bid recommendation or business launch.
- The log hash chain is *not* externally anchored. A privileged actor able to rewrite all SQLite records can forge a replacement chain. Actual immutable external auditing, trusted time and secure offsite retention remain pending.

## Clear distinction from prior CE-1C2 signed capture bundle

The **CE-1C2** bundle expects `capture_method=approved_tls_fetch` asserted by a trusted actual source capture service and bound original issuer listing/PDF observations. **CE-1C3b does not produce that claim.** It produces a distinctly marked `local_staged_bytes_unverified` attestation and is not interchangeable with a trusted authentic issuer receipt. A deployed signer must examine verifiable protected transport records, lawful access and issuer source identity before it can attest stronger claims.

## Accepted tests vs unfinished production requirements

**Offline acceptance tests:** separately root-signed key registry, forged/tampered root or signer signature refusal, root revision rollback, revoked keys and receipt IDs, role narrowing, expired keys or policies, disallowed hosts, private IP metadata, unsupported certification assertions, replay, out-of-order sequences, symlinked/altered staging files, audit hash corruption and strict nonpublication responses.

**Missing:** independent real capture signer/key service and authenticated role-bound API, revocation propagation between isolated workers, production root/key rotation custody, secure database external anchoring, zero-trust proof of original network capture, actual approved public issuer PDF/listing integration, reliable dynamic addenda enumeration, genuine independent critic and a healthy always-on company-wide release controller.

No external source-fetch service was activated and no production private key, live signed source receipt, copyrighted issuer document or real client data is committed.

### Next critical path

**CE-1C3c:** separately isolated signer and authenticated actual retrieval-receipt handoff with revocation propagation and external durable audit anchor; cross-check the issuer's complete addenda and bid-portal versions. Then **CE-1D/CE-3:** independent reviewer on original pages, version digests and adversarial competitor intelligence. Then **CE-2/4/5:** genuinely running company-wide service and production release safeguards.

**Review:** Internal code review and GitHub CI only. Do not mark CE-1 complete or score overall engine above the mandatory strictly greater than 9.0/10 production threshold without actual independent evidence.

**Checkpoint for resumption:** Read this document, current GitHub main, last merged PR and CI, Issues #32 and #38, source modules and pause/launch policy before continuing. Preserve all earlier work.
