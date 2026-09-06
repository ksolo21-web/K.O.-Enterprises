# Independent financial review — 2026-09-06

**Decision: continue bounded internal validation; hold the proposed paid launch under the current $0 external-spend mandate.** ImportScope can be developed and evaluated with the current offline architecture, but the proposed payment rail creates sale deductions and possible owner cash obligations. No positive business income or economic profit has been demonstrated. This is an analytical review, not a claim of professional credentials or an audit of the owner's finances.

Scope: the assigned `venture/zero-capital-fresh-products` working copy, ImportScope, company resource controls and the segregated OANDA laboratory. Raw records were reviewed independently, before reading any other advisor's conclusions. No accounts, payments, trades, deployments or external messages were initiated. Only this review file was written. `docs/advisory/CURRENT_STATE.md` did not exist when this review began; this report describes the supplied working copy, not a verified latest production/default-branch state.

## The three consequential findings

| Finding and consequence | Evidence, observation and confidence | Revalidation |
| --- | --- | --- |
| **1. No financially validated venture exists yet.** Records show zero verified customers, sales and revenue, no connected payment rail, and zero initiated external cash spend. The $29 offer, acquisition success and low support burden remain hypotheses. No spending can be funded from forecast proceeds. | `docs/ventures/importscope/ACTUALS.json`, `DOSSIER.md`, `LAUNCH_REQUIREMENTS.md`, `PUBLIC_LEDGER_SNAPSHOT.json`; internal declarations and code/workflow inspection; observed 2026-09-06; high confidence in what these records claim, limited assurance beyond this build. No bank/processor evidence inspected. | Every real transaction or resource commitment; otherwise 2026-10-06. |
| **2. Headline-only proceeds omit a published processing cost.** For an illustrative $29 direct card sale, the current ordinary fee model gives $24.46 before other deductions. The dossier's $25.60 is explicitly limited arithmetic, but should not be the operating contribution assumption. | [Gumroad fees](https://gumroad.com/help/article/66-gumroads-fees); current provider help content retrieved 2026-09-06; high confidence in published rate, medium confidence in applicability until the exact account/payment configuration is known. Reproduced below with Decimal. | Before quoting launch economics, on the first authentic transaction statement, on account/rail changes, or 2026-10-06. |
| **3. Sales do not create immediate unrestricted cash, and refunds can breach $0.** Payment-processor fees may survive refunds; negative balances can cause bank debits. A reserve funded only from sale proceeds cannot guarantee zero owner liability when all initial orders reverse. | [Issuing refunds](https://gumroad.com/help/article/47-how-to-refund-a-customer), [Payouts dashboard: bank withdrawals](https://gumroad.com/help/article/269-balance-page), [Getting paid](https://gumroad.com/help/article/13-getting-paid), [Terms §§7.1, 11.3](https://gumroad.com/terms); primary provider documents observed 2026-09-06; high confidence in published exposure, account-specific timing/amount unknown. | Before merchant activation and every refund/dispute; terms change scheduled for existing accounts on 2026-09-16, so review then if relevant. |

## Reconcile the money before judging profitability

| Measure | Evidence-backed state today | Treatment after a real transaction |
| --- | --- | --- |
| Customer payments / gross receipts | $0 verified in this build | Keep customer total, indirect tax and product amount distinct. |
| Fees, refunds, chargebacks, cash costs | No such actual transactions evidenced; $0 external expenditure initiated | Record incurred amounts separately from cash paid and later credits. Absence of a connected account is not a statement about the owner's other accounts. |
| Supplier proceeds / pending payout | No verified receivable or pending payout | Reconcile provider statements; preserve holds, reserves and adjustments separately. |
| Settled bank cash | No verified settlement; $0 business cash is supported by these records | Require bank receipt matching the payout, with private supporting evidence. |
| Available cash | No positive available business cash demonstrated | Settled cash less known obligations and designated reserves; unknown exposure prevents a positive spendable-profit assertion. |
| Economic profit | Not established | Contribution less attributable cash costs and transparent shadow costs for development, maintenance, support and acquisition time. |
| OANDA practice balances/results | Proposed virtual $50; no fetched data, broker orders or performance evidence | Permanently exclude virtual principal, simulated gains and practice trades from sales, revenue, settlements and business capital. |

The company OS and advisor work currently consume resources as internal infrastructure. Generic Notion templates and website audits in the dossier are held alternatives, with no receipts presented. ImportScope is the only commercial prototype substantiated by the supplied venture records. This is not evidence that the owner's entire portfolio has no other income.

## Published payment conditions relevant to $0

- Ordinary direct sales currently carry 10% + $0.50 **plus** card processing of 2.9% + $0.30; Discover is 30% inclusive of processing. The current help page also describes a monthly $20,000 high-volume discount; it is irrelevant to this initial experiment and is excluded from the model. Exact custom-account terms can differ. [Gumroad fees](https://gumroad.com/help/article/66-gumroads-fees)
- For ordinary Gumroad-processed refunds, its own fee is returned on the refunded portion; processing is retained. Connected Stripe/PayPal sales differ: both platform and processor fees remain the seller's responsibility. Old indexed snippets saying all fees always remain are not the current help text. Dashboard refunds require sufficient balance. [Refund help](https://gumroad.com/help/article/47-how-to-refund-a-customer)
- The processor may debit a linked bank account after refunds or chargebacks create a negative balance. [Payouts dashboard](https://gumroad.com/help/article/269-balance-page)
- Standard scheduled payouts require $100 and generally at least seven days of holding, plus account review and bank settlement. First-account review can take 1–3 weeks. US instant payouts cost 3% and have prior-payout/account-age requirements; PayPal payouts cost 2%. Neither is assumed in the base case. [Getting paid](https://gumroad.com/help/article/13-getting-paid)
- Gumroad can refund within 90 days at its discretion; a no-refund label does not remove chargebacks. [Refund policy](https://gumroad.com/help/article/51-what-is-gumroads-refund-policy) Published chargeback guidance returns the platform fee while retaining processing exposure and describes payout pauses above a 1% chargeback-to-sales-volume rate. Disputes can take months. [Chargebacks](https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks)
- The supplier must reimburse refund/dispute amounts and reasonable resolution costs. Terms allow offsets and holds, including holds without a fixed maximum while their basis remains unresolved. A refund rate above 15% can cause a 25% rolling reserve for 90 days. Direct-tax responsibility remains with the seller. These terms were updated August 17, 2026; existing accounts become bound September 16. Exact applicability depends on account history. [Terms §§6.4, 7.1, 10.6, 11.3](https://gumroad.com/terms)

The live help articles render from embedded public article content; the text extractor initially returned only their titles. The article body, rather than search summaries, was used. No signed-in account or personal financial details were accessed. The account's payment settings, settlement configuration and tax treatment remain unverified.

## Cent-based scenarios, not forecasts

Assumptions: USD product price; ordinary direct card purchase; no affiliate; no discount; fee percentage base equals product price; each fee rounded to cents half-up. No sales-tax-related processing, fee taxes, currency conversion, payout charges, withholding or dispute charges are included. These are unknown applicability/amounts, **not verified zeros**. Actual transaction statements must replace these assumptions. A lower fee or higher price does not establish demand.

| Price | Platform fee | Processing | Direct contribution before other costs | Discover contribution before other costs |
| --- | ---: | ---: | ---: | ---: |
| $19 | $2.40 | $0.85 | $15.75 | $13.30 |
| $29 | $3.40 | $1.14 | $24.46 | $20.30 |
| $39 | $4.40 | $1.43 | $33.17 | $27.30 |

At $29, hypothetical direct proceeds for 3 / 5 / 20 orders are $73.38 / $122.30 / $489.20. Four produce $97.84: even four completed orders fall short of the standard $100 payout threshold; five cross it before adjustments. The proposed three-purchase demand signal would therefore not establish payout success. These calculations do not predict a sale or a settlement date.

| $29 ordinary direct-card downside | Arithmetic | Result before other deductions |
| --- | --- | ---: |
| One order, then full refund | $24.46 − $29 + $3.40 returned platform fee | −$1.14 |
| Five orders, one fully refunded | $122.30 − $29 + $3.40 | $96.70 |
| Five orders, all fully refunded | $122.30 − $145 + $17 returned platform fees | −$5.70 |
| Connected-account full refund, using the same assumed original fees | $24.46 − $29, no platform-fee recovery | −$4.54 |

The last row is a conditional sensitivity, not verified connected-account pricing. The negative results are lifetime cash contribution, not a prediction of exact debit timing. Bank exposure after earlier payout can be greater than the net economic loss until returned proceeds are restored. Unspecified dispute costs could increase losses. No finite safe liability ceiling is established by this model.

Reproduction with Python standard library; executed successfully during this review:

```python
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

D = Decimal
def cents(value):
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)

for price in ("19", "29", "39"):
    p = D(price)
    platform = cents(p * D("0.10") + D("0.50"))
    processing = cents(p * D("0.029") + D("0.30"))
    print(p, platform, processing, p - platform - processing,
          p - cents(p * D("0.30")))

p, platform, processing = D("29"), D("3.40"), D("1.14")
net = p - platform - processing
for orders in (1, 3, 4, 5, 20):
    print(orders, p * orders, net * orders)
print("one refund in five", net * 5 - p + platform)
print("five refunds in five", net * 5 - p * 5 + platform * 5)
for minutes in (5, 15, 45, 60):
    print(minutes, net - D(minutes) * D("0.50"))
print("specified shadow-cost break-even", ceil(D("300") / (net - D("7.50"))))
```

## Time and maintenance sensitivity

The dossier's 5–15 support minutes per buyer has no customer evidence. At an explicitly assumed **$30/hour shadow value**, $29 direct contribution falls to $21.96 with 5 minutes, $16.96 with 15 minutes, $1.96 with 45 minutes, and −$5.54 with 60 minutes. These are opportunity costs, not wages authorized or paid. Agent work also consumes included capacity; this review cannot independently meter its marginal price or allocate the owner's subscription.

If a bounded project hypothetically consumes 8 development hours and 2 maintenance hours at that same shadow rate, the specified fixed shadow cost is $300. At 15 support minutes per order, 18 successful direct orders cover those specified costs before refunds, tax, acquisition and unknown deductions. This is a narrowly defined break-even scenario, not overall profitability or a forecast. Further feature development should stop until self-service completion and support time are observed.

## OANDA and infrastructure separation

The code fixes the practice host, uses allowed GET routes, and contains no broker-write route. It starts each historical segment with a fresh virtual $50, splits development/holdout chronologically, models bid/ask prices and 0.1 pip adverse slippage per side, and reports settled-balance drawdown. Exact commissions, intrabar drawdown, liquidity and margin closeout remain unmodeled. Its 5% daily and 30% drawdown controls stop later entries; a trade can overshoot them. Floating-point outputs are simulation measurements, not a business cash ledger. Sources: `experiments/oanda_demo/{README.md,lab.py}`, observed 2026-09-06; high confidence in inspected implementation, no execution-performance evidence. Revalidate on first practice dataset or code change.

The $50→$500 target is a 900% virtual gain; it supplies no spendable capital. OANDA documents distinct practice and live endpoints. [OANDA development guide](https://developer.oanda.com/rest-live-v20/development-guide/) No practice token or live account was accessed in this review.

Both checked workflows use standard Ubuntu runners, with finite timeouts and no artifact-upload step in the practice workflow. GitHub states public-repository standard runner minutes are free; larger runners are billed and storage has separate limits. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) Repository visibility and owner billing settings were not independently audited. `PAUSE_AUTONOMY` exists. Keep affected external/scheduled operations paused; local review remains compatible with $0. Recheck costs before workflow/visibility/storage changes or 2026-10-06.

## One actionable improvement

**Replace headline proceeds with a settlement-aware finance gate before requesting any merchant activation.** The coordinator should add a small Decimal-based internal ledger/model carrying `gross_product_cents`, `customer_tax_cents`, `platform_fee_cents`, `processing_fee_cents`, `refund_cents`, `fee_credit_cents`, `dispute_cost_cents`, `withholding_cents`, `pending_cents`, `restricted_cents`, `settled_cents`, `obligation_reserve_cents`, `support_minutes`, and evidence references. Unknown deductions must stay explicitly unknown. The gate must reject cash deployment whenever exposure is positive or unverifiable under the $0 ceiling. Keep private statements outside the public repository; publish only aggregates and non-sensitive references.

Immediate useful experiment: privately run the existing fictional before/after workflow and time documentation-only completion; set a proposed 15-minute support limit for later consenting testers. This improves economic evidence without accepting money, contacting customers, buying infrastructure or creating liabilities. A later approved test should distinguish purchase count, independent successful use and the first reconciled settlement as separate milestones.

What changes the decision: verified account-specific terms and complete deductions; a valid owner authorization covering any nonzero sale costs and liabilities or a demonstrated arrangement that truly fits $0; applicable seller/tax readiness; and authentic paid/self-service evidence. A promise to keep proceeds in reserve, a higher price, competitor pricing or simulated trading gains alone would not resolve the current financial gate.

## Focused documentation acceptance — 2026-09-06

Reviewed the coordinator's `docs/advisory/BOARD_DECISION.md`, `docs/advisory/CURRENT_STATE.md`, `docs/ventures/importscope/DOSSIER.md` and `docs/ventures/importscope/LAUNCH_REQUIREMENTS.md` against this review's original primary evidence and executed arithmetic. **The documentation corrections are accepted; no material financial misstatement was found.** They correctly qualify $24.46 as ordinary direct-card scenario proceeds before other deductions, preserve the $73.38 three-order/$100 standard-payout distinction, describe retained processing and the $5.70 five-refund downside, and distinguish receipts, economic profit and virtual OANDA results.

**The commerce exposure finding remains open.** This acceptance approves the accuracy of the corrections, not a payment rail, financial obligation, refund arrangement or launch. Account-specific deductions, settlement restrictions and possible negative-balance bank debits remain unresolved under the existing $0 mandate. No new broad research was performed. This note is appended without altering the original review.
