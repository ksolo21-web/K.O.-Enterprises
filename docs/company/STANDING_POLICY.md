# Standing Policy Standard

## Purpose

A standing policy lets the company repeat one well-understood external operation without asking the CEO to approve every instance. It is narrow, deterministic, revocable, expiring, and subordinate to its parent authority.

## Required scope

Name every applicable field:

- policy ID, revision, parent CEO decision, and canonical digest;
- exact action code and prohibited variants;
- allowed executor principal/position and required authentication level;
- account, repository/product, environment, destination, and data class;
- per-action and period cash/resource ceilings;
- rate, maximum uses, valid-from, expiry, and renewal owner;
- task and opportunity/product stage requirements;
- required legal, security/privacy, finance-control, QA, and audit findings;
- input schema, output schema, idempotency, reconciliation, and receipt requirements;
- monitoring, automatic stop, rollback, incident route, and subsystem pause;
- permitted claim/copy/artifact digest where publication is involved.

Wildcards are not permitted for money, identity, contracts, sensitive data, production credentials, public claims, or destructive operations.

## Lifecycle

`draft -> reviewed -> approved -> active -> suspended | expired | exhausted | revoked`

The proposer cannot approve the policy. Activation requires the parent authentic decision and all named reviews. A change to actor, action, account, destination, environment, data class, limit, rate, use count, or expiry is a new revision and cannot exceed the parent decision.

## Execution

Every use receives a fresh task, budget reservation, policy match, pause check, idempotency key, and attempted-action audit record. The executor consumes one authorized use and stores a sanitized receipt. An approval row or possession of a credential is insufficient.

## Suspension and renewal

Any applicable control function may suspend a policy on incident, stale evidence, scope mismatch, unexplained variance, control failure, or material external change. Renewal requires current evidence and reviews; it is never automatic. Expiry means stop.
