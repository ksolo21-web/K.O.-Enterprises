# Home Inspection source-transfer handoff

Scope: truthful recovery checkpoint for the existing `home-inspection-development` branch. This document does not implement or approve the inspection engine.

## Verified repository snapshot

- Repository: `ksolo21-web/K.O.-Enterprises`.
- Observed product commit: `45c9e92e3a927b5c0d2fa415b081b152b58538db`.
- Product directory: `ventures/home-inspection/`.
- Recursive tree was complete, not truncated. It contains six product Markdown files plus `inspection_engine/benchmark.py` and `tests/test_benchmark.py`.
- Both Python files were retrieved and their exact Git blob hashes checked locally; both parse as Python source. This is not execution of their test cases.
- `benchmark.py` imports `.core` and `.capture`; `test_benchmark.py` also imports those modules and loads `examples/demo_project.json`. These required dependencies are absent from the observed product tree.
- Product documents additionally reference `inspection_engine/critic.py`, `inspection_engine/report.py`, a `python -m inspection_engine` entrypoint, supporting scripts and requirements that are not yet transferred.

## Recovery blocker

The original artifact is `Home_Inspection_M2_Technical_Critic_v0.7_Source.zip`. The previously recorded SHA-256 is:

`ba9dedcf000e4f77a746e614e0a55cc279e23343a3a436483e8ede75435cd025`

That digest is a recovery target, not a newly verified artifact in this session. The ZIP is not attached/available to the current workspace; its prior `/mnt/data/` location belongs to the earlier working session. Exact-title and alternate-title Library searches did not recover the source package. No original archive bytes or complete file manifest were available here.

Do not reconstruct the missing v0.7 modules from prose and call them the tested original. Obtain the original ZIP as an attachment or an accessible source location, hash it, inspect its manifest and preserve the known-good source before modifying behavior. Report a digest mismatch and investigate before importing a different package as v0.7.

## Required transfer and acceptance sequence

1. Recover the original source ZIP; verify its digest and inspect file paths/content without executing unknown scripts. Separate actual code/tests from generated reports, runtime databases, customer evidence, private information, secrets, and unlicensed material. No raw customer photos/videos/reports go into this public branch.
2. Stage reviewed source, original tests, requirements and rights-cleared fixtures under `ventures/home-inspection/`. Preserve already committed benchmark work. Record any intentional excluded/private files and any integration differences; do not claim complete archive parity when exclusions exist.
3. Run the documented original regression suite in its required Python/dependency environment. The branch documents report **104 prior tests passed**, but that suite has not run here because the source is missing. Keep original-prototype results separate from the later benchmark tests and any new tests; report actual collected/passed/error counts after recovery.
4. Run reproducible Option 2 report generation, render and inspect every generated page, and test long reports for pagination/omissions. The current design-standard document explicitly identifies fixed-five-page truncation as unresolved; do not call the report engine complete while observations can be dropped.
5. Exercise photo/video intake, native-pixel zoom, lossless still extraction and evidence hashes using rights-cleared fixtures. Sampled frames must not imply exhaustive footage review. Video-only and photo-only input remain supported without invented views/tests.
6. Connect writer and reviewer to actual local vision runtimes within an explicitly supported environment. Record models/versions, real versus scripted execution, timeouts/schema failures and preserved original/crop context. Provider IDs alone do not prove independent workers. No model installation, remote customer-data processing, paid API or deployment is performed by this checkpoint.
7. Compare findings and home descriptions with consented, qualified-inspector-reviewed reference cases. Preserve blinded initial results, observable misses versus input gaps, false alarms, held-out property separation and independent review. Synthetic/mocked tests do not measure field accuracy.
8. Maintain independent review and qualified human verification before client release. Human authentication/sign-off, applicable professional/privacy requirements and real-world accuracy remain unresolved.

## Requirements that must survive integration

- Approved Option 2 editorial report design and original photo evidence.
- Photo-only, video-only and mixed input; source hashes/timestamps and native detail access.
- Complete in-scope home descriptions even with no concerns: foundation, floor structure, subfloor, visible supports, wall/ceiling/roof framing and major systems. Hidden materials remain unknown; floor finish is not subfloor evidence; no automatic whole-system pass.
- T07 owns water-heater identification/manufacture-date research; T08 owns HVAC equipment research, with source/applicability and independent review. Manufacture date, installation date, warranty and remaining useful life stay distinct.
- Full-report study and paired-report learning, evidence-supported differences and controlled versioned lessons. Current L01 full-report ingestion is still future work, not active self-training.
- The live prototype role map is recorded in `MILESTONE_2_AGENT_ORGANIZATION.md` (including M03 descriptions, T01 site and T02 structural coverage). Earlier local design role IDs differ; reconcile explicitly instead of replacing the newer implementation's role map with an older draft.
- `main` and unrelated ventures remain unchanged; repository governance and the existing pause marker remain intact.

## Current acceptance

Source transfer: **BLOCKED — ORIGINAL SOURCE ARTIFACT REQUIRED**.

Original 104-test rerun here: **NOT EXECUTED**.

Live vision specialists and real-property accuracy: **NOT VERIFIED**.

Client release: **NOT AUTHORIZED**.

Next required input: the original v0.7 source ZIP or an accessible location containing those exact bytes. This is a missing source-input requirement, not a request for permission to perform already authorized internal development.
