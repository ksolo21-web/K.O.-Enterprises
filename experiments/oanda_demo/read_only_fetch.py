"""Read-only OANDA Practice research fetch that coexists with demo trades.

This module reads only the account summary and completed EUR/USD bid/ask
candles through :class:`PracticeReader`. Existing practice trades are neither
enumerated nor altered. No order, position, transaction, transfer, deposit,
withdrawal, or live-trading endpoint is implemented.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lab import LabError, PracticeReader


def fetch_snapshot(client: PracticeReader, count: int) -> tuple[dict, dict]:
    """Read a summary and candles without treating open demo trades as an error."""
    summary = client.summary()
    candles = client.candles(count)
    return summary, candles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only OANDA Practice summary and candle capture; no orders."
    )
    parser.add_argument(
        "--output", default="state/oanda-demo-candles.json", help="Ephemeral private output file."
    )
    parser.add_argument("--count", type=int, default=5000)
    args = parser.parse_args(argv)

    try:
        client = PracticeReader.from_environment()
        summary, candles = fetch_snapshot(client, args.count)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(candles, indent=2) + "\n", encoding="utf-8")
        if summary["open_trade_count"]:
            print(
                "Existing open practice trades detected. They were not enumerated, altered, or used by this research fetch."
            )
        print(
            "OANDA Practice account authenticated. Captured completed EUR/USD bid-ask candles for local historical simulation. No orders sent."
        )
        return 0
    except (LabError, OSError, TypeError, KeyError, ValueError) as error:
        print(
            str(error) if isinstance(error, LabError) else "Read-only practice fetch failed safely.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
