# CE-2B — Bounded Internal Worker and Never-Ready Health Probe

**Checkpoint:** 2026-11-05  
**Implementation:** `src/company_os/competitive_worker_runtime.py`.  
**Tests:** `tests/test_competitive_worker_runtime.py`.  
**State:** Offline, manually invoked, local-development worker only. **Not a deployed, continuously monitored or independently certified competitive engine**.

## Purpose and engineering evidence

The durable SQLite queue built in CE-2A supports jobs and leases, but until now no concrete runner executed batches and checked queue telemetry. This increment provides a **finite internal worker cycle**, explicitly separate from any external source collection or business release.

`run_internal_cycle(repo_root,worker_id,max_jobs,max_seconds)` can process already-queued evidence dossiers to BLOCKED or HELD using the existing deterministic evaluator, and writes only private, Git-ignored telemetry. It honors local lease generations and uses a short-lived single-leader OS file lock so two manual workers in the same filesystem cannot both act as a leader. The worker is constrained to 1–100 jobs and 1–120 seconds; it does not process automatically after a chat ends and has no autonomous scheduler.

There is **no network access**, API key usage, spending, client contact, commercial decision, report publication or other external side effect. Internal, reversible, zero-spend analyses can run under the root emergency pause in manual mode, consistent with the company policy. Any `scheduled=True` invocation is **categorically blocked**, including when a temporary test project is unpaused, until an approved production-supervision path is separately built and authorized.

The internal worker records only counts of held, blocked and failed jobs, its run timestamp, worker identity and local queue audit head. It never outputs private customer dossier contents. Private telemetry writes use a bounded file, exclusive temporary creation and atomic replacement.

## Health is NOT readiness

`probe_offline_worker(repo_root)` can check whether recent *local internal* telemetry exists and whether its fields remain syntactically consistent. Even with an apparently recent heartbeat it **always returns `ready=false`**, `state=NOT_PRODUCTION_READY` and `publication_authorized=false`.

It explicitly lists absent protected external monitoring, authenticated original source worker, genuine independent critic and certified company-wide release controller. Fake changes asserting `production_ready=true` are rejected, and a missing/stale/symlinked telemetry file is never interpreted as healthy. This cannot sign the company's production health attestation and cannot change the launch hard stop.

## Test scope

- 100 synthetic dossiers (99 valid internal holds and one defective document BLOCKED at intake), with correct queue/job audit counts.
- Bounded 5+8 batch resumption without lost/duplicated jobs, empty queue, deliberately expired work lease, stale worker and source revalidation.
- OS file leader lock prevents another local worker from proceeding; symlinked lock targets are rejected.
- Repository and environment pause behavior: manual internal work permitted, scheduled work blocked.
- Tampered/missing/stale/future health telemetry cannot elevate production readiness; no send, deploy or publish operation exists in the module.

## Unfinished mandatory production controls

1. Real service supervision on a CEO-approved, persistent and protected host, with verified automatic boot, crash/restart recovery, log and secret custody, incident response, and bounded cost.
2. Real durable, single-leader distributed queue strategy under actual host failures, external audit anchoring, workload scaling and source-rights controls. A local flock and SQLite file on GitHub Actions are not production failover evidence.
3. Actual authorized primary-source monitoring and competitive comparisons with verified buyer data, independent original-source truth and current addenda/claim snapshots.
4. Truly independent, authenticated review of original sources and rendered PDFs with complete critic evidence and strict >9/10 acceptance.
5. Real per-side-effect authenticated release controller, exhaustive no-bypass tests and explicit CEO authorization; protect all current and future ventures.

**Company gates remain:** `PAUSE_AUTONOMY` active; `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`. Do not generate production live health signatures, activate scheduled processes, or represent finite CI jobs as continuous monitoring.

**Next executable critical path:** Protected original-source collection and external audit; actual independent critic execution and client-fit verification; zero-cost approved host assessment, then controlled supervision/monitor and release-boundary testing. Full acceptance remains blocked until these are demonstrably operating.
