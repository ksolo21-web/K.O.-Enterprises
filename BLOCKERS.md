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
- OANDA practice authentication: resolved on 2026-09-07. The replacement token and configured account ID authenticated successfully against OANDA Practice, the read-only account summary was accepted, and 5,000 completed EUR/USD hourly bid/ask candles were retrieved for an ephemeral local simulation. No order endpoint was used and no trade was sent. The current fixed SMA20/SMA50 baseline failed its holdout test: all three 27-trade scenarios lost virtual money, ending at $49.0710 for 1% risk, $48.5361 for 2% risk, and $48.2502 for 5% risk from separate virtual $50 starts. OANDA access is therefore working, but the tested strategy is not approved for live trading or counted toward the subscription target. Broker-derived files were deleted at workflow completion.

See `docs/ventures/importscope/LAUNCH_REQUIREMENTS.md` and `CHECKOUT_ACTIVATION.md` in that folder. These block the specified external actions, not routine development. A bounded coding-bounty screen found no verified eligible task; that is an opportunity-screen result, not a new account-access blocker.
