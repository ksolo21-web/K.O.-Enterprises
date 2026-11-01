# Milestone 3 — traceable report-text review queue (v1)

**Status:** New bounded source feature for manual review, not autonomous interpretation, training, or customer delivery. This stage supplements the existing `report_learning` private import → compare → correction path. It leaves all previous APIs and the legacy report generator unchanged.

## What the new stage does

1. Consumes an **already-imported**, explicitly authorized and consent-declared PDF/TXT reference bundle **registered** in the existing private study registry. The authoritative `validate_bundle`, `validate_registry`, and `require_registered` checks run before any review work.
2. Enumerates every imported page, including pages with **no extractable text** and pages with embedded images. Exposes exact character-offset spans, SHA-256 for each source span, and complete page-character coverage. Empty/graphic pages are explicitly marked for OCR and/or visual assessment.
3. Attaches only lightweight **untrusted review cue** keywords (e.g. `repair`, `missing`, `stain`). A mention such as **“no leaks observed”** remains an untrusted excerpt; it **never** becomes a defect claim or evidence of safety. Every excerpt is review-pending, including those without cues.
4. Accepts **human-selected** `span_id` and start/end offsets plus explicitly declared system, kind, feature code, location, and description. Emits the *existing* annotation-array format accepted by `report_learning compare`, anchored to exact source-page text. No system/cause/severity classification is generated on behalf of the human.
5. Recreates and checks the queue against the complete authoritative source and current registry on every annotation request. Altered, stale, or partial queues are rejected. Holdout cases remain governed by the existing registry and correction logic; this stage cannot activate any lessons or alter training partitions.

## Commands (private workspace only)

Prior: import with existing CLI, preserving explicit `--authorized-use` and `--consented` flags and **same registry** for all study cases.

```bash
python -m inspection_engine.report_review_queue triage \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --out private_case/review_queue.json
```

The reviewer inspects every queue page and its source PDF images/figures directly. A manual selections file (`private_case/marks.json`) is an array like:

```json
[
  {
    "id": "REF-1", "span_id": "P0001-C000000", "start": 0, "end": 28,
    "system": "exterior", "kind": "potential_concern", "feature_code": null,
    "location": "Front exterior", "description": "Human-entered summary requiring review"
  }
]
```

`start`/`end` are relative to the identified span, not to the entire page. The mark must be adjusted to the actual text; the illustration above does not imply a finding exists.

```bash
python -m inspection_engine.report_review_queue annotate \
  --reference private_case/imported_reference.json \
  --registry private_study/registry.json \
  --queue private_case/review_queue.json \
  --marks private_case/marks.json \
  --out private_case/annotations.json

python -m inspection_engine.report_learning compare private_case/project.json \
  --reference private_case/imported_reference.json \
  --annotations private_case/annotations.json \
  --registry private_study/registry.json \
  --out private_case/comparison.json
```

Outputs are new, non-overwritten mode-0600 local files. The CLI prints counts/status, not private report text. No customer files, reports, images, full standards, or annotations are committed to public GitHub.

## Mandatory gates and known limits

- **Text-only** source: inherited PDF text extraction can miss scanned pages, diagram/photograph contents, handwriting, page-reading order, and hidden table structure; these remain visually unreviewed. A new OCR/evaluation subsystem is still required and should be implemented with source-image and page-hash provenance rather than blindly merging OCR text into verified material.
- A split may make a sentence straddle two chunks. All characters are still preserved, and a human can open the original full page to establish complete context. A cue on either chunk is not a diagnosis.
- Maximum 2,500 spans, 1,000 characters per span, 4 MB output and 5 MB per input JSON. Excess fails explicitly without silent omission.
- **No false assurance**: review cues have no severity or system labels; findings are not reported until qualified inspector review and final customer release requirements are independently met.
- Consent/rights flags currently record operator declarations; they are not authentication or a copyright grant. No learning/weight update or promotion action is implemented.
- Production-grade use needs qualified human review of entire reports, OCR/figures/tables validation, semantic alignment tests, authenticated reviewer identity, held-out field benchmark, conflict-resolution workflow and full latest-branch regression.

## Acceptance checklist

- [x] Every extractable character preserved in page-bound spans (including CRLF, whitespace and long lines)
- [x] No-text and raster pages retained with explicit unreviewed warnings
- [x] Stale/tampered queues and registry changes block annotation
- [x] Exact text quote, page and offset; no invented quote or unsupported system feature mapping
- [x] Current registered reference bundle required, human-selected annotation only
- [x] No customer release, automatic training, field accuracy or code-compliance claim
- [x] Isolated deterministic synthetic tests pass
- [ ] End-to-end latest-branch full regression / live real report tests
- [ ] OCR, figures, reading order and tables understanding
- [ ] Authenticated qualified inspector validation and real holdout accuracy

**Internal review:** no independent agent runtime was available; tests use the old archived core and stub v1.6 validators in the isolated harness. GitHub latest-branch full-suite acceptance is pending, not asserted by focused tests.
