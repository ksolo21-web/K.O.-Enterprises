# M5 V1 — professional field pilot readiness, not deployment

Date: 2026-11-04. Repository: `ksolo21-web/K.O.-Enterprises`, branch `home-inspection-development`.

## Pilot objective

Independently measure real AI home-inspection serious-defect detection and report quality using permissioned photos/video. Avoid training/holdout contamination and unsupported safety claims. Begin with a **private planning and cohort-audit layer**; do not initiate customer operations, publish reports or remove `PAUSE_AUTONOMY`.

## Protocol / responsibility separation

1. **Owner / legal policy gate:** determine service type, Michigan geographic and professional requirements, customer agreements, insurance, retention/deletion, consent scope and incident response. These must be confirmed by appropriate professionals before real pilot intake.
2. **Independent custody:** recruit/authorize external evaluator; privately record consent and originals, source file hashes, source group IDs, timestamps, V10 byte receipts, video replay records and holdout partitions. Independent external pins must predate model predictions and adjudication.
3. **Professional labeling:** one qualified inspector marks actual defect region and system/severity per photo/frame, with explicit uninspected/inconclusive state; distinct qualified adjudicator resolves disagreements and high-severity hazards. All identities and issuer status must be independently authenticated; local IDs alone are insufficient.
4. **Locked benchmark:** preserve V8/V9 hard minima: 100 actual consented cases, 30 critical defects, all 13 inspection systems, residential and commercial, no missed critical/major defects, at least 95% human-adjudicated precision, at least 10 clean-case and 10 clean-image controls representing at least 10% of cases; no training/holdout property/media overlap. Record coverage and confidence intervals alongside misses and false positives.
5. **Protected execution:** no viewing held-out human labels during inference, no model tuning on test cases, no public source-media or identity upload; keep V9 model/prediction seal, V10 private byte verifier, independent human adjudication and signed review as separate controls.
6. **Product evidence:** after qualified permission, assess actual review corrections, report description completeness, safety referral language, source attribution, PDF accessibility, time/cost and user value. No invented customer demand, market accuracy, or inspection qualification claims.

## Implemented V1 cohort design instrument

`inspection_engine/m5_pilot_readiness.py`, `scripts/m5_pilot_readiness_cli.py` and offline synthetic adversarial tests provide a private declaration-only planning summary, with precise cohort quantities and role separation. Even perfect synthetic inputs return `field_pilot_authorized=false` and `customer_release_allowed=false`. Consent, qualifications, source custody and accuracy are not independently authenticated by the CLI.

## Acceptance blocked until external execution

- Real inspector, independent evaluator and custodian identities and authority verified by relevant issuers.
- Actual consented case-level original media stored off Git, permission and confidentiality agreements signed.
- Independent holdout freeze and third-party quality review under an approved label protocol.
- Actual prediction run and signed results meeting every safety threshold with no source/label leakage.
- Legal/professional operating requirements, insurance and verified human signoff satisfied before any customer-facing release.

**Status: M5 software-planning foundation staged, real pilot not started, production readiness not approved.**
