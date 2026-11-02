# Original Milestone 3 — completion status and v7 workflow

**Continuation note:** This preserves the v7 disposition. V8 subsequently implemented automatic proposals and an actual signed local promotion/consumption/rollback framework; see `M3_AUTOMATIC_AND_SIGNED_RUNTIME_V8.md` and `CHECKPOINT_M3_V8.md` for current software status. Original professional/empirical acceptance remains incomplete. Historical statements below that activation or automatic proposal code is absent describe v7, not the current branch.

The original scope is retained. **Full Milestone 3 is not complete or approved.** The new workflow completes an executable private preparation/mapping path and quarantined learning-lifecycle preparation. It cannot replace professionally evaluated report understanding or approved learning.

## Original requirement matrix

| Original requirement | Implemented software | Acceptance that remains missing |
|---|---|---|
| Private reference import | Bounded PDF/TXT import, source/page receipts, immutable declared partition registry | Authentic permission/provenance is an external declaration |
| Exact annotations | Original PDF span/page/offset quotes; separate untrusted OCR and image-region anchors | Technical meaning still needs qualified review |
| Comparison and corrections | All reference/agent entries retained, explicit decisions, quarantined lessons | No authenticated inspector adjudication |
| Full report understanding | All-page render/OCR/audit/viewer orchestration; typed section/table/figure/finding and cross-page declarations | Reliable automatic semantics and inspector-reviewed extraction benchmark **not established** |
| Durable case governance | Source/partition receipts, source revalidation, complete case-media hash inventory, disjoint training/holdout media in frozen evaluation plans | No authenticated global corpus/provenance service; changed/reencoded media can evade byte-hash overlap detection |
| Approved learning/promotion | Versioned quarantined candidate files, frozen holdout plans, declared evaluation capture, immediate-predecessor rollback preparation | Authenticated approval, actual held-out evaluation and an authorized activation/promotion mechanism **not implemented or exercised** |

No synthetic test or agent critic score closes the last two original acceptance gates. There is deliberately no learning-activation command and no active prompt/model pointer to roll back. A rollback file is a plan to restore a quarantined candidate, not proof that deployed model rollback works.

## Prepare every report page locally

Start with a PDF imported by `inspection_engine.report_learning` and bound to the existing shared private study registry. Then, from `ventures/home-inspection`:

```bash
python -m inspection_engine.report_study_pipeline prepare \
  --reference /private/case/reference.json --registry /private/study/registry.json \
  --source-pdf /private/case/original.pdf --ocr --out-dir /private/case/prepared
```

`--ocr` explicitly runs installed English Tesseract on every rendered page. Omitting it never claims OCR and leaves missing scan OCR in the audit. `--batch-size` accepts 1–8 pages; at most 25 batches are allowed. The default covers up to the existing 200-page source limit. Existing PDF/text/asset/resource limits still apply; exceeding a limit fails rather than truncating.

The command validates source registration, creates a complete queue and plan, renders all batches, optionally runs local OCR, indexes layouts, audits every page, and builds the offline viewer. It records all relative file hashes in `preparation.json`. It never modifies the shared registry. Output must be new; directories use 0700 and files 0600. A caught failure removes only the newly created output. A hard process kill can leave an incomplete directory without a valid receipt; preserve/inspect it and retry to a new directory. There is no claim of crash-atomic directory commits or host filesystem race isolation.

## Record structured interpretation with exact source anchors

Copy `mapping-template.json` **outside** the immutable prepared directory, then fill it as a new private declaration file. Editing a prepared file in place invalidates its receipt. Every original page requires `declared_reviewed` or `unresolved` plus a note. Those are unauthenticated declarations, never professional signoff.

The schema is enforced by `capture_report_mapping` in `inspection_engine/report_understanding.py`; the executable synthetic examples are in `tests/test_m3_completion_v7.py`.

- `sections`: unique ID, title and source anchors.
- `tables`: explicit page, column count, row IDs, and cell IDs/column/span/role/source anchors. Header, data, blank and unresolved roles are declared. A blank requires a selected original image region. Multiline cells preserve each original referenced OCR word and box. Ragged gaps remain `unassigned_columns`; the display labels them unassigned. OCR words cannot be silently assigned to multiple cells in one table.
- `figures`: explicit original page region, declared photo/diagram/unclassified kind and optional caption anchors. Whole-page regions can refer to vector figures or nested forms without claiming an embedded-image locator is known.
- `findings`: declared system/location/description and explicit references to sections, figures and cells. These are interpretations of report content, not verified property findings.
- `relations`: declared continuation/support/contradiction/same-component candidate between separate findings. Evidence must include distinct source pages belonging to both endpoints. An unrendered intervening page blocks a cross-page relation. No records are merged.

Anchor kinds stay separate: `pdf_text` needs exact page/span ID/relative character offset/quote; `ocr_words` needs original sorted unique word IDs; `image_region` needs an existing source-render page and normalized rectangle. Outputs include original source hashes, exact words/boxes and explicit unverified flags. A matching unsigned checksum is not source authorship or professional authentication.

```bash
python -m inspection_engine.report_study_pipeline map \
  --reference /private/case/reference.json --registry /private/study/registry.json \
  --source-pdf /private/case/original.pdf --study-dir /private/case/prepared \
  --declarations /private/case/new-declarations.json --out-dir /private/case/mapped
```

The new package contains a readable offline `index.html`, typed `mapping.json`, original-scope `readiness.json`, and a local `source-viewer/` rebuilt from the original source. Each evidence link opens its original physical PDF page. The regenerated viewer is compared with the entire prepared viewer inventory and receipt; altered markup is rejected even if someone recomputes the outer file hashes. All created directory levels are 0700. Source data is HTML-escaped; the HTML includes no scripts or online resources. Browser/host privacy remains separate from this artifact's behavior.

## Version and evaluate candidates without activation

`inspection_engine.report_learning_candidate` adds four local commands:

```bash
python -m inspection_engine.report_learning_candidate candidate \
  --project /private/case/project.json --reference /private/case/reference.json \
  --registry /private/study/registry.json --source-reference /private/case/original.pdf \
  --comparison /private/case/comparison.json --corrections /private/case/corrections.json \
  --version 1 --out /private/case/candidate-v1.json

python -m inspection_engine.report_learning_candidate freeze-evaluation \
  --candidate /private/case/candidate-v1.json --holdouts /private/study/holdout-paths.json \
  --out /private/study/frozen-plan.json

python -m inspection_engine.report_learning_candidate capture-evaluation \
  --plan /private/study/frozen-plan.json --results /private/study/declared-results.json \
  --out /private/study/captured-results.json

python -m inspection_engine.report_learning_candidate rollback-plan \
  --current /private/case/candidate-v2.json --previous /private/case/candidate-v1.json \
  --out /private/case/rollback-plan.json
```

Version 2 requires `--parent /private/case/candidate-v1.json`. Candidate preparation reconstructs the original corrections against the case/project/media, rechecks original source bytes, excludes locked holdouts, and freezes all original case-media hashes. Frozen evaluation cases must be registered locked holdouts, have matching project IDs and original bytes, and share no source/text/media identity with training or other holdouts. Holdout path records contain `reference`, `registry`, `project`, `source_reference` paths. Evaluation rows cover every holdout exactly once and contain `case_id`, nonnegative integer `true_positives`, `false_positives`, `false_negatives`, `critical_false_negatives`, and `review_record_sha256`.

Captured results are explicitly **unverified supplied counts**. A review hash cannot authenticate the reviewer or prove that evaluation happened. Even perfect supplied counts never become promotion eligible. Rehashed records with false authentication/activation assertions or malformed/empty media inventories are rejected. A deliberate local owner can still rewrite coherent unsigned records and recompute hashes; these files are not a trusted signing infrastructure.

## Defects repaired and actual verification

- Nested PDF Form XObject raster bounds were incorrectly treated as page-space. The independent critic reproduced a wrong locator after translation. Nested rasters are now counted but **unlocated**, so the viewer does not draw a false box. An actual translated/scaled nested-form regression covers the fix; source-page region review remains available. Recursion and object counts are bounded; arbitrary PDF/vector semantics are not inferred.
- Critic probes exposed unrelated-page relation anchors, forged authentication claims in rehashed candidate lineage, incomplete lifecycle media schemas, intermediate mapping directories created with mode 0755, and acceptance of rehashed injected viewer HTML. All were repaired and targeted regressions added; source-viewer presentation is now regenerated rather than imported.
- Focused source-bound v7 suite: **27/27 passed**, including actual local Tesseract, two-batch preparation, typed mappings, holdout media separation, no-activation lifecycle, rehashed HTML/source/receipt tampering, private permissions and caught-failure cleanup.
- Actual Chromium 153 desktop/mobile mapping checks passed at 360/390/768/1280 widths: three declared table cells, source-page links loading original scanned pixels, keyboard details, no document overflow, no remote page requests and no page errors. Parent and independent critic inspected screenshots. The browser OS sandbox was unavailable in this container; web-security/CSP checks stayed enabled.
- Final independent full regression: **804/804 home-inspection tests passed** in 85.534 seconds, zero skips/errors/failures; all five tested Python source/test hashes remained unchanged during the run. **229/229 company tests passed**. Source hashes, regression-log digest, browser results and original-scope blocked flags are saved under `docs/evidence/m3-v7/`. The original M3 gate remains blocked regardless of a scoped engineering score.

## Remaining critical path

1. Obtain authorized professionally labeled reports/case evidence and authenticated review identities when the owner is ready for the deferred work.
2. Evaluate actual semantic extraction and technical interpretation, including ragged/multiline tables, diagrams, handwriting, negation, cross-page identity and paragraph/image attribution. Manual declarations are not an automatic understanding system.
3. Implement a trusted approval/activation integration and perform versioned held-out evaluation plus real rollback validation before enabling learning. Quarantined plans are not deployed learning.

`main`, root pause, existing knowledge, report generation and live inference authorizations are preserved. No remote trial, external account, customer upload, model download or learning activation was launched by this work.
