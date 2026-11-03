# Home Inspection — M4 V5 professional reviewer credentials and revocation preflight

**Date:** 2026-11-03 | **Branch:** `home-inspection-development` | **Release:** ALWAYS BLOCKED | **Scope:** Synthetic security engineering, not real licensing/authentication.

## Why this increment was necessary

V3 introduced two source- and PDF-bound Ed25519 review signatures. They prove possession of registered keys, **not** a person's identity, qualification, employer, independence, experience, professional scope or continuing authority. V4 verified the real browser forms and PDF page renders. V5 adds a **separate read-only credential-evidence preflight** to reject locally insufficient review documentation without altering reports or enabling publication.

**Jurisdiction correction:** Michigan does **not** currently issue a general private home-inspector state license. Requiring a fictitious Michigan state home inspector license would block legitimate practice and create false legal assertions. The code therefore accepts only a dated Michigan-specific policy snapshot (general private residential visual inspection), distinguishes it from governmental building/code inspector licensing, and evaluates documented professional competence/experience/certification. This snapshot must be manually rechecked by 2026-12-03; out-of-state or actual property cases without verified Michigan jurisdiction stay blocked.

Primary/specialist references recorded in `knowledge/m4_michigan_reviewer_policy_v1.json`:
- Michigan LARA occupational licensing: https://www.michigan.gov/en/lara/bureau-list/bpl/occ
- Michigan LARA Construction Codes licensing: https://www.michigan.gov/lara/bureau-list/bcc/sections/licensing-section
- National Home Inspector Examination Michigan regulations: https://nationalhomeinspectorexam.org/regulations/michigan/

These links are informational, **not a live government licensing API**. The exact case jurisdiction, specialty work, consumer contracts and applicable local requirements still require separate review. Never infer that absence of a statewide home-inspector license means other business, specialty, insurance or contract obligations are inapplicable.

## New implementation

- `inspection_engine/m4_credential_gate.py`: function `professional_review_preflight()` for private local read-only examination. Must see **both** preexisting signed reviewer decisions, authentic signed qualification and signed revocation records, exact project/report request hash, currently pinned reviewer trust and verified source/proof bytes.
- Two reviewer key holders and two separate officer key holders: `qualification_officer` and `revocation_officer`. **No overlap** in reviewer IDs, reviewer public keys or declared organizations between reviewer and officer roles; the two officers must also have distinct IDs, keys and organizations.
- For **each** signed reviewer: explicit role, matching registered key, separate organization, qualification basis (documented field experience, documented training or voluntary professional certification), issuer, identifying metadata, scope, evidence bytes with matching SHA256, evidence freshness (≤30 days), expiry, identity-check description, independence attestation and conflict-of-interest check.
- Proof bytes must remain in a private root outside original customer evidence, case workspaces and Git; unauthorized symlink/relative-path escapes are denied.
- Revocation officer signs the **same case request**, reviewer registry hash, date, expiry, sequence, and enumerated revoked reviewer/officer IDs. Revocation snapshot must be fresh (at most 1 day old) and valid for no longer than 2 days.
- **Rollback protection**: caller MUST supply `minimum_revocation_sequence` obtained from an independently controlled authoritative system of record. The local signed revocation snapshot must meet that monotonic watermark. The CLI does not invent or provide a sequence. A locally typed number alone does not create a trustworthy independent anchor.
- Dated policy snapshot: `knowledge/m4_michigan_reviewer_policy_v1.json`. Unknown jurisdiction, future-dated or expired policy snapshot fails closed. Never auto-infer that an inspector is valid merely from a credential label.
- `scripts/m4_credential_cli.py`: local **read-only** CLI, no internet, account creation or customer release:

```bash
python -m scripts.m4_credential_cli \
  --workspace /private/cases/CASE \
  --reviewer-trust /private/trusted_reviewers.json \
  --officer-registry /private/trusted_qualification_officers.json \
  --qualification-attestation /private/signed_qualification.json \
  --revocation-attestation /private/signed_revocations.json \
  --proof-root /private/professional_qualification_evidence \
  --trusted-revocation-sequence 42
```

**Important:** The sequence `42` is purely an illustrative placeholder, **not** a valid production value. Obtain a real minimum from a protected independently managed revocation log. All personal credential proof, certificate documents and signer PEM private keys must be kept private and never committed. The verifier sees only locally supplied signed claims; it cannot establish which person really controls the officer key without prior external vetting.

## Acceptance against existing milestones

- The new gate does **not** change `m4_human_review.verify_reviews()`, `case_state.json`, `m4_pipeline`, `report.py`, `PAUSE_AUTONOMY` or the production/no-release contract.
- No claim of real verified identity, issuer/registry status, legal compliance, independent ownership of organizations or actual field competence is made, even when the synthetic precheck returns a passing `LOCAL_SIGNED_CREDENTIAL_EVIDENCE_PRECHECK_ONLY` status.
- There is no programmatic `release_allowed=True`, customer delivery, professional final approval, or way for a model to self-certify.
- New synthetic security tests in `tests/test_m4_credential_gate.py` verify successful non-releasing precheck and negative cases for missing signed reviewer, altered proof, tampered officer signature, self-certification, shared officer key/organization, stale/expired/future qualification and revocation data, conflicting organizations, untrusted credential basis, identity mismatch, revocation after signing, stale legal policy, private/Git path restrictions, symlinks and revocation rollback.
- Existing 892/892 tests and V4 Chromium three-viewport + 13-page PDF synthetic visual evidence are preserved; a full new HEAD-CI must verify V5 integration. Do not assume success merely because files were committed.

## Security limitations / mandatory remaining work

1. **No independently authenticated identities or real approved enrollment:** current trust and officer registry files are operator-supplied; signed local declarations are NOT proof of what any licensing, certification or identity authority actually found.
2. **No live issuer verification:** need official API or carefully controlled manual corroboration, evidence receipt (exact source/URL/credential number/date), independent reviewers and immutable identity-audit trail. Qualification statuses must not be promoted from self-reported claims.
3. **Revocation watermark trust is external:** this CLI can compare a signed snapshot with an externally established sequence, but cannot itself protect against a dishonest or rolled-back external source. Do not use a user-chosen watermark in production.
4. **Multi-jurisdiction/legal requirements** need separately validated policies and the correct case address/jurisdiction. No automatic assumption that MI covers other states.
5. **Real field evaluation** and professionally labeled serious-defect detection data, plus human accessibility and larger-report reviews, remain mandatory.
6. **Actual customer release is prohibited.** Do not merge such capabilities into this increment; retain reviewer feedback and Q03/report holds until professional approval architecture is separately implemented.

**Internal review only; no separate callable critic agent was available.** Acceptance is limited to synthetic testable enforcement, not professional/business readiness. Strict >9/10 plus every mandatory check is required for true production approval.

## Resume instruction

On a subsequent **“continue Milestone 4”**, first verify HEAD CI for this V5 checkpoint and repair any failed tests, then prioritize independent identity/credential issuer verification and a controlled, immutable revocation source, followed by larger-case visual stress tests and supervised field-label evaluation. Preserve the experimental DeepSeek/Qwen model checkpoint separately; no model was downloaded or installed in V5.
