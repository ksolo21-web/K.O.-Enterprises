# CE-1H — Comparator claim and advantage evidence integrity

**Checkpoint:** 2026-11-08  
**Status:** Internal, offline defensive increment; no production milestone certification.

## Defects addressed

Schema 1.1 attributed sources and `strength`/`weakness` claims to comparator IDs, but it did not enforce source-subject agreement for `buyer_value`, `cost`, and `contrary` claims. A generic claim could cite a named vendor's evidence and appear unrelated to that vendor. An advantage could also use a valid, named claim about an alternative **outside** its `compared_alternative_ids`. Furthermore, the contradiction rule grouped comparable fact keys globally, so legitimate different values from two different vendors could be incorrectly marked contradictory.

## Defensive behavior

- Every schema 1.1 claim, including generic buyer/cost/contrary claims, must cite **only** matching subject-attributed supporting and counter-sources. A generic (`null`) claim must cite generic sources; a named claim must cite its exact named subject. Do not infer the original source's truth from this equality.
- Exact original URLs and SHA-256 byte digests may be reused among records of the **same** subject, but cannot appear under different subjects, **including generic versus named** records. Null subjects must not evade duplicate checks.
- An advantage's support/contrary claim subject, when non-null, must be listed in its actual compared alternatives. Generic support and contrary hypotheses remain permitted.
- Unreconciled values for the same `fact_key` block **within the same subject**. Different values under the same fact key for different vendors do **not** constitute a contradiction. Legacy schema 1.0 preserves its former generic contradiction scope and receives its existing unattributed warning.
- Adversarial tests cover both rejected evidence laundering and positive, internally held evidence patterns.

## Acceptance evidence and hard limits

- [ ] Full GitHub Python CI completed on this exact PR head; record observed count and status.
- [ ] All new adversarial subject, advantage, source-reuse, and contradiction tests passed.
- [ ] Release-surface / document-quality checks passed.
- [ ] Independent qualified critic and actual original issuer/buyer evidence are **not** supplied by this code-only increment.
- [ ] Root `PAUSE_AUTONOMY`, root production hard lock, and all existing authorization requirements remain unchanged.

**Output is always internal BLOCK or HOLD.** This gate proves only that operator-supplied structures agree; it does not authenticate issuer origins, truth of comparisons, source permissions, consumer demand, payment, a separate reviewer, secure hosting, monitored uptime, or safe release. CE-1 through CE-5 and Market Intelligence M1-M5 remain unaccepted until their complete external evidence requirements are met.

Related: [#32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32), [#38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38), [CE-1G](CE1G_COMPARATOR_SOURCE_ATTRIBUTION.md).
