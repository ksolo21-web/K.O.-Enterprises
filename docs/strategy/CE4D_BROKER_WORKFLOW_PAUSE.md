# CE-4D — Fail-closed GitHub broker workflow guard (engineering-only)

**Date:** 2026-11-06  
**Scope:** Five repository-local OANDA Practice research workflows.  
**Acceptance:** Source checks and remote CI only; this is **not** production certification or permission to perform external network operations.

## Observed defect and correction

The five OANDA broker-connected Actions workflows previously included credential-bearing token resolution and issuer API reads but no explicit `PAUSE_AUTONOMY` check **before** the credential-bearing steps. Their triggers included manual dispatch, and the forward Practice scan also has a push trigger on its feature branch. A read-only broker API call still needs to obey the global emergency stop.

All five workflows now perform a first-step, fail-closed check after source checkout and **before** secret references or broker scripts:

- A present repository `PAUSE_AUTONOMY` marker blocks immediately.
- A step-local `COMPANY_OS_PAUSED: "1"` is deliberately hardcoded so removing the marker alone cannot enable broker API calls.
- A future legitimate unpause requires separately reviewed source changes, real production/execution controls and appropriate CEO authorization. There is **no** override or automatic launch in this PR.

Affected workflows: `oanda-practice-research.yml`, `oanda-forward-scan.yml`, `oanda-fresh-tournament.yml`, `oanda-wave3-preholdout.yml`, `oanda-wave4-preholdout.yml`.

`tests/test_ce4d_broker_workflow_pause.py` scans all broker-marked workflow YAML, requires early denial, pins the known set of workflows for change review, and checks removal/reordering/weakening failures. The tests are static source checks; GitHub job execution remains an external execution surface.

## Evidence and limitations

- `main` HEAD inspected at `9772daeee7e46b4c7c5e19a958da888f5233bf67`. GitHub reports `main.protected=false` and branch protection disabled; the repository rulesets list was empty. **This is a separate P0 administrative blocker.**
- The previous CE-4C scan reported 42 files, 11 potential-execution files, 83 indicators. Heuristic flags are not independent no-bypass proof.
- Only the five workflow files are changed in this patch; this does **not** govern manual GitHub dispatch from other branches, external SaaS dashboards, plugins, browser actions, unknown repositories, production hosts, trading infrastructure, or non-GitHub credentials.
- GitHub administrators must establish an independently enforced repository ruleset / branch protection: PR-only changes, separate required reviewer, required successful CI and document checks, restrictions on bypass and changes to `.github/workflows` plus control-plane security files. Verify protected status from GitHub itself after configuration.
- No broker secrets are read or changed, no trade is placed, no customer data accessed, and no external workflow is executed by this patch.
- **No change** to `PAUSE_AUTONOMY`, `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`, CE-1–CE-5 production acceptance status, CEO authority or release-controller certification.

## Remaining evidence before any launch

1. Approved always-on protected runtime with externally observed restart/recovery, key custody and protected audit evidence.
2. Lawful authenticated original issuer, competitor and buyer evidence; complete dynamic addenda discovery and source-rights checks.
3. A genuinely separate authenticated original-source/PDF factual and visual critic passing 12/12, strictly over 9.0, with immutable proof.
4. Every actual side-effect connector behind a protected atomic controller; independent no-bypass tests across GitHub, host, browser, SaaS, payments and messaging.
5. An authenticated, scoped owner acceptance after compliance, privacy, budget and incident-review gates. Emergency pause and hard production lock remain until those conditions are genuinely met.

**Disposition:** internal hardening only. **NO-GO** for production, sales, marketing, broker-connected research while paused, or any K.O. venture launch.
