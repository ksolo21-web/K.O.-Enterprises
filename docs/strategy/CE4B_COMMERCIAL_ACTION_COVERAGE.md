# CE-4B — Expanded Commercial Release Action Coverage

**Checkpoint:** 2026-11-06 · **Status:** Internal code-level protection, not certified host-side no-bypass enforcement.  
**Changes:** `src/company_os/competitive_launch_guard.py`, `src/company_os/policy.py`, `tests/test_commercial_action_coverage.py`.  
**Prerequisite:** [CE-4A deny-only exact-release preflight](CE4A_COMPETITIVE_RELEASE_PREFLIGHT.md).  
**Emergency controls:** `PAUSE_AUTONOMY` remains active and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` remains the hard launch stop.

## Gap and implementation

The prior launch guard explicitly recognized launch, deploy and publish action prefixes. A new commercial channel could select a name such as `send_sales_proposal`, `advertise_business` or `create_payment_link` and thereby enter the ordinary approval policy without first checking competitive-engine readiness. This change extends the **canonical company policy** to catch and block these action families even when callers omit `external=True`:

- Customer-facing report delivery, sales proposals and quotes.
- Marketing email, public social promotion, advertising and solicitation.
- Checkout and subscription creation/activation, payment-link and invoice creation, storefront opening, new orders and charging new customers. The first CI run exposed an omitted `activate_subscription_service` alias; the rule and dedicated regression case were corrected before final acceptance.
- Unqualified generic email, SMS, direct messaging, proposal, contract and invoice-sending verbs. Explicitly named existing-customer transactional messaging remains governed under separate policy rather than being mistaken for a new launch.
- Existing generic launch, deployment, go-live, revenue-start and publishing actions.

Additionally, a **previously unknown action** marked as `external=True` now requires competitive-engine readiness, even if it presents a CEO approval or calls itself low risk. This is deliberately conservative until a real authenticated host can classify side effects.

**Explicit operational continuity and bootstrap exceptions** stay governed by their separate approval and emergency-pause rules: `deploy_competitive_engine` (the exact dedicated engine bootstrap action only), `call_approved_api` (approved bounded-source research may be needed to build the engine), `send_transactional_message` (existing lawful customer continuity), and `predefined_refund`. None is automatically approved, and the emergency pause still refuses external/scheduled calls.

## Negative tests

The new tests exercise dozens of exact and prefixed commercial verbs, uppercase and whitespace variants, fake `AUTO_ALLOWED` requests, missing engine health even with fabricated CEO approval, an unknown outbound verb with valid approval metadata, paused bootstrap/source actions, and accidental deletion of the root emergency marker or hard-coded production release lock.

## What this cannot prove

This is **name/metadata-based internal policy code**, not a protected release controller installed at all real execution boundaries. A connector that does not call `company_os.policy`, or one that dishonestly labels commercial work as permitted routine research/continuity, can still evade it. Actual production must use authenticated executor identities, capabilities and a complete side-effect inventory, not trust action strings or `external` booleans supplied by untrusted callers.

No branch protections, protected deployment environments, external audit anchors, genuine critic, or production monitor were enabled in this change. Real source verification and all business launches remain blocked. **Do not interpret passing unit tests as CE-4/CE-5 acceptance**.

## Next mandatory acceptance

1. Inventory **every actual** GitHub workflow, CLI, plugin/connector, outbound API, publisher, billing path and external deployment credential on the authorized production host. Bind each path to a privileged, atomic and signed release controller; verify exhaustively against bypass attempts.
2. Independently authenticate original sources and customer-demand evidence; operate the separate critic on genuine source content and rendered report pages with all twelve checks passing above 9.0/10.
3. Deploy on an explicitly approved protected and monitored environment with supervisor, secure key custody and externally anchored audit, then test outage and safe recovery.
4. Obtain explicit scoped CEO authority only after those controls and the complete operating cost/privacy/legal checks are demonstrated. Preserve emergency pause and the hard stop until then.

**Evaluation:** Internal code review plus GitHub CI only; a separate critic agent/runtime has not been exercised. A 10/10 company launch score cannot be awarded without real operational evidence.
