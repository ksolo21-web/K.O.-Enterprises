# v0.7 — Milestone 2: read-only second-pass technical critique

The verified local coordination layer now includes a **separately invoked Q02 technical-review provider**, with the original image and a native-pixel crop supplied together. Q02 may classify a specialist's draft as visually plausible, not supported, or insufficient evidence, but it cannot certify a defect or approve a report. All claimed review outcomes remain provisional until a qualified inspector reviews actual source evidence.

**Actual verification:** 104/104 local automated tests; two SCRIPTED technical-review cases marked insufficient evidence; one page of a synthetic internal QA record visually reviewed. No real vision model was run. This is not evidence of reliable defect detection or a running independent agent. The source is not pushed to GitHub.

New commands (requires TWO separately installed local vision-capable models, not supplied or tested here):

```bash
python -m inspection_engine agents-critic private_case/staged.json --dossier private_case/writer_dossier.json --review-model REVIEWER_MODEL --out private_case/second_pass.json
```

See `REVIEW_PROTOCOL_M2_v0.7.md`, `ACCEPTANCE_M2_v0.7.md`, `CHECKPOINT_M2_v0.7.md`. Reproducible regression tests are in `tests/test_critic.py` and `tests/test_model_transport.py`. The `.github/workflows/validation.yml` is prepared but has not run on a remote GitHub repository. **Never commit real customer evidence to GitHub.**

---

# Home Inspection Intelligence — v0.6 specialist coordination

**2026-10-30 | Engineering prototype; NOT a real inspection and NOT autonomous production software.**

New Milestone 2 implementation: eight specialist role configurations (13 systems), M00 work-order dispatcher, bounded agent-directed native zoom and video-photo requests, deterministic Q01/Q02 evidence/scope checks, fully traceable proposals, and an optional local Ollama vision-model interface. No real vision model was installed or run for this delivery; the demonstration uses disclosed scripted responses. Findings remain review-pending.

- `MILESTONE_2_AGENT_ORGANIZATION.md` — approved reporting structure, delegated authority and next work.
- `ACCEPTANCE_M2_v0.6.md` — tested vs untested, release conditions.
- `CHECKPOINT_M2_v0.6.md` — recovery checkpoint.
- `inspection_engine/agents.py` — working dispatcher, specialist evidence tools, Q01/Q02 contract checks.
- `scripts/build_m2_specialist_demo.py` — deterministic two-work-order replay: zoom + video still.
- `output/m2_specialist_demo/` — synthetic PDF, work-order plan, agent dossier and unapproved project.

**Verification:** 85/85 regression tests passed (64 retained + 21 new), one native video photograph pixel-compared to original video, seven PDF pages rendered without out-of-page text. Production release remains blocked: no live model run, no real property/inspector benchmark, no independent AI technical critic, no customer identity/consent controls, no dedicated GitHub repository.

### Milestone 2 commands

```bash
python -m unittest discover -s tests -q
python -m inspection_engine agents-plan examples/v05_photo_from_video/01_video_photos_and_zoom_project.json --media-ids P0001 P0002 V0002
python -m scripts.build_m2_specialist_demo
```

### Earlier v0.5 notes (preserved)

# Home Inspection Intelligence — v0.5 video still-photo capture (extends v0.4 native zoom)

**2026-10-30. A local engineering prototype — NOT autonomous home inspection software or a client-ready inspection service.**

Continues the approved home-inspection business concept and its **Option 2 editorial navy/white report**, photo-only/video-only/mixed intake, major property characteristics including no-defect sections, HVAC/water-heater date research, quality reviewers, and approved-example learning concept. All earlier report/style requirements remain in force; this update does not substitute a new aesthetic or company structure.

## Milestone 2 addition: source-pixel zoom for specialist agents

**Implemented and exercised with synthetic evidence.** Agents may request any valid native-resolution crop of original photos, 1–32 overlapped tiles per batch, or additional close-ups automatically derived from unverified candidate bounding boxes. This is iterative with no arbitrary digital zoom multiplier, but detail is always limited to original source pixels. For video zoom, native frames are decoded from the actual video rather than enlarging the 1280-pixel convenience still. Every close-up retains original media ID, exact normalized/pixel coordinates, hash, agent requester and purpose, and video time. Source-pixel equality is re-verified before feeding a crop to a model. Model crop coordinates are mapped to the full source and every proposed finding remains `review_pending`.

The approved Option 2 PDF can show **context and source-native detail side-by-side**, with evidence IDs. **54/54 baseline tests passed in v0.4**, including video-resolution, tamper/forgery and iterative auto-zoom tests. Synthetic eight-page example at `output/m2_option2_native_zoom_editorial.pdf`; demonstration overview `output/m2_zoom_overview.png`. No actual vision model/real inspection used; no live AI detection claims.

See `ZOOM_NATIVE_SOURCE_SPEC.md`, `MILESTONE_2_ACCEPTANCE.md` and `CHECKPOINT_v0.4.md` for commands, dependency-aware tests, open blockers, and a resumable checkpoint. No new external accounts/services are required to run deterministic tests.

## This milestone's functioning features

- A **local CLI** copies JPEG/PNG/WebP or playable videos into a project-specific evidence folder. File extensions, content, dimensions, media duration, size, provenance, SHA-256 and rollback for invalid batches are checked.
- FFmpeg/ffprobe produce **timestamped stills from videos** with exact decoded `pts_time`, source video ID/hash and time. Sampling explicitly **does not** constitute full-video review.
- An **optional, explicitly invoked local Ollama image adapter** takes single photographs/derived frames and requests structured candidate notes. It is configured for `127.0.0.1`; no hosted model or external cloud is used.
- Deterministic reviewer-pending proposal validation rejects unknown specialist codes, nonmatching hidden areas, bad bounding boxes, overlong text and absolute safety/defect-free claims. This catches known bad outputs, **not all AI hallucinations**.
- A local mock-provider test and a **fully disclosed human-authored synthetic replay** exercise the same proposal-to-report path. They do not prove image recognition.
- Draft observations are evidence-linked and **cannot become human-verified through this adapter**. A model-suggested concern goes to human review; no definitive defect or safety conclusion is established.
- The approved five-page photography-led PDF can append one or more restrained **Visual Evidence Review** pages, keeping every proposed note traceable.
- The original structured human/reference comparison, manufacturer research, thirteen-system profile and draft-release gates remain in place.

## Install and test

Python **3.12+**, Pillow, ReportLab, pypdf (regression checks), and FFmpeg/ffprobe (system executable). No external API account is needed for the baseline test. A downloadable local vision model is optional and needs a compatible computer with sufficient RAM/GPU.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m inspection_engine audit examples/m1/04_provisional_project.json
python -m inspection_engine report examples/m1/04_provisional_project.json \
  --out output/my_synthetic_report.pdf
```

To rebuild the synthetic proof (requires FFmpeg):

```bash
python -m scripts.build_m1_demo
```

**Provenance:** `examples/m1/` has generated illustrations, an FFmpeg test-pattern clip, captured stills and manually scripted sample predictions. No model produced those predictions, and no real property has been inspected.

## Add real media locally (CLI)

Use a writable project directory and a project JSON copy using the schema in `examples/m1/00_baseline_project.json`. The destination JSON must share the same parent directory as its source so relative media paths continue to resolve. Never use `examples/m1` for actual private property evidence.

```bash
python -m inspection_engine intake private_case/project.json \
  --area exterior --room 'front elevation' \
  --out-project private_case/intake.json /path/to/photo.jpg /path/to/video.mp4

python -m inspection_engine frames private_case/intake.json \
  --video-id V0001 --count 6 --out-project private_case/frames.json
```

The software copies and keeps media **locally**; original metadata and client identifiers may remain in source files. Do not commit the `private_case/` folder or deliver these drafts to customers. The intake CLI itself does not enforce authenticated user access or encrypted storage.

## Optional local model analysis

With a separately installed local Ollama server and a genuinely vision-capable model (no such model was installed or run in this build):

```bash
python -m inspection_engine analyze private_case/frames.json \
  --media-ids P0001 V0001-F01 --model <your-installed-vision-model> \
  --out private_case/proposals.json

python -m inspection_engine apply private_case/frames.json \
  --predictions private_case/proposals.json \
  --out-project private_case/provisional.json

python -m inspection_engine audit private_case/provisional.json
python -m inspection_engine report private_case/provisional.json \
  --out private_case/draft_report.pdf
```

`analyze` contacts **only** the local Ollama endpoint, using its documented image+JSON schema generation interface: https://github.com/ollama/ollama/blob/main/docs/api.md . There is no automatic fallback to online services. An absent server fails visibly. The local test suite uses a fake provider (structured fixture) and **does not establish compatibility with a particular model**.

## Scope and quality

- `MILESTONE_1_ACCEPTANCE.md` — formal checks, tested evidence and precise limitations.
- `CHECKPOINT.md` — all previously agreed requirements and resumption point.
- `docs/ARCHITECTURE_AND_ACCEPTANCE.md` — approved M00/M01/M02/M03/L01/T07/T08/Q01/Q02/human roles.
- `OPTION2_DESIGN_STANDARD.md` — approved visual standard, not an arbitrary AI report look.
- `output/m1_photo_video_evidence_editorial_demo.pdf` — synthetic 7-page example.
- `output/m1_report_contact_sheet.png` — all rendered pages at a glance.

**GitHub:** No dedicated repository exists in the connected account, and this source is **not pushed**. Use a dedicated, private repository rather than mixing actual customer media into an existing unrelated public repo. This source archive is prepared to commit after the repository is available.

## Added in v0.5 — photographs taken from videos

A specialist or inspector can save **full-resolution standalone photographs** from any selected time in an inspection video. Unlike the v0.3 representative 1280px sampling thumbnails, these are native decoded PNGs with dedicated photo IDs, original-video hashes, actual timestamps and full report integration. They support the v0.4 progressive native zoom and are individually usable for local model analysis. Video-photo integrity can be independently checked through a pixel-for-pixel re-decode.

See `VIDEO_PHOTOS_FROM_FOOTAGE_SPEC.md` for CLI commands and guarantees, and `scripts/build_video_photo_demo.py` for the fully disclosed synthetic demonstration. No installed image recognition model, production sub-agent orchestrator, mobile video UI, or real inspection has been validated. Existing specialist review/approval gates remain required.

**Current acceptance:** 64/64 v0.5 regression tests pass, 3 native PNG stills deep-pixel-verified against source video, and 9/9 Option 2 report pages rendered and checked. See `ACCEPTANCE_v0.5.md`.
