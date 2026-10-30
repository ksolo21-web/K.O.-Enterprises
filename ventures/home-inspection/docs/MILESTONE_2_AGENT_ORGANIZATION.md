# Milestone 2: specialist organization and controlled evidence work orders
**2026-10-30 | v0.6 | local engineering prototype | never a field inspection**

## Approved chain of command, preserved

```text
Owner / CEO
  M00 Inspection Director (workflow/approval routing)
    Evidence & Knowledge Lead
      M01 intake and evidence custody
      M02 coverage and missing views
      M03 construction/system descriptions
      L01 learning and evaluation (future full-report ingestion)
    Technical Lead
      T01 site/drainage
      T02 foundation/support/subfloor/framing/crawlspace
      T03 exterior/roof
      T04 attic/insulation/ventilation
      T05 interiors/stairs/finishes
      T06 electrical
      T07 plumbing/water-heating + manufacturer reference requests
      T08 heating/cooling + manufacturer reference requests
    Report Lead
      factual and editorial composition of Option 2 report
  Independent controls (can stop release, not directed by Report Lead)
    Q01 evidence/custody/coverage reviewer
    Q02 technical-claim/scope reviewer
  Qualified human inspector: actual technical verification and final sign-off
```

These are **role configurations**, not independently running AI agents. `execute_specialists` uses one callable provider per assigned technical work order. Q01/Q02 currently run deterministic contract checks, **not** independent AI critique. This distinction is explicit in output JSON.

## New working implementation

1. `agents-plan` routes inspector-labeled photos/video frames to the responsible specialist; raw video is held as requiring frame selection. Unrecognized areas go to human triage, not fabricated scope.
2. `agents-run` can call an **already installed local Ollama vision model**; it supplies system-scoped prompts and strictly accepts `candidates` and one `request` per step.
3. Authorized requests: `zoom` (native source-pixel crop) and `video_still` (lossless native-resolution video photograph, timestamped).
4. Each role gets at most three model iterations per work order; no shell/network arbitrary action, purchases, external publication or changes in authority.
5. Native zoom crops and saved video stills retain source hashes, exact boxes, source video/time and evidence references.
6. Image candidates are validated by the original proposal contract and attached as `review_pending` only. Neither a specialist nor a contract critic can set `human_verified` or produce a customer deliverable.
7. Q01 checks source custody, hashes, zoom native pixel integrity and cited sources. Q02 checks delegated specialty and disallows absolute condition/safety assurances. **These checks do not prove the findings are true**.
8. M00 preserves a JSON work-order plan and event dossier; the approved Option 2 report generator consumes the resulting draft project.

## Operational boundaries

- Evidence images are processed locally. No customer photo/videos are uploaded to a public repo or remote AI by this milestone.
- A model is **not installed or executed** in the delivered fixture; tests call a disclosed deterministic/mock provider, not separate autonomous workers.
- Video frames are samples, **not** an exhaustive video inspection.
- No model may infer concealed structure, operation of an appliance, code compliance, absence of defects, or the true manufacture date from insufficient photos.
- A passed Q01/Q02 **contract check** never substitutes for a human inspector's findings.
- Customer identity, upload UI, consent, encrypted storage, retention, and legal/insurance review are not implemented.

## Resumable critical path

1. Install and connect a capable locally operated vision model; prove the specialist-request contract works under timeouts, schema deviations and actual images.
2. Benchmark against consented, qualified-inspector-annotated real photos/videos, with missed-defect and false-alarm metrics. Do not assert recognition accuracy from synthetic fixtures.
3. Add a true independent *technical critic* model or qualified specialist process, plus authenticated human approval and immutable audit.
4. Implement full-report learning and equipment manufacturer verification as bounded evidence tasks; never automatically absorb human report errors.
5. Secure customer-facing application and dedicated private GitHub repository/CI, followed by field and legal/privacy validation.

### Local commands

```bash
python -m unittest discover -s tests -q
python -m inspection_engine agents-plan examples/v05_photo_from_video/01_video_photos_and_zoom_project.json --media-ids P0001 P0002 V0002
python -m scripts.build_m2_specialist_demo
```

Live local Ollama use, **only after explicitly installing a compatible vision model** (model identifier is never presumed):

```bash
python -m inspection_engine agents-run private_case/project.json --media-ids P0001 \
  --model YOUR_LOCAL_VISION_MODEL \
  --out-project private_case/agents_pending.json --dossier private_case/agent_dossier.json
```

**All proposed findings remain internal drafts.** Do not send to customers as a completed inspection.