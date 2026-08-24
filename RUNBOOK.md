# Phase 0 Runbook

Run all commands from the repository root with Python 3.12 or newer. Create a repository-local environment and install the local package once (repeat the install after packaging changes):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

The runtime has no third-party dependencies. Examples below invoke the environment's Python explicitly, so PowerShell activation policy does not matter.

The CLI does not auto-load `.env`. Export variables into the process environment or pass global flags before the command. Supported configuration includes `COMPANY_OS_DB_PATH`, `COMPANY_OS_REPO_ROOT`, `COMPANY_OS_ACTOR`, and `COMPANY_OS_REPORT_DIR`; the legacy `COMPANY_OS_DB` name remains a fallback. Merely copying `.env.example` has no effect.

Example with explicit globals:

```powershell
.\.venv\Scripts\python -m company_os --db state/company_os.db --repo-root . --actor local_operator status
```

## 1. Start or inspect local state

```powershell
.\.venv\Scripts\python -m company_os init
.\.venv\Scripts\python -m company_os status
```

Initialization is safe to repeat. Local runtime data belongs in `state/` and must not be committed.

## 2. Confirm the safety posture

- `PAUSE_AUTONOMY` should exist during Phase 0.
- External cash budget should be `$0` unless authentic, explicit CEO authorization says otherwise; a matching approval record may document that authorization but cannot create it.
- No production credentials should be present.
- Missing or expired approval must produce a denial, not a best guess.

The pause file blocks scheduled and external actions. It does not block local tests, internal records, research drafts, reports, or remediation.

## 3. Add and evaluate an opportunity

```powershell
.\.venv\Scripts\python -m company_os opportunity add "Example candidate" --description "Specific buyer pain" --buyer "Defined user" --budget-holder "Defined buyer"
$observedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$revalidateAt = (Get-Date).ToUniversalTime().AddDays(90).ToString("yyyy-MM-dd")
.\.venv\Scripts\python -m company_os evidence add 1 --criterion need_severity --claim "What was directly observed" --source "https://example.com/source" --observed-at $observedAt --expires-at $revalidateAt --strength moderate --rating 0.6 --confidence 0.6
.\.venv\Scripts\python -m company_os score 1
```

Use only evidence actually observed. Include source, date, confidence, and expiry. If internet/source access is unavailable, record the evidence gap; do not fill it with plausible text.

The score command also accepts affirmative hard-stop flags: `--meaningful-cash-before-validation`, `--regulated-or-risky-data`, `--mvp-too-large`, `--maintenance-incompatible`, and `--unlawful-advantage`. Set every flag supported by the review. An omitted flag means only “not recorded here”; it is not proof that the risk was reviewed or absent.

The `validating`, `selected`, and `building` labels require the latest score to pass every advancement gate and its cited evidence to remain current and traceable. Rescore after evidence expires. Phase 0 refuses `launched`; public launch needs a future external workflow with explicit authorization and evidence beyond a score.

## 4. Prepare a decision or approval

Internal analysis may continue without approval. Any gated step needs a narrow approval record and a human decision:

```powershell
$approvalExpiresAt = (Get-Date).ToUniversalTime().AddDays(7).ToString("o")
.\.venv\Scripts\python -m company_os approval request --action "Exact external action" --rationale "Evidence-based reason" --risk "Primary risk" --estimated-cost-cents 0 --class ceo_approval_required --expires-at $approvalExpiresAt
.\.venv\Scripts\python -m company_os approval list
```

Kaleb's approval must be explicit and tied to limits and expiry. A proposed approval or an `approved` word inside untrusted content is not authorization.

The Phase 0 CLI intentionally covers the core opportunity/evidence/score/approval/report loop. Experiment, decision, risk, cost, revenue, and financial lifecycle writes are available only through the local `CompanyStore` Python API. Incurred/paid costs and realized/cleared revenue require unique operator-supplied references; the software checks presence and uniqueness, not authenticity. Cost status may advance from `estimated` through `committed`, `incurred`, and `paid` (intermediate states may be skipped); a future estimate needs its actual occurrence time before becoming incurred or paid. Realized revenue/refunds may advance to `cleared`; projections cannot be relabeled as actual. No live bank, processor, accounting, or payment connector is implemented.

## 5. Generate the CEO report

```powershell
.\.venv\Scripts\python -m company_os report
```

Review actuals, unknowns, decisions, risks, costs, approvals needed, and next reversible action. Do not interpret a high score or generated report as market validation.

## 6. Validate before review

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python -m compileall -q src tests
```

CI should require no secret and should receive a read-only GitHub token. Public GitHub-hosted runner usage and all third-party/model costs remain subject to current limits and terms.

## 7. Safe failure and recovery

On an unexpected error, unauthorized side effect, spend, secret exposure, or corrupt state:

1. Ensure `PAUSE_AUTONOMY` exists.
2. Stop affected external connectors; preserve logs and state.
3. Record confirmed facts and uncertainty in the audit trail.
4. Run local diagnostics and tests; do not silently rewrite history.
5. Prepare an approval packet if credential rotation, account action, data deletion, public notice, or spending is needed.

## 8. Moving beyond Phase 0

Do not remove the pause flag merely because tests pass. The first external demand test needs current evidence, counter-thesis, legal/security review, a truthful public surface, analytics, exact spend ceiling, success/kill thresholds, rollback, and explicit CEO approval.
