# Milestone 2 — local vision runtime preflight (v0.9)

**Status:** implementation/tests complete; live AI defect detection, independent runtime identity, and qualified inspector benchmarks **blocked/unverified**.

## What this version changes

- The optional Ollama transport now uses Python's direct loopback HTTP connection (`127.0.0.1:11434`) instead of a redirect-following URL handler. Redirect responses fail closed and **cannot** forward evidence to another host via the client.
- Only `GET /api/tags`, `POST /api/show`, and `POST /api/generate` are allowed. The tool makes no arbitrary web calls, follows no HTTP redirects, and uses no proxies. Input size, reply size, and timeouts are bounded.
- `python -m inspection_engine model-preflight --writer-model <installed-writer:tag> --review-model <installed-reviewer:tag>` checks that two distinct model names exist locally and advertise `vision` in `/api/show`. The command performs **no** image inference and does not download models.
- A missing server, model, or vision capability returns a clear JSON `BLOCKED` result and a nonzero exit code.
- The existing `agents-run` and `agents-critic` commands remain **separate opt-in commands**. Model IDs being different does **not** prove independent execution environments, impartiality, or qualified reviewer expertise.
- The local test suite exercises the complete HTTP protocol against a tiny temporary loopback stub, including simulated forbidden redirects. It does **not** use Ollama or measure visual accuracy.

## Evidence from this development session — 2026-10-30

- Original fresh-checkout baseline: 118/118 local automated tests passed.
- After v0.9 transport + preflight additions: **129/129 tests passed**, including synthetic image/video regression tests.
- Host inspection: no Ollama binary or model server found, no model installed; `127.0.0.1:11434` connection refused.
- Actual CLI preflight: `BLOCKED` with `Local Ollama unavailable`; `real_inference_completed: false`, `customer_release_allowed: false`.
- No customer evidence, media or private data used or uploaded. No production workflow activated.

## Reproducible local check (after the saved fixture generator is run)

```bash
cd ventures/home-inspection
python -m pip install -r requirements.txt
python -m scripts.generate_public_fixtures
python -m unittest discover -s tests -q
python -m inspection_engine model-preflight \
  --writer-model <name-of-installed-local-vision-model> \
  --review-model <different-installed-local-vision-model>
```

The command is blocked until the operator explicitly installs two compatible vision models and starts the local service. Model names must match `/api/tags`. Ollama `/api/show` must explicitly advertise `vision`; lack of reported capability is a conservative rejection, not a claim about other model software.

## Subsequent mandatory acceptance gates

1. Run two actual models on rights-cleared local evidence using the existing `agents-run` and `agents-critic` entry points. Record model names, versions, request/error counts, resource usage, captured timestamps, source hashes, zoom lineage and human corrections. Do not infer that sampled video frames cover the entire video.
2. Test failures such as malformed JSON, missing or low-resolution imagery, poor crops, contradicted proposals, model downtime, latency, provider disagreement, and prompt injection in photos.
3. Validate on independently annotated, consented real property cases with qualified inspectors and a held-out property split. Measure misses by severity, precision/recall, and unsupported claims. Keep customer cases private; do not commit real photos/videos/reports to the public branch.
4. Require a separate Q02 challenge and authenticated human inspection/release approval. Do not promote visually plausible observations to verified defects automatically.
5. Keep the K.O. Enterprises `main` branch and `PAUSE_AUTONOMY` untouched. GitHub Actions under this product directory are documentation only; do not activate automation without authorization.

**Review type:** internal review only (no separate agent runtime was available). **Release score:** not awarded; mandatory real-model and professional validation gates remain untested.
