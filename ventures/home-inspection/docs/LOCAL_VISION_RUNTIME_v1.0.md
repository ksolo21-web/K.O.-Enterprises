# Local vision runtime — installation, proof, and review gates

**Status:** Integration implemented and synthetically tested; no live model weights available in the ChatGPT execution container. NOT a customer-ready inspection system.

## Purpose

Eliminate the **software integration** dependency on an unconfigured Ollama runtime while making it straightforward for the owner to activate two distinct, free local vision models on a computer. Ollama does not run simply because files are stored on GitHub. GitHub is source control, not a persistent inference service. No new account, paid API, deployment, or customer media upload is required.

Recommended initial model pair (both must be installed separately):

| Role | Ollama model | Weight download (approx.) | Reason |
|---|---|---:|---|
| Writer / technical specialist | `qwen2.5vl:3b` | 3.2 GB | Visual grounding, text/labels, positioning |
| Q02 technical challenger | `granite3.2-vision:2b` | 2.4 GB | Different model family and visual-document skills |

Use an up-to-date Ollama runtime, Python 3.12+, FFmpeg, and at least ~8 GB RAM (16 GB preferred) with enough **free** disk space for both models, dependencies and temporary frames. CPU-only is possible but can be slow. Both models are unloaded after a response (`keep_alive: 0`) to reduce RAM overlap. Separate model IDs on one Ollama server do **not** establish independent runtime identities or independent reviewer agents. Model behavior and professional accuracy must be validated.

## Operator activation — Windows

1. Download and install **official Ollama**: https://ollama.com/download/windows . Open Ollama so that the local service is running.
2. Install Python 3.12+, FFmpeg and Python project dependencies in a local virtual environment. From the product directory:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
3. Run from the product directory in PowerShell:

   ```powershell
   .\scripts\setup_vision_models.ps1
   ```

   The script explicitly downloads the two model weights, confirms advertised vision capabilities and runs an actual two-image synthetic inference probe, or exits with a blocker. Model downloads may take time and use bandwidth; they are never hidden or automatic in repository CI.

## Operator activation — Linux/macOS

1. Install official Ollama: https://ollama.com/download and start it (for Linux, run `ollama serve` in another terminal when no local service is running). Keep Ollama loopback-only; do not expose port 11434 externally.
2. From the product directory in a shell:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   bash scripts/setup_vision_models.sh
   ```

   The script assumes that your activated environment provides `python3` and `ollama` on PATH.

## Explicit test commands

```bash
python -m inspection_engine model-preflight --writer-model qwen2.5vl:3b --review-model granite3.2-vision:2b
python -m inspection_engine model-smoke --writer-model qwen2.5vl:3b --review-model granite3.2-vision:2b --out local-results/vision-smoke.json
python -m scripts.run_local_live_trial --writer-model qwen2.5vl:3b --review-model granite3.2-vision:2b --out-dir local-results/synthetic-trial
```

**Do not reuse existing output filenames.** Each run writes new local evidence. If video processing is unavailable, add `--no-video` to the final command but do not claim video was exercised. Each result remains provisional and cannot release a report.

The synthetic trial runs real local model requests against generated exterior drawings and video frames. It lets specialists request native zoom or saved video stills, preserves source hashes and timestamps, and dispatches model-proposed findings to Q02 if any exist. A model choosing *not* to request a tool is recorded as zero executed actions, not a fake success. A model producing no proposals leaves claim-specific reviewer validation incomplete. All field accuracy remains unverified until measured on permissioned human-reviewed real cases.

## Observability and fail-closed rules

- Local-only Python connector: fixed `127.0.0.1:11434`, whitelisted endpoints, no redirects/proxy expansion, no cloud fallback, bounded payloads and replies.
- Two different installed model identifiers required; advertised vision capabilities are not proof of actual inference.
- The smoke test sends distinct synthetic red-square and blue-circle images, requiring successful *image-conditioned* shape/color responses from each model. Passing only the transport mocks never counts as a live proof.
- Generate output JSON in `local-results/` (local only, do not commit). Status records explicitly identify mocks vs live executions.
- Source-pixel zoom, video still selection, hashes and timecodes already form the evidence toolchain, but the model may fail to request them.
- Model errors, missing capabilities, malformed proposals, unapproved actions and failed evidence checks **block** progress. No auto-approval, customer publication, or training from customer data.
- Q02 is a separate model family but runs on the same Ollama host. Genuine role and runtime separation, blind testing, and professional inspector signoff are outstanding.

## Next gates (cannot waive)

1. **LIVE-R1:** Run real Ollama server and download/identify actual models on an authorized host; store model digests, Ollama version, machine CPU/RAM and local test output.
2. **LIVE-R2:** Both models correctly pass image-conditioned smoke, with evidence JSON and no cloud transmission.
3. **LIVE-R3:** Full specialist and Q02 separate model calls execute on synthetic image/video; record exact zoom/still requests, nonrequests and malformed responses.
4. **LIVE-R4:** Compare blind findings against consented real property cases reviewed by qualified inspectors. Score recall, precision, missed defects, unsupported claims, type-of-system descriptions, and input coverage.
5. **LIVE-R5:** Establish authenticated human review, security/privacy compliance and repeated performance checks prior to customer use.

**No live runtime pass, no independent human critique, and no real-field accuracy score are claimed here.**
