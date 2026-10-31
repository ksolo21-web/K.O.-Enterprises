# Home Inspection — local vision activation v1.2

**Scope:** Milestone 2 activation only; never customer inspection approval. Repository: `ksolo21-web/K.O.-Enterprises`, branch `home-inspection-development`, directory `ventures/home-inspection`.

## What actually works

A no-new-account local activation command checks Python >=3.12, FFmpeg, Python dependencies, an installed Ollama executable and service, and two separately named vision-capable Ollama models. It can **explicitly** start the installed local service, download public models, run the existing four-image challenge and full synthetic photo/video → native zoom → technical-review trial, then save unmodified pass/block status to a new local evidence directory.

**Every external download is opt-in.** The command cannot install the Ollama executable or create a hosted computer. An operator must first install Ollama and Python from the official distribution and install the project's `requirements.txt` dependencies. The `ollama serve` subprocess is configured only for `127.0.0.1:11434`. The program never sends media or results to a remote inference endpoint, disables public customer release, and refuses to overwrite prior evidence.

Ollama models used: `qwen2.5vl:3b` (writer) and `granite3.2-vision:2b` (Q02 reviewer). Both models must exist, have distinct digests, advertise vision, and actually respond correctly to different image contents. Smaller models may be inaccurate on real building defects; model size and synthetic color/shape recognition never establish inspection competency.

## Local operation — one command after installing prerequisites

From `ventures/home-inspection/`:

Windows PowerShell:

```powershell
python -m pip install -r requirements.txt
.\scripts\setup_vision_models.ps1
```

Linux/macOS shell:

```bash
python3 -m pip install -r requirements.txt
bash scripts/setup_vision_models.sh
```

These **operator-invoked** scripts start a local Ollama server if necessary, download both public model weights through Ollama, then run real inference trials. There is no background hosting or account creation by this project. Downloading model weights requires several GB of free disk and usable internet access. Model execution may be slow or fail due to RAM/VRAM limits; especially on CPU-only machines.

To audit readiness without authorizing service start or downloads:

```bash
python3 -m scripts.activate_vision --out-dir local-results/check-001
```

To run an already installed and running local stack without downloading anything:

```bash
python3 -m scripts.activate_vision --out-dir local-results/live-001 --run-live-gate
```

The output folder must not exist. `activation_status.json` shows actual prerequisites, actions attempted, model preflight, synthetic-gate stage and failures. The nested `acceptance/acceptance_status.json` is created only if live inference was requested and models became ready. Outputs under `local-results/` are excluded from version control. Never place customer-identifying media in a public repository.

## Mandatory limitations

- Passing the runtime preflight is **not** an inference pass; the status is `LOCAL_MODELS_READY_FIELD_VALIDATION_OPEN`.
- Passing the actual synthetic trial would be `LIVE_SYNTHETIC_GATE_PASSED_FIELD_VALIDATION_OPEN`, still **not** a field-validation pass.
- This local runtime contains no authenticated independent agent host, no qualified-inspector benchmark acceptance, and no client report signoff.
- The parent K.O. Enterprises `PAUSE_AUTONOMY` marker still applies to scheduled and external business actions. Operator-initiated local development is the only scope of this guide.
- Do not imply that GitHub Actions, a temporary ChatGPT container, or a source commit means model weights are downloaded, installed or running.

## Latest verified environment

On 2026-10-31 UTC, the current build environment has 5.8 GiB RAM, no GPU and no Ollama executable or installed model weights. The real activation diagnostic returned `BLOCKED` at `prerequisites` with `model_inference_verified=false`. All **159 local unit/integration checks passed**, including mocked activation controls; no live vision model ran here. The next genuine Milestone 2 acceptance requires executing the above activation procedure on suitable operator-controlled hardware and retaining its actual JSON evidence.
