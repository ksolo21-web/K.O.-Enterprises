# Autonomy Activation Runbook

## Rule

Do not remove `PAUSE_AUTONOMY` merely because policies or tests exist. Activate only the smallest proven stage through a deliberate CEO-authorized change.

## Readiness evidence

Before requesting scheduled internal operation, demonstrate:

- authenticated principals and active assignments;
- executable command-chain and delegation checks;
- durable state, concurrency lock, leases, and recovery;
- hierarchical resource budgets and atomic reservations;
- append-only attempted/denied/completed action audit;
- incident stops and restore testing;
- a shadow cycle that produces truthful output without external effects;
- independent security, privacy, finance-control, QA, and audit findings with no unresolved critical block.

Before requesting a connector, additionally demonstrate exact account/environment/destination/data scope, least-privilege credentials, rate/cost/use limits, idempotency, reconciliation, monitoring, rollback, and a connector-specific kill switch.

## Approval packet

Request one activation stage, not general autonomy. State the exact workflow, actor, schedule, repository, account/environment, actions, data, limits, monitoring, expiry, expected outcome, and stop conditions. Include the policy and code revision digests reviewed.

## Activation

1. Record the authentic decision and its digest.
2. Verify all conditions remain current.
3. Activate in the lowest-risk environment.
4. Run one canary cycle.
5. Reconcile state, audit, cost, and unexpected effects.
6. Continue only if canary acceptance passes.

## Rollback

Restore the global pause on unexplained behavior, unauthorized effects, uncertain execution state, budget mismatch, audit failure, stale identity, control failure, or incident. Preserve evidence and do not auto-resume.
