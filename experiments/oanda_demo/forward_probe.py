"""One-dollar-risk OANDA Practice forward market probe.

The regular forward selector may correctly return no signal. This separate arm
allows one tiny Practice-only observation when a liquid pair shows aligned
near-term relative strength but narrowly misses the regular trend threshold.
It is explicitly an experiment, not a validated strategy or profit claim.

The module uses completed H1 candles, a fresh executable price, a $1 maximum
virtual-risk budget, a maximum of 1,000 units, a price bound, and attached stop
and take-profit. Execution still requires the exact approval phrase and a
short-lived plan-specific permit enforced by ``forward_lab.execute_plan``.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from .forward_lab import (
    FORBIDDEN_UTC_HOURS,
    INSTRUMENTS,
    MAX_PRICE_AGE_SECONDS,
    ForwardPracticeClient,
    MarketFeatures,
    _iso,
    _market_features,
    execute_plan,
)
from .lab import LabError

PROBE_MAX_VIRTUAL_RISK_USD = 1.0
PROBE_MAX_UNITS = 1_000
PROBE_MIN_STOP = 0.0010
PROBE_STOP_ATR = 1.50
PROBE_TARGET_R = 1.25
PROBE_MAX_SPREAD = 0.00030
PROBE_MAX_SPREAD_ATR = 0.25
PROBE_MIN_PRICE_BOUND = 0.00020


def select_probe_signal(markets: dict[str, MarketFeatures]) -> dict[str, Any] | None:
    """Select the strongest aligned near-threshold continuation candidate."""
    if set(markets) != set(INSTRUMENTS):
        raise LabError("Practice probe selection requires the complete universe.")
    candidates: list[tuple[float, MarketFeatures, int]] = []
    for market in markets.values():
        if market.score_24 == 0 or market.score_6 == 0:
            continue
        direction = 1 if market.score_24 > 0 else -1
        if (
            market.score_24 * market.score_6 > 0
            and abs(market.score_24) >= 0.50
            and abs(market.score_6) >= 0.10
            and market.efficiency_24 >= 0.22
            and market.candle_direction in (0, direction)
        ):
            confidence = (
                abs(market.score_24)
                * (0.50 + market.efficiency_24)
                * (1.0 + min(abs(market.score_6), 1.0))
            )
            candidates.append((confidence, market, direction))
    if not candidates:
        return None
    confidence, market, direction = max(candidates, key=lambda item: item[0])
    return {
        "strategy": "forward_relative_strength_probe_v1",
        "instrument": market.instrument,
        "direction": direction,
        "signal_time": market.signal_time,
        "confidence": confidence,
        "atr": market.atr,
        "diagnostics": {
            "score_24": market.score_24,
            "score_6": market.score_6,
            "efficiency_24": market.efficiency_24,
            "candle_direction": market.candle_direction,
        },
    }


def current_prices_without_units_available(
    client: ForwardPracticeClient,
) -> dict[str, dict[str, Any]]:
    """Parse executable prices without assuming optional unitsAvailable fields."""
    payload = client._request(
        "GET", "pricing", params={"instruments": ",".join(INSTRUMENTS)}
    )
    rows = payload.get("prices")
    if not isinstance(rows, list):
        raise LabError("Invalid OANDA Practice pricing response.")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("instrument") not in INSTRUMENTS:
            continue
        try:
            bid = float(row["bids"][0]["price"])
            ask = float(row["asks"][0]["price"])
            timestamp = datetime.fromisoformat(
                str(row["time"]).replace("Z", "+00:00")
            )
        except (KeyError, IndexError, TypeError, ValueError):
            raise LabError("Malformed OANDA Practice probe price record.") from None
        if timestamp.tzinfo is None or not all(
            math.isfinite(value) for value in (bid, ask)
        ):
            raise LabError("Invalid OANDA Practice probe price values.")
        if bid <= 0 or ask <= bid:
            raise LabError("Invalid or crossed OANDA Practice probe price.")
        result[row["instrument"]] = {
            "bid": bid,
            "ask": ask,
            "time": timestamp.astimezone(timezone.utc),
            "tradeable": str(row.get("status", "")).casefold() == "tradeable",
        }
    if set(result) != set(INSTRUMENTS):
        raise LabError("One or more current Practice probe prices are unavailable.")
    return result


def _blocked_time(timestamp: datetime) -> bool:
    return timestamp.weekday() >= 5 or timestamp.hour in FORBIDDEN_UTC_HOURS or (
        timestamp.weekday() == 4 and timestamp.hour >= 18
    )


def build_probe_plan(client: ForwardPracticeClient) -> dict[str, Any]:
    generated = datetime.now(timezone.utc)
    base = {
        "status": "forward_practice_probe_plan",
        "environment": "practice",
        "generated_at": _iso(generated),
        "experimental": True,
        "validated_profitability": False,
        "real_money": False,
    }
    summary = client.summary()
    if summary["open_trade_count"] or summary["pending_order_count"]:
        return {**base, "eligible": False, "reason": "existing_practice_trade_or_order"}
    if summary["guaranteed_stop_mode"].upper() == "REQUIRED":
        return {
            **base,
            "eligible": False,
            "reason": "guaranteed_stop_configuration_not_supported",
        }

    metadata = client.instrument_metadata()
    markets = {
        instrument: _market_features(instrument, client.candles(instrument))
        for instrument in INSTRUMENTS
    }
    signal = select_probe_signal(markets)
    if signal is None:
        return {
            **base,
            "eligible": False,
            "reason": "no_current_microprobe_signal",
            "latest_completed_candles": {
                instrument: _iso(market.signal_time)
                for instrument, market in markets.items()
            },
        }

    prices = current_prices_without_units_available(client)
    instrument = str(signal["instrument"])
    price = prices[instrument]
    age = (generated - price["time"]).total_seconds()
    if age < -10 or age > MAX_PRICE_AGE_SECONDS or not price["tradeable"]:
        return {
            **base,
            "eligible": False,
            "reason": "stale_or_nontradeable_current_price",
            "instrument": instrument,
        }
    if _blocked_time(price["time"]):
        return {
            **base,
            "eligible": False,
            "reason": "microprobe_time_window_blocked",
            "instrument": instrument,
        }

    spread = price["ask"] - price["bid"]
    atr = float(signal["atr"])
    if spread > PROBE_MAX_SPREAD or spread > atr * PROBE_MAX_SPREAD_ATR:
        return {
            **base,
            "eligible": False,
            "reason": "current_spread_too_wide",
            "instrument": instrument,
            "spread_pips": round(spread * 10_000, 4),
        }

    direction = int(signal["direction"])
    stop_distance = max(PROBE_STOP_ATR * atr, spread * 4, PROBE_MIN_STOP)
    units = math.floor(PROBE_MAX_VIRTUAL_RISK_USD / stop_distance)
    units = int(
        min(
            units,
            PROBE_MAX_UNITS,
            metadata[instrument]["maximum_order_units"],
        )
    )
    if units < metadata[instrument]["minimum_trade_size"]:
        return {
            **base,
            "eligible": False,
            "reason": "probe_risk_budget_below_minimum_trade_size",
            "instrument": instrument,
        }

    reference_entry = price["ask"] if direction == 1 else price["bid"]
    stop_price = reference_entry - direction * stop_distance
    target_price = reference_entry + direction * stop_distance * PROBE_TARGET_R
    price_bound = reference_entry + direction * max(
        spread * 2, PROBE_MIN_PRICE_BOUND
    )
    precision = metadata[instrument]["display_precision"]
    seed = "|".join(
        (
            str(signal["strategy"]),
            instrument,
            str(direction),
            _iso(signal["signal_time"]),
        )
    )
    plan_id = "ko-probe-" + hashlib.sha256(seed.encode()).hexdigest()[:18]
    estimated_risk = units * stop_distance
    return {
        **base,
        "eligible": True,
        "reason": "current_microprobe_signal_passed",
        "plan_id": plan_id,
        "strategy": signal["strategy"],
        "instrument": instrument,
        "direction": "long" if direction == 1 else "short",
        "signed_units": units if direction == 1 else -units,
        "signal_time": _iso(signal["signal_time"]),
        "current_price_time": _iso(price["time"]),
        "reference_entry": f"{reference_entry:.{precision}f}",
        "price_bound": f"{price_bound:.{precision}f}",
        "stop_loss": f"{stop_price:.{precision}f}",
        "take_profit": f"{target_price:.{precision}f}",
        "stop_distance_pips": round(stop_distance * 10_000, 4),
        "target_r": PROBE_TARGET_R,
        "spread_pips": round(spread * 10_000, 4),
        "estimated_max_virtual_risk_usd": round(estimated_risk, 4),
        "hard_virtual_risk_cap_usd": PROBE_MAX_VIRTUAL_RISK_USD,
        "hard_unit_cap": PROBE_MAX_UNITS,
        "confidence": round(float(signal["confidence"]), 6),
        "diagnostics": {
            key: round(float(value), 6)
            for key, value in signal["diagnostics"].items()
        },
        "warning": (
            "This is a tiny forward Practice probe selected from current market "
            "conditions, not a historically validated strategy or profit guarantee."
        ),
    }


def _write_json(path: str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-dollar-risk OANDA Practice forward probe."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan")
    scan.add_argument("--output", default="state/oanda-forward-probe-plan.json")
    execute = commands.add_parser("execute")
    execute.add_argument("--permit", required=True)
    execute.add_argument("--output", default="state/oanda-forward-probe-execution.json")
    args = parser.parse_args(argv)
    try:
        client = ForwardPracticeClient.from_environment()
        plan = build_probe_plan(client)
        if args.command == "scan":
            _write_json(args.output, plan)
            suffix = (
                f", plan={plan['plan_id']}, {plan['instrument']} {plan['direction']}, "
                f"units={abs(plan['signed_units'])}, virtual-risk=${plan['estimated_max_virtual_risk_usd']:.2f}."
                if plan.get("eligible")
                else "."
            )
            print(
                f"Forward Practice microprobe: eligible={plan['eligible']}, "
                f"reason={plan['reason']}{suffix}"
            )
        else:
            result = execute_plan(client, plan, args.permit)
            _write_json(args.output, result)
            print(
                f"Practice probe filled: plan={result['plan_id']}, "
                f"{result['instrument']} {result['direction']}, "
                f"units={abs(result['signed_units'])}; attached stop and target verified."
            )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(
            str(error)
            if isinstance(error, LabError)
            else "Practice probe file operation failed.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
