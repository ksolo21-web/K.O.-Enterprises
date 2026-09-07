# OANDA Practice Wave 4 JPY-Momentum Result — 2026-09-07

## Scope and separation

Wave 4 used a new seven-pair JPY-cross universe on completed H4 bid/ask candles after the earlier USD-pair and non-USD cross-pair holdouts had been opened. The first 80 percent of each series was exported for research. The final 20 percent remained ephemeral on the GitHub Actions runner until the candidate, exact parameters, holdout start and release thresholds were committed in source.

No order endpoint, live hostname, scheduler, transfer, withdrawal or account mutation was implemented. No OANDA Practice order was placed.

## Predeclared candidate

The selected candidate was `usd_jpy_h4_breadth_momentum_v1`:

- trade instrument: USD/JPY;
- confirmation universe: USD/JPY, EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY, CAD/JPY and CHF/JPY;
- timeframe: completed H4 candles;
- signal: 72-bar log return divided by 72-bar realized volatility for every pair;
- breadth requirement: the median normalized score must be at least positive or negative 0.25, at least five of seven pairs must agree, and USD/JPY must agree;
- entry: next H4 open;
- protection: 2.5 ATR stop, 3.0R target and 30-market-bar maximum hold;
- rollover-hour entry exclusion and forced Friday close;
- actual bid/ask candle execution, stop-first ambiguous-bar treatment and 0.1-pip modeled adverse slippage per side;
- additional four-, eight- and twelve-pip per-trade stress cases.

The sealed holdout started at 2026-01-16 06:00 UTC.

## Pre-holdout result

The candidate passed every fixed pre-holdout gate:

- 182 trades;
- base result: +37.189R;
- base profit factor: 1.9139;
- base maximum drawdown: 4.489R;
- four-pip stress result: +30.851R;
- eight-pip stress result: +24.514R;
- eight-pip stress profit factor: 1.5117;
- twelve-pip stress result: +18.178R;
- all four contiguous pre-holdout windows remained positive under the eight-pip stress;
- 2024 and 2025 remained positive;
- both long and short subsets remained positive;
- eight-pip block-bootstrap probability of a positive result: 0.9604;
- all eight nearby parameter variants remained positive in separate development and validation segments under the eight-pip stress.

## Sealed holdout result

The final 1,000 completed candles produced a decisive failure:

- 46 trades;
- base result: -3.062R;
- four-pip stress result: -5.082R;
- eight-pip stress result: -7.101R.

The fixed release gate failed, so the candidate is rejected and is not eligible for a Practice order.

## Research-integrity decision

The 2026 H4 JPY-cross holdout is now opened for this hypothesis. It must not be used to retune the rejected candidate and then represented as independent evidence. The repeated failure of strong historical candidates in newer sealed periods is evidence of material regime drift and strategy-selection risk. Future OANDA Practice work should therefore emphasize tiny forward experiments, independent strategy arms, hard virtual-loss limits, attached protection and truthful separation between experimental P&L and validated evidence.
