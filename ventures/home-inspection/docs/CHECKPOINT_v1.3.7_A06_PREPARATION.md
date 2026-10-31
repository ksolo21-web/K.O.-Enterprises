# v1.3.7 — reviewed source and A06 diagnostic preparation

Predecessor: `5f8cc619f874efd231d9490128bfdb46a0b2cd98`. Owner requested continuation from the actual A05 results. Source is now present on the development branch; the older source-ZIP recovery blocker is historical, not current.

## Completed before the remote attempt

- Restored96source/policy files from the predecessor and verified every Git blob hash and size.
- Retrieved A05's actual artifact `13028571288`; ZIP SHA-256 `9d4e05f62fab1b8942ee957ca27c1f9ae5de53b4b3b4589209139e2d905326a7`. Its two referenced JSON hashes also verified. Preserve4/4structured geometry responses, the earlier incorrect Granite answer, and its blocked specialist/zero-tool/zero-Q02 outcome.
- Baseline collected **184/184** passing tests here; do not substitute the older recorded183count. After repairs, **206/206** pass under Python3.12.14, Pillow11.3.0, reportlab4.4.9, pypdf6.10.0 and FFmpeg6.1.1. No original tests removed.
- Separate callable critic `/root/ollama_gate_critic` independently ran **206/206** tests plus10/10acceptance-focused tests and an adversarial failed-smoke probe. Source/evidence/plan score **9.6/10**, all mandatory bounded checks passed. This is not an inspection-accuracy or full-Milestone2 score.

## Repairs

1. Specialist/Q02 generation now requires exact `done: true` and no Ollama error. Synthetic probes use the same strict completion rule.
2. Synthetic trial calls preserve exact inputs/prompts/hashes and bounded untrusted returned envelopes/answers before later proposal/reviewer validation can fail. Engine step/tool events are saved incrementally. Failed smoke probes now preserve request/response/error events too, included in acceptance hashes; no claim depends on a missing failed answer.
3. Video-derived jobs receive actual source identity, decoded timestamp and freshly probed duration. Tool selection remains optional; no crop, timestamp or answer is prescribed.
4. Aggregate counts cannot pass the tool gate: executed actions must lead to traceable result-based proposals and Q02-reviewed evidence.
5. The temporal synthetic gate requires a reviewed still from a new source time and visibly changed pixels. Generic production extraction may still save frame0; no legitimate extractor capability was removed.

The strict feature-code validator remains unchanged. No invented code is corrected into a finding. Option2, photos/video/mixed media, original evidence, native zoom/stills, T07/T08 scope, learning boundaries, human review and nonrelease status remain intact.

## Current dependency-aware milestones

1. Pinned-source recovery and baseline: **COMPLETE**.
2. Evidence/acceptance repairs, tests and independent review: **COMPLETE**.
3. One bounded synthetic A06 GitHub CPU trial: **PREPARED; not executed at preparation time**.
4. Actual artifact readback, independent outcome review and trigger retirement: **PENDING**.

The exact plan and current-request scope are in `A06_TEST_PLAN.md` and `ONE_TIME_SYNTHETIC_TRIAL_APPROVAL_2026-10-30_A06.md`. Only one corrective run on the development branch is scoped; the100-minute standard CPU limit and existing public models/binary pins remain. Full regressions precede downloads. No paid API/runner, customer media, deployment, main change or global pause removal. Retire the temporary A06trigger after the attempt, including on failure. No automatic repeat trial.

No A06 live result, remote corrected-suite result, autonomous tool success, Q02 result, field accuracy or customer release is claimed in this preparation checkpoint. Those require actual run evidence. Qualified-inspector cases, authenticated signoff and full Milestone2 acceptance remain open.
