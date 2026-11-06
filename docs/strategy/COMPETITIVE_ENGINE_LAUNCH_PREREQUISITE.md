# Mandatory Competitive Engine — Company Launch Precondition

**Architecture decision:** KO-CE-LAUNCH-INVARIANT-v1.0  
**Established:** 2026-11-05  
**Status:** ENFORCEMENT PREFLIGHT IN DEVELOPMENT; LIVE ENGINE **NOT** DEPLOYED OR VERIFIED  
**Scope:** ALL K.O. Enterprises ventures, present and future, regardless of business line, proposed platform, pricing, niche, or agent team  
**Related:** [Competitive Strategy](COMPETITIVE_ADVANTAGE_STANDARD.md), [Validation Playbook](COMPETITIVE_VALIDATION_PLAYBOOK.md), [Active Build Roadmap](../ventures/market-intelligence/BUILD_PLAN.md), [Company Approval Policy](../../CEO_APPROVAL_POLICY.md).

## Irrevocable design intent, subject to CEO-governed amendments

**No K.O. business launches, publishes a commercial claim, or deploys a public commercial service unless the shared competitive intelligence engine is already operating in an approved production environment, has current independently verified operational evidence, and separately passes the company approval, privacy, legal and document-release controls.**

The engine itself is a **company-level prerequisite service**, not a standalone business branch and not a substitute for commercial validation. Every future K.O. venture inherits this policy automatically. The root emergency stop always takes precedence. The explicit engine-bootstrap route can provision the prerequisite after a separate CEO-approved activation packet; it is **not** allowed to bootstrap while `PAUSE_AUTONOMY` remains active.

## What is already implemented, and what is not

### Implemented preflight on this feature branch

- `src/company_os/competitive_launch_guard.py` evaluates a **signed, short-lived readiness attestation** stored in trusted runtime state, not public GitHub.
- `src/company_os/policy.py` invokes this fail-closed gate for business launches, go-live, revenue start, public deployment/publication and launch-like aliases. It checks even if the caller omitted `external=True`.
- Readiness requires **two different protected signing keys** (live monitor and critic), a recent heartbeat, genuine-production designation, current source-check metadata, current critic review, 8 operational checks, 12 quality checks, score strictly **greater than 9.0**, zero unresolved critical findings, and positive original-source/comparison counts.
- Approval is **not sufficient** without engine readiness. Engine readiness is **not sufficient** without exact valid approval. `PAUSE_AUTONOMY` blocks both. Missing attestation, keys, critic, or source evidence blocks launch.
- **Additional uncompromising development hold:** `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False` is a hard-coded fail-closed constant. Even an otherwise perfectly signed synthetic `live_healthy` attestation plus an approval **cannot** unlock a real launch while the release controller has not been independently qualified. Only a later, explicitly owner-approved and genuinely reviewed activation change after all real acceptance tests may change that state; demonstration tests mock the flag without changing production code.
- A distinct `deploy_competitive_engine` action has CEO-only approval and honors the emergency pause but does not require the not-yet-deployed engine, avoiding a bootstrap deadlock.
- Offline unit tests prove the preflight logic. **Synthetic HMAC fixtures never constitute authentic production monitoring or independently verified business evidence.**

### Not yet implemented / live launch blockers

- Real authorized original-source retrieval, lawful collection controls, source audit, contradiction tracking, and durable provenance.
- An actual competitive evaluation job orchestrator using current company OS work queues and persistent, secured job state.
- A protected always-running deployment with automatic restart, correct secrets, monitoring, rate limits and durable storage.
- An **actually separate, authenticated** human or reviewer worker inspecting original sources, buyer evidence, citations, competitor comparisons and rendered deliverables. A signed string `reviewer_id` is not independent review.
- A genuine external monitor that checks service reachability, worker processing, last real completed sourced comparison, queue backlog, exception rates and review currency. A signed status JSON alone does not prove a live service.
- A secure, atomic private release controller validating actual approved client/venture identifiers, environment, reviewer certificate, recipient, costs, signed permit, version and audit record immediately before execution.
- Branch/ruleset/deployment protection preventing *other* repository workflows or future connectors from bypassing the company policy module; these admin-level controls have not been provisioned. Do not claim company-wide GitHub enforcement is airtight while alternative unmanaged release channels exist.

## Production target architecture

```text
Approved secure host (automatic service startup/restart)
  |
  +-- Read-only lawful source retrieval adapters -> provenance and expiry ledger
  |        -> competitor strengths / verified buyer pain / alternatives
  |
  +-- Durable competitive jobs, leases, retries and bounded cost/rate budgets
  |        -> evidence-graded battlecards -> independent comparisons
  |
  +-- Independent reviewer execution and separate trust boundary
  |        -> signed criticism, counterevidence, strict 12-gate report
  |
  +-- External monitor probes actual health/queue/records/reviewer
  |        -> short-lived, separately signed readiness evidence
  |
  +-- Authenticated company release controller
           -> recheck LIVE gate + PAUSE + scoped CEO approval
           -> client, privacy, legal, digest, evidence and recipient
           -> allow a *specific* authorized release or BLOCK + audit
```

**GitHub Actions is finite compute and CI, NOT an always-on host, encrypted client database, or guaranteed autonomous AI worker.** Code and sanitized fixture tests live in GitHub. Real customer data and operational secrets must stay on approved protected infrastructure.

### Automatic startup and recovery requirement

When the CEO approves a provider, account, architecture, permissions, rate/cash ceiling and expiry, an authorized host service supervisor should:

1. Start the competitive engine automatically at boot and restart it after process failure with a bounded retry policy.
2. Acquire an authenticated single-leader lease and reopen persistent queued work without lost jobs or double processing.
3. Start in `NOT_READY`, load only protected credentials, verify connectivity and schema, then run critical self-tests.
4. Admit only lawful authorized read-only source work; track cost and source limits. No publication/outreach from a research job.
5. Request separately executed source/professional critic review of actual work, with recorded evidence and correct actor credentials.
6. Permit the monitor to sign a short-lived `live_healthy` attestation **only when it actually observed** all checks. Review service signs independently after genuine review.
7. If a required dependency fails, remove/revoke readiness, do not renew signatures, block *new* commercial launches and report an incident. Never pretend the system is live merely because a process started.
8. Preserve approved continuity obligations and safe recovery routes for **existing customers**; a monitoring outage must not silently violate contracts or wipe customer data. New launches, new unsupported claims and new production changes remain blocked pending recovery.

**Expected monitor bounds in code:** live heartbeat no older than 5 minutes; attestation validity at most 10 minutes; original source verification no older than 24 hours; independent reviewer record no older than 1 hour. These are strict maximum *preflight* tolerances, not proof that every live source or client case is current; high-stakes deadline data may require significantly shorter refresh limits.

### Secret management and reviewer independence

- Environment names: `KO_COMPETITIVE_ENGINE_HEALTH_KEY`, `KO_COMPETITIVE_CRITIC_HEALTH_KEY`, and optional `KO_COMPETITIVE_READINESS_PATH`.
- Both HMAC-SHA256 keys must be high-entropy values of at least 32 bytes, different and held by **separately protected identities**. No default or test keys in production, GitHub Actions logs, or public repository.
- Reviewer credentials must not be accessible to the engine process. Provision separately via approved secure host secret management. Distinct-looking names or keys on a single compromised host do **not** prove genuine independent review.
- Protect the readiness record against unauthorized reading/modification; record full source metadata and monitor evidence in a private append-only audit, including key rotation/revocation and incident traces.
- The signed payload verifies integrity/authorship **conditional on key custody**, not that URLs were really inspected, a critic is qualified, or customers will pay. A production launch requires real observation and independent inspection, not just a mathematically valid test fixture.

### Business launch integration rules

Every future business module must invoke the canonical company policy/release controller for these action families:
`launch_*`, `go_live_*`, `start_revenue_*`, `deploy_*`, `publish_*`, plus explicit `activate_business`, `activate_product`, `activate_venture`, `open_business` and `start_business`. Only the single engine-bootstrap action is excepted from engine dependency; **it still requires CEO permission and an inactive emergency pause**.

The preflight on this branch is **necessary but not sufficient**. A future execution host must enforce it at the actual irreversible side-effect boundary. If an unintegrated connector can launch without consulting that host, the system is **NOT production-ready**. GitHub branch protection, deployment environment reviewers and required checks must also be configured at the correct accounts once authorized and available.

## Required acceptance demonstrations before first business launch

1. **True automated service lifecycle:** reboot, crash, restart, leader-election/failover and durable queue recovery captured from a protected environment.
2. **Source integrity:** original issuer records and addenda inspected; old, edited, derivative, conflicting, prohibited and unreachable sources rejected or properly qualified. Evidence snapshots tied to real retrieval timestamps.
3. **Competitor intelligence quality:** like-for-like battlecard, real incumbent strengths, bounded verified weaknesses, disconfirming findings, client demand and transparent unit-economics evidence.
4. **Separate critic:** genuine authenticated reviewer inspection, independent signed source/visual review evidence, all 12 mandatory items, score >9; forged identity, copied review and old digest fail.
5. **Live observability:** protected external probe demonstrates uptime and completed real work; health outage, stale source, critical issue, wrong key, clock skew, compromised review and key rotation all invalidate readiness.
6. **Launch denial:** every supported business launch path BLOCKS under pause, missing health, expired health, unapproved action, unqualified client, wrong recipient, tampered report and absent review.
7. **No bypass:** simulate all GitHub workflows, connectors, CLIs and release channels; demonstrate no production launch can bypass the release controller. Check changes and reset all testing fixtures.
8. **Financial/privacy/legal:** $0 external spend unless authorized, protected credentials and private data, lawful research access, proper liability-conscious client language, reviewed service terms.
9. **Critic and owner approval:** independent launch review strictly above 9.0/10 with no failed mandatory criteria; CEO approves *the exact* environment, costs, data, accounts, rollout/rollback and scope. Authorization is not inferred from a chat message expressing a design preference.
10. **Post-launch monitoring:** failure triggers alert/review and blocks new launches, with documented safe service continuity/recovery and correction logs.

No launch date is assigned until these *real* acceptance demonstrations are performed. Internal test scores alone cannot grant business activation.

**CE-1A engineering increment (not full CE-1):** [Offline original-source capture and provenance ledger](CE1_SOURCE_PROVENANCE.md). It does not fetch URLs or authenticate issuer content, and every factual claim stays held for independent review. Keep the production hard stop and all CE-1 through CE-5 acceptance requirements.

**CE-1F/CE-2A implementation checkpoint:** [Offline competitive workbench](CE1F_CE2A_COMPETITIVE_WORKBENCH.md) builds factual-evidence/counterevidence validation, balanced comparator checks, buyer signal and economic plausibility checks, and a durable local internal queue. Neither component independently verifies real market facts, runs continuously nor allows publication or release. CE-1 through CE-5 completion still requires real independent operational evidence.

## Development milestones, dependencies and checkpoint

| Stage | Work | Required proof | State |
| --- | --- | --- | --- |
| CE-0 | Adopt mandatory precondition as company policy and integrate signed readiness guard | GitHub-reviewed code and adversarial tests, pause retained | **Under implementation** |
| CE-1 | Deep source & competitor evidence engine | Real lawful sources, independent verification and change monitoring | **Blocked / not complete** |
| CE-2 | Continuous protected hosting and durable queues | Real auto-restart/failover/probe tests; authorized infrastructure | **Not complete** |
| CE-3 | Authenticated independent critic | Genuine separate review, 12/12 evidence, strict score, negative tests | **Not complete** |
| CE-4 | Global release controller with no bypass paths | End-to-end attempted launch coverage, genuine permit and audit | **Not complete** |
| CE-5 | First controlled company-wide activation | CEO-approved operating envelope, recovery demonstration and external audit | **Not complete** |

**Dependency priority:** CE-0 immediately, while existing Market Intelligence M1 source-verification work remains the shared technical critical path for CE-1. CE-2 and CE-3 can develop in parallel once boundaries are defined. CE-4 requires CE-1 through CE-3. CE-5 requires all mandatory checks plus authentic CEO authority.

**Checkpoint 2026-11-05:** This architecture decision preserves the two active K.O. business lines. Vendor Connect and Card Vault remain parked. No genuine engine deployment, client contact, source acquisition or launch authorization is claimed. The correct next implementation after the signed readiness gate is the **lawful primary-source acquisition and provenance adapter (Market Intelligence M1 / Competitive Engine CE-1)**, then a protected, continuously supervised monitor/critic integration.

**If resuming in another chat:** Read this file on `main`, source and tests, the active roadmap, Issue #32, the current CI results, and `PAUSE_AUTONOMY`. Preserve previous working code. Do not claim live status from a signed JSON test fixture.
