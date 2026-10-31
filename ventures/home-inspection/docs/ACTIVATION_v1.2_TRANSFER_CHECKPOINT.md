# Local vision activation v1.2 — recovery checkpoint

**Status, 2026-10-31 UTC:** The new activation implementation was developed and retested locally but has **not been transferred as source files to this GitHub branch**. This document is a factual handoff, not a production approval.

## Completed in the local source package
- A new `scripts/activate_vision.py` controller with explicit `--start-server`, `--download-models`, and `--run-live-gate` permissions.
- Read-only prerequisite diagnostics: Python 3.12+, project dependencies, FFmpeg, Ollama executable, system memory, disk space.
- Strict `127.0.0.1:11434` binding, non-overwriting `activation_status.json`, distinct writer/reviewer model IDs.
- Windows and Linux/macOS operator-invoked activation scripts, plus tests and a setup guide.
- **159/159** local regression tests passed, Python source compiled, shell syntax validated, and ZIP CRC validated.

## Actual machine evidence
- Python 3.13.5 and FFmpeg available.
- RAM 5.8 GiB, no GPU, Ollama not installed, model weights unavailable.
- Real activation command returned `BLOCKED` at prerequisites. **No live model inference occurred.**
- Customer report release remains prohibited.

## Transfer outstanding
- The full 56-file local v1.2 source/checkpoint ZIP is available in the originating ChatGPT conversation as `Home_Inspection_Activation_v1.2_Source_and_Checkpoint.zip`, SHA-256 `843414b163e21f9bddfb2953681a52db57c6e8f6fc801989eeccf992fe93e678`.
- The file handoff encountered a Library storage-cap error; no Library files were deleted.
- **Do not mark v1.2 committed** until the exact source files, tests, and docs are added to `ventures/home-inspection/` and compared with the ZIP.
- The existing v1.1 GitHub source remains the canonical committed executable baseline.

## Remaining release gates
Run actual local vision inference (Qwen2.5-VL 3B writer and Granite 3.2 Vision 2B reviewer), verify real agent-requested zoom and video-photo extraction, benchmark qualified-inspector-labeled real property cases, and obtain authenticated human signoff. The `PAUSE_AUTONOMY` control in the parent repository is unchanged.
