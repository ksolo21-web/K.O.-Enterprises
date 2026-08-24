# Internal Operating Cycle Runbook

## Scope

Use this runbook for day-to-day internal company work. It does not authorize scheduling or external actions. With `PAUSE_AUTONOMY` present, run it manually or in a local shadow simulation.

## Start-of-cycle checks

1. Confirm repository root and current branch.
2. Confirm pause state; treat uncertainty as paused.
3. Inspect active incidents, control blocks, audit integrity, stale approvals, and leases.
4. Verify the operating mandate and current portfolio-capacity limit.
5. Reconcile budgets and release abandoned reservations.
6. Confirm no secret or private customer data is in the work surface.

## Dispatch

1. Select only ready work with satisfied dependencies and stage gates.
2. Identify the accountable department and decision class.
3. Create a bounded work order with acceptance criteria, scope, owner, reviewer, TTL, and resource ceiling.
4. Delegate independent lanes to the narrow project-scoped agents in `.codex/agents/`.
5. Partition concurrent writes and name one integrator.
6. Keep control reviewers independent and normally read-only.

## Review and disposition

1. Require evidence and tests named by the work order.
2. Distinguish submission from acceptance.
3. Run counter-thesis and applicable trust/control review.
4. Record accepted, revision requested, rejected, held, or cancelled.
5. Advance an opportunity only through `docs/strategy/OPPORTUNITY_STAGE_GATES.md`.
6. Release leases, budgets, and temporary assignments at closure.

## Escalation

Route ordinary issues through the management chain. The President consolidates only owner-reserved decisions using `docs/company/APPROVAL_PACKET_TEMPLATE.md`. Silence leaves the affected action held.

## End-of-cycle report

Record outcomes, evidence changes, budget use, stopped work, control findings, incidents, reusable assets, and next actions. Do not report agent activity as customer or financial success.
