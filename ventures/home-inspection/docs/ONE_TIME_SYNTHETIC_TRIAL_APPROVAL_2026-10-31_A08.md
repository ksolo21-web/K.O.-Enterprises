# A08 — isolated synthetic specialist diagnostic

Authorization-ID: OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A08
Authorization-Scope: one synthetic-only GitHub-hosted CPU vision trial, no customers, no secrets, no deployment

The current owner's **“continue”** follows A07's documented failure and next task: isolate the single scoped writer request with server diagnostics and an explicit resource budget. This scopes the current instruction to exactly one A08 attempt in `A08_TEST_PLAN.md`. It does not reuse A07's consumed scope or authorize a repeat/full specialist workflow.

Only the pinned synthetic JPEG/prompt/schema from A07 may be replayed, once, with the same Qwen digest and binary. The isolated request has an absolute600second watchdog (also enforced against slow response drips), an outer630second process deadline plus10second kill grace, and a25minute standard public Ubuntu24 job ceiling. Application transport remains capped at180seconds. This diagnostic may take longer solely to measure whether a completed scoped response arrives after180seconds; it never accepts a partial or malformed answer.

Separate critic review and passing regressions precede the exact triggering commit `trial(home-inspection): OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A08`. Contents-read only, pinned actions and verified Ollama v0.40.13 archive, one public writer model, no additional accounts or paid resources. Keep root pause marker, normal paused workflow and main unchanged. No customer evidence, secrets, outreach, deployment, real report or release. Preserve bounded normal server logs, actual inputs/outputs, completion/metrics, exceptions and hashes. Never retain model thinking/context arrays as evidence.

No repeat, automatic retry, second inference call, forced tool choice, Q02 call or full acceptance run is authorized by this record. Retire the trigger after the attempt. A successful isolated proposal establishes only this single model/request's compatibility and measured latency. Milestone2 and field/customer acceptance stay open.
