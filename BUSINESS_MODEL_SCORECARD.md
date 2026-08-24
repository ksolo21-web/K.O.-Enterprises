# Business Model Scorecard

Scoring prioritizes research. It is not launch authority and cannot compensate for a constitutional violation or missing evidence.

## Evidence requirements

Each material input includes: source URL or artifact ID, observation date, evidence type, affected buyer segment, confidence (`low`, `medium`, or `high`), and revalidation date. Economic behavior outranks opinions; direct buyer actions outrank generic trend claims.

For the broader business-model review, score every factor from 0 (none/hostile) to 5 (strong), multiply by its weight, divide by 5, and sum to a 0–100 score. This strategic review is recorded separately from the executable Market Void score below; do not average the two into false precision.

| Factor | Weight | What earns a high score |
|---|---:|---|
| Need severity and urgency | 14 | Frequent, costly, time-sensitive failure for a specific user. |
| Current demand evidence | 12 | Recent purchases, RFPs, hiring, waitlists, migration, or paid workaround. |
| Supply gap | 12 | Alternatives are scarce, slow, unreliable, inaccessible, or structurally overpriced. |
| Purchase intent / budget | 10 | Identified budget holder and credible existing spend. |
| Reachable beachhead | 8 | Narrow segment available through permission-based, low-cost channels. |
| Material advantage | 9 | Sustainable improvement in outcome, cost, speed, simplicity, safety, or control. |
| Switching feasibility | 6 | Low-risk trial, import/export path, interoperability, and limited lock-in. |
| Speed to demand test | 7 | Useful behavioral test in days, not an oversized build. |
| Near-zero-capital feasibility | 5 | Can validate under current `$0` cash authority. |
| Recurring/repeatable value | 7 | Ongoing problem and natural renewal or repeat purchase. |
| Unit economics | 4 | Plausible high gross margin after compute, support, refunds, and fees. |
| Low owner/support burden | 3 | Self-serve delivery with bounded maintenance and CEO minutes. |
| Defensibility and reuse | 3 | Workflow embed, distribution, data rights, interoperability, trust, or shared assets. |

## Market Void and Entry-Wedge Score (0–100, executable)

- 20 — current need severity and urgency
- 10 — demand acceleration or a new trigger
- 10 — verified spend, procurement, hiring, or costly workaround
- 15 — supply scarcity or poor alternatives
- 10 — incumbent weakness, dissatisfaction, or price umbrella
- 10 — reachable neglected beachhead
- 10 — sustainable cost, speed, simplicity, automation, or service advantage
- 5 — switching and migration feasibility
- 5 — near-zero-capital build/test feasibility
- 5 — recurring, repeatable, or compounding potential

Inputs are normalized from 0 to 1, then multiplied by the weights above. The Phase 0 CLI derives them from active evidence or displays explicit operator overrides in the stored score record.

The executable score also records affirmative hard-stop flags for meaningful pre-validation cash (`--meaningful-cash-before-validation`), regulated/risky data (`--regulated-or-risky-data`), an oversized MVP (`--mvp-too-large`), incompatible maintenance burden (`--maintenance-incompatible`), or an unlawful/prohibited advantage (`--unlawful-advantage`). These flags override any numeric score. Their default absence is not a completed legal, security, privacy, or operating review.

### Executable risk deductions

Each risk input is normalized from 0 to 1 and multiplied by its maximum deduction:

| Risk | Maximum deduction |
|---|---:|
| Legal/regulatory risk | 10 |
| Platform dependence | 8 |
| Proprietary-data dependence | 8 |
| Security exposure | 8 |
| Support burden | 6 |
| Weak buyer reach | 8 |
| Evidence staleness | 7 |

`final_market_void_score = max(0, base_market_void_score - total_deductions)`

Every advancement-eligible score requires qualifying active problem evidence in `need_severity` or `economic_commitment`, plus qualifying active `reachable_beachhead` evidence (rating at least 0.3 and confidence at least 0.5). Evidence with a missing, malformed, or elapsed revalidation date is stale and contributes no positive points. Numerical overrides cannot replace those two evidence gates.

When a candidate is marked low-competition, the Phase 0 gate additionally requires at least one active strong need/economic signal (rating at least 0.5 and confidence at least 0.7) plus qualifying active evidence from at least two independent conservative site identities (rating at least 0.3 and confidence at least 0.5). Multiple paths and sibling subdomains under one base hostname count as one source. Otherwise treat low competition as possible lack of demand and do not advance it.

A critical constitutional, legal, security, privacy, IP, approval, buyer-reach, or evidence failure recorded by a hard flag or found in the required separate review is a hard stop regardless of either numeric score. The numerical scorer cannot discover all such conditions automatically.

## Decision bands

- **80–100:** investigate first; still requires counter-thesis and all gates.
- **65–79:** run a cheap evidence-gathering experiment if reachability is credible.
- **50–64:** hold until a specific evidence gap is resolved.
- **0–49:** reject or archive; preserve any reusable learning.

Before build commitment, define a falsifiable test, maximum time/cost, success threshold, kill threshold, and what decision each outcome causes.

New records cannot begin at an advancement stage. The `validating`, `selected`, and `building` status labels require the latest executable score to be advancement-eligible and all evidence IDs cited by that score to remain current and traceable to the opportunity. Phase 0 deliberately refuses the `launched` label because it has no governed external-launch workflow yet; a score is never launch authority.
