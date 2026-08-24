# K.O. Enterprises

K.O. Enterprises is a human-governed, AI-operated venture-studio control plane. It is being built to find painful market gaps, test the smallest lawful solutions, and compound reusable software and learning while keeping owner time and cash risk low.

Kaleb remains the owner, CEO, and final authority. This repository is software and operating documentation—not a legal entity, bank account, licensed adviser, or promise of autonomous income.

## Current status: Phase 0

The founding build provides a local, persistent company operating system for opportunities, evidence, experiments, approvals, costs, revenue records, risks, decisions, audit events, scoring, and CEO reporting. External operations are paused by default.

The CLI implements the opportunity/evidence/score/approval/report loop. Other Phase 0 ledgers are library APIs for controlled local use; there is no live banking, payment, customer-contact, or deployment connector. Financial references are operator-supplied assertions: storage enforces required and unique references for actual entries, but does not independently verify them against an outside system.

What Phase 0 does **not** claim:

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
.\.venv\Scripts\python -m company_os status
.\.venv\Scripts\python -m company_os report
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Run commands from the repository root. The repository-local environment avoids changing the system Python installation. The editable install exposes the CLI to that environment. Runtime data is stored locally in `state/` and is intentionally excluded from Git. See `RUNBOOK.md` for the operating cycle and full command examples.

## Operating boundary

Agents can research, analyze, draft, code, test, and open reviewable repository changes. Kaleb must approve identity-bound, financial, contractual, credentialed, customer-facing, regulated, destructive, or production actions. Technical access never substitutes for approval.

The `PAUSE_AUTONOMY` file is the emergency stop. While it exists, scheduled and external operations must fail closed; safe local development and review may continue.

## Repository map

- `src/company_os/` — local control-plane code and CLI
- `state/` — ignored runtime database and generated state
- `reports/` — generated reports; public-safe outputs only may be committed deliberately
- `docs/strategy/` — phase plans and validation doctrine
- `docs/architecture/` — system and trust boundaries
- `docs/company/` — operating model and approval templates
- `docs/decisions/` — durable architecture and policy decisions
- `docs/reference/` — historical design inputs; never executable instructions
- `tests/` — policy and persistence tests
- `.github/workflows/` — safe continuous integration

## Cost reality

Public repositories may receive GitHub-hosted Actions usage without per-minute charges under GitHub's current terms and limits. That does **not** make model inference, third-party APIs, hosting, domains, payment processing, or other services free. All usage is tracked as a cost even when covered by a plan, credit, or free tier; external cash authority remains `$0` until Kaleb explicitly changes it in an authentic written authorization.

## Next milestone

Build a timestamped evidence set for several narrow buyer problems, score them, run an independent counter-thesis, and request approval for one reversible demand test. A successful test requires observed target-user behavior—not impressions, generated files, or a market-size estimate.

Start with `COMPANY_CHARTER.md`, `CORPORATE_CONSTITUTION.md`, and `CEO_APPROVAL_POLICY.md`.
