# v1.3.9 — A07 reviewed preparation

Parent: `8abc5a5ff2de6dfb39efee2dc9f29ad7bf04697d`, which records A06 failure and retires its trigger.

The specialist generation path now uses trusted per-work-order schemas. Feature codes are required and coupled to the assigned system; concern and tool alternatives have distinct fields. Live CLI/diagnostic providers receive the schema explicitly, the prompt includes it, and the synthetic audit saves its canonical hash. Existing controlled two-argument providers remain supported. Application validation remains authoritative, including native-pixel crop checks and rejection of unchanged full-frame zooms.

Local Python3.12/Pillow11.3 regression: **211/211 passed**,24.567seconds. Separate critic independently ran **211/211**,25.654seconds, inspected the actual A06 archive and the exact A07 plan/workflow, and returned **9.5/10 PASS with no mandatory code/plan blockers**. Scope is implementation and one bounded diagnostic plan only; this score does not establish live model compatibility or property accuracy.

The exact rejected A06 answer is now a regression case. The tests capture the actual mocked Ollama format field, check work-order system limits, separate tool contracts and canonical schema audit. No external JSON Schema validator check is claimed; no new dependency was added.

Execute only the single attempt in `A07_TEST_PLAN.md` under the current continuation scope in `ONE_TIME_SYNTHETIC_TRIAL_APPROVAL_2026-10-31_A07.md`. Retire its temporary trigger after the attempt. Keep `main`, the ordinary paused workflow and root `PAUSE_AUTONOMY` unchanged.

**Not yet proven:** A07 real inference, useful model-selected zoom, different-time changed-pixel still, Q02 review of resulting evidence, field accuracy, authenticated independent hosts or customer release.
