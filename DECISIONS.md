# Decision Log

Material policy, architecture, portfolio, and external-action decisions are append-only. Corrections add a new entry that supersedes the prior one; they do not erase history. Detailed records may live under `docs/decisions/` and be linked here.

## DEC-0001 — Establish a human-governed control plane

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** Use this public repository as the shared governance and portfolio control plane. Kaleb retains identity-bound, financial, contractual, credentialed, public-launch, outreach, regulated, and irreversible authority. Customer-facing products move to separate repositories when selected.
- **Reason:** Separating governance from products makes policies durable while keeping product code, access, and releases independently bounded.
- **Consequences:** Routine repository building is allowed; public visibility requires careful secret/data hygiene. Repository automation cannot represent itself as a legal entity or claim independent authority.

## DEC-0002 — Bootstrap with a local standard-library runtime

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** Phase 0 uses Python 3.12+, SQLite, and standard-library code with local persistent state. External connectors remain disabled and scheduled/external execution remains paused.
- **Reason:** This provides testable policy enforcement and auditability without a paid dependency or credential.
- **Consequences:** Initial capability is intentionally narrow. A dependency or hosted service needs evidence, security review, cost accounting, and any required approval.
