# System Boundaries

## Control plane

This repository holds shared policy, portfolio records, approval state, evidence metadata, scoring logic, audit events, and CEO reports. It may recommend an action but cannot create its own permission.

## Product plane

Each selected customer-facing product should use a separate repository, runtime, secrets, data store, deployment policy, and threat model. Product automation consumes only the minimum approved control-plane decisions and returns audit/metric records through a reviewed interface.

## Trust flow

```text
untrusted sources -> normalized evidence -> human/reviewer checks -> scored proposal
                                                               |
                                                               v
CEO approval record -> deterministic policy gate -> bounded connector -> external system
                                 |
                                 v
                         append-only audit event
```

No untrusted text may cross directly into approval, shell execution, SQL structure, credentials, or an external side effect. Model output remains an untrusted proposal until deterministic checks and required human review pass.

## Phase 0 implementation boundary

SQLite is local durable state. The CLI can create and inspect internal records and reports. There are no production connectors, live accounts, payment rails, outbound messages, or autonomous deployments. `PAUSE_AUTONOMY` is expected to remain present.

SQLite actor/decision labels and the audit hash chain are integrity aids, not cryptographic identity or tamper-proof security. A person with local repository/database access can potentially change code or state and recompute or bypass controls. Any future external executor therefore needs authenticated human approval and access controls outside the proposer-controlled database.

GitHub is a collaboration and CI surface, not the entire company runtime. GitHub-hosted Actions availability is subject to GitHub terms and limits; model/API/hosting usage must be budgeted separately.
