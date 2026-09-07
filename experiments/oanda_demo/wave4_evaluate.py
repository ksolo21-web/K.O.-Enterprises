"""Sealed Wave 4 evaluation for a predeclared JPY breadth-momentum strategy.

The candidate was selected exclusively from the first 80 percent of a new H4
JPY-cross universe and fixed in source before the final 20 percent was opened.
It trades only USD_JPY, using the other six JPY crosses as independent breadth
confirmation:

* calculate 72-bar log return divided by 72-bar realized volatility for every
  JPY cross, using only completed candles;
* require the median normalized score to be at least +/-0.25, at least five of
  seven pairs to agree, and USD_JPY itself to agree;
* enter USD_JPY at the next H4 open;
* use a 2.5 ATR stop, 3.0R target, 30-market-bar maximum hold and forced Friday
  close;
* model actual bid/ask execution, adverse 0.1-pip slippage per side, stop-first
  ambiguous candles, and extra cost stresses of four, eight and twelve pips.

This module cannot place orders and contains no live hostname, scheduler,
transfer, withdrawal, or account mutation route.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
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
from .wave4_jpy_data import INSTRUMENTS, PIP_SIZE, parse_candles

PRIMARY_INSTRUMENT = "USD_JPY"
HOLDOUT_START = datetime(2026, 1, 16, 6, 0, tzinfo=timezone.utc)
LOOKBACK = 72
BREADTH_REQUIRED = 5
MEDIAN_SCORE_THRESHOLD = 0.25
ATR_PERIOD = 14
STOP_ATR = 2.5
TARGET_R = 3.0
MAX_HOLD_BARS = 30
MAX_SPREAD = 0.08
MAX_SPREAD_ATR = 0.20
MIN_STOP = 0.05
SLIPPAGE = 0.001
FRIDAY_LAST_ENTRY_HOUR_UTC = 13
FRIDAY_EXIT_HOUR_UTC = 17
ROLLOVER_HOURS_UTC = (21, 22)
PREHOLDOUT_START_INDEX = 150
DEVELOPMENT_END_INDEX = 3000
PREHOLDOUT_BOUNDARY_INDICES = (1100, 2050, 3000)
STRESS_PIPS = (4.0, 8.0, 12.0)
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_BLOCK = 3


@dataclass(frozen=True)
class Parameters:
    lookback: int = LOOKBACK
    breadth_required: int = BREADTH_REQUIRED
    median_threshold: float = MEDIAN_SCORE_THRESHOLD
    stop_atr: float = STOP_ATR
    target_r: float = TARGET_R
    max_hold_bars: int = MAX_HOLD_BARS


EXACT_PARAMETERS = Parameters()
NEIGHBORHOOD = (
    Parameters(target_r=2.0),
    Parameters(target_r=2.5),
    Parameters(target_r=3.0),
    Parameters(stop_atr=3.0, target_r=2.5),
    Parameters(breadth_required=6, target_r=2.5),
    Parameters(breadth_required=6, target_r=3.0),
    Parameters(breadth_required=6, max_hold_bars=24, target_r=3.0),
    Parameters(max_hold_bars=24, target_r=3.0),
)


class AlignmentError(LabError):
    pass


def _timestamp_maps(features: dict[str, Features]) -> dict[str, dict[datetime, int]]:
    maps: dict[str, dict[datetime, int]] = {}
    for instrument, item in features.items():
        mapping = {bar.time: index for index, bar in enumerate(item.bars)}
        if len(mapping) != len(item.bars):
            raise AlignmentError("Duplicate candle timestamp in Wave 4 input.")
        maps[instrument] = mapping
    return maps


def _normalized_score(features: Features, signal_index: int, lookback: int) -> float | None:
    if signal_index < lookback:
        return None
    closes = features.close
    one_bar_returns = [
        math.log(closes[index] / closes[index - 1])
        for index in range(signal_index - lookback + 1, signal_index + 1)
    ]
    volatility = statistics.pstdev(one_bar_returns)
    if volatility <= 0 or not math.isfinite(volatility):
        return None
    total_return = math.log(closes[signal_index] / closes[signal_index - lookback])
    return total_return / (volatility * math.sqrt(lookback))


def setup_at_signal(
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    signal_index: int,
    parameters: Parameters = EXACT_PARAMETERS,
) -> dict[str, Any] | None:
    primary = features[PRIMARY_INSTRUMENT]
    if signal_index < parameters.lookback or signal_index >= len(primary.bars):
        return None
    signal_time = primary.bars[signal_index].time
    scores: dict[str, float] = {}
    for instrument in INSTRUMENTS:
        aligned_index = maps[instrument].get(signal_time)
        if aligned_index is None:
            raise AlignmentError("Wave 4 instruments are not timestamp-aligned.")
        score = _normalized_score(features[instrument], aligned_index, parameters.lookback)
        if score is None:
            return None
        scores[instrument] = score
    median_score = statistics.median(scores.values())
    positive = sum(score > 0 for score in scores.values())
    negative = sum(score < 0 for score in scores.values())
    direction = 0
    if median_score >= parameters.median_threshold and positive >= parameters.breadth_required:
        direction = 1
    elif median_score <= -parameters.median_threshold and negative >= parameters.breadth_required:
        direction = -1
    if direction == 0 or math.copysign(1.0, scores[PRIMARY_INSTRUMENT]) != direction:
        return None
    atr = primary.atr[signal_index]
    if atr is None or atr <= 0 or not math.isfinite(atr):
        return None
    return {
        "direction": direction,
        "signal_index": signal_index,
        "signal_time": signal_time,
        "median_score": median_score,
        "positive_pairs": positive,
        "negative_pairs": negative,
        "primary_score": scores[PRIMARY_INSTRUMENT],
        "scores": scores,
        "atr": atr,
    }


def signal_at_entry(
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    entry_index: int,
    parameters: Parameters = EXACT_PARAMETERS,
) -> dict[str, Any] | None:
    primary = features[PRIMARY_INSTRUMENT]
    if entry_index < 1 or entry_index >= len(primary.bars):
        return None
    entry_bar = primary.bars[entry_index]
    if entry_bar.time.weekday() >= 5 or entry_bar.time.hour in ROLLOVER_HOURS_UTC:
        return None
    if (
        entry_bar.time.weekday() == 4
        and entry_bar.time.hour >= FRIDAY_LAST_ENTRY_HOUR_UTC
    ):
        return None
    setup = setup_at_signal(features, maps, entry_index - 1, parameters)
    if setup is None:
        return None
    spread = entry_bar.ask_o - entry_bar.bid_o
    atr = float(setup["atr"])
    if spread <= 0 or spread > MAX_SPREAD or spread > atr * MAX_SPREAD_ATR:
        return None
    stop_distance = max(parameters.stop_atr * atr, spread * 4.0, MIN_STOP)
    return {
        **setup,
        "entry_index": entry_index,
        "entry_time": entry_bar.time,
        "spread": spread,
        "stop_distance": stop_distance,
    }


def _exit_trade(
    features: Features,
    entry_index: int,
    end: int,
    direction: int,
    entry_price: float,
    stop_distance: float,
    parameters: Parameters,
) -> tuple[int, float, str]:
    stop = entry_price - direction * stop_distance
    target = entry_price + direction * stop_distance * parameters.target_r
    final_index = min(end - 1, entry_index + parameters.max_hold_bars - 1)
    for index in range(entry_index, final_index + 1):
        bar = features.bars[index]
        if direction == 1:
            stop_hit = bar.bid_l <= stop
            target_hit = bar.bid_h >= target
        else:
            stop_hit = bar.ask_h >= stop
            target_hit = bar.ask_l <= target
        # Pessimistic convention: stop wins when one H4 candle contains both.
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
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    start: int,
    end: int,
    parameters: Parameters = EXACT_PARAMETERS,
) -> list[dict[str, Any]]:
    primary = features[PRIMARY_INSTRUMENT]
    if not 0 <= start < end <= len(primary.bars):
        raise LabError("Invalid Wave 4 backtest segment.")
    trades: list[dict[str, Any]] = []
    index = max(start, parameters.lookback + ATR_PERIOD + 1)
    while index < end:
        signal = signal_at_entry(features, maps, index, parameters)
        if signal is None:
            index += 1
            continue
        direction = int(signal["direction"])
        stop_distance = float(signal["stop_distance"])
        bar = primary.bars[index]
        entry_price = bar.ask_o + SLIPPAGE if direction == 1 else bar.bid_o - SLIPPAGE
        exit_index, exit_price, exit_reason = _exit_trade(
            primary,
            index,
            end,
            direction,
            entry_price,
            stop_distance,
            parameters,
        )
        pnl_price = direction * (exit_price - entry_price)
        trades.append(
            {
                "entry_index": index,
                "entry_time": bar.time,
                "exit_time": primary.bars[exit_index].time,
                "direction": direction,
                "r_multiple": pnl_price / stop_distance,
                "pnl_pips": pnl_price / PIP_SIZE,
                "stop_distance_pips": stop_distance / PIP_SIZE,
                "median_score": float(signal["median_score"]),
                "primary_score": float(signal["primary_score"]),
                "positive_pairs": int(signal["positive_pairs"]),
                "negative_pairs": int(signal["negative_pairs"]),
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
        result[key] = round(item, 6) if isinstance(item, float) else item
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


def _holdout_index(primary: Features) -> int:
    for index, bar in enumerate(primary.bars):
        if bar.time >= HOLDOUT_START:
            if bar.time != HOLDOUT_START:
                raise LabError("Wave 4 sealed holdout timestamp is missing.")
            return index
    raise LabError("Wave 4 data does not reach the sealed holdout start.")


def _preholdout_windows(holdout_index: int) -> list[tuple[int, int]]:
    boundaries = (
        PREHOLDOUT_START_INDEX,
        *PREHOLDOUT_BOUNDARY_INDICES,
        holdout_index,
    )
    if not all(left < right for left, right in zip(boundaries, boundaries[1:])):
        raise LabError("Invalid Wave 4 preholdout boundaries.")
    return list(zip(boundaries[:-1], boundaries[1:]))


def _calendar_metrics(
    trades: list[dict[str, Any]], extra_pips: float
) -> dict[str, dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[trade["entry_time"].year].append(trade)
    return {
        str(year): _public_metrics(metrics(group, extra_pips))
        for year, group in sorted(grouped.items())
    }


def _direction_metrics(
    trades: list[dict[str, Any]], extra_pips: float
) -> dict[str, dict[str, Any]]:
    return {
        "long": _public_metrics(
            metrics([trade for trade in trades if trade["direction"] == 1], extra_pips)
        ),
        "short": _public_metrics(
            metrics([trade for trade in trades if trade["direction"] == -1], extra_pips)
        ),
    }


def _neighborhood_results(
    features: dict[str, Features],
    maps: dict[str, dict[datetime, int]],
    holdout_index: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for number, parameters in enumerate(NEIGHBORHOOD, start=1):
        development = backtest(
            features,
            maps,
            PREHOLDOUT_START_INDEX,
            DEVELOPMENT_END_INDEX,
            parameters,
        )
        validation = backtest(
            features,
            maps,
            DEVELOPMENT_END_INDEX,
            holdout_index,
            parameters,
        )
        development_metrics = metrics(development, 8.0)
        validation_metrics = metrics(validation, 8.0)
        passed = (
            development_metrics["trades"] >= 80
            and validation_metrics["trades"] >= 20
            and development_metrics["sum_r"] > 0
            and validation_metrics["sum_r"] > 0
            and development_metrics["profit_factor"] >= 1.10
            and validation_metrics["profit_factor"] >= 1.05
        )
        results.append(
            {
                "variant": number,
                "parameters": {
                    "lookback": parameters.lookback,
                    "breadth_required": parameters.breadth_required,
                    "median_threshold": parameters.median_threshold,
                    "stop_atr": parameters.stop_atr,
                    "target_r": parameters.target_r,
                    "max_hold_bars": parameters.max_hold_bars,
                },
                "development_stress_plus_8_pips": _public_metrics(development_metrics),
                "validation_stress_plus_8_pips": _public_metrics(validation_metrics),
                "passed": passed,
            }
        )
    return results


def evaluate_bundle(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "wave4_full_ephemeral_market_data":
        raise LabError("Invalid Wave 4 sealed-evaluation bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Wave 4 evaluation requires the complete JPY-cross whitelist.")
    features = {
        instrument: build_features(parse_candles(raw[instrument], instrument), ATR_PERIOD)
        for instrument in INSTRUMENTS
    }
    maps = _timestamp_maps(features)
    primary = features[PRIMARY_INSTRUMENT]
    holdout_index = _holdout_index(primary)
    if DEVELOPMENT_END_INDEX >= holdout_index:
        raise LabError("Wave 4 development boundary overlaps the holdout.")

    preholdout_trades = backtest(
        features, maps, PREHOLDOUT_START_INDEX, holdout_index
    )
    development_trades = backtest(
        features, maps, PREHOLDOUT_START_INDEX, DEVELOPMENT_END_INDEX
    )
    validation_trades = backtest(
        features, maps, DEVELOPMENT_END_INDEX, holdout_index
    )
    windows: list[dict[str, Any]] = []
    for number, (start, end) in enumerate(_preholdout_windows(holdout_index), start=1):
        window_trades = backtest(features, maps, start, end)
        windows.append(
            {
                "window": number,
                "start": primary.bars[start].time.isoformat(),
                "end_exclusive": primary.bars[end].time.isoformat(),
                "base": _public_metrics(metrics(window_trades)),
                "stress_plus_8_pips": _public_metrics(metrics(window_trades, 8.0)),
                "stress_plus_12_pips": _public_metrics(metrics(window_trades, 12.0)),
            }
        )

    pre_base = metrics(preholdout_trades)
    pre_stress4 = metrics(preholdout_trades, 4.0)
    pre_stress8 = metrics(preholdout_trades, 8.0)
    pre_stress12 = metrics(preholdout_trades, 12.0)
    development_stress8 = metrics(development_trades, 8.0)
    validation_stress8 = metrics(validation_trades, 8.0)
    calendar_stress8 = _calendar_metrics(preholdout_trades, 8.0)
    direction_stress8 = _direction_metrics(preholdout_trades, 8.0)
    bootstrap8 = _block_bootstrap_probability_positive(preholdout_trades, 8.0)
    neighborhood = _neighborhood_results(features, maps, holdout_index)
    neighborhood_passes = sum(result["passed"] for result in neighborhood)

    preholdout_passed = (
        pre_base["trades"] >= 160
        and pre_base["long_trades"] >= 80
        and pre_base["short_trades"] >= 45
        and development_stress8["trades"] >= 100
        and development_stress8["sum_r"] > 0
        and development_stress8["profit_factor"] >= 1.20
        and development_stress8["maximum_drawdown_r"] <= 8.0
        and validation_stress8["trades"] >= 30
        and validation_stress8["long_trades"] >= 20
        and validation_stress8["short_trades"] >= 5
        and validation_stress8["sum_r"] > 0
        and validation_stress8["profit_factor"] >= 1.10
        and validation_stress8["maximum_drawdown_r"] <= 6.0
        and pre_stress8["sum_r"] > 0
        and pre_stress8["profit_factor"] >= 1.20
        and pre_stress8["maximum_drawdown_r"] <= 8.0
        and pre_stress12["sum_r"] > 0
        and pre_stress12["profit_factor"] >= 1.15
        and all(window["stress_plus_8_pips"]["sum_r"] > 0 for window in windows)
        and calendar_stress8.get("2024", {}).get("sum_r", 0.0) > 0
        and calendar_stress8.get("2025", {}).get("sum_r", 0.0) > 0
        and direction_stress8["long"]["sum_r"] > 0
        and direction_stress8["short"]["sum_r"] > 0
        and bootstrap8 >= 0.90
        and neighborhood_passes >= 6
    )

    result: dict[str, Any] = {
        "status": "wave4_sealed_evaluation",
        "environment": "practice",
        "strategy_id": "usd_jpy_h4_breadth_momentum_v1",
        "parameters": {
            "primary_instrument": PRIMARY_INSTRUMENT,
            "confirmation_instruments": list(INSTRUMENTS),
            "granularity": "H4",
            "lookback_bars": LOOKBACK,
            "breadth_required": BREADTH_REQUIRED,
            "median_normalized_score_threshold": MEDIAN_SCORE_THRESHOLD,
            "atr_period": ATR_PERIOD,
            "stop_atr": STOP_ATR,
            "target_r": TARGET_R,
            "maximum_hold_bars": MAX_HOLD_BARS,
            "maximum_spread_pips": MAX_SPREAD / PIP_SIZE,
            "maximum_spread_atr": MAX_SPREAD_ATR,
            "minimum_stop_pips": MIN_STOP / PIP_SIZE,
            "adverse_slippage_pips_per_side": SLIPPAGE / PIP_SIZE,
            "friday_last_entry_hour_utc": FRIDAY_LAST_ENTRY_HOUR_UTC,
            "friday_exit_hour_utc": FRIDAY_EXIT_HOUR_UTC,
            "excluded_rollover_hours_utc": list(ROLLOVER_HOURS_UTC),
        },
        "holdout_start": HOLDOUT_START.isoformat(),
        "preholdout": {
            "development_stress_plus_8_pips": _public_metrics(development_stress8),
            "validation_stress_plus_8_pips": _public_metrics(validation_stress8),
            "windows": windows,
            "aggregate": {
                "base": _public_metrics(pre_base),
                "stress_plus_4_pips": _public_metrics(pre_stress4),
                "stress_plus_8_pips": _public_metrics(pre_stress8),
                "stress_plus_12_pips": _public_metrics(pre_stress12),
                "stress_8_block_bootstrap_probability_positive": round(bootstrap8, 6),
                "calendar_year_stress_plus_8_pips": calendar_stress8,
                "direction_stress_plus_8_pips": direction_stress8,
                "neighborhood_variants_passed": neighborhood_passes,
                "neighborhood_variants_total": len(neighborhood),
                "passed": preholdout_passed,
            },
            "neighborhood": neighborhood,
        },
        "holdout_inspected": False,
        "holdout": None,
        "latest_setup": None,
        "decision": "preholdout_gate_failed",
        "limitations": [
            "Historical Practice simulation is not a broker fill record or a profit guarantee.",
            "The candidate, holdout start and all release gates are fixed before the final 20 percent is inspected.",
            "Actual bid/ask candles, adverse slippage, stop-first ambiguous bars, rollover exclusions, Friday exits and additional cost stresses are modeled.",
            "Exact financing, latency, partial fills, market impact and stop slippage beyond the modeled candle gap convention are not fully modeled.",
            "A passing result authorizes only a separate tightly bounded OANDA Practice execution review; it never authorizes live trading.",
        ],
    }
    if not preholdout_passed:
        return result

    holdout_trades = backtest(features, maps, holdout_index, len(primary.bars))
    holdout_base = metrics(holdout_trades)
    holdout_stress4 = metrics(holdout_trades, 4.0)
    holdout_stress8 = metrics(holdout_trades, 8.0)
    holdout_stress12 = metrics(holdout_trades, 12.0)
    probability4 = _block_bootstrap_probability_positive(holdout_trades, 4.0)
    probability8 = _block_bootstrap_probability_positive(holdout_trades, 8.0)
    midpoint = holdout_index + (len(primary.bars) - holdout_index) // 2
    first_half_stress4 = metrics(
        backtest(features, maps, holdout_index, midpoint), 4.0
    )
    second_half_stress4 = metrics(
        backtest(features, maps, midpoint, len(primary.bars)), 4.0
    )
    holdout_passed = (
        holdout_base["trades"] >= 25
        and holdout_base["long_trades"] >= 5
        and holdout_base["short_trades"] >= 5
        and holdout_base["sum_r"] > 0
        and holdout_base["profit_factor"] >= 1.20
        and holdout_base["maximum_drawdown_r"] <= 7.0
        and holdout_stress4["sum_r"] > 0
        and holdout_stress4["profit_factor"] >= 1.15
        and holdout_stress4["maximum_drawdown_r"] <= 8.0
        and holdout_stress8["sum_r"] > 0
        and holdout_stress8["profit_factor"] >= 1.05
        and holdout_stress8["maximum_drawdown_r"] <= 9.0
        and probability4 >= 0.75
        and probability8 >= 0.65
        and first_half_stress4["sum_r"] > 0
        and second_half_stress4["sum_r"] > 0
    )
    result["holdout_inspected"] = True
    result["holdout"] = {
        "start": primary.bars[holdout_index].time.isoformat(),
        "end": primary.bars[-1].time.isoformat(),
        "base": _public_metrics(holdout_base),
        "stress_plus_4_pips": _public_metrics(holdout_stress4),
        "stress_plus_8_pips": _public_metrics(holdout_stress8),
        "stress_plus_12_pips": _public_metrics(holdout_stress12),
        "stress_4_block_bootstrap_probability_positive": round(probability4, 6),
        "stress_8_block_bootstrap_probability_positive": round(probability8, 6),
        "first_half_stress_plus_4_pips": _public_metrics(first_half_stress4),
        "second_half_stress_plus_4_pips": _public_metrics(second_half_stress4),
        "passed": holdout_passed,
    }
    result["decision"] = (
        "eligible_for_separate_guarded_practice_execution_review"
        if holdout_passed
        else "holdout_gate_failed"
    )
    if holdout_passed:
        latest = setup_at_signal(features, maps, len(primary.bars) - 1)
        if latest is not None:
            result["latest_setup"] = {
                "signal_time": latest["signal_time"].isoformat(),
                "direction": "long" if latest["direction"] == 1 else "short",
                "median_score": round(float(latest["median_score"]), 6),
                "primary_score": round(float(latest["primary_score"]), 6),
                "positive_pairs": int(latest["positive_pairs"]),
                "negative_pairs": int(latest["negative_pairs"]),
                "atr": round(float(latest["atr"]), 8),
                "requires_current_pricing_and_spread_check": True,
            }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sealed OANDA Practice Wave 4 gate.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="state/oanda-wave4-results.json")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
            raise LabError("Wave 4 evaluation input is too large.")
        result = evaluate_bundle(json.loads(source.read_text(encoding="utf-8")))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pre = result["preholdout"]["aggregate"]
        print(
            f"Wave 4 preholdout: {pre['base']['trades']} trades, "
            f"stress8 {pre['stress_plus_8_pips']['sum_r']:.3f}R, "
            f"stress12 {pre['stress_plus_12_pips']['sum_r']:.3f}R, "
            f"neighborhood {pre['neighborhood_variants_passed']}/"
            f"{pre['neighborhood_variants_total']}, passed={pre['passed']}."
        )
        if result["holdout_inspected"]:
            holdout = result["holdout"]
            print(
                f"Wave 4 sealed holdout: {holdout['base']['trades']} trades, "
                f"base {holdout['base']['sum_r']:.3f}R, "
                f"stress4 {holdout['stress_plus_4_pips']['sum_r']:.3f}R, "
                f"stress8 {holdout['stress_plus_8_pips']['sum_r']:.3f}R, "
                f"passed={holdout['passed']}."
            )
        print(f"Wave 4 decision: {result['decision']}.")
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Wave 4 evaluation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
