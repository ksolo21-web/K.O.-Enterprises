# P0 — Repository-wide GitHub Actions broker-workflow containment

**Checkpoint:** 2026-11-09. **Mandatory security blocker, not CE production approval.**
**Code availability is not evidence that GitHub Actions has actually been disabled.**

## Verified incident scope and why main does not protect old refs

GitHub branch metadata query on 2026-11-09 returned **88 branch refs**, all reported \`protected=false\`; this does **not** determine the effective org/repo rules. The current repository workflow-folder listings were reviewed for all 88 branch names (including legacy docs, geodata, territory, home-inspection and venture branches). Many branches still reference the exact same unguarded broker workflow **Git blob IDs**, despite the main branch having early emergency-pause guards.

Five common unsafe legacy workflow definitions were opened and examined on \`docs/companywide-competitive-advantage-standard-20261105\`:

| Workflow file | Unguarded original Git blob SHA | Broker secret referenced? | Manual dispatch? |
|---|---|---|---|
| \`oanda-forward-scan.yml\` | \`580bf46c2f81e451aa127daab9de82e04a3df22a\` | Yes | Yes |
| \`oanda-fresh-tournament.yml\` | \`4cb7be3ba8a680c964d3c0fb6bf360627fa19994\` | Yes | Yes |
| \`oanda-practice-research.yml\` | \`a1d9d3c539ce8ec678d3bfb3d5d43cfdf9b080a7\` | Yes | Yes |
| \`oanda-wave3-preholdout.yml\` | \`74dee8cec6cc262f550b4628bd3a5299c863f806\` | Yes | Yes |
| \`oanda-wave4-preholdout.yml\` | \`815530b28a923d3e755e5b8db342c84b4cec412b\` | Yes | Yes |

Additional original variants without the guard existed under \`fix/oanda-credential-forensics-v2\`, \`fix/oanda-account-id-validation\`, \`venture/payment-workflow-screen\` and \`fix/oanda-practice-risk-reconciliation-20260908\`. The branch workflow directory scan also saw a legacy \`oanda-guarded-continuation-check.yml\` absent from main. The **source code** exposure is verified; **actual Actions dispatchability, token validity, secrets scope, environment protections, and runtime privilege are NOT verified** by these read-only GitHub source inspections.

Avoid running any unguarded broker workflow as a test. No broker token, network trading request or account ID was obtained.

## Prepared manual admin containment, not executed

The new source \`src/company_os/github_broker_workflow_containment.py\` and **manual-only** \`.github/workflows/p0-owner-disable-oanda.yml\` provide a repo-wide mitigation to disable the **five registered** OANDA workflow IDs, rather than trying to patch the same workflow definition individually across dozens of historical refs. GitHub's Actions workflow enable/disable operations apply to registered workflow IDs at repository scope.

The owner-triggered workflow:

1. Exposes only \`workflow_dispatch\`, with default option \`CANCEL_NO_CHANGES\`. A deliberate selection of \`DISABLE_ALL_FIVE_OANDA_WORKFLOWS\` is required. No scheduled or push invocation can disable anything.
2. Permits only repo owner actor \`ksolo21-web\`, default \`main\` branch, exact repo identity, Actions event and matching input/explicit process opt-in. Requires the original \`PAUSE_AUTONOMY\` file and literal \`PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False\`.
3. Uses a short-lived GitHub Actions \`GITHUB_TOKEN\` scoped to \`actions:write\` and \`contents:read\`; **does not load OANDA secrets** or client data. It never uses GitHub broker workflows.
4. Reads the registered workflow inventory; rejects missing/duplicate target files, unknown OANDA/broker workflows, extra pagination, invalid IDs/states and changed preflight records **before** disabling any workflow. Restricts all API operations to literal allowlisted workflow metadata and \`PUT .../disable\`; **never invokes /enable**.
5. Attempts to disable the five exact registered workflow IDs (skipping ones already disabled). Verifies each ID and its final \`disabled_manually\`/\`disabled_inactivity\` state, then re-reads the registered inventory. A partial GitHub failure must report **BLOCK** and require manual reconciliation; it cannot return success.
6. Reports what changed and explicitly states that it has **not** audited all tags, legacy-only workflow registrations, secret/env scope, other repositories or non-Actions channels. **No production launch authority is granted.**

**Activation remains owner-controlled:** on GitHub, open **Actions → P0 owner-approved disable of registered OANDA Actions → Run workflow**, select **main**, then explicitly select **DISABLE_ALL_FIVE_OANDA_WORKFLOWS**. Run only after the CEO authorizes the repository-wide change and confirms any business impact. The action can be re-run idempotently.

**Do not interpret adding this workflow or passing mocked tests as completed containment.** GitHub repository permissions and Actions workflow states must be observed after the owner invokes it. The GitHub connector in this chat cannot inspect actual repository Actions admin settings/secrets or perform a verified admin disable directly.

## Acceptance and remaining blockers

- [ ] New owner-only workflow and allowlisted transport pass GitHub CI on exact PR head.
- [ ] 21 offline tests exercise successful synthetic disable, retry idempotence, unauthorized actor/ref/event/confirmation, missing pause/lock, unknown registered workflows, wrong status, changed preflight, partial API failure and prohibited API endpoints.
- [ ] Exact PR-head document quality and existing release-surface no-go audit succeed.
- [ ] Internal review, fix/retest, merge and verify \`main\` still paused.
- [ ] **Owner separately approves and runs** the manual control. Independently verify all five *real* GitHub registered workflow states are disabled using admin-authorized access and verify effective credentials/env exposure. No approval is implied by PR merge.
- [ ] Complete remaining *all-ref* audit across branch worktrees, tags, legacy-only workflows, historical rerun cases, protected environments, fork/PAT dispatch surfaces and adjacent repositories; revoke/rotate any exposed OANDA credentials with account-owner authorization.
- [ ] Demonstrate no-bypass across remaining commercial channels with safe no-secret denial, independent reviewer and audit evidence. **Do not close P0 issue #61 or lift production pause until all required external evidence exists.**

Related: [P0 issue #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61), [Competitive Engine #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38), [CE-1M baseline](CE1M_REPRODUCIBLE_ORIGINAL_PDF_RENDER.md). This increment is a release-safety blocker reduction only; it does not change CE-1L/CE-1M critic authenticity or launch readiness.
