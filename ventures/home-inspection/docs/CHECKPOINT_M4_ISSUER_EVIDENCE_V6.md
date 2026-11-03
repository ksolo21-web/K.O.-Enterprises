# Home Inspection M4 V6 — Issuer-source corroboration checkpoint

**Date:** 2026-11-03 | **Repository:** `ksolo21-web/K.O.-Enterprises` | **Development branch:** `home-inspection-development` | **Release:** BLOCKED; never customer-facing.

## Summary and original requirements preserved

V5 established a 915/915-test baseline for signed reviewer credential and revocation preflight. It could confirm local cryptographic signatures, document hashes and policy freshness, **not** the legitimacy of a claimed professional certification issuer, the actual inspector's identity, or third-party verification authority. V6 adds a second, read-only issuer **corroboration** layer; it must not mutate V5's accepted code, Q02/Q03, PDF artifacts, human signatures or source evidence. It deliberately does **not** upgrade issuer- or identity-verification claims to true.

The user-supplied DeepSeek/Qwen model remains a separate research-only candidate documented in `CHECKPOINT_M4_MODEL_CANDIDATE_DEEPSEEK_QWEN35_9B_2026-11-03.md`. No AI models, external services, customer photos, or paid accounts are installed/used by this work.

## What V6 builds

- `inspection_engine/m4_issuer_receipts.py`: `issuer_evidence_preflight` first requires the complete, existing V5 offline credential and revocation preflight. V6 then verifies two additional **source-bound, Ed25519-signed issuer-corroboration receipts** with strict reviewer role, name/id, issuer, certification ID, report request digest, policy-bound qualification digest, officer/reviewer key registry hashes and short freshness windows.
- Third verifying role must use an Ed25519 public key in a separate verifier registry and provide an out-of-band independently trusted SHA256 pin for that registry. No overlap in signer name, key or organization with either existing reviewer or the two V5 officers. The hash pin alone does **not** establish that the verifier was independently enrolled: it must be supplied and safeguarded by a separately governed source of trust, not typed as an arbitrary self-selected value.
- Captured official association source files are stored in a distinct private non-Git location and checked for exact SHA256, size, symlink avoidance and path containment. Association-domain allowlists and tight URI path rules reject lookalikes.
- For **certification claims only**, use separate codes `ASHI_CERTIFIED` and `INTERNACHI_CPI`, not general membership. Current official directories were confirmed, but an ASHI directory listing or InterNACHI member-ID lookup alone is **not** sufficient to prove active certification or real identity. The receipt demands declared certification status, reviewer-credential match and notes; those declarations remain untrusted until independently verified by the issuer.
- Strong negative paths: missing record, expired or substituted verification, training/experience being substituted for certification, forged signer, changed original capture, URL host/path confusion, role duplication, stale V5 revocation, unsupported issuer, symlink and path escapes, and all release attempts.
- `scripts/m4_issuer_receipts_cli.py`: explicit read-only CLI. Requires operator-supplied *out-of-band* registry SHA pin and monotonic trusted revocation watermark. Never invent these parameters in production.

## Current public issuer verification references (checked 2026-11-03)

1. ASHI official directory: https://www.homeinspector.org/for-consumers/find-an-inspector/ . ASHI describes active members and different ASHI Inspector versus ASHI Certified Inspector (ACI) membership categories. See https://www.homeinspector.org/reporter-articles/find-an-inspector/ .
2. InterNACHI official member-ID lookup: https://www.nachi.org/verify/lookup . This page **only establishes the ability to look up a member ID**; additional current CPI credential checks are necessary. The public association also provides a "Find a Certified Home Inspector" directory.
3. Michigan LARA licensed occupational professions (private general home inspectors not listed): https://www.michigan.gov/lara/bureau-list/bpl/occ . Do not invent a Michigan general private-home-inspector state license. Government code inspectors and specialty trades have different scopes.

For real verification, a professional authorization process must access the issuer's current authenticated response or confirm the claimed qualification directly with the issuing organization. A saved screenshot, URL, local Ed25519 signature, or claimed response does **not** independently prove that the original issuer issued it or that the person shown controls a signing key.

## Schema and private workflow

Only an authorized operator may create private input files. This code does **not** fetch private credentials or perform issuer logins. The verification officer's saved private third-party registry file must contain:

```json
{"schema_version":1,"issuer_verifier_id":"externally-enrolled-id",
 "organization_id":"independent-issuer-verification-org",
 "public_key_hex":"<64-lowercase-hex-ed25519-public-key>",
 "active":true,"enrolled_by_external_authority":true,
 "external_enrollment_reference":"A verified, substantive enrollment reference"}
```

**The `enrolled_by_external_authority` boolean is a declaration, not independently trusted proof.** A production relying party MUST also verify the external organization enrollment and independently pin the resulting public key. This increment cannot perform that process.

Signed receipt envelope: `{"schema_version":1,"key_algorithm":"Ed25519","payload":{...},"signature_hex":"<128-lowercase-hex>"}`. Receipt `payload` must contain:
`schema_version, issuer_verifier_id, verifier_registry_sha256, officer_registry_sha256, reviewer_registry_sha256, project_id, request_digest, qualifications_digest, checked_on, valid_until, claims, customer_release_allowed=false`.
There must be exactly one `claims` row for each of the two reviewers. Each row contains role, reviewer ID, certification issuer, credential ID, official URL, issuer record type, claimed certification status, declared identity-match method, capture date, path/hash, provenance and verifier notes. All claims must pass signature, source, type, age and segregation checks.

Example CLI (paths and values shown as placeholders, **not ready-to-run credentials**):

```bash
python -m scripts.m4_issuer_receipts_cli \
 --workspace /private/case \
 --reviewer-trust /private/reviewer_registry.json \
 --officer-registry /private/officer_registry.json \
 --qualification-attestation /private/signed_qualification.json \
 --revocation-attestation /private/signed_revocation.json \
 --proof-root /private/credential_proofs \
 --issuer-verifier-registry /private/pinned_issuer_verifier.json \
 --issuer-receipts /private/issuer_receipts_signed.json \
 --issuer-capture-root /private/issuer_captures \
 --independently-pinned-registry-sha256 <independently-stored-sha256> \
 --trusted-revocation-sequence <independently-controlled-monotonic-number>
```

The CLI fails closed without any required input. Never store real personal credentials, customer photographs, addresses, original reports, PEM signing keys or full issuer evidence in a public GitHub checkout.

## Acceptance and honesty

- [x] V5 case source, complete signed human reviews, qualification metadata and fresh revocation are compulsory preconditions.
- [x] Exact issuer claim-to-reviewer and credential binding with independent third-role signature and separately supplied pin.
- [x] Exact captured-document SHA checks, bounded files, URL issuer allowlist, unsupported-claim rejection and no release.
- [x] 21 synthetic negative/positive tests implemented in `tests/test_m4_issuer_receipts.py`.
- [x] V6 software integration **validated:** latest source commit `49e7696cfe92e478c511aa6dbb7aeda98fc60932`; GitHub Actions [run 41670261317](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41670261317) completed **SUCCESS**; Python compilation, targeted M3 7+5+28 cases, all **936/936 offline inspection tests** and tracked source integrity check passed.
- [ ] Actual independently governed enrollment trust and issuer-authenticated credential verification are **not performed**.
- [ ] Real issuer documents, actual professional-qualification evidence, signed timestamp authority and revocation governance remain **unverified**.
- [ ] Real labeled defect-detection corpus, qualified-inspector legal sign-off and secure customer-delivery product remain **blocked**.

**Internal review, not independent agent.** Production Milestone 4 score stays under the >9/10 acceptance threshold until all real-world gates pass. Even full synthetic CI cannot convert this into real credential verification, legal status or customer-release authorization.

## Internal critic and acceptance evidence

The software-only V6 preflight increment passes its synthetic negative and regression checks (21 new tests). A separately callable independent critic agent was not available. No real issuer, credential or actual inspector was authenticated; the return contract explicitly says so. Full Milestone 4 remains below 9/10 overall because official credential enrollment, independently established trust pins, live issuer status, serious-defect accuracy and legally qualified human sign-off have **not** been verified. No amount of synthetic regression passing can remove those blockers.

## Next critical-path work

After validating V6 on the newest branch SHA, build a **tamper-evident external trust enrollment and revocation timeline**, including independently retained hash anchors, separate organization officer permissions, nonreplay signing challenges, and a date-scoped case-verification packet. Only then pursue live issuer identity confirmation through supported official APIs or permitted manual professional checks using real authorized identities. Do not substitute synthesized screenshots or self-attested enrollment for actual issuer proof.
