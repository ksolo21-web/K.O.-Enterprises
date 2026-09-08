# Territory card production

This branch adds the zero-paid-service territory runner without changing the business workflows.

## Non-negotiable controls

- No Work, Codex, Copilot, paid model APIs, or model-provider credentials in the production runner.
- Standard public GitHub-hosted runners only for public-code tests. No paid or larger runners, artifact uploads, caches, or schedules are introduced.
- Private maps, original cards, address datasets and review evidence stay outside this public repository.
- Preserve the original `territory-map-card-builder`, `territory-card-critic`, and `kaleb-quality-loop` sources and their exact SHA-256 identities.
- The latest recovered territory policy requires every scoring category to equal 10 with all mandatory evidence. It supersedes older 9 or 9.99 thresholds for this recovered workflow.
- A deterministic validator is not an independent visual reviewer. Local vision inference remains advisory until calibrated; generating screenshots is not inspection.
- Never replace a missing source, review, or evidence field with a pass. Never overwrite an approved source or existing candidate.

## Implementation status

The branch is a production-workflow migration, not a claim that any real territory card has been completed. Read `production/CHECKPOINT.json` for the exact verified and pending milestones.

The complete retained source capsule contains 138 source and policy files. The source loader verifies file identities and refuses unmanifested inputs, archive traversal, stale hashes and missing dependencies.

## Local commands

Use Python 3.12 or later in a virtual environment:

```sh
python -m pip install -r territory/production/requirements.txt
python territory/production/engine.py doctor
python territory/production/engine.py build /private/job/recipe.json '/private/job/Territory - 999.pdf'
python territory/production/engine.py capture '/private/job/Territory - 999.pdf' /private/job/review-round-1
```

The builder requires an approved blank front template and a hash-locked, complete source-map page. It preserves geometry and uses isotropic placement, not a redraw. Text placements must be explicitly approved, fit their boxes, and avoid the map. It never manufactures a template, street identity, address assignment or map repair.

For actual local vision review, run Ollama with cloud features disabled (`OLLAMA_NO_CLOUD=1`) and the local `qwen2.5vl:3b` model. The runner contacts only `127.0.0.1:11434`, disables proxies, saves the actual model response and image hashes, and does not convert the model's score into release approval.

The original project/review gates are invoked for releases. Independent-review authenticity is checked separately from the JSON assertions. An owner-pinned independent reviewer key is supported for signed human review. Unattended model-only release remains disabled until calibration and review attestation are validated.

## Public CI and private production are different

Public CI proves code behavior using synthetic inputs. It does not process private territory materials or award real cards a passing score. Ordinary script execution does not call ChatGPT or a paid AI service. Repository visibility is checked before a hosted runner is allocated, and no paid-runner fallback is configured.

No OANDA, Stripe or existing business secrets are used or changed. The business `PAUSE_AUTONOMY` file and existing workflows remain unchanged.
