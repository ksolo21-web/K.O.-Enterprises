# OANDA Practice continuation — verified status

Observed at 2026-09-08T03:09:53Z, which is September 7, 2026 at 11:09:53 p.m. America/Detroit.

## Broker observations

The known first GBP/USD long remains OPEN with 888 units, entry 1.35433, original stop 1.35320 and original target 1.35574. Both original protective orders were independently read as PENDING and attached to the expected trade. The account had one open trade, two pending dependent orders and zero unprotected trades.

Unrealized Practice P/L: -$0.7459. Realized price P/L on this trade: $0. Financing: $0. The entry-to-stop price risk for the actual fill is $1.00344 before stop slippage. The original target price profit is $1.25208 before costs. These are virtual amounts, not withdrawable revenue.

The corrected next-entry scan returned ineligible because the existing trade or orders remain present. No additional trade was entered in this continuation.

## Signal change and blocked close

For the completed GBP/USD candle beginning 2026-09-08T02:00:00Z, the stored six-hour momentum score is -0.355263, the twenty-four-hour score is +0.765948 and the last candle direction is -1. The shorter-horizon alignment that supported the long no longer holds; that is an experimental interpretation, not a validated forecast.

A discretionary close of only this known Practice trade was prepared, but the connected tool blocked creation of its execution workflow. No close order was sent. No alternate route or retry of the blocked action was attempted. Neither the original stop nor target was widened, cancelled or replaced. The close helper and its tests exist as source on the working branch; its execution workflow was not deployed and its new close tests have not been reported as run.

## Implemented and tested controls

The new guarded_probe entry point uses exact-decimal practice_risk sizing based on rounded bracket prices, the worst permitted entry price and a one-pip stop-slippage allowance. It never increases the proposed units and caps modeled risk at $1 and units at 1,000. This modeled budget is not a guaranteed loss ceiling during a gap. It adds fresh-completed-candle and current-price checks and a local single-use permit claim; the claim is not cross-run broker idempotency.

The first_probe_reconcile reader distinguishes open from closed trades, reports realized price P/L and financing separately, and verifies protective order status rather than merely checking object presence.

Thirty focused tests passed in GitHub Actions, including nine sizing tests with 300 rounding regression cases. These are software checks, not profitability validation. The new guard is a successor entry point; the historical forward_probe source was not silently rewritten.

## Evidence and scope

- Read-only workflow run: 34182344760, attempt 2.
- Verification job: 101924373692, completed successfully.
- Sanitized artifact: 10039392905, oanda-guarded-check-34182344760-2.
- Executed source: 3420e50bf0dab54a7e311048978b40786e8fd9eb.
- Working branch: fix/oanda-practice-risk-reconciliation-20260908.
- Changes are saved on this working branch, not claimed merged into main.
- No live-account execution, funding, withdrawal or subscription payment occurred.
- No scheduled or continuous trading service was enabled. The existing broker-side protective orders, not this chat, continue managing the open position.
