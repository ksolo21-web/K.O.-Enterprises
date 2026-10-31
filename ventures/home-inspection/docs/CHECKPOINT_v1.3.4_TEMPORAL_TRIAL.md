# Home inspection v1.3.4 — temporal-video synthetic trial hardening

Status: SOURCE IMPLEMENTED; LOCAL TESTS PASSED; LIVE VISION RUN NOT EXECUTED.
Date: 2026-10-30 (Detroit), with remote branch state checked during this development turn.

## Why this change was necessary

The previous public-safe fixture generator made its MP4 by looping one static photograph. It allowed exercising frame extraction and provider interfaces, but a model's `video_still` request could not be shown to depend on changing video evidence. That is inadequate as a proof of meaningful video analysis.

## Implemented changes

1. Generate a four-second synthetic house video with temporally distinct content: an orange square in the first half and a blue circle in the second half. Each frame is generated from the existing original synthetic drawing; no customers, copyrighted third-party videos or private evidence.
2. Sample two temporally separated representative frames and compare downsampled pixel values with a compression-tolerant difference test. Refuse a synthetic trial that provides no material temporal variation.
3. Extend the acceptance JSON to record `synthetic_video_temporal_change_verified`, and block full synthetic acceptance if that evidence is absent.
4. Add tests for actual decoded video frames, repeatable source generation, a still loop rejection, minor pixel noise, and a deliberately missing video-content variation claim.
5. Inspect representative decoded frames at 0.25 s, 1.25 s, 2.25 s and 3.25 s in a four-panel local contact sheet. Orange-square and blue-circle halves were visibly distinct as intended.

## Evidence

- Local source was based on the verified v1.3.1 source archive. Original versions of all four modified production/test files had matching Git blob SHA-1 against `home-inspection-development` before edits.
- Full local regression: **179 tests run, 179 passed** (previous archive baseline: 172; seven additional tests). Python dependencies and FFmpeg available locally.
- This suite was run against the local archive plus this patch, not a fresh remote GitHub checkout. The development branch already had one further prerequisite-ordering test since v1.3.1, which is not included in the local total. Do not represent 179 as a remote Actions pass.
- Synthetic video challenge is not a proof that any vision model selected the correct time, noticed the changed pixels or evaluated actual home defects. The model runtimes are still unexecuted for this trial.

## Governance and release gates

- No GitHub Actions trial was started in this update. Previous one-time A01/A02 authorizations were consumed; their triggers have been removed.
- The K.O. Enterprises root `PAUSE_AUTONOMY` stays in effect; `main` is unchanged. No customer photos, video, reports, secrets, or payments were processed.
- Professional field accuracy, live inference, genuine independent reviewer execution, and qualified human signoff all remain **UNVERIFIED / BLOCKED**. Customer release remains forbidden.
- Next executable step (after separate owner authorization): rerun a one-time synthetic-only GitHub CPU trial with both FFmpeg and zstd provisioned at the start; require the accepted temporal-video result alongside four live image-conditioned probes, native zoom requests and separate Q02 model output. Revert the temporary one-shot workflow afterward.

## Internal review

This is an internal review, not a separate critic agent. The actual code was tested, generated PNG/video was decoded at multiple timestamps, and the output collage was visually inspected. No standalone professional inspector assessed this synthetic material.
