# Observation quality, shared memory and independent adjudication — v1.5

## Why A08 repeated itself

A08 was one Qwen2.5VL3B response, not eleven agents agreeing and not eleven accepted inspection findings. It emitted twelve candidates: one unsupported roof description filed under cladding and eleven copies of a door/trim description. The allowed array could contain up to twelve entries. We observed repetition; we cannot claim to know the model's private cause. The unchanged full-image zoom blocked the response before tool/report acceptance. Existing exact-duplicate rejection alone did not give subsequent work orders a shared record.

The tested3B configuration is **not promoted as the inspection lead or reliable specialist**. Bigger parameters, a longer timeout or a neat JSON schema do not establish inspection competence. Ollama's official structured-output guidance describes format enforcement, not field inspection validation: https://docs.ollama.com/capabilities/structured-outputs (consulted2026-10-31). A08 directly demonstrates a syntactically constrained response with wrong/repeated content.

## Requirements and preserved approvals

- Preserve photo/video/mixed intake, native source crops, timestamped lossless video stills, full home characteristics including unknowns, T07/T08 research, human-reviewed learning and Option2 ModernEditorial output.
- Seed the lead's memory from existing observations/findings and current specialist work. Keep source/zoom hashes, locations and bounds. Never overwrite human records or call a draft a verified finding.
- Reject exact repeated claims at the same view/location, including reimported identical source bytes. A new crop or different photo may supply corroboration; it must be reconciled rather than automatically merged into a physical component.
- Send a bounded, explicit prior-record window to the specialist. Keep full ledger identity, counts and omission flags. Omission is never evidence that a component was not previously observed.
- Reject redundant evidence actions, including a seek that decodes to the current frame. Preserve valid new native evidence and complete custody.
- Independently challenge visual claims through Q02, then reconcile the combined record through Q03. No stage may invent a missing feature, resolve a contradiction by guessing, remove a hold, approve safety or release.
- Pass strictly above9 with all code/evidence requirements; live quality remains open until actual model benchmarks pass. No new model installation, paid service, customer upload, live trial or pause removal is part of this change.

## Reporting organization

| Role | Responsibility | Boundary |
|---|---|---|
| M00 Inspection Director | Route work, maintain shared ledger, track coverage/evidence tasks | Coordinates; does not certify findings |
| Evidence Lead | Custody, useful views, missing evidence and provenance | A saved frame is not proof of exhaustive coverage |
| T01–T08 specialists | Provisional observations in assigned systems | Must read prior records; no quota-filling or self-approval |
| Q01 | Deterministic custody, completeness and reference checks | Does not diagnose |
| Q02 visual challenger | Inspect original/context/detail pixels and feature-code fit | Preserve reasons and specific missing evidence |
| Q03 adjudicator | Reconcile all bounded ledger claims with Q02 reasons, overlaps and conflicts | Text/record reasoning; does not replace Q02 pixel review |
| Report Lead | Compose the approved Option2 report from resolved, reviewed material | Cannot publish around unresolved holds |
| Qualified human inspector | Resolve uncertain component identity, physical testing and final verification | Human release remains mandatory and unauthenticated in this prototype |

These are logical role configurations and callable providers. They are not proof of independently hosted/authenticated AI workers. Q03 must use a distinct configured provider ID from writer and Q02; that alone does not prove different weights or hosts.

## Executable milestones

1. **Shared ledger:** `entries`, `memory_context` and `require_new_candidate` in adjudication.py, used by every specialist work order. Full index bounded128entries; prompt window defaults4records and stays at or below6000bytes. The complete specialist prompt is capped20000bytes. Larger context fails or exposes omissions; it never silently declares full coverage.
2. **Evidence selection:** assigned-feature questions, prior zoom regions and current-video metadata enter the prompt. A chosen action must still pass coordinate/custody/budget rules. Same requested/decoded video moment is rejected; newly created rejected stills are rolled back without deleting prior evidence. Subpixel coordinate changes selecting the same native source rectangle are rejected and rolled back. Different native rectangles remain valid even when uniform pixels yield identical crop hashes; image hash alone never establishes physical identity.
3. **Independent adjudication:** `adjudicate` requires source-matched Q02 review of every pending claim, including feature/system/type/location/bbox, valid nonempty source hashes and every referenced crop's hash/region. It passes Q02 reasons and gaps as untrusted data. Q03 must return one disposition for every entry: distinct, possible_duplicate, conflict, unsupported or needs_evidence. Possible duplicates are holds, not merges. No text similarity rule establishes physical identity.
4. **Report hold:** saved Q03 results are revalidated for complete coverage, fresh source/zoom/provenance snapshots, consistent holds and preserved Q02 dispositions. Deleting the cached queue cannot bypass the requirement for model-generated records. A resolved Q03 result is still an internal draft and does not change human review states.
5. **Model promotion:** no replacement lead/adjudicator is installed or approved. Controlled tests verify plumbing, not intelligence. Actual benchmark and hardware/context/latency validation are the next dependency before a new live workflow.

Q03 context is bounded60000serialized characters and128ledger entries. Explicit batched reconciliation for larger inspections is **not implemented**; exceeding the bound blocks instead of reviewing only part of a home. This is a material prototype limitation, not a completed production organization.

## Local command

After actual independent Q02 review, with a separate already-installed and appropriately evaluated local reasoning model:

```bash
python -m inspection_engine agents-adjudicate private_case/project.json \
  --technical-review private_case/technical_review.json \
  --reasoning-model SEPARATE_LOCAL_REASONER \
  --out private_case/adjudication.json \
  --out-project private_case/adjudicated_project.json
```

Outputs must be new files beside the project. The input project is not overwritten. Unresolved decisions and Q02 holds remain holds. This command has controlled tests; no live Q03 model execution has been demonstrated. Do not put private_case or customer evidence in the public repository.

## Stronger-brain promotion checklist

Do not select a model by parameter count or a published aggregate score alone. Run candidate lead, visual specialist and adjudicator roles on the same held-out cases and retain actual requests/responses, model digests, settings, input hashes, timing and adjudication decisions. Pre-register task-specific thresholds with a qualified inspector; do not tune on the held-out answers.

Mandatory cases include:
- A08 exact repetition, paraphrased duplicates, reimported photos and recurrence in a later work order.
- Two genuinely distinct but similar components; preserve both and never silently merge them.
- Conflicting claims about the same identified component; retain both sources and request resolution.
- Roof/cladding misclassification, unsupported materials, concealed components and physical-operation claims.
- Useful smaller native crops, pointless/full-frame crops, repeated existing regions, and requested-vs-decoded video timestamps.
- Q02 rejection/evidence gaps that Q03 cannot override; altered source pixels and stale snapshots.
- Untrusted image/report/memory instructions; no tool, authority or release expansion.
- Complete report descriptions even when no defect is proposed, with unobserved/unknown attributes explicit.

A stronger text reasoner may coordinate and adjudicate without receiving every image, while a proven vision model handles pixels. A stronger multimodal lead is another candidate. Neither architecture is promoted until measured. Current GitHub CPU inference took217seconds for a bad answer; performance and quality must both be assessed on the actual available hardware. No paid provider or new account is selected here.

Reference reports and joint inspections can later supply adjudicated misses and counterexamples. They do not automatically retrain model weights or turn an inspector's report into unquestionable ground truth.

## Acceptance evidence to save

Full deterministic regression log, genuinely independent critic result, exact source readback on the development branch, unchanged main/pause/workflows, and a resumable checkpoint. Code acceptance must be scoped separately from untested live model quality, full Milestone2, real-property accuracy and customer release.
