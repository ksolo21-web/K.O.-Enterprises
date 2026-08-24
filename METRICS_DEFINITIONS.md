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

## Corporate operations and workforce

| Metric | Definition |
|---|---|
| Queue depth | Nonterminal work orders by department and state at the observation time. Always report the oldest ready and blocked age with it. |
| SLA adherence | Accepted work completed within its department service-level cycles / accepted eligible work. Approved policy or owner waits are excluded and reported separately. |
| Independent acceptance rate | Work accepted on first submission by a different authorized reviewer / reviewed work. Self-review never counts. |
| Review rejection rate | Submissions returned for unmet frozen acceptance criteria / reviewed submissions. A useful rejection is a quality-control outcome, not automatically a worker failure. |
| Dead-letter rate | Work exhausting its safe retry budget / work attempted. Policy denials and owner waits are not retries. |
| Autonomous completion rate | Independently accepted, pre-authorized work completed without human intervention / eligible work attempted. A deterministic integrity handler may count; merely creating a task may not. |
| Owner-attention rate | Owner-reserved packets requiring Kaleb / total material decisions. Routine questions routed upward incorrectly are tracked as avoidable interruptions. |
| CEO minutes | Measured Kaleb time on reserved decisions and exceptions. Strategy time is separated from operational interruption time. |
| Evidence/audit completeness | Accepted material outcomes with required source, date, evidence type, confidence, expiry, work lineage, and reviewer record / accepted material outcomes. |
| Resource efficiency | Accepted weighted outcome units / recorded capacity or compute units. Free-tier use still has a recorded resource unit even when cash cost is zero. |
| Worker performance state | `insufficient_sample` until five independently accepted weighted outcomes; thereafter derived from quality, objective contribution, SLA reliability, resource efficiency, evidence/audit completeness, and handoff quality. Critical policy violations override averages with red status. |
| Safe-denial rate | Correct policy/control denials / gated attempts. Safe denials must never lower an agent's performance score. |
| Lease recovery count | Expired internal leases safely fenced and recovered. Stale workers must be unable to submit after a later lease epoch. |
| Integrity gate | Combined SQLite integrity and audit-chain result for a cycle. Any failure blocks advancement and opens the applicable incident path. |

Impressions, lines of code, files generated, agent turns, and projected market size are diagnostic activity—not evidence of business success.
