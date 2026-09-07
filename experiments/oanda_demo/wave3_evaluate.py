"""Sealed Wave 3 evaluation for a predeclared GBP/AUD H4 reversal strategy.

The candidate was selected exclusively from the first 80 percent of the Wave 3
cross-pair data and fixed in source before the final 20 percent was inspected.
It is intentionally simple:

* instrument: GBP_AUD, four-hour completed bid/ask candles;
* setup: the completed signal candle closes at least 1.7 standard deviations
  from the mean of the preceding 32 closes;
* confirmation: the extreme candle reverses direction before it closes and
  finishes at least 40 percent through its own range;
* entry: next candle open;
* protection: 1.75 ATR stop, 2.5R target, maximum 12 market bars;
* forced Friday close; actual bid/ask execution plus adverse slippage;
* separate extra-cost stress cases of four and eight pips per trade.

This module is research-only. It contains no order endpoint, live hostname,
scheduler, transfer, withdrawal, or account mutation capability.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Any

from .lab import LabError, MAX_RESPONSE
from .tournament import Features, build_features
from .wave3_cross_data import INSTRUMENTS, parse_candles

PRIMARY_INSTRUMENT = "GBP_AUD"
HOLDOUT_START = datetime(2026, 1, 16, 6, 0, tzinfo=timezone.utc)
LOOKBACK = 32
ZSCORE_THRESHOLD = 1.7
REVERSAL_CLOSE_LOCATION = 0.40
ATR_PERIOD = 14
STOP_ATR = 1.75
TARGET_R = 2.50
MAX_HOLD_BARS = 12
MAX_SPREAD_ATR = 0.35
MAX_ABSOLUTE_SPREAD = 0.0030
MIN_STOP = 0.00050
SLIPPAGE = 0.00001
FRIDAY_EXIT_HOUR_UTC = 17
PREHOLDOUT_START_INDEX = 200
PREHOLDOUT_BOUNDARY_INDICES = (1150, 2100, 3000)
STRESS_PIPS = (4.0, 8.0)
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_BLOCK = 3


def signal_at(features: Features, entry_index: int) -> dict[str, Any] | None:
    """Use only the completed candle immediately before the entry candle."""
    signal_index = entry_index - 1
    if signal_index < LOOKBACK or entry_index >= len(features.bars):
        return None
    baseline = features.close[signal_index - LOOKBACK : signal_index]
    mean = statistics.fmean(baseline)
    deviation = statistics.pstdev(baseline)
    if deviation <= 0 or not math.isfinite(deviation):
        return None
    close = features.close[signal_index]
    opening = features.open[signal_index]
    high = features.high[signal_index]
    low = features.low[signal_index]
    candle_range = high - low
    atr = features.atr[signal_index]
    if candle_range <= 0 or atr is None or atr <= 0:
        return None
    zscore = (close - mean) / deviation
    close_location = (close - low) / candle_range
    direction = 0
    if (
        zscore <= -ZSCORE_THRESHOLD
        and close > opening
        and close_location >= REVERSAL_CLOSE_LOCATION
    ):
        direction = 1
    elif (
        zscore >= ZSCORE_THRESHOLD
        and close < opening
        and close_location <= 1.0 - REVERSAL_CLOSE_LOCATION
    ):
        direction = -1
    if direction == 0:
        return None
    return {
        "direction": direction,
        "signal_index": signal_index,
        "signal_time": features.bars[signal_index].time,
        "entry_time": features.bars[entry_index].time,
        "zscore": zscore,
        "close_location": close_location,
        "atr": atr,
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
        # Pessimistic convention: stop wins when an H4 bar contains both.
        if stop_hit:
            price = min(bar.bid_o, stop) if direction == 1 else max(bar.ask_o, stop)
            return index, price - direction * SLIPPAGE, "stop"
        if target_hit:
            return index, target - direction * SLIPPAGE, "target"
        if bar.time.weekday() == 4 and bar.time.hour >= FRIDAY_EXIT_HOUR_UTC:
            price = bar.bid_c if direction == 1 else bar.ask_c
            return index, price - direction * SLIPPAGE, "friday_close"
    bar = features.bars[final_index]
    price = bar.bid_c if direction == 1 else bar.ask_c
    return final_index, price - direction * SLIPPAGE, "time_exit"


def backtest(
    features: Features,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    if not 0 <= start < end <= len(features.bars):
        raise LabError("Invalid Wave 3 backtest segment.")
    trades: list[dict[str, Any]] = []
    index = max(start, LOOKBACK + 2)
    while index < end:
        bar = features.bars[index]
        if bar.time.weekday() >= 5:
            index += 1
            continue
        signal = signal_at(features, index)
        if signal is None:
            index += 1
            continue
        spread = bar.ask_o - bar.bid_o
        atr = float(signal["atr"])
        if (
            spread <= 0
            or spread > MAX_ABSOLUTE_SPREAD
            or spread > atr * MAX_SPREAD_ATR
        ):
            index += 1
            continue
        direction = int(signal["direction"])
        stop_distance = max(STOP_ATR * atr, spread * 4.0, MIN_STOP)
        entry_price = bar.ask_o + SLIPPAGE if direction == 1 else bar.bid_o - SLIPPAGE
        exit_index, exit_price, exit_reason = _exit_trade(
            features,
            index,
            end,
            direction,
            entry_price,
            stop_distance,
        )
        pnl_price = direction * (exit_price - entry_price)
        trades.append(
            {
                "entry_index": index,
                "entry_time": bar.time,
                "exit_time": features.bars[exit_index].time,
                "direction": direction,
                "r_multiple": pnl_price / stop_distance,
                "pnl_pips": pnl_price * 10_000,
                "stop_distance_pips": stop_distance * 10_000,
                "zscore": float(signal["zscore"]),
                "exit_reason": exit_reason,
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


def metrics(trades: list[dict[str, Any]], extra_pips: float = 0.0) -> dict[str, Any]:
    values = [
        float(trade["r_multiple"])
        - extra_pips / float(trade["stop_distance_pips"])
        for trade in trades
    ]
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
        "total_pips_after_extra_cost": sum(
            float(trade["pnl_pips"]) - extra_pips for trade in trades
        ),
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
    trades: list[dict[str, Any]], extra_pips: float
) -> float:
    values = [
        float(trade["r_multiple"])
        - extra_pips / float(trade["stop_distance_pips"])
        for trade in trades
    ]
    if not values:
        return 0.0
    generator = random.Random(20260907)
    maximum_start = max(0, len(values) - BOOTSTRAP_BLOCK)
    blocks_needed = math.ceil(len(values) / BOOTSTRAP_BLOCK)
    positive = 0
    for _ in range(BOOTSTRAP_DRAWS):
        sample: list[float] = []
        for _ in range(blocks_needed):
            start = generator.randint(0, maximum_start)
            sample.extend(values[start : start + BOOTSTRAP_BLOCK])
        positive += sum(sample[: len(values)]) > 0
    return positive / BOOTSTRAP_DRAWS


def _holdout_index(features: Features) -> int:
    for index, bar in enumerate(features.bars):
        if bar.time >= HOLDOUT_START:
            if bar.time != HOLDOUT_START:
                raise LabError("Wave 3 sealed holdout timestamp is missing.")
            return index
    raise LabError("Wave 3 data does not reach the sealed holdout start.")


def _preholdout_windows(holdout_index: int) -> list[tuple[int, int]]:
    boundaries = (
        PREHOLDOUT_START_INDEX,
        *PREHOLDOUT_BOUNDARY_INDICES,
        holdout_index,
    )
    if not all(left < right for left, right in zip(boundaries, boundaries[1:])):
        raise LabError("Invalid Wave 3 preholdout boundaries.")
    return list(zip(boundaries[:-1], boundaries[1:]))


def _calendar_year_metrics(
    trades: list[dict[str, Any]], extra_pips: float
) -> dict[str, dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[trade["entry_time"].year].append(trade)
    return {
        str(year): _public_metrics(metrics(group, extra_pips))
        for year, group in sorted(grouped.items())
    }


def evaluate_bundle(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "wave3_full_ephemeral_market_data":
        raise LabError("Invalid Wave 3 sealed-evaluation bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Wave 3 evaluation requires the complete cross-pair whitelist.")
    features_by_instrument = {
        instrument: build_features(parse_candles(raw[instrument], instrument), ATR_PERIOD)
        for instrument in INSTRUMENTS
    }
    features = features_by_instrument[PRIMARY_INSTRUMENT]
    holdout_index = _holdout_index(features)

    preholdout_trades = backtest(features, PREHOLDOUT_START_INDEX, holdout_index)
    windows: list[dict[str, Any]] = []
    for number, (start, end) in enumerate(_preholdout_windows(holdout_index), start=1):
        window_trades = backtest(features, start, end)
        windows.append(
            {
                "window": number,
                "start": features.bars[start].time.isoformat(),
                "end_exclusive": features.bars[end].time.isoformat(),
                "base": _public_metrics(metrics(window_trades)),
                "stress_plus_4_pips": _public_metrics(metrics(window_trades, 4.0)),
                "stress_plus_8_pips": _public_metrics(metrics(window_trades, 8.0)),
            }
        )

    pre_base = metrics(preholdout_trades)
    pre_stress4 = metrics(preholdout_trades, 4.0)
    pre_stress8 = metrics(preholdout_trades, 8.0)
    yearly_stress8 = _calendar_year_metrics(preholdout_trades, 8.0)
    pre_bootstrap = _block_bootstrap_probability_positive(preholdout_trades, 8.0)
    preholdout_passed = (
        pre_base["trades"] >= 100
        and pre_base["long_trades"] >= 30
        and pre_base["short_trades"] >= 30
        and pre_stress4["sum_r"] > 0
        and pre_stress4["profit_factor"] >= 1.35
        and pre_stress8["sum_r"] > 0
        and pre_stress8["profit_factor"] >= 1.20
        and pre_stress8["maximum_drawdown_r"] <= 8.0
        and all(window["stress_plus_8_pips"]["sum_r"] > 0 for window in windows)
        and yearly_stress8.get("2024", {}).get("sum_r", 0.0) > 0
        and yearly_stress8.get("2025", {}).get("sum_r", 0.0) > 0
        and pre_bootstrap >= 0.85
    )

    result: dict[str, Any] = {
        "status": "wave3_sealed_evaluation",
        "environment": "practice",
        "strategy_id": "gbp_aud_h4_extreme_reversal_v1",
        "parameters": {
            "instrument": PRIMARY_INSTRUMENT,
            "granularity": "H4",
            "lookback_closes": LOOKBACK,
            "zscore_threshold": ZSCORE_THRESHOLD,
            "reversal_close_location": REVERSAL_CLOSE_LOCATION,
            "atr_period": ATR_PERIOD,
            "stop_atr": STOP_ATR,
            "target_r": TARGET_R,
            "maximum_hold_bars": MAX_HOLD_BARS,
            "maximum_spread_atr": MAX_SPREAD_ATR,
            "maximum_absolute_spread_pips": MAX_ABSOLUTE_SPREAD * 10_000,
            "minimum_stop_pips": MIN_STOP * 10_000,
            "adverse_slippage_pips_per_side": SLIPPAGE * 10_000,
            "friday_exit_hour_utc": FRIDAY_EXIT_HOUR_UTC,
        },
        "holdout_start": HOLDOUT_START.isoformat(),
        "preholdout": {
            "windows": windows,
            "aggregate": {
                "base": _public_metrics(pre_base),
                "stress_plus_4_pips": _public_metrics(pre_stress4),
                "stress_plus_8_pips": _public_metrics(pre_stress8),
                "stress_8_block_bootstrap_probability_positive": round(pre_bootstrap, 6),
                "calendar_year_stress_plus_8_pips": yearly_stress8,
                "passed": preholdout_passed,
            },
        },
        "holdout_inspected": False,
        "holdout": None,
        "latest_signal": None,
        "decision": "preholdout_gate_failed",
        "limitations": [
            "Historical Practice simulation is not a broker fill record or a profit guarantee.",
            "The strategy and holdout start are fixed in source before the final 20 percent is inspected.",
            "Actual bid/ask candles, adverse slippage, stop-first ambiguous bars, Friday exits, and added four- and eight-pip stress charges are modeled.",
            "Exact financing, latency, partial fills, and market impact are not modeled.",
            "A pass can authorize only a separate, tightly bounded OANDA Practice execution review; it never authorizes live trading.",
        ],
    }
    if not preholdout_passed:
        return result

    holdout_trades = backtest(features, holdout_index, len(features.bars))
    holdout_base = metrics(holdout_trades)
    holdout_stress4 = metrics(holdout_trades, 4.0)
    holdout_stress8 = metrics(holdout_trades, 8.0)
    probability4 = _block_bootstrap_probability_positive(holdout_trades, 4.0)
    probability8 = _block_bootstrap_probability_positive(holdout_trades, 8.0)
    holdout_passed = (
        holdout_base["trades"] >= 20
        and holdout_base["long_trades"] >= 5
        and holdout_base["short_trades"] >= 5
        and holdout_stress4["sum_r"] > 0
        and holdout_stress4["profit_factor"] >= 1.20
        and holdout_stress4["maximum_drawdown_r"] <= 7.0
        and holdout_stress8["sum_r"] > 0
        and holdout_stress8["profit_factor"] >= 1.08
        and probability4 >= 0.70
        and probability8 >= 0.60
    )
    result["holdout_inspected"] = True
    result["holdout"] = {
        "start": features.bars[holdout_index].time.isoformat(),
        "end": features.bars[-1].time.isoformat(),
        "base": _public_metrics(holdout_base),
        "stress_plus_4_pips": _public_metrics(holdout_stress4),
        "stress_plus_8_pips": _public_metrics(holdout_stress8),
        "stress_4_block_bootstrap_probability_positive": round(probability4, 6),
        "stress_8_block_bootstrap_probability_positive": round(probability8, 6),
        "passed": holdout_passed,
    }
    result["decision"] = (
        "eligible_for_separate_guarded_practice_execution_review"
        if holdout_passed
        else "holdout_gate_failed"
    )
    if holdout_passed:
        # A current signal must come from the latest completed H4 candle and is
        # reported only after all historical gates pass.
        latest = signal_at(features, len(features.bars) - 1)
        if latest is not None:
            current_bar = features.bars[-1]
            spread = current_bar.ask_o - current_bar.bid_o
            if (
                current_bar.time.weekday() < 5
                and 0 < spread <= MAX_ABSOLUTE_SPREAD
                and spread <= float(latest["atr"]) * MAX_SPREAD_ATR
            ):
                result["latest_signal"] = {
                    "signal_time": latest["signal_time"].isoformat(),
                    "entry_reference_time": latest["entry_time"].isoformat(),
                    "direction": "long" if latest["direction"] == 1 else "short",
                    "zscore": round(float(latest["zscore"]), 6),
                    "atr": round(float(latest["atr"]), 8),
                    "reference_spread_pips": round(spread * 10_000, 4),
                }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sealed OANDA Practice Wave 3 gate.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="state/oanda-wave3-results.json")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
            raise LabError("Wave 3 evaluation input is too large.")
        result = evaluate_bundle(json.loads(source.read_text(encoding="utf-8")))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pre = result["preholdout"]["aggregate"]
        print(
            f"Wave 3 preholdout: {pre['base']['trades']} trades, "
            f"stress4 {pre['stress_plus_4_pips']['sum_r']:.3f}R, "
            f"stress8 {pre['stress_plus_8_pips']['sum_r']:.3f}R, "
            f"passed={pre['passed']}."
        )
        if result["holdout_inspected"]:
            holdout = result["holdout"]
            print(
                f"Wave 3 sealed holdout: {holdout['base']['trades']} trades, "
                f"base {holdout['base']['sum_r']:.3f}R, "
                f"stress4 {holdout['stress_plus_4_pips']['sum_r']:.3f}R, "
                f"stress8 {holdout['stress_plus_8_pips']['sum_r']:.3f}R, "
                f"passed={holdout['passed']}."
            )
        print(f"Wave 3 decision: {result['decision']}.")
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Wave 3 evaluation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
