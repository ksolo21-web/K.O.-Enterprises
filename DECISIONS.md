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


## 2026-09-06 — Fresh zero-capital venture

Kaleb authorized fresh ideas using public GitHub branches as the build workspace, with $0 capital. The prior-project camera direction was shelved. Built ImportScope as a bounded new catalog-comparison experiment and prepared a separate read-only OANDA demo research lab. No checkout, customer outreach, spending, corporate scheduler or broker orders were activated. See `docs/decisions/2026-09-06-zero-capital-fresh-venture.md` and `docs/ventures/importscope/`.

## 2026-09-06 — Save and use five independent business advisors

Kaleb explicitly requested separate business, financial, tax, growth and revenue advisors reusable across chats. Installed five personal advisor skills and one board coordinator with senior analytical standards, truthful credentials and bounded assignments. Five separate first reviews are preserved under `docs/advisory/reviews/2026-09-06/`.

The coordinator accepts their recommendation to retain one ImportScope experiment and freeze feature expansion while testing a specific report workflow. The current fee illustration now includes published card processing; refund and bank-debit exposure leaves paid commerce unresolved under $0. Qualification and activation remain unmeasured, and no disconnected-checkout period counts as failed demand. A concrete comparative packet is prepared. No entity, merchant account, payment, outreach, public sales launch, recurring operation or OANDA activity was created. The pause and existing controls remain. See `docs/advisory/CURRENT_STATE.md` and `BOARD_DECISION.md` for the resume point, evidence and next action. This records the active task, not an amendment or invented CEO approval for external commerce.

## 2026-09-06 — Execute the first-revenue handoff

The owner directed the team to proceed toward profits. A bounded independent screen of advertised coding bounties found no eligible open task we could verify; a separate cash review distinguished sponsor-paid contributor awards from operating a seller checkout. No bounty was claimed, submitted or paid. ImportScope remains the single experiment.

Prepared `docs/ventures/importscope/CHECKOUT_ACTIVATION.md` with the exact $29 offer, candidate Stripe connection, provider test/live sequence, delivery evidence, public Site audience request, ordinary-fee arithmetic and refund/dispute exposure. Stripe is available but not installed/connected. The current GitHub reader rejects native traffic access, so the reach test remains unstarted with unknown counts. No policy, pause, identity, commercial terms, audience, payment, outreach or actuals were changed by preparing this packet. Routine repository delivery proceeds under existing user authority; commercial connection and exposure decisions remain specific owner dependencies.

## 2026-09-06 — Stripe connected; account actions not exposed

Supersedes the earlier connection blocker: Kaleb successfully connected Stripe during the active execution turn, and the plugin directory confirmed installation. The coordinator and a fresh financial-advisor turn independently found no Stripe actions or tool-search facility in their available tools. No account/mode/capability read, product, price or checkout creation occurred. Do not ask for installation or connection again; resume minimum account inspection when the integration's actions are available. No authentication workaround, secret search or browser fallback was used.

PR 4 was merged to main at `482b13e5713e215b9ec61a0bb3f709d00e484788` after 188 local tests and GitHub CI passed. The tested product, independent reviews and exact checkout handoff now reside on the default branch. Stripe readiness remains unknown, verified venture revenue and initiated external cash spend remain $0, and public audience/cost decisions are unchanged.
