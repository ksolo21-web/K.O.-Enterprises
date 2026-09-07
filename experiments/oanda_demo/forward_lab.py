"""Tiny, forward-only OANDA Practice experiment selector and executor.

This module deliberately does not reuse or retune the rejected Wave 1-4
strategies. It selects between two simple *current-condition* arms across four
USD-quoted liquid pairs:

* adaptive trend: multi-horizon direction plus path efficiency;
* exhaustion reversal: statistical extension plus a completed reversal candle.

The scanner is read-only. Execution is separately gated by an exact approval
phrase and a short-lived plan-specific permit. At most one Practice market order
may be submitted, with attached stop-loss and take-profit prices. The live OANDA
hostname is absent by design. There is no scheduler, retry loop, transfer,
withdrawal, deposit, account-configuration, trade-close, or order-cancel route.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .lab import LabError, MAX_RESPONSE, NoRedirects, PRACTICE_ORIGIN
from .tournament import build_features, parse_candles

INSTRUMENTS = ("EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD")
GRANULARITY = "H1"
CANDLE_COUNT = 240
ACCOUNT_ID_RE = re.compile(r"[0-9]+(?:-[0-9]+){3}", re.ASCII)
APPROVAL_PHRASE = "K_O_PRACTICE_FORWARD_ONLY_2026_09_07"
DEFAULT_PERMIT = "OANDA_PRACTICE_EXECUTION_PERMIT.json"
MAX_PRICE_AGE_SECONDS = 120
MAX_SPREAD = 0.00035
MAX_SPREAD_ATR = 0.22
MAX_VIRTUAL_RISK_USD = 10.0
RISK_FRACTION_OF_NAV = 0.0002
MAX_UNITS = 5_000
MIN_STOP = 0.0010
SLIPPAGE_BOUND_MIN = 0.0002
FORBIDDEN_UTC_HOURS = (20, 21)


@dataclass(frozen=True)
class MarketFeatures:
    instrument: str
    signal_time: datetime
    close: float
    atr: float
    score_24: float
    score_6: float
    efficiency_24: float
    zscore_24: float
    candle_direction: int
    close_location: float


class ForwardPracticeClient:
    """Strict OANDA Practice client with one narrowly scoped POST route."""

    def __init__(self, token: object, account_id: object, opener=None) -> None:
        token = token.strip() if isinstance(token, str) else ""
        account_id = account_id.strip() if isinstance(account_id, str) else ""
        if not token or len(token) > 4096 or any(char.isspace() for char in token):
            raise LabError("Missing or invalid OANDA Practice token.")
        if not account_id or len(account_id) > 128 or not ACCOUNT_ID_RE.fullmatch(account_id):
            raise LabError("Missing or invalid OANDA Practice account ID.")
        self._token = token
        self._account = account_id
        self._opener = opener or build_opener(NoRedirects())

    @classmethod
    def from_environment(cls) -> "ForwardPracticeClient":
        return cls(
            os.environ.get("OANDA_DEMO_TOKEN"),
            os.environ.get("OANDA_DEMO_ACCOUNT_ID"),
        )

    def _request(
        self,
        method: str,
        resource: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        allowed_get = {"summary", "instruments", "pricing", "openTrades"}
        allowed_get.update(f"instruments/{instrument}/candles" for instrument in INSTRUMENTS)
        if method == "GET":
            if resource not in allowed_get or payload is not None:
                raise LabError("Unapproved OANDA Practice forward-lab read route.")
        elif method == "POST":
            if resource != "orders" or params is not None or not isinstance(payload, dict):
                raise LabError("Unapproved OANDA Practice forward-lab write route.")
        else:
            raise LabError("Unapproved OANDA Practice method.")
        url = f"{PRACTICE_ORIGIN}/v3/accounts/{self._account}/{resource}"
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if request_id:
            if not re.fullmatch(r"[A-Za-z0-9_.-]{8,64}", request_id):
                raise LabError("Invalid Practice request identifier.")
            headers["ClientRequestID"] = request_id
        body = json.dumps(payload, separators=(",", ":")).encode() if payload else None
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=25) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise LabError("OANDA Practice forward-lab response exceeded the size limit.")
        except HTTPError as error:
            # Never print broker bodies, account IDs, tokens, or request headers.
            raise LabError(
                f"OANDA Practice forward-lab {method} returned HTTP {error.code}. No automatic retry."
            ) from None
        except (URLError, TimeoutError):
            if method == "POST":
                raise LabError(
                    "OANDA Practice order outcome is uncertain after a transport failure. Do not retry; reconcile open trades manually."
                ) from None
            raise LabError("OANDA Practice forward-lab read failed.") from None
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            raise LabError("OANDA Practice forward-lab returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise LabError("OANDA Practice forward-lab returned an unexpected response.")
        return result

    def summary(self) -> dict[str, Any]:
        account = self._request("GET", "summary").get("account")
        if not isinstance(account, dict) or account.get("currency") != "USD":
            raise LabError("A USD-denominated OANDA Practice account is required.")
        try:
            nav = float(account["NAV"])
            margin_available = float(account["marginAvailable"])
        except (KeyError, TypeError, ValueError):
            raise LabError("Invalid OANDA Practice account summary.") from None
        if not math.isfinite(nav) or nav <= 0 or not math.isfinite(margin_available):
            raise LabError("Invalid OANDA Practice NAV or available margin.")
        return {
            "nav": nav,
            "margin_available": margin_available,
            "open_trade_count": int(account.get("openTradeCount", 0)),
            "pending_order_count": int(account.get("pendingOrderCount", 0)),
            "guaranteed_stop_mode": str(account.get("guaranteedStopLossOrderMode", "DISABLED")),
        }

    def instrument_metadata(self) -> dict[str, dict[str, Any]]:
        payload = self._request(
            "GET", "instruments", params={"instruments": ",".join(INSTRUMENTS)}
        )
        rows = payload.get("instruments")
        if not isinstance(rows, list):
            raise LabError("Invalid OANDA Practice instrument metadata.")
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict) or row.get("name") not in INSTRUMENTS:
                continue
            try:
                precision = int(row["displayPrecision"])
                unit_precision = int(row["tradeUnitsPrecision"])
                minimum = float(row["minimumTradeSize"])
                maximum = float(row["maximumOrderUnits"])
            except (KeyError, TypeError, ValueError):
                raise LabError("Malformed OANDA Practice instrument metadata.") from None
            if precision not in range(3, 7) or unit_precision != 0 or minimum < 1 or maximum < 1:
                raise LabError("Unsupported OANDA Practice instrument constraints.")
            result[row["name"]] = {
                "display_precision": precision,
                "minimum_trade_size": math.ceil(minimum),
                "maximum_order_units": math.floor(maximum),
            }
        if set(result) != set(INSTRUMENTS):
            raise LabError("One or more forward-lab instruments are unavailable.")
        return result

    def candles(self, instrument: str) -> dict[str, Any]:
        if instrument not in INSTRUMENTS:
            raise LabError("Unapproved forward-lab instrument.")
        payload = self._request(
            "GET",
            f"instruments/{instrument}/candles",
            params={
                "granularity": GRANULARITY,
                "price": "BA",
                "count": CANDLE_COUNT,
                "smooth": "false",
            },
        )
        parse_candles(payload, instrument)
        return payload

    def prices(self) -> dict[str, dict[str, Any]]:
        payload = self._request(
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
                timestamp = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
                availability = row["unitsAvailable"]["default"]
                available_long = math.floor(float(availability["long"]))
                available_short = math.floor(float(availability["short"]))
            except (KeyError, IndexError, TypeError, ValueError):
                raise LabError("Malformed OANDA Practice price record.") from None
            if timestamp.tzinfo is None or not all(math.isfinite(value) for value in (bid, ask)):
                raise LabError("Invalid OANDA Practice price values.")
            if bid <= 0 or ask <= bid:
                raise LabError("Invalid or crossed OANDA Practice price.")
            result[row["instrument"]] = {
                "bid": bid,
                "ask": ask,
                "time": timestamp.astimezone(timezone.utc),
                "tradeable": str(row.get("status", "")).casefold() == "tradeable",
                "available_long": available_long,
                "available_short": available_short,
            }
        if set(result) != set(INSTRUMENTS):
            raise LabError("One or more current Practice prices are unavailable.")
        return result

    def open_trades(self) -> list[dict[str, Any]]:
        rows = self._request("GET", "openTrades").get("trades")
        if not isinstance(rows, list):
            raise LabError("Invalid OANDA Practice open-trades response.")
        return [row for row in rows if isinstance(row, dict)]

    def place_market_order(
        self,
        order: dict[str, Any],
        *,
        request_id: str,
    ) -> dict[str, Any]:
        response = self._request(
            "POST", "orders", payload={"order": order}, request_id=request_id
        )
        if "orderRejectTransaction" in response:
            raise LabError("OANDA Practice rejected the forward experiment order.")
        if "orderCancelTransaction" in response:
            raise LabError("OANDA Practice did not fill the forward experiment order.")
        fill = response.get("orderFillTransaction")
        if not isinstance(fill, dict):
            raise LabError("OANDA Practice returned no confirmed order fill.")
        trade = fill.get("tradeOpened")
        if not isinstance(trade, dict) or not str(trade.get("tradeID", "")).isdigit():
            raise LabError("OANDA Practice fill did not open one identifiable trade.")
        return {
            "transaction_id": str(fill.get("id", "")),
            "trade_id": str(trade["tradeID"]),
            "instrument": str(fill.get("instrument", "")),
            "units": str(fill.get("units", "")),
            "fill_price": str(fill.get("price", "")),
            "fill_time": str(fill.get("time", "")),
        }


def _market_features(instrument: str, payload: dict[str, Any]) -> MarketFeatures:
    bars = parse_candles(payload, instrument)
    features = build_features(bars)
    if len(features.bars) < 50 or features.atr[-1] is None:
        raise LabError("Insufficient completed candles for the forward lab.")
    close = features.close
    atr = float(features.atr[-1])
    if atr <= 0:
        raise LabError("Invalid forward-lab ATR.")
    score_24 = (close[-1] - close[-25]) / (atr * math.sqrt(24))
    score_6 = (close[-1] - close[-7]) / (atr * math.sqrt(6))
    path = sum(abs(close[index] - close[index - 1]) for index in range(len(close) - 24, len(close)))
    efficiency = abs(close[-1] - close[-25]) / path if path > 0 else 0.0
    baseline = close[-25:-1]
    deviation = statistics.pstdev(baseline)
    zscore = (close[-1] - statistics.fmean(baseline)) / deviation if deviation > 0 else 0.0
    last = features.bars[-1]
    opening = features.open[-1]
    candle_direction = 1 if close[-1] > opening else (-1 if close[-1] < opening else 0)
    candle_range = max(features.high[-1] - features.low[-1], 1e-12)
    close_location = (close[-1] - features.low[-1]) / candle_range
    return MarketFeatures(
        instrument=instrument,
        signal_time=last.time,
        close=close[-1],
        atr=atr,
        score_24=score_24,
        score_6=score_6,
        efficiency_24=efficiency,
        zscore_24=zscore,
        candle_direction=candle_direction,
        close_location=close_location,
    )


def select_signal(markets: dict[str, MarketFeatures]) -> dict[str, Any] | None:
    """Choose a current forward arm without historical parameter optimization."""
    if set(markets) != set(INSTRUMENTS):
        raise LabError("Forward signal selection requires the complete universe.")
    median_efficiency = statistics.median(
        market.efficiency_24 for market in markets.values()
    )
    trend_candidates: list[tuple[float, MarketFeatures]] = []
    for market in markets.values():
        same_direction = market.score_24 * market.score_6 > 0
        direction = 1 if market.score_24 > 0 else -1
        candle_ok = market.candle_direction in (0, direction)
        if (
            same_direction
            and abs(market.score_24) >= 0.35
            and abs(market.score_6) >= 0.12
            and market.efficiency_24 >= 0.25
            and candle_ok
        ):
            confidence = abs(market.score_24) * (0.5 + market.efficiency_24)
            trend_candidates.append((confidence, market))
    if median_efficiency >= 0.28 and trend_candidates:
        confidence, market = max(trend_candidates, key=lambda item: item[0])
        direction = 1 if market.score_24 > 0 else -1
        return {
            "strategy": "forward_adaptive_trend_v1",
            "instrument": market.instrument,
            "direction": direction,
            "signal_time": market.signal_time,
            "confidence": confidence,
            "atr": market.atr,
            "stop_atr": 1.50,
            "target_r": 1.75,
            "diagnostics": {
                "median_universe_efficiency": median_efficiency,
                "score_24": market.score_24,
                "score_6": market.score_6,
                "efficiency_24": market.efficiency_24,
            },
        }

    reversal_candidates: list[tuple[float, MarketFeatures, int]] = []
    for market in markets.values():
        if (
            market.zscore_24 >= 1.65
            and market.candle_direction == -1
            and market.close_location <= 0.55
            and market.efficiency_24 <= 0.48
        ):
            reversal_candidates.append((abs(market.zscore_24), market, -1))
        elif (
            market.zscore_24 <= -1.65
            and market.candle_direction == 1
            and market.close_location >= 0.45
            and market.efficiency_24 <= 0.48
        ):
            reversal_candidates.append((abs(market.zscore_24), market, 1))
    if reversal_candidates:
        confidence, market, direction = max(reversal_candidates, key=lambda item: item[0])
        return {
            "strategy": "forward_exhaustion_reversal_v1",
            "instrument": market.instrument,
            "direction": direction,
            "signal_time": market.signal_time,
            "confidence": confidence,
            "atr": market.atr,
            "stop_atr": 1.25,
            "target_r": 1.30,
            "diagnostics": {
                "median_universe_efficiency": median_efficiency,
                "zscore_24": market.zscore_24,
                "efficiency_24": market.efficiency_24,
                "close_location": market.close_location,
            },
        }
    return None


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def build_plan(client: ForwardPracticeClient) -> dict[str, Any]:
    generated = datetime.now(timezone.utc)
    summary = client.summary()
    if summary["open_trade_count"] or summary["pending_order_count"]:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "existing_practice_trade_or_order",
        }
    if summary["guaranteed_stop_mode"].upper() == "REQUIRED":
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "guaranteed_stop_configuration_not_supported",
        }
    metadata = client.instrument_metadata()
    candles = {instrument: client.candles(instrument) for instrument in INSTRUMENTS}
    markets = {
        instrument: _market_features(instrument, candles[instrument])
        for instrument in INSTRUMENTS
    }
    signal = select_signal(markets)
    if signal is None:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "no_current_forward_signal",
            "latest_completed_candles": {
                instrument: _iso(market.signal_time)
                for instrument, market in markets.items()
            },
        }
    prices = client.prices()
    instrument = signal["instrument"]
    price = prices[instrument]
    age = (generated - price["time"]).total_seconds()
    if age < -10 or age > MAX_PRICE_AGE_SECONDS or not price["tradeable"]:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "stale_or_nontradeable_current_price",
            "instrument": instrument,
        }
    if price["time"].weekday() >= 5 or price["time"].hour in FORBIDDEN_UTC_HOURS:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "forward_lab_time_window_blocked",
            "instrument": instrument,
        }
    spread = price["ask"] - price["bid"]
    atr = float(signal["atr"])
    if spread > MAX_SPREAD or spread > atr * MAX_SPREAD_ATR:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "current_spread_too_wide",
            "instrument": instrument,
            "spread_pips": round(spread * 10_000, 4),
        }
    stop_distance = max(float(signal["stop_atr"]) * atr, spread * 4, MIN_STOP)
    risk_budget = min(MAX_VIRTUAL_RISK_USD, summary["nav"] * RISK_FRACTION_OF_NAV)
    units = math.floor(risk_budget / stop_distance)
    available = price["available_long"] if signal["direction"] == 1 else price["available_short"]
    units = min(units, MAX_UNITS, available, metadata[instrument]["maximum_order_units"])
    units = int(units)
    if units < metadata[instrument]["minimum_trade_size"]:
        return {
            "status": "forward_practice_plan",
            "environment": "practice",
            "generated_at": _iso(generated),
            "eligible": False,
            "reason": "risk_budget_below_minimum_trade_size",
            "instrument": instrument,
        }
    direction = int(signal["direction"])
    reference_entry = price["ask"] if direction == 1 else price["bid"]
    stop_price = reference_entry - direction * stop_distance
    target_price = reference_entry + direction * stop_distance * float(signal["target_r"])
    bound_distance = max(spread * 2, SLIPPAGE_BOUND_MIN)
    price_bound = reference_entry + direction * bound_distance
    precision = metadata[instrument]["display_precision"]
    plan_seed = "|".join(
        (
            str(signal["strategy"]),
            instrument,
            str(direction),
            _iso(signal["signal_time"]),
        )
    )
    plan_id = "ko-fwd-" + hashlib.sha256(plan_seed.encode()).hexdigest()[:20]
    estimated_risk = units * stop_distance
    return {
        "status": "forward_practice_plan",
        "environment": "practice",
        "generated_at": _iso(generated),
        "eligible": True,
        "reason": "current_forward_signal_passed",
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
        "target_r": signal["target_r"],
        "spread_pips": round(spread * 10_000, 4),
        "estimated_max_virtual_risk_usd": round(estimated_risk, 4),
        "hard_virtual_risk_cap_usd": MAX_VIRTUAL_RISK_USD,
        "confidence": round(float(signal["confidence"]), 6),
        "diagnostics": {
            key: round(float(value), 6)
            for key, value in signal["diagnostics"].items()
        },
    }


def _load_permit(path: str, plan: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("OANDA_PRACTICE_EXECUTION_APPROVAL") != APPROVAL_PHRASE:
        raise LabError("Missing exact OANDA Practice-only execution approval phrase.")
    permit_path = Path(path)
    if not permit_path.is_file() or permit_path.stat().st_size > 16_384:
        raise LabError("Missing or invalid OANDA Practice execution permit.")
    try:
        permit = json.loads(permit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise LabError("Unreadable OANDA Practice execution permit.") from None
    if not isinstance(permit, dict):
        raise LabError("Invalid OANDA Practice execution permit.")
    try:
        expires = datetime.fromisoformat(str(permit["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        raise LabError("Invalid OANDA Practice permit expiration.") from None
    now = datetime.now(timezone.utc)
    if expires.tzinfo is None or not now < expires.astimezone(timezone.utc) <= now.replace(microsecond=0) + __import__("datetime").timedelta(hours=2):
        raise LabError("OANDA Practice execution permit is expired or too long-lived.")
    checks = (
        permit.get("environment") == "practice",
        permit.get("plan_id") == plan.get("plan_id"),
        permit.get("max_orders") == 1,
        isinstance(permit.get("max_units"), int) and 1 <= permit["max_units"] <= MAX_UNITS,
        isinstance(permit.get("max_virtual_risk_usd"), (int, float))
        and 0 < float(permit["max_virtual_risk_usd"]) <= MAX_VIRTUAL_RISK_USD,
        permit.get("single_use") is True,
        permit.get("scope") == "oanda_practice_forward_experiment_only",
    )
    if not all(checks):
        raise LabError("OANDA Practice execution permit does not match the current plan or limits.")
    if abs(int(plan["signed_units"])) > permit["max_units"]:
        raise LabError("Current Practice plan exceeds the permitted unit cap.")
    if float(plan["estimated_max_virtual_risk_usd"]) > float(permit["max_virtual_risk_usd"]):
        raise LabError("Current Practice plan exceeds the permitted virtual-risk cap.")
    return permit


def execute_plan(
    client: ForwardPracticeClient,
    plan: dict[str, Any],
    permit_path: str = DEFAULT_PERMIT,
) -> dict[str, Any]:
    if not plan.get("eligible"):
        raise LabError("No eligible current Practice plan exists.")
    permit = _load_permit(permit_path, plan)
    summary = client.summary()
    if summary["open_trade_count"] or summary["pending_order_count"] or client.open_trades():
        raise LabError("Practice account is no longer empty; refusing the one-order experiment.")
    order = {
        "type": "MARKET",
        "instrument": plan["instrument"],
        "units": str(plan["signed_units"]),
        "timeInForce": "FOK",
        "positionFill": "DEFAULT",
        "priceBound": plan["price_bound"],
        "stopLossOnFill": {
            "timeInForce": "GTC",
            "price": plan["stop_loss"],
        },
        "takeProfitOnFill": {
            "timeInForce": "GTC",
            "price": plan["take_profit"],
        },
    }
    request_id = str(permit.get("request_id", ""))
    fill = client.place_market_order(order, request_id=request_id)
    open_trades = client.open_trades()
    matching = [trade for trade in open_trades if str(trade.get("id")) == fill["trade_id"]]
    if len(matching) != 1:
        raise LabError("Practice fill occurred but post-fill trade reconciliation failed.")
    trade = matching[0]
    if not isinstance(trade.get("stopLossOrder"), dict) or not isinstance(trade.get("takeProfitOrder"), dict):
        raise LabError("Practice trade opened without both attached protection orders.")
    return {
        "status": "practice_forward_order_filled",
        "environment": "practice",
        "plan_id": plan["plan_id"],
        "strategy": plan["strategy"],
        "instrument": plan["instrument"],
        "direction": plan["direction"],
        "signed_units": plan["signed_units"],
        "estimated_max_virtual_risk_usd": plan["estimated_max_virtual_risk_usd"],
        "stop_loss": plan["stop_loss"],
        "take_profit": plan["take_profit"],
        "fill": fill,
        "attached_stop_verified": True,
        "attached_take_profit_verified": True,
        "real_money": False,
        "warning": "This is a forward Practice experiment, not validated profitability or withdrawable profit.",
    }


def _write_json(path: str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OANDA Practice forward-only micro experiment.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan")
    scan.add_argument("--output", default="state/oanda-forward-plan.json")
    execute = commands.add_parser("execute")
    execute.add_argument("--permit", default=DEFAULT_PERMIT)
    execute.add_argument("--output", default="state/oanda-forward-execution.json")
    args = parser.parse_args(argv)
    try:
        client = ForwardPracticeClient.from_environment()
        plan = build_plan(client)
        if args.command == "scan":
            _write_json(args.output, plan)
            print(
                f"Forward Practice scan: eligible={plan['eligible']}, reason={plan['reason']}"
                + (
                    f", plan={plan['plan_id']}, {plan['instrument']} {plan['direction']}, units={abs(plan['signed_units'])}."
                    if plan.get("eligible")
                    else "."
                )
            )
        else:
            result = execute_plan(client, plan, args.permit)
            _write_json(args.output, result)
            print(
                f"Practice order filled: plan={result['plan_id']}, {result['instrument']} "
                f"{result['direction']}, units={abs(result['signed_units'])}; attached stop and target verified."
            )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Forward Practice file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
