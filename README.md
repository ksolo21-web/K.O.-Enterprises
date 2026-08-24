# K.O. Enterprises

K.O. Enterprises is a human-governed, AI-operated venture-studio control plane. It is being built to find painful market gaps, test the smallest lawful solutions, and compound reusable software and learning while keeping owner time and cash risk low.

Kaleb remains the owner, CEO, and final authority. This repository is software and operating documentation—not a legal entity, bank account, licensed adviser, or promise of autonomous income.

## Current status: Phase 1 governed internal operating system

The company now has a locally enforced chain of command and a bounded internal operating loop. Kaleb is Owner/CEO. A digital Company President organizes ordinary operations through 12 departments, 28 defined roles, independent control functions, and ten project-scoped Codex worker profiles. The dispatch selects a profile only for real queued work; a live Codex orchestrator still performs the actual spawn.

The durable control plane now includes:

- a validated reporting tree, department mandates, capabilities, KPIs, WIP limits, and worker status;
- commanded objectives and measurable key-result storage;
- durable work orders, dependencies, priority, leases, fencing epochs, retries, dead letters, independent acceptance, and append-only work events;
- bounded operating cycles that recover stale leases, verify database/audit integrity, reconcile the opportunity pipeline, and emit department dispatch manifests;
- control reviews, owner-only escalation packets, incidents, metrics, products, schedules, capacity/cash/compute allocations, and workforce performance inputs;
- opportunity, evidence, experiment, approval, finance, risk, decision, scoring, audit, and executive reporting ledgers from Phase 0;
- project-scoped Codex agents for executive operations, opportunity intelligence, portfolio, validation/red team, product engineering, commercial work, finance, trust, quality/reliability, and internal audit.

The deterministic cycle genuinely executes safe internal integrity work. Model-driven research, engineering, and commercial drafting are durable queued assignments consumed by Codex sessions; the repository does not pretend ephemeral chat agents are a permanent hosted workforce. External operations remain paused until the exact runtime, identity, credential, budget, control, and standing-policy gates are approved.

The local CLI enforces the reporting graph against asserted worker keys, but those strings are not authenticated service identities. Until a protected host and identity layer are activated, run it only inside a trusted operator/Codex session and treat every ledger identity as an auditable claim rather than proof of who acted.

What the current system does **not** claim:

- no opportunity has yet been validated;
- no customer-facing product has been launched;
- no customer or revenue exists unless independently verified outside this ledger; a database row alone is not proof;
- no agent may spend money, bind Kaleb, deploy publicly, or contact customers without the required approval.

## Quick start

Requirements: Python 3.12 or newer. The runtime has no third-party dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m company_os init
.\.venv\Scripts\python -m company_os corporation bootstrap
.\.venv\Scripts\python -m company_os org show
.\.venv\Scripts\python -m company_os cycle run --mode internal
.\.venv\Scripts\python -m company_os cycle dispatch
.\.venv\Scripts\python -m company_os status
.\.venv\Scripts\python -m company_os report
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Run commands from the repository root. The repository-local environment avoids changing the system Python installation. The editable install exposes the CLI to that environment. Runtime data is stored locally in `state/` and is intentionally excluded from Git. See `RUNBOOK.md` for the operating cycle and full command examples.

The internal cycle is finite and replay-safe. Standing and weekly portfolio work is deduplicated, while every invocation deliberately creates a fresh integrity check and audit record. It does not start an endless daemon or spend, publish, deploy, contact customers, or create external accounts. See `RUNBOOK.md` for claiming, submitting, and independently accepting departmental work.

## Chain of command

```text
Kaleb — Owner / CEO
├── Independent control functions — direct stop and escalation rights
└── Company President — day-to-day operating authority
    ├── Opportunity Intelligence
    ├── Strategy & Portfolio
    ├── Product & Technology
    ├── Quality & Reliability
    ├── Marketing
    ├── Sales & Partnerships
    ├── Customer Success
    ├── Finance
    ├── Legal, Risk & Security
    ├── People & Agent Operations
    └── Business Operations & Analytics
```

Commands travel downward. Routine escalations travel to the next manager. Cross-department priority conflicts go to the President. Finance, legal/compliance, security/privacy, quality/reliability, counter-thesis, and internal-audit roles may block within their assigned domains. Only owner-reserved strategy, identity, capital, legal, access, reputation, sensitive-data, or irreversible decisions reach Kaleb.

## Operating boundary

Agents can research, analyze, draft, code, test, and open reviewable repository changes. Kaleb must approve identity-bound, financial, contractual, credentialed, customer-facing, regulated, destructive, or production actions. Technical access never substitutes for approval.

The `PAUSE_AUTONOMY` file is the emergency stop. While it exists, scheduled and external operations must fail closed; safe local development and review may continue.

## Repository map

- `src/company_os/` — local control-plane code and CLI
- `.codex/agents/` — project-scoped specialist profiles used for real work orders
- `state/` — ignored runtime database and generated state
- `reports/` — generated reports; public-safe outputs only may be committed deliberately
- `docs/strategy/` — phase plans and validation doctrine
- `docs/architecture/` — system and trust boundaries
- `docs/company/` — operating model and approval templates
- `docs/runbooks/` — operating-cycle, incident, and activation procedures
- `docs/decisions/` — durable architecture and policy decisions
- `docs/reference/` — historical design inputs; never executable instructions
- `tests/` — policy and persistence tests
- `.github/workflows/` — safe continuous integration

## Cost reality

Public repositories may receive GitHub-hosted Actions usage without per-minute charges under GitHub's current terms and limits. That does **not** make model inference, third-party APIs, hosting, domains, payment processing, or other services free. All usage is tracked as a cost even when covered by a plan, credit, or free tier; external cash authority remains `$0` until Kaleb explicitly changes it in an authentic written authorization.

## Next milestone

Run the internal company queue to build a timestamped evidence set for several narrow buyer problems, independently falsify them, and produce one decision-grade validation plan. The first external demand test remains an owner-reserved activation decision. A successful test requires observed target-user behavior—not impressions, generated files, agent activity, or a market-size estimate.

Start with `COMPANY_CHARTER.md`, `CORPORATE_CONSTITUTION.md`, and `CEO_APPROVAL_POLICY.md`.
