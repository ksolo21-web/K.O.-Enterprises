# Algora bounty cash review — 2026-09-06

**Decision: a credible route to attempt useful work with $0 upfront spending; not yet a verified route to an obligation-free payout.** An accepted, sponsor-paid code contribution can generate a contributor reward. The inspected ordinary-bounty implementation adds fees to the sponsor's charge and credits the contributor's share without those deductions. This materially improves the initial cash case compared with operating a Gumroad product checkout. However, no connected account, funded award for Kaleb, accepted contribution or settled payment exists in this assignment. No source establishes a blanket guarantee against recovery or owner obligations.

Scope: bounded primary-source review under `ko-financial-advisor`; `AGENTS.md` and `docs/advisory/CURRENT_STATE.md` read. No signup, terms acceptance, claim, issue/PR submission, tokens, private-account access, messages, spending or money movement. Only this file was written. This is financial analysis, not a credentialed legal opinion.

## Three findings

| Finding | Evidence and confidence, observed 2026-09-06 | Revalidation |
| --- | --- | --- |
| Ordinary contributor work has no upfront charge in the inspected flow; ordinary bounty fees are added to the sponsor charge. | Official Algora code: [bounty payment construction](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/bounties/bounties.ex), [payment/transfer implementation](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/payments/payments.ex). High confidence in source behavior, medium in live applicability; deployment and account settings unverified. | Exact bounty and provider terms before claiming/connecting; otherwise 2026-09-13. |
| A listed reward is contingent, and acceptance does not establish bank cash. | Official [reward workflow](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/bounties/in-your-own-repos.md) has the satisfied sponsor proceed to checkout. [Payment documentation](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/payments.md) describes typical payout after payment. High for stated process; no claim-specific funding or acceptance probability established. | Bounty status, competing work and sponsor approval immediately before work/submission; reconcile each payment. |
| Zero recourse is unproven, but ordinary sponsor refunds must not be assumed to create Gumroad-like contributor bank debits. | [Stripe balance rules](https://docs.stripe.com/connect/account-balances), [transfer reversals](https://docs.stripe.com/api/transfer_reversals), [Connected Account Agreement](https://stripe.com/legal/connect-account), and [Algora terms](https://algora.io/legal/terms). High for published mechanisms; actual Algora configuration/contract allocation unknown. | Before payout enrollment or accepting award terms; any agreement/fee/configuration change. |

## Who pays the fees

The current public repository's main tree was `74a49d7728400152f5d640ac8d461e6664b7c2eb` when checked. This is primary implementation evidence, **not proof of the deployed revision or a contractual price quote**.

For ordinary bounties, `generate_line_items` adds a platform fee based on the sponsor's `fee_pct` and a transaction fee. The current [user schema](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/accounts/schemas/user.ex) defaults the platform percentage to 9%; `Payments.get_transaction_fee_pct` returns 4%. Sponsor overrides and legacy-bounty settings exist. The payer's charge contains the additional fees; contributor credits and subsequent transfers use their award share with `total_fee` zero. Marketplace contracts have different logic and are outside this ordinary-bounty conclusion. [Bounty code](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/bounties/bounties.ex), [payments code](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/payments/payments.ex)

Illustrative integer-cent calculation under those defaults, single contributor, before taxes/bank/FX/other account-specific deductions:

```python
award_cents = 10_000
sponsor_platform_cents = award_cents * 9 // 100
sponsor_transaction_cents = award_cents * 4 // 100
sponsor_charge_cents = award_cents + sponsor_platform_cents + sponsor_transaction_cents
contributor_credit_cents = award_cents
assert (sponsor_charge_cents, contributor_credit_cents) == (11_300, 10_000)
```

A hypothetical $100 award produces a $113 sponsor charge and $100 contributor credit in that scenario. It is not a $100 receipt today. A split award reduces the contributor's share. Optional accelerated payout, currency conversion, external-bank fees, withholding and negotiated account terms remain unverified; do not silently set them to zero. Historic 23% fee commentary is not a current quote.

## Funding, acceptance and payout are different facts

| Stage | Evidence required | Cash treatment |
| --- | --- | --- |
| Announced bounty | Current issue/award record and sponsor identity | Contingent opportunity; $0 receipts |
| Claimed/submitted solution | Genuine tested PR linked to the issue, permitted contribution | Work at risk; no guaranteed award |
| Accepted/merged or approved claim | Maintainer/sponsor decision and precise award/share | Acceptance evidence; payment still needs separate proof |
| Sponsor payment completed | Provider confirmation of successful collected payment | Payout entitlement/pending funds subject to applicable conditions |
| Transfer to contributor's Stripe balance | Matching transfer and enabled payout account | Distinguish pending from available platform balance |
| Settled bank payout | Bank receipt matched to provider payout | Actual received cash, still distinct from after-tax economic profit |

The official workflow lets the sponsor choose the satisfactory solution and pay at checkout; it does not prove every public bounty is prepaid escrow. Autopay settings or a merge alone do not establish successful collection. Current payment documentation says contributors typically receive payouts 1–3 business days after payment completes, not after posting a PR. It lists the US among supported countries and says missing required credentials can block payouts. These are provider expectations, not a guarantee for a new account. [Reward workflow](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/bounties/in-your-own-repos.md), [payments](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/payments.md)

Acceptance uncertainty includes another contributor winning, an already solved issue, changed scope, incomplete tests, license/CLA restrictions and the sponsor not paying. None has a defensible probability from this review. With an assumed $30/hour shadow value, three hours of work on a $100 paid award leaves $10 before tax and other costs; rejection leaves a $90 opportunity-cost loss while external cash spending can remain $0. No hourly rate, award or profit is promised.

## Reversals and exact limits of the cash conclusion

Algora's source charges the platform and later creates a separate transfer to the contributor, using `transfer_group`. Stripe initially assigns refunds/disputes to the account carrying the original charge. That supports an inference that sponsor chargebacks initially affect Algora's platform balance. It does not automatically make Kaleb the card merchant. Stripe also allows platforms to reverse transfers; its current API documentation restricts reversal of a `transfer_group` transfer to the destination's available covering balance. Thus the inspected ordinary reversal mechanism **does not demonstrate an ability to force a contributor negative after all funds were paid out**. [Stripe balances](https://docs.stripe.com/connect/account-balances), [transfer reversals](https://docs.stripe.com/api/transfer_reversals)

Separately, Stripe documents bank debits when a connected balance becomes negative, including supported US bank accounts. The account agreement permits specified fees to be deducted and requires examination of the platform agreement. Its §7 excludes some transfers outside Stripe Payments Services. Applicability must be established, not assumed. Whether Algora charges later contributor fees, requires repayment after sponsor fraud/disputes, or provides contractual protection is not settled by the examined material. [Balance rules](https://docs.stripe.com/connect/account-balances), [Connected Account Agreement §§1, 4.2, 7](https://stripe.com/legal/connect-account)

The live Algora terms still say last updated August 17, 2021. They require adult eligibility, accurate account/content representations, allow account termination, contain broad liability language, and permit separate promotion rules. They do not specify a complete bounty acceptance, refund, repayment, finality or contributor-fee schedule. Section 8 also restricts automated service access; an unattended payout/claim bot is not authorized by this review. These terms do not supply the missing zero-recourse guarantee. [Algora terms §§4, 7–10, 17–18](https://algora.io/legal/terms)

This differs from the earlier Gumroad review, where provider help explicitly described seller bank-debit exposure from refunds/chargebacks. Do not transfer that finding wholesale to Algora. Equally, zero upfront cost and sponsor-paid fees cannot be upgraded into a promise of zero possible owner obligation.

## Concrete setup and payout steps that remain

1. **Select one exact eligible bounty:** verify its open status, sponsor, amount/share, acceptance conditions, competing claims, repository rules and source/license requirements. Determine whether funding is collected or merely promised and identify any supplementary award/CLA agreement. No bounty is claimed by this review.
2. **Resolve account and cash terms before enrollment:** the owner must choose the actual individual/entity recipient and inspect applicable Algora/Stripe agreements, contributor deductions, repayment rights and negative-balance settings. Obtain a clear answer to who bears sponsor reversals and whether recovery is limited to unpaid award funds. Those missing facts affect payout activation, not local patch preparation.
3. **Authenticate the real contributor:** Algora's developer onboarding supports GitHub sign-in; the account linked to the real PR author must be used. No identity, age, credentials or work history may be invented. [Developer onboarding source](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora_web/live/onboarding/dev.ex)
4. **Configure payout through the authenticated Transactions flow:** select the country where the person/business legally operates, then continue to Stripe-hosted onboarding. Public code selects Express for US accounts, records the resulting service-agreement type, and requires `payouts_enabled` before transfers. [Transactions UI](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora_web/live/user/transactions_live.ex), [country/account mapping](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/lib/algora/psp/connect_countries.ex)
5. **Complete actual verification and agreement acceptance:** provide the identity, address, tax and external-bank information Stripe requests, with any supporting documents. Requirements depend on country, individual/entity type, capabilities and service agreement; the exact account-specific field list has not been observed. Returning from onboarding does not prove approval. Check outstanding requirements and payout enablement. Keep all identifiers/documents out of public records and chat. [Stripe verification](https://docs.stripe.com/connect/handling-api-verification), [Express onboarding](https://docs.stripe.com/connect/express-accounts), [service agreements](https://docs.stripe.com/connect/service-agreement-types)
6. **Only under applicable submission authority, deliver and claim genuine work:** Algora documents `/claim #issue` in the PR body and optional splits. Await sponsor acceptance/payment, verify the transfer, and reconcile the bank receipt. A claim is an external representation, not a local task marker. [Command reference](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/commands.md)
7. **Keep tax and profit records:** Algora classifies bounties as nonemployee compensation and says it handles US 1099 reporting. This is the platform's stated process, not an exemption from recipient income obligations or verification of the owner's filing circumstances. [Algora reporting](https://github.com/algora-io/algora/blob/74a49d7728400152f5d640ac8d461e6664b7c2eb/priv/content/docs/payments/reporting.md)

## Action now

Prepare one small, well-tested local patch for an exact legitimate bounty with existing tools and a fixed effort cap; stop if it requires paid tooling, deposits or an entry fee. Keep the intended award at $0 recognized receipts until genuine collection evidence exists. In parallel, prepare the precise account/award terms for owner review. That would make the next decision concrete without opening accounts or accepting liabilities.

**The route partially resolves the current constraint: it supports no-upfront work and a sponsor-fee model. It does not yet resolve the strict no-owner-debit/obligation constraint or the missing authorized payout identity.** The specific fact that would clear the financial gate is account- and award-specific evidence showing no upfront cost and no recovery obligation beyond retained, unspent award funds, with all applicable fees disclosed. A working patch, bounty badge or advertised amount is insufficient financial proof.

Source limitations: former `docs.algora.io` now redirected to the homepage, and generic `/docs` links were unavailable. Current documentation was read in Algora's official public source at the pinned main-tree revision above. That source is useful evidence but may omit deployment-specific settings, private cloud behavior or supplementary terms. No contract, bank ledger or live account configuration was inspected.
