# Milestone 3 report-study foundation

Current continuation: `M3_AUTOMATIC_AND_SIGNED_RUNTIME_V8.md` and `CHECKPOINT_M3_V8.md`. The implementation statuses below are the historical v1.6 foundation; the original acceptance requirements remain binding. Automatic source-backed proposals and signed local lesson activation now have implementations, while real professional/empirical acceptance remains unestablished.

2026-10-31. Source foundation only; full Milestone 3 remains incomplete.

## Requirements and dependency-aware milestones

| Work | Dependency | Acceptance | Current result |
|---|---|---|---|
| Private local reference import | Explicit comparison consent/use declarations | Preserve complete bounded text, source checksum, page warnings | Implemented; synthetic tests |
| Reference annotations | Imported case/source/page text | Exact page and character-offset quote; reject invented quotes | Implemented; human annotation required |
| Comparison ledger | Same case and immutable registry partition | Retain all reference and agent entries; preserve ambiguous candidates | Implemented; exact-key suggestions only |
| Correction capture | Fresh comparison, source/evidence custody | One disposition per entry; actionable lesson needs case evidence | Implemented; declarations unauthenticated |
| Quarantined lessons | Complete correction capture | No prompt/weight updates, no release; holdout emits no lessons | Implemented; no promotion path |
| Full report understanding | OCR, table/image interpretation, evaluated extraction | Inspector-reviewed section/finding/evidence mapping | Not implemented |
| Approved learning/promotion | Authenticated review, durable case governance, held-out evaluation | Versioned candidate, independent regression and rollback | Not implemented |

The existing comparison function in `learning.py` remains backward compatible. The new interface preserves entries rather than indexing multiple components under one feature and overwriting earlier records.

## Commands

Use a private local directory and the **same registry for every study case**. Do not commit reports, annotations, addresses or customer evidence to the public repository. Output parents must already exist. Commands refuse existing outputs; newly created study files use mode 0600.

```bash
python -m inspection_engine.report_learning import private_case/reference.pdf \
  --case-id CASE_ID --partition training_candidate \
  --authorized-use --consented --registry private_study/registry.json \
  --out private_case/imported_reference.json

python -m inspection_engine.report_learning compare private_case/project.json \
  --reference private_case/imported_reference.json \
  --annotations private_case/annotations.json \
  --registry private_study/registry.json --out private_case/comparison.json

python -m inspection_engine.report_learning correct private_case/project.json \
  --reference private_case/imported_reference.json \
  --comparison private_case/comparison.json --decisions private_case/decisions.json \
  --reviewer-id INSPECTOR_DECLARATION_ID \
  --registry private_study/registry.json --out private_case/corrections.json
```

`CASE_ID` must equal `project_id` in the inspection project. The flags record the operator's declarations; they do not authenticate consent, authorship, copyright permissions or inspector qualifications. No new customer material was collected to build this source foundation.

Supported import: PDF and UTF-8 TXT. PDF extraction is text only; images, layout and handwriting are not interpreted. Each page records text availability, raster-image presence and visual-review limitations. Missing-text pages explicitly need OCR/review. Encrypted, corrupt, oversized and resource-exceeding inputs fail; text is never silently truncated. Page offsets refer to **extracted text**, not geometric coordinates in a rendered PDF. Presence of text does not establish complete extraction.

Annotation example (an array of objects):

```json
[{"id":"R1","system":"exterior","kind":"feature","feature_code":"cladding_type",
  "location":"Front wall","description":"Possible mark described by the source report",
  "page":1,"offset":0,"quote":"Exact text at this extracted-page offset"}]
```

`kind` is `feature` or `potential_concern`; an unknown feature code can be null. The annotation binds a human interpretation to an actual quote; it does not prove that interpretation is technically correct. Exact system/kind/feature/location keys suggest possible agent matches. They do not establish physical-component identity, semantic agreement or ground truth. Every source and agent row remains in the review list, including unmatched and ambiguous records.

Correction decisions must cover **every** `review_entry_ids` entry exactly once:

```json
[{"entry_id":"reference:R1","category":"missed_observation",
  "related_entry_ids":[],"evidence_ids":["P0001"],
  "explanation":"Operator's evidence-bound correction for independent review",
  "lesson_text":"Proposed lesson, pending external review"}]
```

Categories: `missed_observation`, `false_alarm`, `description_correction`, `evidence_gap`, `ambiguous_match`, `reference_error`, `no_change`. Misses refer to reference entries; false alarms refer to agent entries. Actionable categories require original case evidence and explicit proposed lesson text. Evidence gaps, ambiguous matches and unchanged rows do not generate lesson candidates. The human reference can itself be wrong. Even actionable corrections remain **human-declared candidates awaiting external review**, never authenticated defect labels. No model is called, trained or modified by these commands.

## Holdout protection and its boundary

Registry bindings preserve the declared case partition, source-byte SHA256 and an NFKC/case/whitespace-normalized text fingerprint. Renaming a file, changing its extension/container with the same extracted text, or reusing a declared case ID cannot silently move a locked holdout into learning. Locked-holdout corrections produce no lesson candidates.

This is a **local anti-leakage safeguard**, not authenticated corpus governance or semantic deduplication. A deliberately new/deleted registry, arbitrary substantive report edits, different declared case IDs with changed text, or reused property evidence under different reports require external case-provenance review. The current registry does not bind original case-media identities across different cases. Identical generic templates may conservatively collide and require manual governance review. It does not grant an automatic override. Checksums detect inconsistent versions; an owner can still edit local records and recompute checksums. No learning activation exists to treat those declarations as verified truth.

## Bounds and recovery

20MB original file, 200 pages, 500,000 text characters; PDF child process 768MiB address space, 10 CPU seconds, 20-second wall timeout. PDF warnings go to a discarded stderr stream, not an unbounded parent buffer. Both original and post-extraction reads are bounded, with replacement/change checks. The worker parses the exact hashed bytes supplied through stdin; it never reopens the source path. FIFO inputs are rejected without blocking. Imported controls are data, never instructions.

Study JSON reads are bounded to 5MB, including project inputs. Comparisons allow up to 128 reference annotations and 128 agent claims and cap serialized output at 4MB. Exported agent descriptions/locations/IDs are bounded. Exceeding a limit fails explicitly; batch orchestration is future work.

Registry import uses an exclusive lock, checks for concurrent changes, writes mode-0600 files, and atomically replaces the registry. A registry-write failure removes the new output. A process crash between output and registry persistence may leave an unregistered import; comparison rejects it. Preserve source files, inspect the registry, and reimport to a new output after resolving the interrupted operation. Do not reset the registry to bypass holdout constraints.
