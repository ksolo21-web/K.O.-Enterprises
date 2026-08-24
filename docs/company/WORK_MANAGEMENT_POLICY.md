# Work Management Policy

## Work orders

No agent performs material work from a vague standing instruction. A work order must identify an objective, issuer, accountable department, assignee or selection rule, scope, inputs, acceptance criteria, dependencies, decision class, risk, resource ceiling, deadline or TTL, idempotency requirement, reviewer, and escalation target.

## Lifecycle

```text
proposed -> authorized -> ready -> claimed -> in_progress -> submitted
          -> review -> accepted
                    -> revision_requested -> ready
                    -> rejected | cancelled | held
```

An external action has a separate authorize-and-execute lifecycle and cannot be implied by task acceptance. State transitions are append-only events. Skipped states, duplicate claims, stale leases, and missing reviewers fail closed.

## Assignment

The dispatcher or manager selects an agent using required capability, independence, current capacity, evidence calibration, accepted-work history, defect/rework history, and estimated resource cost. It must not assign a reviewer to its own work or optimize for raw activity.

Parallelize independent read-heavy work freely within capacity. Partition concurrent write work by explicit file ownership. One manager owns integration and resolves conflicts.

## Acceptance

Submission is not completion. Acceptance requires the named evidence, tests, artifacts, truthful limitations, and any control reviews. The accepting role records whether criteria passed, failed, or need revision. A manager may not silently weaken acceptance criteria after seeing results.

## Retry and idempotency

Internal deterministic tasks may retry within a stated limit. External actions require a unique idempotency key and a just-in-time authority recheck. If an external result is uncertain, quarantine the key and reconcile; never retry blindly.

## Closure

Close tasks with outcome, evidence, resource use, reusable assets, remaining risk, and follow-up. Release leases, reservations, and temporary assignments. Failed and killed work remains in the record because negative evidence improves the portfolio.
