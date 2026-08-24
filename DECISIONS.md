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

## DEC-0003 — Establish an executable chain of command

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** Kaleb remains Owner/CEO. A digital Company President holds day-to-day internal operating authority and commands department executives, who command specialized digital workers. Commands travel downward; routine escalations travel to the next manager; cross-department conflicts route to the President. Independent finance, legal/compliance, security/privacy, quality/reliability, counter-thesis, and audit controls retain scoped stop rights and direct escalation routes.
- **Reason:** Owner leverage requires delegated routine authority, while reliable autonomy requires machine-enforced responsibility, review independence, and control functions that revenue leadership cannot overrule.
- **Consequences:** Every meaningful work order names a commander, accountable role, worker, reviewer, acceptance criteria, decision class, resource ceiling, and audit lineage. Kaleb receives only owner-reserved strategy, capital, identity/legal, access/data, reputation, or irreversible matters.

## DEC-0004 — Use bounded durable cycles instead of an unbounded autonomous daemon

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** The internal company runs finite, replay-safe operating cycles over SQLite. Standing and weekly portfolio work is deduplicated, while each invocation creates a fresh integrity record. Each cycle enforces a work ceiling, verifies integrity, recovers stale leases, reconciles objectives and opportunity work, executes allowlisted deterministic internal handlers, and emits department dispatches. Concrete queue items name the project agent a live Codex orchestrator may instantiate; every output requires independent acceptance.
- **Reason:** Finite cycles are observable, recoverable, testable, and compatible with pause and budget controls. Chat sub-agents are ephemeral and must not be represented as a permanent hosted workforce.
- **Consequences:** The public repository is source and governance, not a durable production database. External scheduling needs an approved protected coordinator host, authenticated model/runtime adapter, budget, backup/restore, incident channel, and standing-policy executor. GitHub Actions remains CI, not the company state store.

## DEC-0005 — Preserve external pause through internal-autonomy build

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** Internal planning, research assignments, code, tests, reviews, reporting, integrity checks, and safe recovery may operate autonomously. Spending, credentials, contracts, identity use, outreach, publishing, production deployment, sensitive data, and irreversible actions remain paused and owner-reserved unless an exact approved envelope and executor exist.
- **Reason:** The current request establishes the corporation and delegated internal operations; it does not supply authenticated external accounts, cash authority, legal status, private state infrastructure, or a specific launch approval.
- **Consequences:** `PAUSE_AUTONOMY` remains. Scheduled or external cycle attempts fail closed. This is an activation boundary, not incomplete internal authority.

## DEC-0006 — Adopt a Michigan virtual, low-touch portfolio mandate

- **Date:** 2026-08-24
- **Status:** Accepted
- **Decision:** Treat Michigan, United States as the owner-declared principal operating jurisdiction. Target online-only products whose ordinary acquisition, onboarding, delivery, billing, support, and renewal can be predominantly asynchronous and self-service. Reject business models that require physical client interaction or recurring high-touch sales, implementation, consulting, or account-management labor.
- **Reason:** The owner directed the company to minimize customer-facing work and physical interaction. Low-touch digital delivery better matches an agent-operated, low-owner-time venture studio.
- **Consequences:** Opportunity research and scoring must measure customer-interaction burden explicitly. This mandate does not remove legal duties to customers, tax authorities, regulators, or counterparties; it does not prove entity formation, assumed-name registration, tax registration, licensing, or multistate compliance. Unavoidable support, notices, refunds, accessibility, privacy, security, and complaint handling must remain truthful and functional.
