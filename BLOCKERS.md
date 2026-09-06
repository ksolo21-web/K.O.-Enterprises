# Blockers

Only genuine external blockers belong here. Ordinary implementation work, untested hypotheses, and missing nice-to-have infrastructure are not blockers.

## Founding-build blockers

None currently recorded.

## Expected future approval gates (not current blockers)

The first customer-facing validation test will require a specific proposal and CEO approval before publication, outreach, deployment, credential use, or spend. Legal-entity formation, domains, billing, production hosting, and payment accounts remain deliberately out of scope until evidence justifies them.


## Current commercial / OANDA connections — 2026-09-06

- Taking payments: Stripe is connected, tools are exposed and account listing succeeded. The owner has not selected the account/context requested by the integration; account-specific capabilities remain unverified. No checkout exists. Do not request connection again. The active prepared offer is the $49 Detailer Promo Pack; ImportScope checkout work is paused. Actual seller/terms/tax configuration and compatibility with the $0 mandate remain unresolved.
- First buyer test: the creative sample and sales-message draft are complete, but no permitted placement or sender/channel is verified. Developer rules require an explicit external-send instruction before messaging others. This blocks sending, not artifact preparation. Do not substitute repeated building for missing distribution.
- Public Site access: the ImportScope preview remains owner-only. The Sites access operation requires an explicit request for the proposed public audience.
- Measured repository reach: the current GitHub reader does not support the traffic endpoint. The prepared reach test has no verified observable traffic source and has not started.
- OANDA practice data: Kaleb reports adding a demo key. Secret names and values cannot be verified through this GitHub connection, no OANDA variables are present locally, and the repository run list contains no OANDA run. The manual workflow expects `OANDA_DEMO_TOKEN` and `OANDA_DEMO_ACCOUNT_ID`. The connection can read results but exposes no dispatch action; the owner can run it in GitHub Actions. No broker reads or orders occurred here.

See `docs/ventures/importscope/LAUNCH_REQUIREMENTS.md` and `CHECKOUT_ACTIVATION.md` in that folder. These block the specified external actions, not routine development. A bounded coding-bounty screen found no verified eligible task; that is an opportunity-screen result, not a new account-access blocker.
