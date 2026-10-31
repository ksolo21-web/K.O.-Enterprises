# Home Inspection — v1.2 GitHub Transfer & Runtime Acceptance Checkpoint

Date: 2026-10-30 (America/Detroit); local execution evidence timestamp 2026-10-31T01:29:46Z.

## What is verified
- Development branch: `home-inspection-development`; `main` unchanged at `61ca9202fbfe45aae4a0ed29326df44cf7b25c9e`.
- v1.2 activation transfer: `2f53ebea0465f3b67a1f688e5180e7b73dbdb898`. Six files committed and all six read back from GitHub (README addition verified; other five exact content matches).
- Clean source package: local v1.2 ZIP integrity check passed (56 members; no corrupt ZIP members).
- Project test suite: **159/159 passed locally**, rerun from `home_inspection_live_runtime_v12` (23.789 seconds measured in the local test runner; this is historical evidence, not an ETA).
- Product tree at transfer: 70 files, non-truncated recursive GitHub tree.
- No real customer evidence, model weights, private photographs, videos, or credentials were committed. The company `PAUSE_AUTONOMY` marker remains in place.

## Current live inference blocker — observed, not inferred
The *read-only* activation test `python -m scripts.activate_vision --out-dir <new-dir>` returned `BLOCKED` at `prerequisites`, exit code 2.
- `ollama_binary_found=false`
- `system_ram_gib=5.8`
- `ffmpeg_found=true`
- `python_supported=true` (3.13.5)
- `project_dependencies_found=true`
- `model_downloads_performed=[]`
- `model_inference_verified=false`
- `field_accuracy_verified=false`
- `customer_release_allowed=false`

**These results are not a real image-analysis pass.** No vision weights or inference were loaded on this machine. GitHub source storage does not supply a persistent local model host.

## Next executable work on an authorized compatible machine
1. Install a trusted current Python 3.12+, FFmpeg, project dependencies, and official Ollama, as described in `docs/LOCAL_ACTIVATION_v1.2.md`.
2. Operator explicitly runs `scripts/setup_vision_models.ps1` on Windows or `scripts/setup_vision_models.sh` on Linux/macOS to start a loopback service, download public writer `qwen2.5vl:3b` and reviewer `granite3.2-vision:2b`, and run the synthetic live acceptance gate. Do not run this unsupervised or on customer media.
3. Check `local-results/activation-*/activation_status.json` and nested live evidence; diagnose model load, image-conditioned answers, native zoom requests, video-still selection, and Q02 technical review.
4. Preserve fail-closed status if any check fails. Distinct model files do not prove independent worker governance, and synthetic shape tests do not establish field accuracy.
5. Separate real property validation, qualified-inspector blinded benchmarks, signed human reviews, privacy controls and approval before customer release.

## Approval
- Source-transfer acceptance: **PASS**
- Local test-suite acceptance: **PASS**
- Real vision-model operation: **BLOCKED**
- Real-world inspection accuracy: **UNTESTED**
- Customer-ready milestone: **NOT APPROVED**

**Internal review only:** no separate critic-agent runtime was available for this checkpoint. GitHub Actions/remote CI has not been executed; do not mark it passed.
