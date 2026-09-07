# OANDA Practice Fresh-Strategy Results — 2026-09-07

## Scope and authority

This work used the authenticated OANDA Practice account only. No live hostname, live funds, transfer, withdrawal, or production trading authority was used. No order endpoint was called and no demo order was placed during these research waves.

## Wave 1: broad tournament

The first fresh tournament tested 56 fixed candidates across five non-SMA families and four liquid USD-quoted pairs:

- compression breakout;
- range reversion;
- failed breakout;
- impulse pullback; and
- session breakout.

Each candidate was evaluated on bid/ask candles with adverse slippage, stop-first treatment of ambiguous candles, fixed development/validation/holdout boundaries, a ten-times virtual notional cap, and bounded per-trade risk. No candidate passed both the development and validation screen, so the final holdout was not opened for any Wave 1 candidate. Decision: reject the entire Wave 1 field.

## Wave 2: pair-confirmed GBP shock continuation

Wave 2 was selected using only a sanitized pre-holdout export ending at 2026-07-10 04:00 UTC. The final holdout start was fixed in source before evaluation at 2026-07-10 05:00 UTC.

The predeclared candidate continued a GBP/USD one-hour move of at least one ATR only when at least two of EUR/USD, AUD/USD and NZD/USD moved in the same direction. It used a 2.5-ATR protective stop, a 2.5R target, a 36-market-bar maximum hold, forced Friday exit, actual bid/ask candles, 0.1-pip modeled adverse slippage on entry and exit, and an additional two-pip-per-trade stress case.

### Pre-holdout result

- Trades: 145
- Base result: +24.154102R
- Base profit factor: 1.362710
- Base maximum drawdown: 7.826486R
- Two-pip stress result: +15.747884R
- Two-pip stress profit factor: 1.220831
- All four contiguous pre-holdout windows were positive in both the base and stress cases.

The pre-holdout gate passed.

### Sealed holdout result

- Period: 2026-07-10 05:00 UTC through 2026-09-07 20:00 UTC
- Trades: 39
- Base result: +2.575568R
- Base profit factor: 1.133005
- Base maximum drawdown: 5.484541R
- Two-pip stress result: -0.295263R
- Two-pip stress profit factor: 0.985953
- Stress block-bootstrap probability of a positive result: 0.498400

The holdout failed the predeclared release gate. Although the unstressed simulation remained slightly profitable, its profit factor was below 1.15 and the stress case was negative. Decision: reject Wave 2 and do not place a demo order from it.

## Next research boundary

The 2026-07-10 through 2026-09-07 H1 holdout for the original four USD-quoted pairs is now considered opened for this hypothesis. It must not be used to retune the rejected strategy and then represented as independent evidence.

The next wave must use a genuinely new hypothesis and an independently sealed dataset, such as a disjoint cross-currency universe or a separately aggregated timeframe. Any future Practice order requires its own passing holdout, current spread and signal checks, attached protection, bot-specific ownership tags, a hard risk cap, and independent safety review.
