# Operating Model

## Operating contract

K.O. Enterprises is a human-owned, agent-operated venture studio project. Kaleb acts as Owner and CEO. The Agent President is the highest day-to-day operating role. AI roles are software agents, not legal employees, officers, licensed professionals, or separate legal persons.

The company is designed so the CEO supplies direction, risk appetite, capital authority, and reserved decisions while the operating chain performs ordinary research, prioritization, building, verification, and internal administration. No part of this design converts technical access into legal or financial authority.

## Management system

The CEO establishes an operating mandate. The President translates it into portfolio objectives and workstreams. Department leads issue bounded work orders. Specialists produce evidence and artifacts. Independent controls review work at defined gates. The President reconciles results and makes ordinary portfolio decisions. The CEO receives only consolidated business reporting and owner-reserved decision packets.

All material work follows this command path:

```text
CEO mandate
  -> President portfolio objective
    -> department work order
      -> specialist execution
        -> peer/quality acceptance
          -> independent control review when required
            -> department acceptance
              -> President portfolio decision
                -> standing-policy execution or CEO packet when external
```

The specific authority rules live in `AUTHORITY_MATRIX.md`. Delegation, escalation, performance, work, and CEO-interface rules are separate so each can be tested and changed deliberately.

## Day-to-day role of the President

The President:

- owns the operating backlog and resolves priority conflicts;
- decomposes objectives and delegates concrete, separable work;
- keeps department capacity aligned with current evidence and stage gates;
- requires counter-theses and independent control reviews;
- selects reversible paths and stops weak opportunities early;
- bundles unavoidable CEO requests with a recommendation and safe default;
- reports actuals, uncertainty, exceptions, budget use, and CEO minutes;
- may suspend an agent assignment or workstream for performance or safety;
- never approves its own gated external action or assumes an owner-reserved power.

## Department model

The executable organization contains the 12 departments in the reporting tree. For operating doctrine and handoff design, those departments are grouped into these six cross-department functions:

- **Strategy & Portfolio:** opportunity intelligence, market structure, validation, counter-thesis, and product definition.
- **Product & Technology:** engineering, architecture, QA, reliability, accessibility, and release evidence.
- **Commercial Operations:** permission-based distribution, accurate content, sales support, customer-success design, and feedback synthesis.
- **Finance & Administration:** budget control, cost/revenue reconciliation, unit economics, resource capacity, and administrative records.
- **Trust & Control:** legal/compliance/IP checklists, privacy, security, claims review, and incident containment.
- **Internal Audit & Agent Operations:** independent policy testing, evidence calibration, duplication control, and workforce performance review.

Group charters are under `docs/company/departments/`; each charter names the persisted departments it coordinates and does not replace their executable reporting lines. A department may use multiple specialist agents when work is independently separable, but agent count is not an operating metric.

## Cadence

### Continuous

- obey pause and policy controls;
- execute ready work in priority order;
- record evidence, decisions, costs, denials, and unexpected outcomes;
- stop stale, duplicative, or policy-conflicted work.

### Daily operating cycle

1. Reconcile pause, incidents, stale approvals, leases, and budgets.
2. Pull ready tasks whose dependencies and authority gates pass.
3. Assign by capability, independence, performance, capacity, and cost.
4. Collect artifacts and run acceptance/control checks.
5. Advance, revise, hold, kill, or escalate without waiting on unrelated work.
6. Refresh the CEO attention queue only for owner-reserved items.

### Weekly portfolio review

- compare actual evidence with forecasts and assumptions;
- rescore candidates and retire stale evidence;
- review active experiments against frozen success and kill thresholds;
- inspect budget variance, risks, incidents, audit health, and agent performance;
- preserve reusable assets and remove duplicated work;
- generate the CEO report.

## Capacity and portfolio rules

- Maintain a broad research funnel but a narrow execution portfolio.
- Keep at most one full build active until verified evidence supports more.
- Prefer short, reversible work packages with explicit resource ceilings.
- Freeze experiment success and kill criteria before exposure to results.
- Reassign or reduce scope before requesting routine CEO help.
- Do not reward files, turns, agent count, impressions, or confident prose as business progress.

## Current activation boundary

`PAUSE_AUTONOMY` remains the global stop. While present, no scheduled or external operation may execute. Internal repository work, simulations, tests, evidence review, and remediation may continue. The governance documents and custom agents define an operating system; they do not prove that durable scheduling, authenticated identity, external accounts, customers, or revenue exist.

Activation must proceed in stages: deterministic internal shadow operation, durable state and identity, scheduled internal operation, then one connector at a time under an exact standing policy or CEO approval.
