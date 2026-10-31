# Home Inspection v1.2.1 — Verified Recovery Checkpoint

**Date:** 2026-10-30; **branch:** `home-inspection-development` in `ksolo21-web/K.O.-Enterprises`.

## Verified result
- The prior v1.2 activation transfer is complete. All six activation-file contents match the tested package, including the preserved README.
- The v1.2 benchmark correction now uses **maximum-cardinality matching** for overlapping issue boxes instead of greedy highest-IoU matching, preventing false reductions in true-positive counts.
- Corrected benchmark commit: `96cf60a029b36698ea23b4709fe77498c0f364ca`. GitHub readback matched the tested benchmark and test files.
- **160/160 local automated tests passed**, after running `python scripts/generate_public_fixtures.py` to create safe synthetic fixtures. Initial tests without fixtures were not considered passing.
- Existing `main` branch observed unchanged at `61ca9202fbfe45aae4a0ed29326df44cf7b25c9e`.

## Still blocked
The genuine `scripts.activate_vision` readiness check returned `BLOCKED`: Ollama is not installed in the execution environment. Python 3.13, FFmpeg, and required project packages are available; 5.8 GiB system RAM is reported. No model weights, live image inference, genuinely independent host execution, real-world defect accuracy, or professional inspector signoff have been demonstrated.

**No customer report may be released.** Synthetic-model pass labels and benchmark computations do not establish real-world professional inspection performance.

## Resume path
On a computer with official Ollama installed, sufficient RAM/VRAM and disk space, run the operator-invoked `scripts/setup_vision_models.ps1` (Windows) or `bash scripts/setup_vision_models.sh` (Linux/macOS) from `ventures/home-inspection/`. Model downloads are explicit; no account or paid service is created by the project. Preserve the resulting `local-results/activation-*/activation_status.json` and nested `acceptance/acceptance_status.json` locally, without committing model media, client evidence, private data, or runtime artifacts.

After genuine vision inference, require independent inspector-labeled, held-out field cases and measured critical misses/false alarms before any release decision. Do not change `PAUSE_AUTONOMY` or activate scheduled/external workflows without the corresponding authorization.
