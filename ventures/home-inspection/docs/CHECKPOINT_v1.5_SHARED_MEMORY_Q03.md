# v1.5 — Shared observation memory and Q03 adjudication

Development parent after reconciliation: `0d820f7d96b56ca0aa70dfa7ba5b739427c3a389`. Initial working baseline was `2e67ffa17c686ff3309c7d06f1c5222f4a9d13a3`. While this work was built, concurrent commits `bdd4968c395fa43b96642fc11737603f803a3321` and `0d820f7d96b56ca0aa70dfa7ba5b739427c3a389` added the 13-system knowledge source of truth and integrity fixes. All nine added files were preserved byte-for-byte by Git blob hash. The sole agents.py merge conflict was resolved by retaining the knowledge brief before the complete prompt-size gate. Current owner request asks why duplicates occurred, whether an adjudicator/smarter brain is needed, and to improve observation quality and useful evidence selection.

## Implemented and controlled-tested

- M00 supplies existing project records and current-batch proposals to each work order through a bounded memory window. Full source/zoom/provenance snapshot, total counts and omissions stay explicit. Exact same-view recurrence/reimported identical source bytes are rejected before adding another observation. New photos/crops may be potential corroboration and remain subject to Q03; they are not silently merged.
- Specialists receive assigned-feature questions and prior evidence context. Wall cladding questions explicitly exclude roof material. Optional actions should address an unresolved detail; no successful crop/time/claim is prescribed.
- Redundant normalized/native-pixel crops, current/decoded-same video moments are rejected. Newly created rejected files are rolled back. Different native regions remain allowed even if uniform pixels yield identical image hashes.
- Q02 review records now bind system and crop pixel hash/region as well as feature, location, source bbox and source image identity.
- Q03 takes the full bounded ledger plus source-matched Q02 decisions, reasons and missing-evidence notes. Every pending claim requires valid recorded hashes and matching review. The distinct configured text-reasoning provider can flag distinct claims, possible duplicates, conflicts, unsupported claims or missing evidence. It cannot merge, rewrite or approve records, run tools, override Q02 holds or change human verification.
- Saved adjudication is rechecked for all claim IDs, derived holds, review/evidence freshness and non-release/non-edit constraints. Removing a cached queue does not bypass Q03 for model records. A reconciled result remains an internal draft; human release requirements remain.
- A local `agents-adjudicate` CLI writes separate new review/project files. Controlled CLI tests cover held output and unchanged source.

## Verification

Pre-merge verification: **260/260 local tests passed**,36.147seconds; a genuinely separate critic independently reran **260/260**,36.010seconds. After preserving the concurrent knowledge work, **309/309 combined local tests passed**,36.178seconds. The separate critic independently passed **309/309**,36.406seconds, and returned **9.7/10 PASS with no mandatory integration blocker**. Its controlled calls across all13systems retained the knowledge brief (largest complete prompt6739bytes); an oversized brief was rejected before provider invocation. This merged review supersedes the earlier260test review and covers local implementation/integration only.

Adversarial repairs include missingSHA=None comparisons, stale crops under the same ID, empty saved decisions, stale source snapshots, lost Q02 explanations, oversized memory, same decoded frame despite a different requested time, and subpixel changes selecting the same native rectangle. All have meaningful regression coverage. The combined309test source supersedes earlier counts. The offline knowledge audit covers13systems/13registered references,12active and one pending-effective-date source, with catalog digest `6dd714ce69f51f2ea4d2f9b540c95e9bd8454b7fb6b06d39e3e72602e8770792`; it does not establish live source verification or field accuracy.

No live model call, new installation, replacement-model promotion, paid service, customer upload or temporary workflow was added. Remote inference was not rerun. This test/critic score is **not** a score for actual observation intelligence or full Milestone2.

Final exported-plan metadata now lists Q03 alongside Q01/Q02. A final full local rerun after that declarative update passed **309/309**,36.073seconds; no execution or approval claim is implied by a role appearing in the plan.

## Limits and critical next step

The current3B vision configuration has not earned the lead role. A stronger reasoning or multimodal model must be evaluated, not assumed competent. Q03 currently has a callable text-provider interface and controlled tests, not proven live semantic adjudication or authenticated separate runtime.

Bounded ledger128entries, memory≤6000bytes/default4records, specialist prompt≤20000bytes, Q03 packet≤60000serialized characters. Larger-inspection batched reconciliation is not implemented and fails explicitly. No source claim is dropped to pretend a whole inspection was reviewed.

Next: benchmark role-specific candidate models on A08 and held-out duplicates/paraphrases, distinct components, conflicts, wrong feature descriptions, unknown/hidden conditions and genuinely useful evidence actions. Retain actual outputs/digests/timings/source hashes. Use qualified-inspector real cases before field acceptance. The new writer prompts/Q03 logic have not yet been live-evaluated.

Full requirements, organization, executable milestones and model-promotion checklist: `OBSERVATION_QUALITY_AND_ADJUDICATION_v1.5.md`. Original Option2 report direction, photo/video capabilities, T07/T08, human-reviewed learning and all earlier mandatory gates remain preserved. Main, root pause and ordinary paused workflow must remain unchanged.
