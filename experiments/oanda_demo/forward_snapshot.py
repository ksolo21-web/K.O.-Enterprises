"""Sanitized read-only snapshot for forward Practice experiment design."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .forward_lab import ForwardPracticeClient, INSTRUMENTS, _iso, _market_features
from .lab import LabError


def build_snapshot(client: ForwardPracticeClient) -> dict[str, Any]:
    markets = {
        instrument: _market_features(instrument, client.candles(instrument))
        for instrument in INSTRUMENTS
    }
    prices = client.prices()
    rows: dict[str, dict[str, Any]] = {}
    for instrument in INSTRUMENTS:
        market = markets[instrument]
        price = prices[instrument]
        rows[instrument] = {
            "signal_time": _iso(market.signal_time),
            "score_24": round(market.score_24, 6),
            "score_6": round(market.score_6, 6),
            "efficiency_24": round(market.efficiency_24, 6),
            "zscore_24": round(market.zscore_24, 6),
            "candle_direction": market.candle_direction,
            "close_location": round(market.close_location, 6),
            "atr_pips": round(market.atr * 10_000, 4),
            "price_time": _iso(price["time"]),
            "tradeable": price["tradeable"],
            "spread_pips": round((price["ask"] - price["bid"]) * 10_000, 4),
        }
    return {
        "status": "forward_practice_market_snapshot",
        "environment": "practice",
        "account_data_included": False,
        "markets": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a sanitized OANDA Practice forward snapshot.")
    parser.add_argument("--output", default="state/oanda-forward-snapshot.json")
    args = parser.parse_args(argv)
    try:
        result = build_snapshot(ForwardPracticeClient.from_environment())
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        leaders = sorted(
            result["markets"].items(),
            key=lambda item: abs(item[1]["score_24"]),
            reverse=True,
        )
        print(
            "Forward snapshot leaders: "
            + ", ".join(
                f"{instrument} score24={row['score_24']:.3f} z={row['zscore_24']:.3f} spread={row['spread_pips']:.1f}p"
                for instrument, row in leaders
            )
        )
        return 0
    except (LabError, OSError) as error:
        print(str(error) if isinstance(error, LabError) else "Forward snapshot file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
