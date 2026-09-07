# Blockers

Only genuine external blockers belong here. Ordinary implementation work, untested hypotheses, and missing nice-to-have infrastructure are not blockers.

## Founding-build blockers

None currently recorded.

## Expected future approval gates (not current blockers)

The first customer-facing validation test will require a specific proposal and CEO approval before publication, outreach, deployment, credential use, or spend. Legal-entity formation, domains, billing, production hosting, and payment accounts remain deliberately out of scope until evidence justifies them.


## Current commercial / OANDA connections — 2026-09-07

- Taking payments: Stripe is connected, tools are exposed and account listing succeeded. The owner has not selected the account/context requested by the integration; account-specific capabilities remain unverified. No checkout exists. Do not request connection again. Detailer and ImportScope commercialization are paused; the Idea Panel has held the publisher build and selected no qualified product. Actual seller/terms/tax configuration and compatibility with the $0 mandate remain unresolved.
- First buyer test: no accepted distribution listing, verified audience or sender/channel exists. Developer rules require explicit authorization before messaging others. These affect external acquisition and do not prevent bounded internal demand research. A failed opportunity screen is a decision, not an external blocker.
- Public Site access: the ImportScope preview remains owner-only. The Sites access operation requires an explicit request for the proposed public audience.
- Measured repository reach: the current GitHub reader does not support the traffic endpoint. The prepared reach test has no verified observable traffic source and has not started.
- OANDA practice authentication: the owner-named secrets are present and reach GitHub Actions. A merged fixed-host, read-only forensic probe removes only harmless copy/paste wrappers and then tests the token against OANDA Practice. After Practice returned HTTP 401, the probe made one fixed read-only account-list request to OANDA Live solely to rule out an environment mismatch; Live also returned HTTP 401. The stored token is therefore not accepted by either environment and must be revoked and regenerated from the intended OANDA profile before any account ID or market data can be checked. Replace only `OANDA_demo_API_token` first. If the fresh token authorizes exactly one Practice account, the probe safely resolves that account without printing its ID; if it authorizes multiple accounts, `OANDA_demo_account_ID` must then contain the full matching v20 ID. No account data was retained, no order endpoint exists, and no trade was attempted.

See `docs/ventures/importscope/LAUNCH_REQUIREMENTS.md` and `CHECKOUT_ACTIVATION.md` in that folder. These block the specified external actions, not routine development. A bounded coding-bounty screen found no verified eligible task; that is an opportunity-screen result, not a new account-access blocker.
