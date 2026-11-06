# CE-1F + CE-2A — Competitive Evidence Evaluator and Durable Internal Queue

**Checkpoint:** 2026-11-05  
**Status:** Built for offline/internal testing only. **Not a deployed autonomous competitive engine or customer product.**  
**Owner:** K.O. Enterprises  
**Code:** `src/company_os/competitive_evidence_engine.py` and `src/company_os/competitive_work_queue.py`  
**Tests:** `tests/test_competitive_engine_pipeline.py`

## Problem solved

Earlier CE-1 increments focused on issuer PDFs, signed receipts, cross-UID staging, and addenda history. The actual company competitive engine also needs to **compare incumbents accurately, challenge weaknesses, test buyer value, preserve economic realism, and process repeatable work without lost/duplicated jobs**. This increment adds those internal capabilities.

### The evidence evaluator

`assess_competitive_dossier(dossier)` requires a bounded JSON input with: named venture, buyer segment/problem/geography, author and date; original or secondary sources with source origin, lawful access basis, observation date and digest; attributed claims with materiality, explicit counterevidence and limitations; at least three concrete same-segment/same-geography alternative offers with evidenced strengths; and 1–3 proposed buyer-valued advantages with comparator, counterexamples, switching friction, estimated delivery cost and potential price, and reported buying signals.

It rejects unsupported document schemas, off-registry HTTPS hosts, stale/future evidence, unsupported original-authentication claims, false grade upgrades used to assert competitor weaknesses, duplicated origin pretending to be independent corroboration, missing counterevidence for competitor weaknesses, unresolved conflicting observed values, material claims without original/firsthand sources, unregistered competitor claims, materially noncomparable competitor profiles and negative contribution-margin hypotheses.

**Crucially, reported source grades, issuer original records and paid pilot states are operator metadata, NOT independently certified facts.** A complete internal dossier always returns `HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW` with `publication_authorized=false`, `original_sources_independently_authenticated=false`, `paid_demand_independently_verified=false`, and `independent_critic_approved=false`. A defective dossier returns `BLOCK`; no input can produce a release decision.

Source evidence scores cannot be elevated merely by duplicated derivatives of the same original publisher. A hash proves only that the supplied local bytes have not changed, not that the named vendor, issuer or buyer actually supplied them. The separate critic must still inspect real original sources and unregistered claims.

### Durable internal queue

`CompetitiveWorkQueue` holds *private* local JSON workloads in a restricted, Git-ignored SQLite database at `state/competitive_engine/work_queue/work.sqlite3`. It supports:

- **Immutable content digest and job identity**; repeated matching job submissions are idempotent, while reuse of the same ID with altered contents is blocked.
- **Single-worker transaction leases** with a 10–900-second TTL, monotonic generation numbers, and recovery after a crash/expiry without accepting stale-worker results.
- **Bounded retries**, explicit failure reason codes, delay windows, three-attempt cap and a terminal dead-letter state.
- **An append-only hash-linked local audit** with a read-only audit status and no business publication actions. As with previous local ledgers, this is NOT externally tamper-proof.
- **Only held/blocked terminal states.** There is no `APPROVED`, `PUBLISHED` or `LAUNCH` state.
- **Offline private execution under the emergency pause**, because it neither downloads, contacts people, schedules, pays, deploys, publishes, nor starts revenue. All external side effects remain forbidden.

### Batch dry run

The new test suite includes a deterministic **100-dossier synthetic workload**: 99 internally coherent fictional dossiers must be accepted and processed into **HELD** review state; one intentionally malformed pack must be **BLOCKED at intake**. It verifies all 99 jobs are accounted for, with exact count of 297 queue audit events (submit, lease, held), no job leakage, and no publication.

Additional adversarial tests cover stale worker after crash/re-lease, conflicting worker identities, lease expiry, duplicate jobs, malicious source URLs, contradictions, unsupported weaknesses, stale material evidence, forged paid-pilot status, changed SQLite payload, audit corruption and symlinked private DB paths.

### Operating limitations

- No real competitor data has been independently authenticated; test fixture sources are synthetic and not valid paid-buyer evidence.
- A SQLite queue running in GitHub Actions does not demonstrate an approved persistent, continuously running, supervised production service or durable storage under failure.
- No genuine independent reviewer agent/human has inspected original sources or rendered PDF pages. The 12-item critic and score >9.0 remain mandatory.
- No authenticated release controller exists at each side-effect boundary; a future connector can still bypass this code until wired to a protected host.
- Protected customer information, original copyrighted documents and keys must never be committed in public GitHub or printed in logs.
- `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` remain unchanged. **CE-1/CE-2 and company launches are not accepted.**

## Next critical path

1. **CE-1D/CE-3:** Separate authenticated reviewer packet bound to exact evidence/output digests and the twelve mandatory checks, with deterministic adversarial negative tests and actual independently inspected original-source/PDF evidence before real signoff.
2. **CE-2B:** Test continuous worker supervision, leader leases, shutdown/recovery, source budgets and actual protected infrastructure, without assuming GitHub Actions is an always-on host.
3. **CE-1C3f:** Authenticated lawful issuer transport receipts with genuinely separate source checks, dynamic portal/addenda enumeration and externally anchored audit.
4. **CE-4/CE-5:** Wire every real K.O. release path into protected CEO-scoped release controller; demonstrate no bypass and obtain explicit owner approval before external production activation.

**Resume checkpoint:** Review this file, latest main/CI, root launch locks, Issues #32/#38, source-verification and competitor playbook. Do not claim the engine is live or that any buyer data is real.
