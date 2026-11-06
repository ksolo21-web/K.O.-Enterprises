# CE-3A — Root-Governed Critic Review and Exact-Artifact Attestation

**Checkpoint:** 2026-11-05. **Status: offline reviewer signature-verification prototype, not a genuinely independently staffed or live-reviewed operation.**  
**Sources:** `src/company_os/competitive_critic_review.py`, `src/company_os/competitive_critic_audit.py`.  
**Tests:** `tests/test_competitive_critic_review.py` (ephemeral synthetic review/root signing keys, no real reviewer or signed customer report).  
**Related:** [Competitive workbench](CE1F_CE2A_COMPETITIVE_WORKBENCH.md), [Company launch prerequisite](COMPETITIVE_ENGINE_LAUNCH_PREREQUISITE.md), [Market Intelligence QA](../ventures/market-intelligence/QUALITY_SYSTEM.md).

## Why this matters

Earlier document quality checks accepted a reviewer identity string and an asserted digest. They cannot establish who authored the signature or whether the report was modified after review. CE-3A adds public-key-only verification against a separately signed reviewer registry and binds the reviewer assertion to the *exact* competitive dossier SHA-256, delivered artifact SHA-256 and every listed source SHA-256.

**A valid Ed25519 signature is NOT proof that a separate person inspected the originals, used qualified professional judgment, checked screenshots, or agreed to commercial use.** The legal/operational independent-review requirement remains unmet.

## Governance policy

A root signer distinct from analysts/reviewers issues an Ed25519-signed seven-day-or-less policy with reviewer IDs, key IDs, business/venture scopes, public keys, validity windows, revoked keys and revoked review IDs. The verifier gets only `KO_CRITIC_ROOT_PUBLIC_KEY_B64`, not any private key. Key and review revocations are monotonic in the private local critic audit ledger: a subsequent signed policy revision cannot silently remove them. Earlier policies cannot be replayed to revive a disqualified review. A signed policy still requires real trusted root key custody and external identity governance before production use.

## Reviewer attestation requirements

- Distinct author and reviewer IDs, correct venture and approved reviewer key scope. A source operator cannot call itself an independently reviewed provider by declaring a new string.
- Score **strictly greater than 9.0/10** and no more than 10. All **twelve** quality checks (exact required names) present and `true`, no critical findings and no unresolved objections.
- Review completion no older than one hour, expiry within one hour, signer key valid at review completion and current root-signed policy.
- Exact competitive dossier digest, delivered artifact digest, and reviewer-claimed inspection of **every source digest** in the dossier. An edited source/dossier/report fails verification. The inspector's method is labeled `reviewer_claimed_original_review` — a claim, not a cryptographic proof that the named source was accessed.
- Reviewer-claimed rendered-PDF page inspections with screenshot SHA-256 references, matching the artifact digest, sequential unique page numbers from page one and meaningful review notes. **This does not read screenshot pixels or prove visual accessibility.** A separate reviewer must actually see original rendered pages at overview/closeup and record genuine evidence.
- The verifier's successful state is `SIGNED_REVIEW_METADATA_VALID_EXTERNAL_INDEPENDENCE_UNVERIFIED`, with `original_source_truth_independently_verified=false`, `reviewer_independence_operationally_proven=false`, `external_publication_authorized=false`, and `production_engine_ready=false`. A failed gate produces BLOCK, never an approval.

## Local critic audit

`CriticReviewLedger` stores accepted reviewer-policy/review IDs, SHA-256-bound metadata, monotonic revisions and signed key/review revocation events under ignored private `state/competitive_engine/critic_audit/reviews.sqlite3`. It refuses replay review IDs, older root policies and changed policy data with the same revision, and rechecks current revocations on status inspection. SQL mutation triggers plus hash chaining detect accidental/tampered edits but are **not an immutable externally anchored audit**.

## Acceptance requirements and unresolved gaps

The tests cover forged root and reviewer signatures, self-review, score 9.0, any failed of twelve checks, unresolved critical findings, old/revoked keys, missing inspected original hashes, edited dossier/report digest, wrong or missing page evidence, duplicate review, stale policy and revocation replay. **All test reviewers and PDF page assertions are fictional.**

A genuine independent reviewer must have separately protected access and credentials, actually inspect the source content and every rendered PDF page, review substantive accuracy and contradictions (not merely claim to have done so), record genuine source/file evidence and subjective critique, and use an authenticated review execution channel. Review certification alone cannot authorize a launch or customer delivery: source authentication, external audit, secure hosting, supervised monitoring, release-controller no-bypass coverage and CEO's precise approval are all still mandatory.

Keep `PAUSE_AUTONOMY`, `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` and all CEO approval safeguards. No automatically scheduled job, spending, real web harvesting, customer contact or delivery is authorized by this module.

**Next critical path:** Connect reviewer attestation to the durable work-queue result digest, actual artifact renderer and authenticated source evidence, then independent human/agent review, monitored protected runtime, and company-wide release controller. Do not mark CE-3 complete until a real independently authenticated critic and source/page visual inspection have happened.
