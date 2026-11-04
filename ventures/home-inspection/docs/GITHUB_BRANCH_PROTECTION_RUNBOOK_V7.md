# Home Inspection M5 V7 — GitHub administrator ruleset setup

**Owner action required. Not applied or remotely enforceable by this integration.**

Target repository: `ksolo21-web/K.O.-Enterprises` (public, development-stage)  
Target **exact** branch: `home-inspection-development`; do **not** apply these untested choices to `main`.

## Why this needs a real repository administrator

The V6 branch API reported `protected=false` and repository rulesets were empty; the branch protection administration endpoint returned **403 Resource not accessible by integration**. The CI job can detect source changes, but the current GitHub permission set **cannot require reviews or prevent direct pushes**.

The revised V7 event policy removes **pull-request file-path filters** from the two inspection workflows, because GitHub documents that skipping a required workflow due to path filters leaves a check Pending and blocks merging. Pushes to the development branch remain path-filtered to avoid unrelated reruns. Official reference: https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks

## Suggested active ruleset for the inspection development branch

Go to the repo's **Settings → Rules → Rulesets → New branch ruleset**, target only `home-inspection-development`, and set enforcement to **Active** (where the current GitHub plan and permissions allow). Follow official instructions: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository

- **Require a pull request before merging.**
- **Require at least one actual approving review from a distinct, authorized person** and, if supported, **dismiss stale approvals** after new commits; require approval of the most recent reviewable push. Automated self-review is *not* a distinct reviewer.
- **Require successful status checks** for exact job contexts `m3-v8-regression` and `synthetic-quality`, from the GitHub Actions app. The ordinary repository job `Python 3.12 safety and unit tests` may also be required if it is consistently triggered for every target PR. Review current names in PR #24 before selecting; workflow display names differ from check/job context names.
- **Require branch up-to-date with the base branch** for the strictest status-check policy, provided it fits the team's workflow.
- **Block force pushes and deletions**, prevent code-author/reviewer bypass as far as available, and do not add blanket admin exemptions for the automated account.
- Do not enable merge queues until required workflows separately handle the `merge_group` event (not enabled today).

Official details: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

## Required post-configuration independent acceptance

1. Reconfirm the branch ruleset is **active**, its target matches the intended development branch, and no bypass authority invalidates the approvals.
2. Open a **new harmless PR** and show that both job contexts are required and successful. Open a harmless root-only change to confirm job checks are not skipped by path filtering.
3. Verify a PR containing a deliberately invalid *synthetic* safety fingerprint fails the required `synthetic-quality` check. Do not use actual client media or real qualifications.
4. Verify merging without the required independent reviewer is **blocked**. Have a genuinely distinct qualified reviewer evaluate the code and changes, then verify GitHub's enforced reviewer state. Never approve the same changes using multiple accounts controlled by one individual.
5. Verify a direct push to the protected branch is rejected in a controlled, non-destructive exercise, and that there is a documented recovery route if a ruleset is misconfigured.
6. Record the GitHub ruleset ID, effective rules, reviewer and CI audit. Treat untested settings as blocked, not completed.

No branch ruleset, evidence signature, independent code review, qualified inspector or field operations approval is created by this document. Keep `PAUSE_AUTONOMY`, `main` and customer-release blocking untouched.
