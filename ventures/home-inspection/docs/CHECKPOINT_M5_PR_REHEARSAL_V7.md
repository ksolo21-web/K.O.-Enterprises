# M5 V7 — Live pull-request CI rehearsal (synthetic only)

**2026-11-04 · source branch:** `home-inspection-m5-pr-validation-v7`  
**Target:** `home-inspection-development` · **Business/customer release:** BLOCKED.

This branch intentionally changes only a harmless checkpoint document for the initial positive control. It is an actual GitHub PR rehearsal, not independent professional code review, approval, or user/media intake.

## Required rehearsal sequence

1. From V6's verified development checkpoint, create a draft PR changing only this documentation file. Ensure **both** real GitHub Actions workflows run with `pull_request` event and complete successfully at the expected PR head.
2. Check the PR quality workflow has **zero published synthetic QA artifacts**, as its `if: ... github.event_name != 'pull_request'` guard prohibits upload; verify the 16-page PDF was regenerated and the nine contract scenarios passed **inside the job**. Check the full inspection suite completes.
3. Make a disposable **invalid-source-registry-only** commit on this PR branch. It must fail the M5 change detector and full regression; never use actual media/PII or edit `main` or `PAUSE_AUTONOMY`.
4. Restore the exact approved registry contents in a new PR-branch commit (no force-push). Both PR workflows must pass again. Do not merge without actual independent review.
5. Record run IDs, Git commit SHAs, PR check conclusions and any limits in the development README and formal V7 checkpoint, without treating missing administrative branch protection as fixed.

## Mandatory boundaries

No secret credentials, human inspector identity, paid service, or customer photo/video/report may enter Git. `home-inspection-development` is not yet protected by enforced branch rules; a green test on a PR **does not require developers to use PRs**. A draft PR and its self-authored code are not a separate independent critic. No production/model-accuracy or real professional approval is inferred.

**State:** rehearsal opened; outcomes pending actual CI evidence.
