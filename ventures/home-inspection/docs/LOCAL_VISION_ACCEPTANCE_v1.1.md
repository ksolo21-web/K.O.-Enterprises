# Local vision model acceptance gate — v1.1

**Scope:** K.O. Enterprises / `home-inspection-development`. A reproducible **synthetic technical test**, not a licensed property inspection. This feature requires a machine with an authorized local Ollama service and both model weights available. Source control alone does not activate them.

## One operator action, no new account

Install Ollama, Python 3.12+, FFmpeg, and the three Python requirements from `requirements.txt` on a computer with enough local memory/disk. Keep port 11434 bound to `127.0.0.1`. From `ventures/home-inspection/`, run the existing `scripts/setup_vision_models.ps1` on Windows or `bash scripts/setup_vision_models.sh` on Linux/macOS. These scripts make *explicit* public-model downloads only when run by an operator. They now invoke the consolidated local acceptance gate and save an isolated `local-results/acceptance-<timestamp>/` record.

If models are already installed, skip downloads and use:

```bash
python -m scripts.run_vision_acceptance --writer-model qwen2.5vl:3b --review-model granite3.2-vision:2b --out-dir local-results/acceptance-manual-001
```

Use a **new** directory for each attempt. `local-results/` is local evidence, not a GitHub dataset. No customer video/photos or personally identifiable report data belong in this repository.

## Strengthened gates

1. `/api/tags` and `/api/show` establish **two distinct model IDs**, vision capabilities and two distinct SHA-256 model digests. A label alone is insufficient; a digest collision blocks acceptance.
2. **Each model** receives both real synthetic PNG pixel arrays (red square and blue circle) with the *same* prompt. Four actual model responses must match their images. A canned answer cannot pass both images for one model. Model output from simulated transport is marked `MOCK` and cannot satisfy this gate.
3. A synthetic exterior image and video are sent through the production specialist workflow. The model must **actually request** native zoom and a saved photo from video. If it does not select those actions, the gate records a blocker rather than substituting scripted actions.
4. At least one staged proposal must receive a distinct reviewer-model visual assessment. Source hashes, actions, timestamps and evidence IDs stay in local trial JSON.
5. Passing these gates yields `LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN`, **not** permission to serve customers. Human-reviewed field benchmarks, independent reviewer-host integrity and inspector sign-off remain mandatory.

## Evidence outputs

- `acceptance_status.json`: overall status, gates, model names/digests, tool counts, blocking reason, scoped SHA-256 artifact manifest.
- `image_probe.json`: four model-image condition checks; `actual_image_inference_executed` distinguishes live transport from tests.
- `trial/trial_status.json`, `specialist_dossier.json`, `technical_review.json`: video/photo/tool and claim-review evidence when stages complete.

The script refuses existing output paths and returns exit code 2 when blocked. Missing Ollama, missing model weights, invalid capabilities, mismatched digests, wrong visual answers, absent zoom/still requests, no Q02 visual review, and any JSON/model error are **hard blockers**.

## Current machine verification

On 2026-10-31 UTC, this ChatGPT execution environment had no running Ollama or installed weights. The real acceptance command was executed and wrote `BLOCKED` at `preflight`, with `live_model_inference_verified=false` and `customer_release_allowed=false`. The **147/147 local tests** (including controlled model replies) are useful engineering regressions, not a substitute for actual model inference or field tests.

The parent repository retains `PAUSE_AUTONOMY`. This development procedure does not activate public deployment, scheduled GitHub workflows, customer outreach, payments, or any other external operation.
