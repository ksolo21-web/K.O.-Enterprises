# OANDA Practice Wave 3 Cross-Pair Result — 2026-09-07

## Scope and separation

Wave 3 deliberately used a new market and timeframe after the H1 USD-pair holdouts from Waves 1 and 2 were opened. It downloaded 5,000 four-hour bid/ask candles for six non-USD cross-currency pairs and exported only the first 80 percent for strategy research. The final 20 percent remained ephemeral on the GitHub Actions runner until the selected strategy, its parameters, the holdout start and the acceptance thresholds were committed in source.

No order endpoint, live hostname, scheduler, transfer, withdrawal or account mutation was implemented. No Practice order was placed.

## Predeclared candidate

The selected candidate was `gbp_aud_h4_extreme_reversal_v1`:

- instrument: GBP/AUD;
- timeframe: completed H4 candles;
- signal: the candle closes at least 1.7 standard deviations from the mean of the preceding 32 closes;
- confirmation: an extreme low must reverse upward before closing and an extreme high must reverse downward before closing;
- entry: next H4 candle open;
- protection: 1.75 ATR stop, 2.5R target and 12-market-bar maximum hold;
- forced Friday exit;
- actual bid/ask candle execution and 0.1 pip modeled adverse slippage per side;
- additional four-pip and eight-pip per-trade stress cases.

The sealed holdout started at 2026-01-16 06:00 UTC.

## Pre-holdout result

The candidate passed the fixed pre-holdout gate:

- 118 trades: 57 long and 61 short;
- base result: +27.243756R;
- base profit factor: 1.696947;
- four-pip stress result: +21.853848R;
- eight-pip stress result: +16.463940R;
- eight-pip stress profit factor: 1.370951;
- eight-pip stress maximum drawdown: 6.263182R;
- all four contiguous pre-holdout windows remained positive under the eight-pip stress;
- calendar years 2024 and 2025 remained positive under the eight-pip stress;
- eight-pip block-bootstrap probability of a positive result: 0.8994.

## Sealed holdout result

The final 1,000 completed candles, covering 2026-01-16 06:00 UTC through 2026-09-07 17:00 UTC, reversed the result:

- 35 trades: 23 long and 12 short;
- base result: -4.002911R;
- base profit factor: 0.742658;
- base maximum drawdown: 6.626239R;
- four-pip stress result: -5.747602R;
- eight-pip stress result: -7.492293R;
- eight-pip stress profit factor: 0.574085;
- eight-pip stress maximum drawdown: 9.232338R;
- four-pip stress block-bootstrap probability of a positive result: 0.1146;
- eight-pip stress block-bootstrap probability of a positive result: 0.0468.

The holdout failed decisively. The strategy is rejected and is not eligible for a Practice order.

## Research integrity decision

The GBP/AUD H4 holdout beginning 2026-01-16 is now opened for this hypothesis. It must not be used to retune this candidate and then represented as independent evidence. Wave 4 must use a genuinely different hypothesis and a disjoint data universe. The selected direction is a JPY-cross momentum portfolio, motivated by published evidence that currency momentum can exist while recognizing that transaction costs and implementation constraints can erase apparent returns.
