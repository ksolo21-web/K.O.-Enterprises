# M2 A09 preparation — three-role synthetic reconciliation

2026-10-31. **Prepared and controlled-tested; no live A09 run authorized or executed by this change.** No temporary workflow/trigger, download, model promotion, pause removal, paid service or customer upload was added.

## Next executable dependency

Local read-only inventory failed: `Local Ollama connection refused; verify the local runtime is listening`. No Ollama binary was found on PATH. The two successful A05 models ran on an earlier ephemeral GitHub runner; that does not make them installed here. An evaluated third Q03 model has not been selected or installed. The root pause remains in place. A GitHub run needs its own exact, bounded authorization/workflow envelope; old A05–A08 approvals are not reusable.

Choose and evaluate the three roles against the A08 counterexamples before promoting a model. Current Qwen2.5-VL 3B output has not earned the lead role. Model selection, availability, weight digests, CPU/memory capacity and practical latency must be established; a larger parameter count is not acceptance evidence.

## New executable harness

`scripts/run_m2_reconciliation_trial.py` extends the existing synthetic writer/Q02 trial with Q03 and a held Option 2 report. It accepts no customer-media input. Models must already be installed. It downloads nothing and dispatches no remote workflow.

After the missing prerequisites and appropriate execution authorization are satisfied:

```bash
python -m scripts.run_m2_reconciliation_trial \
  --writer-model EVALUATED_WRITER \
  --review-model EVALUATED_Q02 \
  --reasoning-model EVALUATED_Q03 \
  --out-dir new_synthetic_replay --allow-local-inference
```

The names above are placeholders, not an approved model selection or a currently executable authorization. The CLI requires an OS with SIGALRM and enforces a 1,800-second absolute deadline. Existing loopback transport allows 180 seconds per generation. Maximum six writer calls, 48 combined claim/task-photo Q02 assessments and one Q03 call; zero automatic retries. A deadline or disconnected client does **not** prove Ollama server-side generation was cancelled. After any timeout, inspect/stop the trial runtime before another attempt; do not assume it is idle.

Preflight requires three distinct names and recorded, distinct weight digests; writer and Q02 must advertise vision, and Q03 completion capability. Digests establish different recorded weights, not authenticated independent hosts. The actual role performance still needs evaluation.

## Acceptance checklist

- [ ] Actual evaluated writer, Q02 and Q03 models installed and recorded with digests/settings/hardware.
- [ ] Exact runtime/location/source revision and bounded execution authorization established.
- [x] Generate synthetic-only photo and varying native video fixtures.
- [x] Give scoped hazard/specialty instructions to specialist work.
- [x] Prove requested zoom and materially distinct selected video still through engine and Q02 lineage, rather than aggregate call counts.
- [x] Save Q02 claim/task-photo reviews and explicit deterministic missing-view holds.
- [x] Save Q03 request, actual returned structured reply, safe transport fields, durations and validated full ledger dispositions.
- [x] Preserve technical, missing-evidence and physical-check holds even for `distinct` decisions.
- [x] Generate an explicitly unreleased Option 2 PDF and source/evidence hash manifest.
- [ ] Execute these steps with actual models and independently assess observation/tool quality.
- [ ] Qualified-inspector field benchmark, authenticated physical completion and human release workflow.

Checked implementation items above have **controlled-provider synthetic evidence only**. They are not checked live-inference requirements.

`SYNTHETIC_RECONCILIATION_COMPLETE_UNVERIFIED` requires both source-matched tool lineages, proposed claims and successful Q03/report integration. If the models return no claims or choose no tools, a completed Q03/report produces `SYNTHETIC_RECONCILIATION_WITH_GAPS`, not synthetic acceptance. Invalid writer/reviewer/Q03 records block; raw evidence survives. Scripted providers are explicitly `controlled_test`, with live completion flags false. Even an actual successful synthetic run always leaves `full_milestone_2_approved=false`, `field_accuracy_verified=false`, and `customer_release_allowed=false`.

## Evidence files

Existing writer/Q02 invocation audit, original image hashes, native crops/stills and tool-review lineage are preserved. Added files: `q03_request.json`, `q03_response.json`, `adjudication.json`, `adjudicated_project.json`, `held_report.pdf`, `reconciliation_status.json` and `reconciliation_manifest.json`. Transport audit excludes thinking and context arrays. Model output is always untrusted data. Capture artifacts after success or failure and retire any future one-time remote trigger after its authorized attempt.
