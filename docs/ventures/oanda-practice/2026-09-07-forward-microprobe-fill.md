# OANDA Practice Forward Microprobe Fill — 2026-09-07

## Status

One OANDA Practice-only market order was filled under the Owner/CEO's explicit authorization to experiment in the demo account. This is virtual Practice activity, not real money, withdrawable profit, business revenue, or subscription funding.

## Confirmed fill

- strategy: `forward_relative_strength_probe_v1`;
- plan ID: `ko-probe-a3e162ec815c8f7efc`;
- environment: OANDA Practice;
- instrument: GBP/USD;
- direction: long;
- units: 888;
- fill price: 1.35433;
- fill time: 2026-09-07T22:36:24.165279973Z;
- Practice transaction ID: 5;
- Practice trade ID: 5;
- attached stop-loss: 1.35320;
- attached take-profit: 1.35574;
- estimated maximum virtual loss at the modeled stop: $0.9995;
- real money: no.

The post-fill reconciliation found the trade exactly once and verified both the attached stop-loss order and attached take-profit order.

## Selection context

The regular current-condition selector correctly returned no trade. The separate microprobe selected GBP/USD because its completed H1 data showed aligned positive 24-hour and 6-hour movement, positive candle direction and near-threshold path efficiency. AUD/USD lacked short-horizon confirmation, EUR/USD had conflicting horizons and NZD/USD lacked meaningful 24-hour strength.

The microprobe was intentionally limited to $1 virtual risk because the prior four independent research waves all failed their sealed or friction-stressed release gates. This order is a forward data-collection experiment, not evidence that the strategy has a durable edge.

## Controls actually enforced

- fixed OANDA Practice hostname only;
- exact first-attempt push-triggered workflow;
- plan-specific, short-lived, single-use permit;
- empty account before submission;
- fresh tradeable price and spread checks;
- maximum 888 units and maximum $1.00 modeled virtual risk;
- fill-or-kill market order with price bound;
- attached stop-loss and take-profit;
- no POST retry after uncertainty;
- confirmed fill reconciled against the open trade;
- broker-derived runner files deleted;
- execution branch reset to `main` immediately after the fill, removing the permit, one-shot workflow and scoped exception;
- repository-wide `PAUSE_AUTONOMY` remains active on `main`.

## Next decision boundary

No second Practice order is authorized. The existing attached protection controls this experiment. A later status read or another order requires a new bounded action and must distinguish unrealized Practice P&L, realized Practice P&L and actual cash. None may be counted as K.O. Enterprises revenue.
