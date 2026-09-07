"""Export sanitized development/validation market data without holdout bars.

The export contains no account summary, account identifier, credentials, or
final holdout observations. It exists solely to support faster local research
without leaking the untouched acceptance set into strategy design.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .lab import LabError, MAX_RESPONSE
from .tournament import INSTRUMENTS, parse_candles

PREHOLDOUT_FRACTION = 0.80


def export_preholdout(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "practice_market_data":
        raise LabError("Invalid Practice market-data bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Pre-holdout export requires the complete instrument whitelist.")
    exported: dict[str, dict[str, Any]] = {}
    ranges: dict[str, dict[str, Any]] = {}
    for instrument in INSTRUMENTS:
        payload = raw[instrument]
        bars = parse_candles(payload, instrument)
        split = int(len(bars) * PREHOLDOUT_FRACTION)
        if split < 1000 or split >= len(bars):
            raise LabError("Invalid pre-holdout split.")
        original_rows = payload.get("candles")
        if not isinstance(original_rows, list):
            raise LabError("Malformed candle payload.")
        complete_rows = [
            row for row in original_rows
            if isinstance(row, dict) and row.get("complete") is True
        ]
        selected = complete_rows[:split]
        exported[instrument] = {
            "instrument": instrument,
            "granularity": payload.get("granularity"),
            "candles": selected,
        }
        ranges[instrument] = {
            "exported_complete_candles": len(selected),
            "withheld_complete_candles": len(bars) - len(selected),
            "first_exported_time": selected[0]["time"],
            "last_exported_time": selected[-1]["time"],
            "first_withheld_time": complete_rows[split]["time"],
        }
    return {
        "status": "pre_holdout_market_data",
        "source_status": "practice_market_data",
        "preholdout_fraction": PREHOLDOUT_FRACTION,
        "holdout_exported": False,
        "instruments": list(INSTRUMENTS),
        "ranges": ranges,
        "candles": exported,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export sanitized development/validation candles while withholding holdout."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="state/oanda-preholdout-market.json")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
            raise LabError("Practice market-data bundle is too large.")
        exported = export_preholdout(json.loads(source.read_text(encoding="utf-8")))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(exported, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            "Exported development and validation candles only; final holdout remains withheld."
        )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(
            str(error) if isinstance(error, LabError) else "Pre-holdout export failed.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
