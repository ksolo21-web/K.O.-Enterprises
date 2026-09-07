"""Development/validation diagnostics for the fresh Practice tournament.

This intentionally does not inspect holdout data. It explains why candidates
were rejected before the holdout gate so new research can be directed without
quietly tuning to the final test set.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .lab import LabError, MAX_RESPONSE
from .tournament import (
    INSTRUMENTS,
    _public_metrics,
    _segment_results,
    _selection_score,
    build_features,
    generate_candidates,
    parse_candles,
)


def rejection_reasons(development: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    checks = (
        (development["return_percent"] > 0, "development_return_not_positive"),
        (validation["return_percent"] > 0, "validation_return_not_positive"),
        (development["trades"] >= 20, "too_few_development_trades"),
        (validation["trades"] >= 8, "too_few_validation_trades"),
        (development["profit_factor"] >= 1.02, "development_profit_factor_below_1.02"),
        (validation["profit_factor"] >= 1.02, "validation_profit_factor_below_1.02"),
        (validation["max_drawdown_percent"] <= 8.0, "validation_drawdown_above_8_percent"),
        (validation["positive_instruments"] >= 2, "fewer_than_two_positive_validation_instruments"),
        (validation["worst_instrument_return_percent"] > -3.0, "validation_worst_instrument_at_or_below_minus_3_percent"),
    )
    return [reason for passed, reason in checks if not passed]


def diagnose(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "practice_market_data":
        raise LabError("Invalid tournament diagnostic input.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Diagnostic input must contain the complete instrument whitelist.")
    features = {
        instrument: build_features(parse_candles(raw[instrument], instrument))
        for instrument in INSTRUMENTS
    }
    rows: list[dict[str, Any]] = []
    for candidate in generate_candidates():
        development = _segment_results(features, candidate, "development")
        validation = _segment_results(features, candidate, "validation")
        rows.append(
            {
                "candidate_id": candidate.identifier,
                "family": candidate.family,
                "parameters": candidate.params,
                "selection_score": round(_selection_score(development, validation), 6),
                "development": _public_metrics(development),
                "validation": _public_metrics(validation),
                "rejection_reasons": rejection_reasons(development, validation),
            }
        )
    rows.sort(key=lambda row: row["selection_score"], reverse=True)
    families: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = families.get(row["family"])
        if current is None or row["selection_score"] > current["selection_score"]:
            families[row["family"]] = row
    return {
        "status": "pre_holdout_diagnostics",
        "holdout_inspected": False,
        "candidate_count": len(rows),
        "top_candidates": rows[:15],
        "best_by_family": families,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explain pre-holdout OANDA tournament rejections.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="state/oanda-tournament-diagnostics.json")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
            raise LabError("Tournament diagnostic input is too large.")
        report = diagnose(json.loads(source.read_text(encoding="utf-8")))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for row in report["top_candidates"][:5]:
            print(
                f"Pre-holdout {row['candidate_id']}: development "
                f"{row['development']['return_percent']:.3f}%, validation "
                f"{row['validation']['return_percent']:.3f}%, reasons="
                f"{','.join(row['rejection_reasons']) or 'none'}."
            )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Tournament diagnostic file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
