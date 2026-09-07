"""Fresh, read-only OANDA Practice strategy tournament.

The module downloads completed bid/ask candles for a fixed whitelist of liquid
USD-quoted currency pairs and evaluates several strategy families that are
unrelated to the retired SMA20/SMA50 crossover. Development and validation data
select candidates; the final holdout is used only as an acceptance gate.

No order endpoint, live hostname, scheduler, transfer, or withdrawal capability
is implemented here.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import sys
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .lab import LabError, MAX_RESPONSE, NoRedirects, PRACTICE_ORIGIN

INSTRUMENTS = ("EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD")
GRANULARITY = "H1"
ACCOUNT_ID_RE = re.compile(r"[0-9]+(?:-[0-9]+){3}", re.ASCII)
SLIPPAGE = 0.00001
MIN_STOP = 0.00040
MAX_SPREAD = 0.00030
START_EQUITY = 1_000.0
RISK_PERCENT = 0.25
LEVERAGE_CAP = 10.0


@dataclass(frozen=True)
class Bar:
    time: datetime
    bid_o: float
    bid_h: float
    bid_l: float
    bid_c: float
    ask_o: float
    ask_h: float
    ask_l: float
    ask_c: float


@dataclass(frozen=True)
class Features:
    bars: tuple[Bar, ...]
    open: tuple[float, ...]
    high: tuple[float, ...]
    low: tuple[float, ...]
    close: tuple[float, ...]
    atr: tuple[float | None, ...]


@dataclass(frozen=True)
class Candidate:
    family: str
    parameters: tuple[tuple[str, float | int], ...]

    @property
    def params(self) -> dict[str, float | int]:
        return dict(self.parameters)

    @property
    def identifier(self) -> str:
        tail = ",".join(f"{key}={value}" for key, value in self.parameters)
        return f"{self.family}[{tail}]"


@dataclass(frozen=True)
class Signal:
    direction: int
    stop_distance: float
    target_r: float
    max_hold: int
    confidence: float
    reason: str


class PracticeResearchClient:
    """Strict GET-only OANDA Practice reader for research data."""

    def __init__(self, token: object, account_id: object) -> None:
        token = token.strip() if isinstance(token, str) else ""
        account_id = account_id.strip() if isinstance(account_id, str) else ""
        if not token or len(token) > 4096 or any(ch.isspace() for ch in token):
            raise LabError("Missing or invalid OANDA practice token.")
        if not ACCOUNT_ID_RE.fullmatch(account_id) or len(account_id) > 128:
            raise LabError("Missing or invalid OANDA practice account ID.")
        self._token = token
        self._account = account_id
        self._opener = build_opener(NoRedirects())

    @classmethod
    def from_environment(cls) -> "PracticeResearchClient":
        return cls(
            os.environ.get("OANDA_DEMO_TOKEN"),
            os.environ.get("OANDA_DEMO_ACCOUNT_ID"),
        )

    def _get(self, resource: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        allowed = {"summary", "instruments"}
        allowed.update(f"instruments/{name}/candles" for name in INSTRUMENTS)
        if resource not in allowed:
            raise LabError("Unapproved OANDA Practice research route.")
        url = f"{PRACTICE_ORIGIN}/v3/accounts/{self._account}/{resource}"
        if params:
            url += "?" + urlencode(params)
        request = Request(
            url,
            headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=25) as response:
                body = response.read(MAX_RESPONSE + 1)
                if len(body) > MAX_RESPONSE:
                    raise LabError("OANDA Practice response exceeded the size limit.")
        except HTTPError as error:
            raise LabError(
                f"OANDA Practice research request returned HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError):
            raise LabError("OANDA Practice research request failed.") from None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise LabError("OANDA Practice returned invalid JSON.") from None
        if not isinstance(payload, dict):
            raise LabError("OANDA Practice returned an unexpected response.")
        return payload

    def summary(self) -> dict[str, Any]:
        account = self._get("summary").get("account")
        if not isinstance(account, dict) or account.get("currency") != "USD":
            raise LabError("A USD-denominated OANDA Practice account is required.")
        return {
            "environment": "practice",
            "currency": "USD",
            "balance": _finite(account.get("balance"), "balance"),
            "nav": _finite(account.get("NAV"), "NAV"),
            "open_trade_count": int(account.get("openTradeCount", 0)),
            "pending_order_count": int(account.get("pendingOrderCount", 0)),
        }

    def available_instruments(self) -> set[str]:
        payload = self._get("instruments", {"instruments": ",".join(INSTRUMENTS)})
        rows = payload.get("instruments")
        if not isinstance(rows, list):
            raise LabError("OANDA Practice returned invalid instrument metadata.")
        result = {
            row.get("name")
            for row in rows
            if isinstance(row, dict) and row.get("type") == "CURRENCY"
        }
        return {name for name in result if isinstance(name, str)}

    def candles(self, instrument: str, count: int = 5000) -> dict[str, Any]:
        if instrument not in INSTRUMENTS:
            raise LabError("Unapproved research instrument.")
        if type(count) is not int or not 1000 <= count <= 5000:
            raise LabError("Research candle count must be between 1000 and 5000.")
        payload = self._get(
            f"instruments/{instrument}/candles",
            {
                "granularity": GRANULARITY,
                "price": "BA",
                "count": count,
                "smooth": "false",
            },
        )
        parse_candles(payload, instrument)
        return payload


def _finite(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise LabError(f"Invalid {name}.") from None
    if not math.isfinite(number):
        raise LabError(f"Invalid {name}.")
    return number


def _price(record: dict[str, Any], side: str, key: str) -> float:
    try:
        value = _finite(record[side][key], "candle price")
    except (KeyError, TypeError):
        raise LabError("Malformed candle price.") from None
    if value <= 0:
        raise LabError("Candle prices must be positive.")
    return value


def parse_candles(payload: object, instrument: str) -> tuple[Bar, ...]:
    if (
        not isinstance(payload, dict)
        or payload.get("instrument") != instrument
        or payload.get("granularity") != GRANULARITY
    ):
        raise LabError(f"Expected {instrument} {GRANULARITY} candles.")
    rows = payload.get("candles")
    if not isinstance(rows, list) or not 1000 <= len(rows) <= 5000:
        raise LabError("Expected 1000-5000 candle records.")
    bars: list[Bar] = []
    for row in rows:
        if not isinstance(row, dict):
            raise LabError("Malformed candle record.")
        if row.get("complete") is not True:
            continue
        try:
            stamp = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            raise LabError("Malformed candle timestamp.") from None
        if stamp.tzinfo is None:
            raise LabError("Candle timestamps must include a timezone.")
        stamp = stamp.astimezone(timezone.utc)
        bar = Bar(
            time=stamp,
            bid_o=_price(row, "bid", "o"),
            bid_h=_price(row, "bid", "h"),
            bid_l=_price(row, "bid", "l"),
            bid_c=_price(row, "bid", "c"),
            ask_o=_price(row, "ask", "o"),
            ask_h=_price(row, "ask", "h"),
            ask_l=_price(row, "ask", "l"),
            ask_c=_price(row, "ask", "c"),
        )
        if not (
            bar.bid_l <= min(bar.bid_o, bar.bid_c) <= max(bar.bid_o, bar.bid_c) <= bar.bid_h
            and bar.ask_l <= min(bar.ask_o, bar.ask_c) <= max(bar.ask_o, bar.ask_c) <= bar.ask_h
            and bar.ask_o >= bar.bid_o
            and bar.ask_c >= bar.bid_c
        ):
            raise LabError("Invalid candle OHLC or crossed bid/ask values.")
        if bars and stamp <= bars[-1].time:
            raise LabError("Candles must be strictly chronological and unique.")
        bars.append(bar)
    if len(bars) < 950:
        raise LabError("Too few completed candles for the tournament.")
    return tuple(bars)


def build_features(bars: tuple[Bar, ...], atr_period: int = 14) -> Features:
    mid_open = tuple((bar.bid_o + bar.ask_o) / 2 for bar in bars)
    mid_high = tuple((bar.bid_h + bar.ask_h) / 2 for bar in bars)
    mid_low = tuple((bar.bid_l + bar.ask_l) / 2 for bar in bars)
    mid_close = tuple((bar.bid_c + bar.ask_c) / 2 for bar in bars)
    true_range: list[float] = []
    for index, bar in enumerate(bars):
        previous = mid_close[index - 1] if index else mid_close[index]
        true_range.append(
            max(mid_high[index] - mid_low[index], abs(mid_high[index] - previous), abs(mid_low[index] - previous))
        )
    atr: list[float | None] = [None] * len(bars)
    rolling = sum(true_range[:atr_period])
    if len(bars) >= atr_period:
        atr[atr_period - 1] = rolling / atr_period
    for index in range(atr_period, len(bars)):
        rolling += true_range[index] - true_range[index - atr_period]
        atr[index] = rolling / atr_period
    return Features(bars, mid_open, mid_high, mid_low, mid_close, tuple(atr))


def _quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise LabError("Cannot calculate an empty quantile.")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _efficiency_ratio(close: tuple[float, ...], end: int, length: int) -> float:
    start = end - length
    if start < 0:
        return 1.0
    net = abs(close[end] - close[start])
    path = sum(abs(close[index] - close[index - 1]) for index in range(start + 1, end + 1))
    return net / path if path > 0 else 0.0


def candidate_signal(candidate: Candidate, features: Features, entry_index: int) -> Signal | None:
    if entry_index <= 100 or entry_index > len(features.bars):
        return None
    family = candidate.family
    p = candidate.params
    j = entry_index - 1
    atr = features.atr[j]
    if atr is None or atr <= 0:
        return None
    last_open = features.open[j]
    last_high = features.high[j]
    last_low = features.low[j]
    last_close = features.close[j]
    last_range = max(last_high - last_low, 1e-12)

    if family == "compression_breakout":
        channel = int(p["channel"])
        window = int(p["window"])
        if entry_index <= max(channel + 2, window + 15):
            return None
        atr_values = [
            value
            for value in features.atr[j - window + 1 : j + 1]
            if value is not None
        ]
        threshold = _quantile(atr_values, float(p["quantile"]))
        if atr > threshold:
            return None
        prior_high = max(features.high[j - channel : j])
        prior_low = min(features.low[j - channel : j])
        close_location = (last_close - last_low) / last_range
        if last_close > prior_high and close_location >= 0.72 and last_close > last_open:
            strength = (last_close - prior_high) / atr + max(0.0, 1 - atr / threshold)
            return Signal(1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), strength, "compressed upside breakout")
        if last_close < prior_low and close_location <= 0.28 and last_close < last_open:
            strength = (prior_low - last_close) / atr + max(0.0, 1 - atr / threshold)
            return Signal(-1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), strength, "compressed downside breakout")
        return None

    if family == "range_reversion":
        lookback = int(p["lookback"])
        if entry_index <= lookback + 2:
            return None
        baseline = features.close[j - lookback : j]
        mean = statistics.fmean(baseline)
        deviation = statistics.pstdev(baseline)
        if deviation <= 1e-12:
            return None
        zscore = (last_close - mean) / deviation
        efficiency = _efficiency_ratio(features.close, j, lookback)
        if efficiency > float(p["max_efficiency"]):
            return None
        close_location = (last_close - last_low) / last_range
        if zscore >= float(p["zscore"]) and last_close < last_open and close_location <= 0.58:
            return Signal(-1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), abs(zscore) - float(p["zscore"]) + (float(p["max_efficiency"]) - efficiency), "range upper-tail rejection")
        if zscore <= -float(p["zscore"]) and last_close > last_open and close_location >= 0.42:
            return Signal(1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), abs(zscore) - float(p["zscore"]) + (float(p["max_efficiency"]) - efficiency), "range lower-tail rejection")
        return None

    if family == "failed_breakout":
        channel = int(p["channel"])
        if entry_index <= channel + 2:
            return None
        prior_high = max(features.high[j - channel : j])
        prior_low = min(features.low[j - channel : j])
        upper_wick = (last_high - max(last_open, last_close)) / last_range
        lower_wick = (min(last_open, last_close) - last_low) / last_range
        buffer = atr * float(p["buffer_atr"])
        if last_high > prior_high and last_close < prior_high and last_close < last_open and upper_wick >= float(p["wick"]):
            distance = max(MIN_STOP, last_high - last_close + buffer, atr * 0.75)
            return Signal(-1, distance, float(p["target_r"]), int(p["hold"]), upper_wick + (last_high - prior_high) / atr, "failed upside breakout")
        if last_low < prior_low and last_close > prior_low and last_close > last_open and lower_wick >= float(p["wick"]):
            distance = max(MIN_STOP, last_close - last_low + buffer, atr * 0.75)
            return Signal(1, distance, float(p["target_r"]), int(p["hold"]), lower_wick + (prior_low - last_low) / atr, "failed downside breakout")
        return None

    if family == "impulse_pullback":
        window = int(p["window"])
        if entry_index <= window + 3:
            return None
        impulse_start = j - window - 1
        impulse_end = j - 1
        move = features.close[impulse_end] - features.close[impulse_start]
        reference_atr = features.atr[impulse_end]
        if reference_atr is None or abs(move) < float(p["impulse_atr"]) * reference_atr:
            return None
        retracement = features.close[impulse_end] - last_close
        fraction = retracement / move if move != 0 else 0.0
        if move > 0 and 0 < fraction <= float(p["max_pullback"]) and last_close < last_open and last_close > features.close[impulse_start] + move * 0.5:
            return Signal(1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), abs(move) / reference_atr - float(p["impulse_atr"]), "bullish impulse pullback")
        if move < 0 and 0 < fraction <= float(p["max_pullback"]) and last_close > last_open and last_close < features.close[impulse_start] + move * 0.5:
            return Signal(-1, max(MIN_STOP, atr * float(p["stop_atr"])), float(p["target_r"]), int(p["hold"]), abs(move) / reference_atr - float(p["impulse_atr"]), "bearish impulse pullback")
        return None

    if family == "session_breakout":
        range_end = int(p["range_end"])
        trade_end = int(p["trade_end"])
        hour = features.bars[j].time.hour
        if not range_end < hour <= trade_end:
            return None
        day = features.bars[j].time.date()
        session_indices = [
            index
            for index in range(max(0, j - 30), j)
            if features.bars[index].time.date() == day
            and 0 <= features.bars[index].time.hour <= range_end
        ]
        if len(session_indices) < range_end + 1:
            return None
        session_high = max(features.high[index] for index in session_indices)
        session_low = min(features.low[index] for index in session_indices)
        session_range = session_high - session_low
        if session_range <= 0 or session_range > atr * 8:
            return None
        close_location = (last_close - last_low) / last_range
        distance = max(MIN_STOP, atr * float(p["stop_atr"]), session_range * float(p["range_stop_fraction"]))
        if last_close > session_high and last_close > last_open and close_location >= 0.65:
            return Signal(1, distance, float(p["target_r"]), int(p["hold"]), (last_close - session_high) / atr, "early-session upside break")
        if last_close < session_low and last_close < last_open and close_location <= 0.35:
            return Signal(-1, distance, float(p["target_r"]), int(p["hold"]), (session_low - last_close) / atr, "early-session downside break")
        return None

    raise LabError("Unknown strategy family.")


def _exit_trade(
    features: Features,
    entry_index: int,
    end: int,
    signal: Signal,
    entry_price: float,
) -> tuple[int, float, str]:
    stop = entry_price - signal.direction * signal.stop_distance
    target = entry_price + signal.direction * signal.stop_distance * signal.target_r
    final_index = min(end - 1, entry_index + signal.max_hold - 1)
    for index in range(entry_index, final_index + 1):
        bar = features.bars[index]
        if signal.direction == 1:
            stop_hit = bar.bid_l <= stop
            target_hit = bar.bid_h >= target
        else:
            stop_hit = bar.ask_h >= stop
            target_hit = bar.ask_l <= target
        if stop_hit:
            price = min(bar.bid_o, stop) if signal.direction == 1 else max(bar.ask_o, stop)
            return index, price - signal.direction * SLIPPAGE, "stop"
        if target_hit:
            return index, target - signal.direction * SLIPPAGE, "target"
        if bar.time.hour >= 20 or (bar.time.weekday() == 4 and bar.time.hour >= 18):
            close = bar.bid_c if signal.direction == 1 else bar.ask_c
            return index, close - signal.direction * SLIPPAGE, "session_close"
    bar = features.bars[final_index]
    close = bar.bid_c if signal.direction == 1 else bar.ask_c
    return final_index, close - signal.direction * SLIPPAGE, "time_exit"


def backtest(
    features: Features,
    candidate: Candidate,
    start: int,
    end: int,
    *,
    start_equity: float = START_EQUITY,
    risk_percent: float = RISK_PERCENT,
) -> dict[str, Any]:
    if not 0 <= start < end <= len(features.bars):
        raise LabError("Invalid backtest segment.")
    equity = start_equity
    peak = equity
    maximum_drawdown = 0.0
    trades: list[dict[str, Any]] = []
    index = max(start, 110)
    while index < end:
        bar = features.bars[index]
        if bar.time.weekday() >= 5 or not 6 <= bar.time.hour <= 19:
            index += 1
            continue
        atr = features.atr[index - 1]
        if atr is None:
            index += 1
            continue
        spread = bar.ask_o - bar.bid_o
        if spread <= 0 or spread > min(MAX_SPREAD, atr * 0.45):
            index += 1
            continue
        signal = candidate_signal(candidate, features, index)
        if signal is None:
            index += 1
            continue
        stop_distance = max(signal.stop_distance, spread * 4, MIN_STOP)
        signal = Signal(
            signal.direction,
            stop_distance,
            signal.target_r,
            signal.max_hold,
            signal.confidence,
            signal.reason,
        )
        entry = (bar.ask_o + SLIPPAGE) if signal.direction == 1 else (bar.bid_o - SLIPPAGE)
        risk_dollars = equity * risk_percent / 100
        units_by_risk = math.floor(risk_dollars / (stop_distance + SLIPPAGE * 2))
        units_by_notional = math.floor(equity * LEVERAGE_CAP / entry)
        units = min(units_by_risk, units_by_notional)
        if units < 1:
            index += 1
            continue
        exit_index, exit_price, exit_reason = _exit_trade(features, index, end, signal, entry)
        pnl = signal.direction * units * (exit_price - entry)
        before = equity
        equity += pnl
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, (peak - equity) / peak if peak else 0.0)
        trades.append(
            {
                "entry_time": bar.time.isoformat(),
                "exit_time": features.bars[exit_index].time.isoformat(),
                "direction": signal.direction,
                "units": units,
                "pnl": pnl,
                "return_on_equity": pnl / before if before else 0.0,
                "reason": signal.reason,
                "exit_reason": exit_reason,
                "confidence": signal.confidence,
            }
        )
        if equity <= start_equity * 0.90:
            break
        index = exit_index + 1
    wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
    losses = [trade["pnl"] for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "start_equity": start_equity,
        "end_equity": equity,
        "return_percent": (equity / start_equity - 1) * 100,
        "max_drawdown_percent": maximum_drawdown * 100,
        "trades": len(trades),
        "wins": len(wins),
        "win_rate_percent": (len(wins) / len(trades) * 100) if trades else 0.0,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "trade_returns": [trade["return_on_equity"] for trade in trades],
        "trade_log": trades,
    }


def aggregate_results(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    start = sum(result["start_equity"] for result in results.values())
    end = sum(result["end_equity"] for result in results.values())
    gross_profit = sum(result["gross_profit"] for result in results.values())
    gross_loss = sum(result["gross_loss"] for result in results.values())
    returns = {name: result["return_percent"] for name, result in results.items()}
    positive_profit = [max(0.0, result["end_equity"] - result["start_equity"]) for result in results.values()]
    sum_positive = sum(positive_profit)
    concentration = max(positive_profit, default=0.0) / sum_positive if sum_positive > 0 else 1.0
    trade_returns = list(itertools.chain.from_iterable(result["trade_returns"] for result in results.values()))
    return {
        "return_percent": (end / start - 1) * 100,
        "max_drawdown_percent": max((result["max_drawdown_percent"] for result in results.values()), default=0.0),
        "trades": sum(result["trades"] for result in results.values()),
        "wins": sum(result["wins"] for result in results.values()),
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
        "positive_instruments": sum(value > 0 for value in returns.values()),
        "worst_instrument_return_percent": min(returns.values(), default=0.0),
        "best_instrument_return_percent": max(returns.values(), default=0.0),
        "profit_concentration": concentration,
        "instrument_returns": returns,
        "trade_returns": trade_returns,
    }


def generate_candidates() -> tuple[Candidate, ...]:
    result: list[Candidate] = []

    def add(family: str, **parameters: float | int) -> None:
        result.append(Candidate(family, tuple(sorted(parameters.items()))))

    for channel, quantile, target in itertools.product((12, 24, 48), (0.25, 0.40), (1.6, 2.4)):
        add("compression_breakout", channel=channel, window=72, quantile=quantile, stop_atr=1.2, target_r=target, hold=12)
    for lookback, zscore, efficiency in itertools.product((16, 24, 36), (1.6, 2.0), (0.30, 0.45)):
        add("range_reversion", lookback=lookback, zscore=zscore, max_efficiency=efficiency, stop_atr=1.25, target_r=1.15, hold=10)
    for channel, wick, target in itertools.product((12, 24, 48), (0.35, 0.50), (1.4, 2.0)):
        add("failed_breakout", channel=channel, wick=wick, buffer_atr=0.20, target_r=target, hold=10)
    for window, impulse, pullback in itertools.product((3, 6, 12), (1.5, 2.1), (0.30, 0.50)):
        add("impulse_pullback", window=window, impulse_atr=impulse, max_pullback=pullback, stop_atr=1.2, target_r=2.0, hold=12)
    for range_end, target, stop_fraction in itertools.product((4, 5), (1.5, 2.0), (0.50, 0.75)):
        add("session_breakout", range_end=range_end, trade_end=11, stop_atr=1.0, range_stop_fraction=stop_fraction, target_r=target, hold=10)
    return tuple(result)


def _segment_results(
    features_by_instrument: dict[str, Features],
    candidate: Candidate,
    segment: str,
) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for instrument, features in features_by_instrument.items():
        length = len(features.bars)
        development_end = int(length * 0.60)
        validation_end = int(length * 0.80)
        if segment == "development":
            start, end = 0, development_end
        elif segment == "validation":
            start, end = development_end, validation_end
        elif segment == "holdout":
            start, end = validation_end, length
        else:
            raise LabError("Unknown tournament segment.")
        results[instrument] = backtest(features, candidate, start, end)
    return aggregate_results(results)


def _selection_score(development: dict[str, Any], validation: dict[str, Any]) -> float:
    stability = min(development["return_percent"], validation["return_percent"])
    return (
        validation["return_percent"]
        + stability * 0.6
        + min(validation["profit_factor"] - 1.0, 1.0) * 2.0
        + math.sqrt(max(validation["trades"], 0)) * 0.08
        - validation["max_drawdown_percent"] * 0.8
        - max(0.0, -validation["worst_instrument_return_percent"]) * 0.25
    )


def _qualifies_for_holdout(development: dict[str, Any], validation: dict[str, Any]) -> bool:
    return (
        development["return_percent"] > 0
        and validation["return_percent"] > 0
        and development["trades"] >= 20
        and validation["trades"] >= 8
        and development["profit_factor"] >= 1.02
        and validation["profit_factor"] >= 1.02
        and validation["max_drawdown_percent"] <= 8.0
        and validation["positive_instruments"] >= 2
        and validation["worst_instrument_return_percent"] > -3.0
    )


def bootstrap_probability_positive(trade_returns: list[float], draws: int = 2000) -> float:
    if not trade_returns:
        return 0.0
    generator = random.Random(20260907)
    positive = 0
    count = len(trade_returns)
    for _ in range(draws):
        compounded = 1.0
        for _ in range(count):
            compounded *= 1.0 + generator.choice(trade_returns)
        positive += compounded > 1.0
    return positive / draws


def _passes_holdout(holdout: dict[str, Any]) -> bool:
    probability = bootstrap_probability_positive(holdout["trade_returns"])
    return (
        holdout["return_percent"] > 0
        and holdout["trades"] >= 8
        and holdout["profit_factor"] >= 1.05
        and holdout["max_drawdown_percent"] <= 6.0
        and holdout["positive_instruments"] >= 2
        and holdout["worst_instrument_return_percent"] > -2.5
        and holdout["profit_concentration"] <= 0.85
        and probability >= 0.55
    )


def latest_signals(features_by_instrument: dict[str, Features], candidate: Candidate) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for instrument, features in features_by_instrument.items():
        signal = candidate_signal(candidate, features, len(features.bars))
        if signal is None:
            continue
        last = features.bars[-1]
        spread = last.ask_c - last.bid_c
        atr = features.atr[-1]
        if last.time.weekday() >= 5 or atr is None or spread <= 0 or spread > min(MAX_SPREAD, atr * 0.45):
            continue
        signals.append(
            {
                "instrument": instrument,
                "direction": "long" if signal.direction == 1 else "short",
                "stop_distance": signal.stop_distance,
                "target_r": signal.target_r,
                "max_hold_hours": signal.max_hold,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "last_complete_candle": last.time.isoformat(),
            }
        )
    return sorted(signals, key=lambda item: item["confidence"], reverse=True)


def evaluate_bundle(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "practice_market_data":
        raise LabError("Invalid tournament input bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Tournament input must contain the complete instrument whitelist.")
    features_by_instrument = {
        instrument: build_features(parse_candles(raw[instrument], instrument))
        for instrument in INSTRUMENTS
    }
    candidates = generate_candidates()
    screened: list[dict[str, Any]] = []
    for candidate in candidates:
        development = _segment_results(features_by_instrument, candidate, "development")
        validation = _segment_results(features_by_instrument, candidate, "validation")
        if _qualifies_for_holdout(development, validation):
            screened.append(
                {
                    "candidate": candidate,
                    "development": development,
                    "validation": validation,
                    "selection_score": _selection_score(development, validation),
                }
            )
    screened.sort(key=lambda row: row["selection_score"], reverse=True)
    finalists: list[dict[str, Any]] = []
    winner: dict[str, Any] | None = None
    for row in screened[:8]:
        candidate = row["candidate"]
        holdout = _segment_results(features_by_instrument, candidate, "holdout")
        probability = bootstrap_probability_positive(holdout["trade_returns"])
        passed = _passes_holdout(holdout)
        final = {
            "candidate_id": candidate.identifier,
            "family": candidate.family,
            "parameters": candidate.params,
            "selection_score": row["selection_score"],
            "development": _public_metrics(row["development"]),
            "validation": _public_metrics(row["validation"]),
            "holdout": _public_metrics(holdout),
            "holdout_bootstrap_probability_positive": probability,
            "passed": passed,
        }
        finalists.append(final)
        if winner is None and passed:
            winner = {
                **final,
                "latest_signals": latest_signals(features_by_instrument, candidate),
            }
    digest = hashlib.sha256(
        json.dumps(bundle["candles"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "status": "fresh_strategy_tournament",
        "environment": "practice",
        "data_sha256": digest,
        "instrument_count": len(INSTRUMENTS),
        "instruments": list(INSTRUMENTS),
        "granularity": GRANULARITY,
        "candidate_count": len(candidates),
        "development_fraction": 0.60,
        "validation_fraction": 0.20,
        "holdout_fraction": 0.20,
        "risk_percent_per_trade": RISK_PERCENT,
        "screened_candidate_count": len(screened),
        "finalists": finalists,
        "winner": winner,
        "decision": "eligible_for_guarded_demo_execution" if winner else "no_strategy_passed_holdout",
        "limitations": [
            "Historical simulation is not a broker fill record or a profit guarantee.",
            "Only four USD-quoted currency pairs and the latest 5,000 H1 candles per pair are tested.",
            "Bid/ask execution, adverse slippage, stop-first ambiguous bars, time exits, and a ten-times notional cap are modeled.",
            "Development and validation select candidates; holdout only accepts or rejects them.",
            "A passing result authorizes at most a separate guarded Practice-only execution review, never live trading.",
        ],
    }


def _public_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "return_percent",
        "max_drawdown_percent",
        "trades",
        "wins",
        "profit_factor",
        "positive_instruments",
        "worst_instrument_return_percent",
        "best_instrument_return_percent",
        "profit_concentration",
        "instrument_returns",
    )
    result: dict[str, Any] = {}
    for key in keys:
        value = metrics[key]
        if isinstance(value, float):
            value = round(value, 6)
        elif isinstance(value, dict):
            value = {name: round(number, 6) for name, number in value.items()}
        result[key] = value
    return result


def fetch_bundle(client: PracticeResearchClient, count: int = 5000) -> dict[str, Any]:
    summary = client.summary()
    if summary["open_trade_count"] or summary["pending_order_count"]:
        raise LabError("Existing practice trades or pending orders found; research fetch will not alter them.")
    available = client.available_instruments()
    missing = [instrument for instrument in INSTRUMENTS if instrument not in available]
    if missing:
        raise LabError("One or more tournament instruments are unavailable for this account.")
    candles = {instrument: client.candles(instrument, count) for instrument in INSTRUMENTS}
    return {
        "status": "practice_market_data",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "candles": candles,
    }


def _read_json(path: str) -> Any:
    source = Path(path)
    if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
        raise LabError("Tournament input file is too large.")
    return json.loads(source.read_text(encoding="utf-8"))


def _write_json(path: str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fresh OANDA Practice strategy tournament.")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Download whitelisted Practice market data with GET requests only.")
    fetch.add_argument("--output", default="state/oanda-tournament-data.json")
    fetch.add_argument("--count", type=int, default=5000)
    evaluate = commands.add_parser("evaluate", help="Run development, validation, and untouched holdout tests.")
    evaluate.add_argument("--input", required=True)
    evaluate.add_argument("--output", default="state/oanda-tournament-results.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            payload = fetch_bundle(PracticeResearchClient.from_environment(), args.count)
            _write_json(args.output, payload)
            print(
                f"Captured {len(INSTRUMENTS)} whitelisted instruments for a read-only Practice tournament. No orders sent."
            )
        else:
            payload = evaluate_bundle(_read_json(args.input))
            _write_json(args.output, payload)
            print(
                f"Tournament tested {payload['candidate_count']} fresh candidates; "
                f"screened {payload['screened_candidate_count']}; decision: {payload['decision']}."
            )
            for finalist in payload["finalists"]:
                holdout = finalist["holdout"]
                print(
                    f"Finalist {finalist['candidate_id']}: holdout return "
                    f"{holdout['return_percent']:.3f}%, PF {holdout['profit_factor']:.3f}, "
                    f"drawdown {holdout['max_drawdown_percent']:.3f}%, "
                    f"trades {holdout['trades']}, passed={finalist['passed']}."
                )
            if payload["winner"]:
                print(f"Winner: {payload['winner']['candidate_id']}")
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Tournament file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
