# CE-4A — Company-wide Release Proposal Preflight (Deny-Only)

**Checkpoint:** 2026-11-05  
**State:** Internal/offline preflight — **every outcome BLOCK; no action executor, no release authority and no production certification.**  
**Modules:** `src/company_os/competitive_release_preflight.py`, `src/company_os/competitive_work_queue.py` (new verified snapshot).  
**Adversarial tests:** `tests/test_competitive_release_preflight.py`.  
**Existing emergency controls:** `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` stay active.

## Purpose

The company-wide requirement is that no K.O. Enterprises business may go live without its shared competitive engine already operating safely, independently reviewed and authorized. A signed reviewer string or generic company approval cannot safely authorize a customer-specific report, recipient, venture, budget or deployment. This module integrates the previous engineering evidence into a single **fail-closed, non-executing release-proposal inspection**.

### Mandatory exact bindings

A release proposal names one request ID, action, venture, exact dossier ID+SHA-256, exact artifact PDF SHA-256, critic review ID, symbolic recipient ID, client scope ID, dated claimed privacy/legal/consent review references, UTC proposal time and bounded cost. The preflight:

1. Requires an action classified as launch/publication/deployment by the canonical company-wide competitive-engine gate. Unknown or potentially unguarded release verbs are rejected.
2. Re-reads the **completed durable queued dossier** and its output digest, verifies the original payload and held evaluator report hashes, and confirms exactly the same dossier ID and SHA-256 as the release proposal. Unfinished/replayed/stale/altered jobs cannot proceed.
3. Rechecks the original PDF bytes, root-governed critic policy and signed review payload; the signed review must bind to the exact current dossier and artifact, all source hashes and every actual parsed PDF page.
4. Rechecks the critic ledger's latest key/review revocations. A signed old review loses trust when revoked; unsigned/self-signed packets do not satisfy the gate.
5. Requires the **CEO approval metadata** to match the precise action, venture, cost, recipient, client scope and both digests. A broadly approved action does not cover a different client or edited report. **These are metadata checks, not real CEO identity authentication.**
6. Calls the canonical company policy for root pause, competitive-engine live readiness and exact action approval; additionally reports the missing independent source authentication, production-quality independent critic, actual privacy/legal/consent verification, external immutable audit and protected no-bypass controller.
7. Returns **BLOCK** with categorized reason codes, `release_authorized=false` and `publication_authorized=false` even if every synthetic document and signed assertion agrees.

`ReleaseAttemptLedger` can persist only refused attempts, using an append-only local hash chain and **hash-only** request/issue references. Client identity, recipient details and report bytes are not logged. This ledger is not an externally immutable production audit sink.

## Acceptance evidence

Tests exercise otherwise coherent synthetic end-to-end paperwork through the source evaluator, durable held queue, signer root policy and original report PDF, critic audit, CEO-scoped release proposal and company launch gate. The expected result is **BLOCK** with the emergency pause and missing production-source/reviewer/controller evidence. Deliberate mutations to queue payload/output, report bytes, source digest, reviewer status, recipient, client scope, cost and action all fail. Additional tests challenge stale requests, refusal logging, SQL tampering and all supported launch aliases.

**The module does NOT have a send, publish, deploy, spend, schedule, monitor or launch function.** It is not proof that every future connector calls this check. It is a necessary component of a future release controller, not the actual production controller.

## Unfinished critical requirements

- **CE-1:** Real original-lawful-source acquisition, complete issuer addenda/portal checks and separate independent original-truth verification.
- **CE-2:** Approved protected always-on host, authenticated worker/monitor lifecycle, failover, real recovery and external audit store. GitHub CI is not an always-on engine.
- **CE-3:** A genuinely separate qualified reviewer must inspect the actual originals and rendered pages, catch unregistered assertions, test all 12 checks and score >9 with externally verifiable review evidence. A signing key alone is insufficient.
- **CE-4:** Install a true, atomic, private release controller at every supported side-effect path with actual CEO identity-bound approval, verified customer consent, recipient, privacy/legal and protected secrets; demonstrate no bypass across every connector/CLI/workflow.
- **CE-5:** Independently test the complete protected environment, incident response, downtime/rollback, cost controls, source freshness, commercial viability and explicit CEO authorization before activating the engine or any business. Keep the root pause and production hard lock until actual evidence supports a separately reviewed change.

**Next executable critical path:** integrate protected original-source capture evidence into the critic's actual source/page inspection, provision an approved always-on service with separate identities, verify exhaustive side-effect channel coverage, and run a supervised end-to-end live-source pilot under explicit scoped CEO authority.

No fake readiness or synthetic signature may unlock the production hard stop. This checkpoint preserves the original company requirements.
