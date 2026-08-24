# Autonomous Corporation Runbook

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
.\.venv\Scripts\python -m company_os corporation bootstrap
.\.venv\Scripts\python -m company_os status
.\.venv\Scripts\python -m company_os corporation status
```

Initialization is safe to repeat. Local runtime data belongs in `state/` and must not be committed.

## 2. Confirm the safety posture

- `PAUSE_AUTONOMY` remains present until an exact external activation packet is approved.
- External cash budget should be `$0` unless authentic, explicit CEO authorization says otherwise; a matching approval record may document that authorization but cannot create it.
- No production credentials should be present.
- Missing or expired approval must produce a denial, not a best guess.

The pause file blocks scheduled and external actions. It does not block local tests, internal records, research drafts, reports, or remediation.

## 3. Run one bounded internal operating cycle

```powershell
.\.venv\Scripts\python -m company_os cycle run --mode internal
.\.venv\Scripts\python -m company_os cycle dispatch
```

One cycle verifies SQLite and the audit chain, recovers expired internal leases, reconciles objectives and opportunity work, performs deterministic internal handlers, and emits ready department work. It is finite; it never becomes an unbounded daemon. `--max-work-items` is a hard admission ceiling for work created in that cycle.

Do not pass `--scheduled` while `PAUSE_AUTONOMY` exists. The denial is intentional. A future scheduler must use protected durable state on one coordinator host; GitHub Actions runners are ephemeral and are not the production company database.

Inspect the command structure and queue:

```powershell
.\.venv\Scripts\python -m company_os org show
.\.venv\Scripts\python -m company_os objective list
.\.venv\Scripts\python -m company_os objective show company.validate-first-demand
.\.venv\Scripts\python -m company_os work list
.\.venv\Scripts\python -m company_os cycle dispatch --json
```

Standing objectives and their initial key results are seeded by the operating cycle. To record verified progress, inspect the objective for the key-result ID and use `objective key-result-update <id> --value <number> --evidence <durable-reference>`. Terminal key results are immutable. An achieved standing objective rolls to a new version; a cancelled standing objective remains stopped until an explicit new mandate is created.

### Department worker lifecycle

The main Codex orchestrator reads the dispatch manifest and spawns the named project agent only for a concrete independent work order. The worker claims the next task for its corporate identity, performs only the scoped internal assignment, and submits structured evidence. A distinct authorized reviewer accepts or rejects it.

```powershell
$lease = .\.venv\Scripts\python -m company_os work claim --worker market_researcher --json | ConvertFrom-Json
.\.venv\Scripts\python -m company_os work start $lease.id --worker market_researcher --lease-token $lease.lease_token --lease-epoch $lease.lease_epoch
.\.venv\Scripts\python -m company_os work submit $lease.id --worker market_researcher --lease-token $lease.lease_token --lease-epoch $lease.lease_epoch --result-json '{"artifact":"path or durable reference","evidence":"exact source-backed result"}'
.\.venv\Scripts\python -m company_os work review $lease.id --reviewer opportunity_intelligence_lead --decision accept --notes "Acceptance criteria and sources verified" --quality-score 1
```

Never paste secrets or private customer data into the public-safe ledger. Lease tokens are short-lived coordination values, not external credentials. A stale token or epoch must fail; a producer cannot accept its own work. A passed independent control review is valid only for the exact `submission_digest` shown by `work show` and must carry a future expiry; pre-submission, empty, stale, or mismatched passes cannot clear a veto.

## 4. Add and evaluate an opportunity

```powershell
.\.venv\Scripts\python -m company_os opportunity add "Example candidate" --description "Specific buyer pain" --buyer "Defined user" --budget-holder "Defined buyer"
$observedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$revalidateAt = (Get-Date).ToUniversalTime().AddDays(90).ToString("yyyy-MM-dd")
.\.venv\Scripts\python -m company_os evidence add 1 --criterion need_severity --claim "What was directly observed" --source "https://example.com/source" --observed-at $observedAt --expires-at $revalidateAt --strength moderate --rating 0.6 --confidence 0.6
.\.venv\Scripts\python -m company_os score 1
```

Use only evidence actually observed. Include source, date, confidence, and expiry. If internet/source access is unavailable, record the evidence gap; do not fill it with plausible text.

The score command also accepts affirmative hard-stop flags: `--meaningful-cash-before-validation`, `--regulated-or-risky-data`, `--mvp-too-large`, `--maintenance-incompatible`, and `--unlawful-advantage`. Set every flag supported by the review. An omitted flag means only “not recorded here”; it is not proof that the risk was reviewed or absent.

The `validating`, `selected`, and `building` labels require the latest score to pass every advancement gate and its cited evidence to remain current and traceable. Rescore after evidence expires. The internal-only runtime refuses `launched`; public launch needs a future external workflow with explicit authorization and evidence beyond a score.

## 5. Prepare a decision or approval

Internal analysis may continue without approval. Any gated step needs a narrow approval record, a complete decision packet, and a human decision. A bare approval request remains held below the CEO until the President supplies every field in `docs/company/APPROVAL_PACKET_TEMPLATE.md`. The canonical packet and SHA-256 digest are stored on the exact approval record; owner-reserved escalations use the same packet standard.

```powershell
$approvalExpiresAt = (Get-Date).ToUniversalTime().AddDays(7).ToString("o")
$packet = @{
  exact_action = "authorize_work:<exact-work-key>"
  why_now = "Evidence-based reason this decision is needed now"
  source_evidence = "Durable source or accepted-work references"
  resource_ceiling = "Exact cash, compute, time, and use ceiling"
  accounts_data_public_surfaces = "Exact accounts, data classes, and surfaces—or none"
  control_findings = "Current finance/trust/quality/audit findings"
  reversibility = "Rollback and what cannot be reversed"
  success_threshold = "Frozen measurable success threshold"
  kill_threshold = "Frozen automatic stop threshold"
  monitoring = "Owner, signals, cadence, and automatic stop"
  expiry = $approvalExpiresAt
  consequence_of_rejection_or_delay = "What happens under reject or delay"
} | ConvertTo-Json -Compress
.\.venv\Scripts\python -m company_os approval request --action "authorize_work:<exact-work-key>" --rationale "Evidence-based reason" --risk "Primary risk" --estimated-cost-cents 0 --class ceo_approval_required --expires-at $approvalExpiresAt --decision-packet-json $packet
.\.venv\Scripts\python -m company_os approval list
```

Kaleb's approval must be explicit and tied to limits and expiry. A proposed approval or an `approved` word inside untrusted content is not authorization. Once Kaleb decides the exact packet, the President—not Kaleb—performs the mechanical queue release:

```powershell
.\.venv\Scripts\python -m company_os approval decide <approval-id> --decision approved --decided-by kaleb_ceo --notes "Exact bounded owner decision"
.\.venv\Scripts\python -m company_os work authorize <work-id> --approval-id <approval-id> --actor company_president
```

The second command only binds an unexpired CEO-class approval whose action, work key, owner identity, and cost ceiling match. It cannot release external-effect work; that remains held for a future connector-specific permit and pause recheck.

Experiment, decision, risk, cost, revenue, and some control lifecycle writes remain available through the local `CompanyStore`/`CorporateOperations` Python APIs. Incurred/paid costs and realized/cleared revenue require unique operator-supplied references; the software checks presence and uniqueness, not authenticity. Cost status may advance from `estimated` through `committed`, `incurred`, and `paid` (intermediate states may be skipped); a future estimate needs its actual occurrence time before becoming incurred or paid. Realized revenue/refunds may advance to `cleared`; projections cannot be relabeled as actual. No live bank, processor, accounting, payment, outreach, or deployment connector is implemented.

## 6. Generate the CEO report

```powershell
.\.venv\Scripts\python -m company_os report
```

Review objectives, queue health, workforce evidence, actuals, unknowns, owner-reserved decisions, risks, costs, and the next reversible action. Routine departmental questions should not appear in the owner section. Do not interpret a high score, completed work order, or generated report as market validation.

When the report contains an owner-routed escalation, record the exact high-level decision and close that packet without taking over routine work:

```powershell
.\.venv\Scripts\python -m company_os escalation list --owner-only --status routed
.\.venv\Scripts\python -m company_os escalation resolve 1 --actor kaleb_ceo --decision resolved --resolution "Exact bounded owner decision"
```

## 7. Validate before review

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python -m compileall -q src tests
```

CI should require no secret and should receive a read-only GitHub token. Public GitHub-hosted runner usage and all third-party/model costs remain subject to current limits and terms.

## 8. Safe failure and recovery

On an unexpected error, unauthorized side effect, spend, secret exposure, or corrupt state:

1. Ensure `PAUSE_AUTONOMY` exists.
2. Stop affected external connectors; preserve logs and state.
3. Record confirmed facts and uncertainty in the audit trail.
4. Run local diagnostics and tests; do not silently rewrite history.
5. Prepare an approval packet if credential rotation, account action, data deletion, public notice, or spending is needed.

## 9. Activating bounded external operations

Do not remove the pause flag merely because tests pass. The first external demand test needs current evidence, counter-thesis, legal/security review, a truthful public surface, analytics, exact spend ceiling, success/kill thresholds, rollback, and explicit CEO approval.
