"""Sealed Wave 2 evaluation for one predeclared OANDA Practice strategy.

The candidate was selected using only candles before ``HOLDOUT_START`` from the
sanitized pre-holdout export. Its parameters are fixed here before the final
holdout is inspected:

* instrument: GBP_USD
* signal: continue a one-hour move of at least 1.0 ATR
* confirmation: at least two of EUR_USD, AUD_USD and NZD_USD moved the same way
* entry: next hourly open, weekdays between 00:00 and 19:00 UTC
* stop: max(2.5 ATR, four entry spreads, 4 pips)
* target: 2.5 times initial risk
* maximum hold: 36 completed market bars; force close Friday at/after 18:00 UTC

Only completed bid/ask candles are used. Stop wins an ambiguous candle, adverse
slippage is charged on entry and exit, and a separate two-pip-per-trade stress
case is required to remain profitable. This module cannot place orders.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Any

from .lab import LabError, MAX_RESPONSE
from .tournament import (
    Features,
    INSTRUMENTS,
    MAX_SPREAD,
    MIN_STOP,
    SLIPPAGE,
    build_features,
    parse_candles,
)

PRIMARY_INSTRUMENT = "GBP_USD"
CONFIRMATION_INSTRUMENTS = ("EUR_USD", "AUD_USD", "NZD_USD")
HOLDOUT_START = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
SHOCK_ATR = 1.0
STOP_ATR = 2.5
TARGET_R = 2.5
MAX_HOLD_BARS = 36
ENTRY_START_HOUR = 0
ENTRY_END_HOUR = 19
FRIDAY_EXIT_HOUR = 18
STRESS_EXTRA_PIPS = 2.0
PREHOLDOUT_WARMUP = 150
PREHOLDOUT_WINDOWS = 4
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_BLOCK = 3


class AlignmentError(LabError):
    pass


def _timestamp_maps(features: dict[str, Features]) -> dict[str, dict[datetime, int]]:
    maps: dict[str, dict[datetime, int]] = {}
    for instrument, item in features.items():
        mapping = {bar.time: index for index, bar in enumerate(item.bars)}
        if len(mapping) != len(item.bars):
            raise AlignmentError("Duplicate candle timestamp in Wave 2 input.")
        maps[instrument] = mapping
    return maps


def _normalized_last_move(features: Features, index: int) -> float | None:
    if index < 1:
        return None
    atr = features.atr[index]
    if atr is None or atr <= 0 or not math.isfinite(atr):
        return None
    return (features.close[index] - features.close[index - 1]) / atr


def signal_at(
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    entry_index: int,
) -> dict[str, Any] | None:
    """Return a signal using information available before the entry bar opens."""
    primary = features[PRIMARY_INSTRUMENT]
    if entry_index < 2 or entry_index >= len(primary.bars):
        return None
    entry_bar = primary.bars[entry_index]
    signal_index = entry_index - 1
    signal_time = primary.bars[signal_index].time
    move = _normalized_last_move(primary, signal_index)
    if move is None or abs(move) < SHOCK_ATR:
        return None
    direction = 1 if move > 0 else -1
    confirmations = 0
    normalized_moves: dict[str, float] = {PRIMARY_INSTRUMENT: move}
    for instrument in CONFIRMATION_INSTRUMENTS:
        aligned_index = maps[instrument].get(signal_time)
        if aligned_index is None:
            raise AlignmentError("Wave 2 instruments are not timestamp-aligned.")
        other_move = _normalized_last_move(features[instrument], aligned_index)
        if other_move is None:
            return None
        normalized_moves[instrument] = other_move
        if (other_move > 0) == (direction > 0):
            confirmations += 1
    if confirmations < 2:
        return None
    if entry_bar.time.weekday() >= 5:
        return None
    if not ENTRY_START_HOUR <= entry_bar.time.hour <= ENTRY_END_HOUR:
        return None
    spread = entry_bar.ask_o - entry_bar.bid_o
    atr = primary.atr[signal_index]
    if atr is None or spread <= 0 or spread > min(MAX_SPREAD, atr * 0.45):
        return None
    stop_distance = max(MIN_STOP, atr * STOP_ATR, spread * 4)
    return {
        "direction": direction,
        "signal_time": signal_time,
        "entry_time": entry_bar.time,
        "normalized_moves": normalized_moves,
        "confirmations": confirmations,
        "entry_spread": spread,
        "atr": atr,
        "stop_distance": stop_distance,
        "target_r": TARGET_R,
        "max_hold_bars": MAX_HOLD_BARS,
    }


def _exit_trade(
    features: Features,
    entry_index: int,
    end: int,
    direction: int,
    entry_price: float,
    stop_distance: float,
) -> tuple[int, float, str]:
    stop = entry_price - direction * stop_distance
    target = entry_price + direction * stop_distance * TARGET_R
    final_index = min(end - 1, entry_index + MAX_HOLD_BARS - 1)
    for index in range(entry_index, final_index + 1):
        bar = features.bars[index]
        if direction == 1:
            stop_hit = bar.bid_l <= stop
            target_hit = bar.bid_h >= target
        else:
            stop_hit = bar.ask_h >= stop
            target_hit = bar.ask_l <= target
        if stop_hit:
            exit_price = (
                min(bar.bid_o, stop) if direction == 1 else max(bar.ask_o, stop)
            )
            return index, exit_price - direction * SLIPPAGE, "stop"
        if target_hit:
            return index, target - direction * SLIPPAGE, "target"
        if bar.time.weekday() == 4 and bar.time.hour >= FRIDAY_EXIT_HOUR:
            exit_price = bar.bid_c if direction == 1 else bar.ask_c
            return index, exit_price - direction * SLIPPAGE, "friday_close"
    bar = features.bars[final_index]
    exit_price = bar.bid_c if direction == 1 else bar.ask_c
    return final_index, exit_price - direction * SLIPPAGE, "time_exit"


def backtest(
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    primary = features[PRIMARY_INSTRUMENT]
    if not 0 <= start < end <= len(primary.bars):
        raise LabError("Invalid Wave 2 backtest segment.")
    trades: list[dict[str, Any]] = []
    index = max(start, 20)
    while index < end:
        candidate = signal_at(features, maps, index)
        if candidate is None:
            index += 1
            continue
        direction = int(candidate["direction"])
        stop_distance = float(candidate["stop_distance"])
        bar = primary.bars[index]
        entry_price = (
            bar.ask_o + SLIPPAGE if direction == 1 else bar.bid_o - SLIPPAGE
        )
        exit_index, exit_price, exit_reason = _exit_trade(
            primary,
            index,
            end,
            direction,
            entry_price,
            stop_distance,
        )
        pnl_price = direction * (exit_price - entry_price)
        stress_pnl_price = pnl_price - STRESS_EXTRA_PIPS / 10_000
        trades.append(
            {
                "entry_time": bar.time.isoformat(),
                "exit_time": primary.bars[exit_index].time.isoformat(),
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "stop_distance": stop_distance,
                "pnl_pips": pnl_price * 10_000,
                "r_multiple": pnl_price / stop_distance,
                "stress_r_multiple": stress_pnl_price / stop_distance,
                "exit_reason": exit_reason,
                "confirmations": candidate["confirmations"],
                "primary_normalized_move": candidate["normalized_moves"][PRIMARY_INSTRUMENT],
            }
        )
        index = exit_index + 1
    return trades


def _maximum_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def metrics(trades: list[dict[str, Any]], *, stress: bool = False) -> dict[str, Any]:
    key = "stress_r_multiple" if stress else "r_multiple"
    values = [float(trade[key]) for trade in trades]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "trades": len(trades),
        "long_trades": sum(trade["direction"] == 1 for trade in trades),
        "short_trades": sum(trade["direction"] == -1 for trade in trades),
        "wins": len(wins),
        "win_rate_percent": len(wins) / len(values) * 100 if values else 0.0,
        "sum_r": sum(values),
        "average_r": statistics.fmean(values) if values else 0.0,
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (99.0 if gross_profit > 0 else 0.0)
        ),
        "maximum_drawdown_r": _maximum_drawdown(values),
        "total_pips": sum(float(trade["pnl_pips"]) for trade in trades)
        - (STRESS_EXTRA_PIPS * len(trades) if stress else 0.0),
        "exit_reasons": {
            reason: sum(trade["exit_reason"] == reason for trade in trades)
            for reason in ("stop", "target", "friday_close", "time_exit")
        },
    }


def _public_metrics(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, float):
            result[key] = round(item, 6)
        else:
            result[key] = item
    return result


def _block_bootstrap_probability_positive(
    values: list[float],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    block: int = BOOTSTRAP_BLOCK,
) -> float:
    if not values:
        return 0.0
    if block < 1 or draws < 1:
        raise LabError("Invalid Wave 2 bootstrap settings.")
    generator = random.Random(20260907)
    maximum_start = max(0, len(values) - block)
    blocks_needed = math.ceil(len(values) / block)
    positive = 0
    for _ in range(draws):
        sample: list[float] = []
        for _ in range(blocks_needed):
            start = generator.randint(0, maximum_start)
            sample.extend(values[start : start + block])
        positive += sum(sample[: len(values)]) > 0
    return positive / draws


def _split_index(primary: Features) -> int:
    for index, bar in enumerate(primary.bars):
        if bar.time >= HOLDOUT_START:
            return index
    raise LabError("Wave 2 input does not reach the sealed holdout start.")


def _preholdout_ranges(holdout_index: int) -> list[tuple[int, int]]:
    start = PREHOLDOUT_WARMUP
    if holdout_index - start < 2000:
        raise LabError("Insufficient pre-holdout history for Wave 2.")
    boundaries = [
        start + round((holdout_index - start) * part / PREHOLDOUT_WINDOWS)
        for part in range(PREHOLDOUT_WINDOWS + 1)
    ]
    return list(zip(boundaries[:-1], boundaries[1:]))


def evaluate_bundle(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "practice_market_data":
        raise LabError("Invalid Wave 2 input bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Wave 2 requires the complete four-instrument whitelist.")
    features = {
        instrument: build_features(parse_candles(raw[instrument], instrument))
        for instrument in INSTRUMENTS
    }
    maps = _timestamp_maps(features)
    primary = features[PRIMARY_INSTRUMENT]
    holdout_index = _split_index(primary)
    preholdout: list[dict[str, Any]] = []
    all_preholdout_trades: list[dict[str, Any]] = []
    for number, (start, end) in enumerate(_preholdout_ranges(holdout_index), start=1):
        trades = backtest(features, maps, start, end)
        all_preholdout_trades.extend(trades)
        preholdout.append(
            {
                "window": number,
                "start": primary.bars[start].time.isoformat(),
                "end_exclusive": primary.bars[end].time.isoformat(),
                "base": _public_metrics(metrics(trades)),
                "stress_plus_2_pips": _public_metrics(metrics(trades, stress=True)),
            }
        )
    pre_base = metrics(all_preholdout_trades)
    pre_stress = metrics(all_preholdout_trades, stress=True)
    preholdout_passed = (
        len(all_preholdout_trades) >= 100
        and pre_base["sum_r"] > 0
        and pre_base["profit_factor"] >= 1.20
        and pre_base["maximum_drawdown_r"] <= 12.0
        and pre_stress["sum_r"] > 0
        and pre_stress["profit_factor"] >= 1.08
        and all(window["base"]["sum_r"] > 0 for window in preholdout)
        and all(window["stress_plus_2_pips"]["sum_r"] > 0 for window in preholdout)
    )
    result: dict[str, Any] = {
        "status": "wave2_sealed_evaluation",
        "environment": "practice",
        "strategy_id": "gbp_shock_continuation_v1",
        "parameters": {
            "primary_instrument": PRIMARY_INSTRUMENT,
            "confirmation_instruments": list(CONFIRMATION_INSTRUMENTS),
            "shock_atr": SHOCK_ATR,
            "required_other_pair_confirmations": 2,
            "stop_atr": STOP_ATR,
            "target_r": TARGET_R,
            "maximum_hold_bars": MAX_HOLD_BARS,
            "entry_utc_hours_inclusive": [ENTRY_START_HOUR, ENTRY_END_HOUR],
            "friday_exit_hour_utc": FRIDAY_EXIT_HOUR,
            "stress_extra_pips_per_trade": STRESS_EXTRA_PIPS,
        },
        "holdout_start": HOLDOUT_START.isoformat(),
        "preholdout": preholdout,
        "preholdout_aggregate": {
            "base": _public_metrics(pre_base),
            "stress_plus_2_pips": _public_metrics(pre_stress),
            "passed": preholdout_passed,
        },
        "holdout_inspected": False,
        "holdout": None,
        "decision": "preholdout_gate_failed",
        "latest_signal": None,
        "limitations": [
            "Historical Practice simulation is not a broker fill record or a profit guarantee.",
            "The final holdout begins at a timestamp fixed before Wave 2 parameters were committed.",
            "Bid/ask execution, adverse slippage, stop-first ambiguous candles, Friday exits, and an additional two-pip stress charge are modeled.",
            "Financing rates, partial fills, latency, and market impact are not modeled.",
            "Passing authorizes only a separately reviewed, tightly bounded OANDA Practice order test; it never authorizes live trading.",
        ],
    }
    if not preholdout_passed:
        return result

    holdout_trades = backtest(features, maps, holdout_index, len(primary.bars))
    holdout_base = metrics(holdout_trades)
    holdout_stress = metrics(holdout_trades, stress=True)
    probability = _block_bootstrap_probability_positive(
        [float(trade["stress_r_multiple"]) for trade in holdout_trades]
    )
    holdout_passed = (
        holdout_base["trades"] >= 20
        and holdout_base["long_trades"] >= 5
        and holdout_base["short_trades"] >= 5
        and holdout_base["sum_r"] > 0
        and holdout_base["profit_factor"] >= 1.15
        and holdout_base["maximum_drawdown_r"] <= 8.0
        and holdout_stress["sum_r"] > 0
        and holdout_stress["profit_factor"] >= 1.05
        and probability >= 0.80
    )
    result["holdout_inspected"] = True
    result["holdout"] = {
        "start": primary.bars[holdout_index].time.isoformat(),
        "end": primary.bars[-1].time.isoformat(),
        "base": _public_metrics(holdout_base),
        "stress_plus_2_pips": _public_metrics(holdout_stress),
        "stress_block_bootstrap_probability_positive": round(probability, 6),
        "passed": holdout_passed,
    }
    result["decision"] = (
        "eligible_for_separate_guarded_practice_order_review"
        if holdout_passed
        else "holdout_gate_failed"
    )
    if holdout_passed:
        latest = signal_at(features, maps, len(primary.bars) - 1)
        if latest is not None:
            result["latest_signal"] = {
                "signal_time": latest["signal_time"].isoformat(),
                "entry_reference_time": latest["entry_time"].isoformat(),
                "direction": "long" if latest["direction"] == 1 else "short",
                "confirmations": latest["confirmations"],
                "primary_normalized_move": round(
                    latest["normalized_moves"][PRIMARY_INSTRUMENT], 6
                ),
                "atr": round(latest["atr"], 8),
                "stop_distance": round(latest["stop_distance"], 8),
                "target_r": TARGET_R,
                "maximum_hold_bars": MAX_HOLD_BARS,
            }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sealed OANDA Practice Wave 2 gate.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="state/oanda-wave2-results.json")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
            raise LabError("Wave 2 input is too large.")
        result = evaluate_bundle(json.loads(source.read_text(encoding="utf-8")))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        aggregate = result["preholdout_aggregate"]["base"]
        print(
            f"Wave 2 pre-holdout: {aggregate['trades']} trades, "
            f"{aggregate['sum_r']:.3f}R, PF {aggregate['profit_factor']:.3f}, "
            f"passed={result['preholdout_aggregate']['passed']}."
        )
        if result["holdout_inspected"]:
            holdout = result["holdout"]
            print(
                f"Wave 2 sealed holdout: {holdout['base']['trades']} trades, "
                f"{holdout['base']['sum_r']:.3f}R, "
                f"PF {holdout['base']['profit_factor']:.3f}, "
                f"stress {holdout['stress_plus_2_pips']['sum_r']:.3f}R, "
                f"passed={holdout['passed']}."
            )
        print(f"Wave 2 decision: {result['decision']}.")
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Wave 2 file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
