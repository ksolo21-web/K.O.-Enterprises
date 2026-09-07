# First OANDA Practice Forward Probe — Status

**Date:** 2026-09-07  
**Environment:** OANDA Practice only  
**Real money:** No

## Confirmed execution

The governed one-shot workflow filled the current microprobe at 2026-09-07T22:36:24Z.

- Instrument: GBP_USD
- Direction: long
- Units: 888
- Strategy: `forward_relative_strength_probe_v1`
- Planned maximum virtual loss: approximately $1.00
- Stop loss: attached and verified
- Take profit: attached and verified
- Overlapping positions: blocked

## First post-fill audit

At 2026-09-07T22:45:56Z, the account contained exactly one open trade and two dependent pending orders. The trade remained fully protected and showed approximately -$0.22 of unrealized Practice P/L. No second signal was allowed while the position remained open.

## Interpretation

This is a forward Practice experiment, not validated profitability and not withdrawable revenue. The result is not known until the trade closes. Increasing leverage or stacking positions solely to accelerate nominal demo profit is prohibited; the purpose is to gather clean forward evidence while preserving bounded loss.
