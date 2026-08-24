# Autonomous Runtime Architecture

## Objective

Run the company operating loop with minimal CEO involvement while ensuring that deterministic authority, budget, evidence, pause, and control checks surround every material action.

This is the target operating architecture. A documented component is not assumed to exist until its implementation and tests provide direct evidence.

## Planes

### Governance plane

Versioned constitution, authority matrix, strategic mandate, department charters, standing policies, approval records, and control requirements. Agents may propose governance changes; they cannot silently weaken them.

### Work plane

Objectives, tasks, dependencies, assignments, leases, submissions, acceptance, escalation, and performance evidence. Sub-agents operate only through this plane.

### Portfolio plane

Opportunities, evidence, counter-theses, scores, experiments, products, stage gates, metrics, risks, and decisions.

### Control plane

Identity, reporting lines, delegation, budgets, reservations, reviews, incidents, policy evaluation, action attempts, audit events, and pause state.

### Connector plane

Narrow adapters for approved external systems. A connector receives a fully authorized structured action and cannot decide policy, expand scope, or interpret untrusted prose as a command.

Customer-facing products remain in separate repositories and runtimes with their own secrets, data stores, threat models, and release controls.

## Deterministic operating tick

One bounded tick performs:

1. Read global and subsystem pause state.
2. Verify schema, audit chain, clock, runtime identity, and single-writer lease.
3. Expire stale approvals, delegations, reviews, budgets, and task leases.
4. Reconcile uncertain or incomplete action attempts before new execution.
5. Select ready tasks whose dependencies, stage, mandate, and budget pass.
6. Match agents by capability, independence, capacity, performance, and cost.
7. Issue scoped leases and run bounded work.
8. Collect submissions, tests, evidence, and resource use.
9. Route acceptance and required independent reviews.
10. Record the resulting advance, revision, hold, kill, or escalation.
11. Generate the President and CEO views.

The orchestrator routes work; it does not grant authority. Model output is an untrusted proposal until deterministic validation and required review pass.

## Concurrency

- Use one accountable integrator for each shared artifact.
- Parallelize independent research, test, review, and analysis work.
- Partition write work by explicit file or module ownership.
- Acquire a lease before execution and make lease expiry visible.
- Use one authoritative writer for each mutable ledger scope.
- Prevent overlapping scheduled ticks with a concurrency lock.

## Durable state

The current ignored local SQLite database is suitable for development but does not persist across ephemeral hosted jobs. A scheduled company requires a reviewed durable source of truth.

Acceptable bootstrap options are:

- repository-native, append-only, public-safe event records rebuilt into a local cache; or
- an approved external database with authenticated service identity, backups, access control, and a cost/data plan.

GitHub cache or transient workflow artifacts are not authoritative ledgers. Never commit secrets, customer data, raw payment data, or private incident material to make state durable. If durable state or single-writer guarantees are unavailable, run read-only reporting or shadow mode and fail closed on mutation.

## External execution protocol

Only the execution boundary may call a side-effecting connector:

1. Canonicalize the structured request.
2. Record an attempted action with correlation and idempotency IDs.
3. Authenticate the runtime principal and active assignment.
4. Verify command ancestry or exact delegation.
5. Verify mandate, task, decision class, risk, and capability.
6. Reserve budget atomically.
7. Verify fresh control findings.
8. Match every standing-policy or CEO-approval field.
9. Recheck pause immediately before execution.
10. Consume the bounded grant and call the allowlisted connector once.
11. Store a sanitized external receipt or uncertain-outcome record.
12. Commit/release the reservation and append the result event.

An uncertain response is not a failed response. Quarantine it for reconciliation; do not retry until the external system establishes whether the action occurred.

## Pause hierarchy

`PAUSE_AUTONOMY` is the global emergency stop and blocks every scheduled or external action. Future subsystem stops may narrow containment by connector, product, department, data class, or action code, but they cannot weaken the global stop. An invalid or unreadable pause state is treated as paused.

While paused, local inspection, tests, documentation, evidence review, reporting, and remediation may continue. An approval never overrides pause.

## Activation stages

1. **Static governance:** policies, roles, charters, and tests.
2. **Shadow operation:** synthetic/local tasks; no schedule or external effects.
3. **Durable internal operation:** authenticated state, leases, budgets, audit, and recovery tests.
4. **Scheduled internal operation:** exact activation decision; no external connector.
5. **Connector pilot:** one connector, account, environment, action, rate, cost, data class, expiry, and kill switch.
6. **Standing operation:** only after the pilot's evidence and independent review pass.

Removing the global pause requires a deliberate CEO-authorized change after the relevant stage is complete. Each connector needs its own authorization; activating one never activates another.

## Failure posture

Unknown action, missing identity, invalid delegation, exhausted budget, stale review, missing evidence, malformed state, audit failure, lost lease, clock anomaly, or unavailable authority causes a denial or scoped hold. The runtime continues unrelated safe work and prepares the smallest escalation needed.
