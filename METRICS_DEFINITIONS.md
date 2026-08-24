# Metrics Definitions

Reports must label each value as **actual**, **estimate**, **forecast**, **assumption**, or **unknown**. Currency records include currency, period, source/evidence, transaction state, and observation time. Never sum unlike currencies without a documented conversion source and timestamp.

Phase 0 has no bank or processor connector. Its financial rows and report totals are operator-recorded assertions, even when their transaction status is `realized`, `cleared`, `incurred`, or `paid`; reference presence and uniqueness are checked, but authenticity is not. Treat a row as an actual under the definitions below only after a human verifies the cited account/processor evidence.

## Financial truth

| Metric | Definition |
|---|---|
| Realized revenue | Gross consideration from completed customer transactions, supported by processor/account evidence. Excludes forecasts, unpaid invoices, credits, and test transactions. |
| Cleared cash | Realized revenue that has settled and is available, net of holds. It is not the same as accounting profit. |
| Refunds/chargebacks | Confirmed customer refunds, reversals, and disputes for the period. |
| Direct cost | Verified cash cost attributable to delivery: processor fees, approved API/compute use, hosting, and similar delivery expenses. Refunds/chargebacks are reported separately and are not included here. |
| Estimated variable cost | Modeled per-use cost not yet invoiced; always labeled estimate with method. |
| Net cash contribution | Cleared cash minus confirmed refunds/chargebacks and paid direct cash costs for the same scope/period. Taxes and unpaid obligations are shown separately. |
| Gross margin | `(realized revenue - direct delivery cost) / realized revenue`; `unknown` when revenue is zero or costs are incomplete. |
| Recurring revenue | Actual recurring billed revenue normalized to a period, excluding one-time charges and unverified pipeline. |

## Customer and product

| Metric | Definition |
|---|---|
| Qualified visitor | A non-test person in the defined target segment who reaches the measured experience. Bot and internal traffic excluded. |
| Activation rate | Qualified users completing the predefined first-value event / qualified users starting the flow. |
| Conversion rate | Qualified users completing the predefined paid or demand-commitment event / qualified users exposed to the offer. |
| Retention | Eligible activated customers still using or paying after a stated cohort interval. State numerator, denominator, cohort, and interval. |
| Time to first value | Median elapsed time from start to the predefined value event for successful users. |
| Support minutes | Human minutes spent on customer-specific help, moderation, refunds, and exceptions. |
| CEO minutes | Kaleb's measured time spent on approvals, exceptions, support, and operation; strategy time reported separately. |

## Experiment and automation

| Metric | Definition |
|---|---|
| Time to first revenue test | Elapsed time from candidate selection to first truthful exposure to a target user with a measurable commitment action. |
| Experiment cost | Confirmed cash plus separately reported compute/API estimate and human time for a completed experiment. |
| Autonomous completion rate | Eligible pre-authorized tasks completed without human intervention / eligible tasks attempted. Denials and safe pauses are not failures; report separately. |
| Revenue per CEO hour | Net cash contribution / measured CEO hours for the same period; `unknown` when time data is incomplete. |
| Shared-asset reuse rate | Completed product/experiment units using at least one maintained shared asset / completed units in the period. |

Impressions, lines of code, files generated, agent turns, and projected market size are diagnostic activity—not evidence of business success.
