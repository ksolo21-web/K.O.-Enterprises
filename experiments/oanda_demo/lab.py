"""Read-only OANDA Practice access and a bounded, deterministic replay baseline.

Uses no third-party packages. No live hostname, order endpoint, scheduler,
deposit, transfer, withdrawal or balance-reset function is implemented.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

PRACTICE_ORIGIN = "https://api-fxpractice.oanda.com"
INSTRUMENT = "EUR_USD"
MAX_RESPONSE = 12 * 1024 * 1024


class LabError(ValueError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LabError("Redirect refused; practice credentials were not forwarded.")


def finite(value, name):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise LabError(f"Invalid {name}.") from None
    if not math.isfinite(n):
        raise LabError(f"Invalid {name}.")
    return n


class PracticeReader:
    def __init__(self, token, account_id):
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise LabError("Missing or invalid OANDA_DEMO_TOKEN; use secret storage.")
        # OANDA documents four hyphen-separated identifier components, without
        # fixed digit widths. Trim copy/paste whitespace, never alter the ID.
        account_id = account_id.strip() if isinstance(account_id, str) else ""
        if not account_id or len(account_id) > 128 or not re.fullmatch(r"[0-9]+(?:-[0-9]+){3}", account_id):
            raise LabError("Practice account ID must contain four numeric groups separated by hyphens. Check the value of OANDA_demo_account_ID; keep its secret name unchanged.")
        self._token = token
        self._account = account_id
        self._opener = build_opener(NoRedirects())

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get("OANDA_DEMO_TOKEN"), os.environ.get("OANDA_DEMO_ACCOUNT_ID"))

    def _get(self, resource, params=None):
        if resource not in {"summary", "instruments/EUR_USD/candles"}:
            raise LabError("Only practice summary and EUR_USD candle reads are implemented.")
        url = PRACTICE_ORIGIN + "/v3/accounts/" + self._account + "/" + resource
        if params:
            url += "?" + urlencode(params)
        request = Request(url, headers={"Authorization": "Bearer " + self._token, "Accept": "application/json"}, method="GET")
        try:
            with self._opener.open(request, timeout=20) as response:
                body = response.read(MAX_RESPONSE + 1)
                if len(body) > MAX_RESPONSE:
                    raise LabError("Practice response exceeded the size limit.")
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise LabError("Unexpected practice response.")
                return result
        except HTTPError as err:
            # No response body, request headers, token or account ID in logs.
            raise LabError(f"OANDA Practice returned HTTP {err.code}. No automatic retry.") from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise LabError("Practice request or JSON decoding failed. No order was sent.") from None

    def summary(self):
        account = self._get("summary").get("account", {})
        if account.get("currency") != "USD":
            raise LabError("This experiment requires a USD-denominated practice account.")
        return {"environment": "practice", "currency": "USD", "nav": finite(account.get("NAV"), "NAV"), "balance": finite(account.get("balance"), "balance"), "open_trade_count": int(account.get("openTradeCount", 0))}

    def candles(self, count=5000):
        if type(count) is not int or not 200 <= count <= 5000:
            raise LabError("Choose 200–5000 hourly candles.")
        data = self._get("instruments/EUR_USD/candles", {"granularity": "H1", "price": "BA", "count": count, "smooth": "false"})
        validate_candles(data)
        return data


def validate_candles(data):
    if not isinstance(data, dict) or data.get("instrument") != INSTRUMENT or data.get("granularity") != "H1":
        raise LabError("Expected EUR_USD H1 bid/ask candles.")
    raw = data.get("candles")
    if not isinstance(raw, list) or not 200 <= len(raw) <= 5000:
        raise LabError("Expected 200–5000 candles.")
    bars = []
    for item in raw:
        if not isinstance(item, dict):
            raise LabError("Invalid candle record.")
        if item.get("complete") is not True:
            continue
        try:
            time = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
            if time.tzinfo is None:
                raise ValueError
            time = time.astimezone(timezone.utc)
            bar = {"time": time}
            for side in ["bid", "ask"]:
                bar[side] = {k: finite(item[side][k], "candle price") for k in "ohlc"}
                p = bar[side]
                if min(p.values()) <= 0 or not p["l"] <= min(p["o"], p["c"]) <= max(p["o"], p["c"]) <= p["h"]:
                    raise LabError("Invalid OHLC range.")
            if bar["ask"]["o"] < bar["bid"]["o"] or bar["ask"]["c"] < bar["bid"]["c"]:
                raise LabError("Crossed bid/ask quotes.")
        except (KeyError, TypeError, ValueError) as err:
            raise LabError("Malformed or invalid candle.") from None
        if bars and time <= bars[-1]["time"]:
            raise LabError("Candles must be unique and strictly chronological.")
        bars.append(bar)
    if len(bars) < 200:
        raise LabError("Need at least 200 completed candles.")
    return bars


def signals(bars):
    """Signal at i uses prices strictly before i; no lookahead."""
    close = [(b["bid"]["c"] + b["ask"]["c"]) / 2 for b in bars]
    result = [0] * len(bars)
    for i in range(51, len(bars)):
        previous = statistics.fmean(close[i-21:i-1]) - statistics.fmean(close[i-51:i-1])
        current = statistics.fmean(close[i-20:i]) - statistics.fmean(close[i-50:i])
        if previous <= 0 < current:
            result[i] = 1
        elif previous >= 0 > current:
            result[i] = -1
    return result


def one_bar_trade(bar, direction, units, stop_distance, slip=0.00001):
    """One-hour position, bid/ask execution, pessimistic stop-first OHLC rule."""
    entry = bar["ask"]["o"] + slip if direction == 1 else bar["bid"]["o"] - slip
    stop, target = entry - direction * stop_distance, entry + direction * 2 * stop_distance
    side = bar["bid"] if direction == 1 else bar["ask"]
    stopped = side["l"] <= stop if direction == 1 else side["h"] >= stop
    reached = side["h"] >= target if direction == 1 else side["l"] <= target
    if stopped:
        exit_price = min(side["o"], stop) if direction == 1 else max(side["o"], stop)
        reason = "stop"
    elif reached:
        exit_price, reason = target, "target"
    else:
        exit_price, reason = side["c"], "hour_close"
    exit_price -= direction * slip
    return {"entry": entry, "exit": exit_price, "pnl": direction * units * (exit_price - entry), "reason": reason, "units": units}


def run_segment(bars, sig, start, end, risk_percent):
    equity = peak = day_start = 50.0
    day = None
    max_dd = 0.0
    trades = []
    goal_time = None
    stopped = False
    for i in range(max(start, 51), end):
        bar = bars[i]
        if bar["time"].date() != day:
            day, day_start = bar["time"].date(), equity
        if equity <= peak * 0.70:
            stopped = True
            break
        if equity <= day_start * 0.95 or equity >= 500:
            continue
        direction = sig[i]
        # Positions close within the candle, before 20:00 UTC. No rollover model.
        if not direction or bar["time"].hour >= 19 or bar["time"].weekday() >= 5:
            continue
        if bar["ask"]["o"] - bar["bid"]["o"] > 0.0003:
            continue
        ranges = []
        for j in range(i-14, i):
            b, previous = bars[j], bars[j-1]
            high = (b["bid"]["h"] + b["ask"]["h"]) / 2
            low = (b["bid"]["l"] + b["ask"]["l"]) / 2
            prior_close = (previous["bid"]["c"] + previous["ask"]["c"]) / 2
            ranges.append(max(high-low, abs(high-prior_close), abs(low-prior_close)))
        distance = max(0.0005, statistics.fmean(ranges)*2)
        entry = bar["ask"]["o"] + 0.00001 if direction == 1 else bar["bid"]["o"] - 0.00001
        units = math.floor(min(equity*(risk_percent/100)/(distance+0.00001), equity*10/entry))
        if units < 1:
            continue
        trade = one_bar_trade(bar, direction, units, distance)
        equity += trade["pnl"]
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak-equity)/peak)
        trades.append({"time": bar["time"].isoformat(), "direction": direction, **trade, "balance": equity})
        if equity >= 500 and goal_time is None:
            goal_time = bar["time"].isoformat()
    wins = sum(t["pnl"] > 0 for t in trades)
    return {"start_virtual_usd": 50, "end_virtual_usd": round(equity, 4), "return_percent": round((equity/50-1)*100, 4), "settled_balance_drawdown_percent": round(max_dd*100, 4), "risk_percent": risk_percent, "trades": len(trades), "winning_trades": wins, "goal_500_reached_at": goal_time, "drawdown_stop_triggered": stopped or equity <= peak*0.70, "trade_log": trades}


def replay(data):
    bars = validate_candles(data)
    sig = signals(bars)
    split = int(len(bars)*0.7)
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"status": "historical_simulation_not_broker_trades", "instrument": INSTRUMENT, "data_sha256": digest, "first_candle": bars[0]["time"].isoformat(), "last_candle": bars[-1]["time"].isoformat(), "completed_candles": len(bars), "split_time": bars[split]["time"].isoformat(), "strategy": "Fixed SMA20/SMA50 crossing; one-hour holding; previous 14-bar range stop; 2R target", "assumptions": ["Bid/ask prices and 0.1 pip adverse slippage per side.", "Stop wins when stop and target occur inside the same hourly candle.", "No position held after its entry hour; entries only before 19:00 UTC weekdays.", "Ten-times virtual notional cap; 1%, 2%, 5% risk scenarios. Stop new entries after 5% settled daily loss or 30% settled drawdown.", "Stops can overshoot model loss thresholds. Intrabar account drawdown, liquidity, exact commissions and broker margin closeout are not modeled.", "First 70% development; final 30% holdout; fixed parameters, no optimization. Each segment starts with separate virtual $50.", "The latest 5000 H1 candles are a limited sample. No live profitability or speed to $500 is established."], "scenarios": [{"risk_percent": risk, "development": run_segment(bars, sig, 51, split, risk), "holdout": run_segment(bars, sig, split, len(bars), risk)} for risk in [1, 2, 5]]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="OANDA Practice read-only research; no orders.")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Read practice account and up to 5000 candles; write to private local state.")
    fetch.add_argument("--output", default="state/oanda-demo-candles.json")
    fetch.add_argument("--count", type=int, default=5000)
    sim = commands.add_parser("replay", help="Run three fixed virtual-$50 historical scenarios without network.")
    sim.add_argument("--input", required=True)
    sim.add_argument("--output", default="state/oanda-demo-replay.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            client = PracticeReader.from_environment()
            summary = client.summary()
            if summary["open_trade_count"]:
                raise LabError("Existing practice trades found. This isolated experiment will not alter them.")
            data = client.candles(args.count)
            print("Practice account connected. No orders sent. Captured completed candle data for local research.")
        else:
            path = Path(args.input)
            if path.stat().st_size > MAX_RESPONSE:
                raise LabError("Input exceeds the size limit.")
            data = replay(json.loads(path.read_text(encoding="utf-8")))
            for x in data["scenarios"]:
                y = x["holdout"]
                print(f"Holdout simulation: risk {x['risk_percent']}%, final virtual USD {y['end_virtual_usd']}, settled drawdown {y['settled_balance_drawdown_percent']}%, trades {y['trades']}, goal reached: {bool(y['goal_500_reached_at'])}")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
        return 0
    except (LabError, OSError, json.JSONDecodeError) as err:
        # File failures can reveal paths but never credentials; avoid arbitrary API bodies.
        print(str(err) if isinstance(err, LabError) else "Local file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
