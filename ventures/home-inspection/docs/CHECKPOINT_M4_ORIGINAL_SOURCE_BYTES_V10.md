# M4 V10 — original source-byte verification (engineering checkpoint)

Date: 2026-11-04. Branch: `home-inspection-development`. All evidence and all identifiers in tests are synthetic; real inspection inputs stay private and **out of Git**.

## New gate

`inspection_engine/m4_source_paths.py` validates private root, canonical relative locators, symlinks, regular-file properties, bounded SHA256 reads and decoded image pixels. `m4_source_byte_custody.py` validates a pre-pinned V9 manifest against the actual bytes of every photo, parent video and derived frame; video frames require PNG, a parent in the same case, a source-PTS match and exact pixel replay by fresh offline FFmpeg decode. All paths remain private. `scripts/m4_source_byte_cli.py` accepts two private JSON inputs and a prior independent hash pin, without writing a receipt file or uploading data.

**This does not prove** media were honestly captured, consent and jurisdiction, the independence of the pin-holder, model competence, a real defect, professionally authenticated labels or reviewer identity. V8/V9 frozen evaluation and human signed release gates remain separate and mandatory. `customer_release_allowed` remains false even on successful local byte checks. `PAUSE_AUTONOMY`, main branch and all existing threshold constants unchanged. JPEG previews of video do not count as exact video-frame replay; use lossless native frames.

## Checkpoints

- Baseline: V9, 1,044/1,044 historical synthetic tests, [V9 checkpoint](CHECKPOINT_M4_SOURCE_MEDIA_GROUNDING_V9.md).
- New V10 tests: synthetic original bytes, file substitution, altered image with updated hash, path traversal, symlinks, no locator, wrong pin, Git check, real lossless video parent/frame replay, wrong timestamp, missing parent, and changed frame pixels with valid recomputed hash.
- **V10 offline engineering regression VERIFIED:** 1,058 / 1,058 tests passed, including 14 V10 cases; compilation, M3 inherited tests and tracked-file integrity passed on source commit `f4a5ef1a32b3bfb31013696600f72d52a2a46d71` in [GitHub Actions run 41817691316](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41817691316). This is synthetic engineering validation, not real-world source authentication or defect recognition.

## Remaining Milestone 4 blockers

Genuinely independent protected evaluation pins/custodian, qualified inspector identity and issuer authorization, real privacy/consent documentation, professionally labeled held-out photos and videos, original serious-defect 100-case/30-critical/13-system benchmarks, zero missed major/critical defects, at least 95% human-adjudicated precision, and qualified human approval. These cannot be synthesized into completion.

Next: verify GitHub offline CI against exact V10 commit. Then begin Milestone 5 private pilot-readiness and business/field integration **without releasing customer reports**.
