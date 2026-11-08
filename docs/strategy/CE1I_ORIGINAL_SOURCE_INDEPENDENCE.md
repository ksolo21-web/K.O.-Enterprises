# CE-1I — Original-source independence and rebuttal integrity

**Checkpoint:** 2026-11-08. **Status:** Internal/offline engineering increment, acceptance pending exact-head CI. No production certification or independent external source authentication.

## Defect fixed

In the CE-1H evaluator, a weakness claim required two distinct operator-supplied `origin_id` values to appear corroborated. Two records referring to the *same original URL or bytes* could invent different `origin_id` values and count as independent. Even case-changed publisher aliases were not included in this check. Separately, the same original URL/byte digest could be assigned two local source IDs and cited as both support and contrary evidence in one claim.

## Implementation

- Require two **structurally separate original-source groups** for each weakness. Sources are grouped transitively by shared operator-asserted `origin_id`, case-normalized publisher, exact URL, or SHA-256 byte digest. Multiple IDs do not guarantee multiple real sources.
- Reject a claim whenever its support and counter-source IDs point to the **same original URL or byte digest**, even if those IDs, labels, claimed origin fields and publishers differ.
- Keep source-group detection bounded by existing max claim source counts, preserve the existing BLOCK code for insufficient corroboration, and apply rebuttal collision protection to both legacy and v1.1 schemas.
- Allow two structurally distinct originals on the same approved host, because domain equality alone does not prove the two publishers are the same. **Neither record is authenticated by this check**.
- Add 10 test cases covering exact URL/digest aliases, forged publisher/origin identity, transitive duplication chains, duplicate rebuttal, legacy schema, and positive held patterns.

## Mandatory acceptance

- [ ] Latest PR-head full GitHub Python suite passes and exact count is recorded.
- [ ] Document-quality and release-surface review pass with `release_authorized=false`.
- [ ] 10 new adversarial and positive tests run in GitHub CI.
- [ ] Merge the verified exact head; re-read `main` after merging.
- [ ] Genuine independent critic, verified original-source fetching and historical source-side document identity remain **not available**; **do not** mark CE-1 or M1 accepted.

This strengthens deterministic integrity only. An attacker could still supply invented metadata and invented bytes to the offline workbench. Verified issuer identity, lawful live source access, source completeness, genuine independent cross-source provenance, real buyer payments and an operating separate critic **cannot** be established from claimed metadata.

Global `PAUSE_AUTONOMY`, `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`, protected release requirements and $0 external spend remain unchanged. Every structurally passing dossier stays **HOLD**, never publication authorization. No automated customer contact, broker calls, deployment, payments or client report release is permitted.

Related: [CE-1G](CE1G_COMPARATOR_SOURCE_ATTRIBUTION.md), [CE-1H](CE1H_COMPARATOR_CLAIM_INTEGRITY.md), [Issue #32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32), [Issue #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38), [P0 Issue #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61).
