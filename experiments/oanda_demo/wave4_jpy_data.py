"""Read-only, sealed-data fetch for OANDA Practice Wave 4.

Wave 4 uses a disjoint seven-pair JPY-cross universe on completed H4 bid/ask
candles. Only the first 80 percent of each series may be exported for strategy
research; the final 20 percent remains ephemeral until a candidate and all
acceptance thresholds are fixed in source.

This module has no order, trade, position, transfer, withdrawal, live-hostname,
or scheduling capability.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .lab import LabError, MAX_RESPONSE, NoRedirects, PRACTICE_ORIGIN
from .tournament import Bar

INSTRUMENTS = (
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CAD_JPY",
    "CHF_JPY",
)
GRANULARITY = "H4"
CANDLE_COUNT = 5000
PREHOLDOUT_FRACTION = 0.80
PIP_SIZE = 0.01
ACCOUNT_ID_RE = re.compile(r"[0-9]+(?:-[0-9]+){3}", re.ASCII)


class Wave4PracticeClient:
    """Strict fixed-route GET-only client for Wave 4 market research."""

    def __init__(self, token: object, account_id: object) -> None:
        token = token.strip() if isinstance(token, str) else ""
        account_id = account_id.strip() if isinstance(account_id, str) else ""
        if not token or len(token) > 4096 or any(ch.isspace() for ch in token):
            raise LabError("Missing or invalid OANDA Practice token.")
        if not account_id or len(account_id) > 128 or not ACCOUNT_ID_RE.fullmatch(account_id):
            raise LabError("Missing or invalid OANDA Practice account ID.")
        self._token = token
        self._account = account_id
        self._opener = build_opener(NoRedirects())

    @classmethod
    def from_environment(cls) -> "Wave4PracticeClient":
        return cls(
            os.environ.get("OANDA_DEMO_TOKEN"),
            os.environ.get("OANDA_DEMO_ACCOUNT_ID"),
        )

    def _get(self, resource: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        allowed = {"summary", "instruments"}
        allowed.update(f"instruments/{instrument}/candles" for instrument in INSTRUMENTS)
        if resource not in allowed:
            raise LabError("Unapproved OANDA Wave 4 route.")
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
                    raise LabError("OANDA Wave 4 response exceeded the size limit.")
        except HTTPError as error:
            raise LabError(f"OANDA Wave 4 request returned HTTP {error.code}.") from None
        except (URLError, TimeoutError):
            raise LabError("OANDA Wave 4 request failed.") from None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise LabError("OANDA Wave 4 returned invalid JSON.") from None
        if not isinstance(payload, dict):
            raise LabError("OANDA Wave 4 returned an unexpected response.")
        return payload

    def summary(self) -> dict[str, Any]:
        account = self._get("summary").get("account")
        if not isinstance(account, dict) or account.get("currency") != "USD":
            raise LabError("Wave 4 requires a USD-denominated Practice account.")
        return {
            "environment": "practice",
            "currency": "USD",
            "open_trade_count": int(account.get("openTradeCount", 0)),
            "pending_order_count": int(account.get("pendingOrderCount", 0)),
        }

    def available_instruments(self) -> set[str]:
        payload = self._get("instruments", {"instruments": ",".join(INSTRUMENTS)})
        rows = payload.get("instruments")
        if not isinstance(rows, list):
            raise LabError("OANDA returned invalid Wave 4 instrument metadata.")
        return {
            row["name"]
            for row in rows
            if isinstance(row, dict)
            and row.get("type") == "CURRENCY"
            and isinstance(row.get("name"), str)
        }

    def candles(self, instrument: str, count: int = CANDLE_COUNT) -> dict[str, Any]:
        if instrument not in INSTRUMENTS:
            raise LabError("Unapproved Wave 4 instrument.")
        if type(count) is not int or not 1200 <= count <= CANDLE_COUNT:
            raise LabError("Wave 4 candle count must be between 1200 and 5000.")
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


def _price(row: dict[str, Any], side: str, key: str) -> float:
    try:
        value = _finite(row[side][key], "Wave 4 candle price")
    except (KeyError, TypeError):
        raise LabError("Malformed Wave 4 candle price.") from None
    if value <= 0:
        raise LabError("Wave 4 candle prices must be positive.")
    return value


def parse_candles(payload: object, instrument: str) -> tuple[Bar, ...]:
    if (
        instrument not in INSTRUMENTS
        or not isinstance(payload, dict)
        or payload.get("instrument") != instrument
        or payload.get("granularity") != GRANULARITY
    ):
        raise LabError(f"Expected approved {instrument} {GRANULARITY} candles.")
    rows = payload.get("candles")
    if not isinstance(rows, list) or not 1200 <= len(rows) <= CANDLE_COUNT:
        raise LabError("Expected 1200-5000 Wave 4 candle records.")
    bars: list[Bar] = []
    for row in rows:
        if not isinstance(row, dict):
            raise LabError("Malformed Wave 4 candle record.")
        if row.get("complete") is not True:
            continue
        try:
            stamp = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            raise LabError("Malformed Wave 4 candle timestamp.") from None
        if stamp.tzinfo is None:
            raise LabError("Wave 4 candle timestamps require a timezone.")
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
            raise LabError("Invalid Wave 4 OHLC or crossed bid/ask values.")
        if bars and stamp <= bars[-1].time:
            raise LabError("Wave 4 candles must be strictly chronological and unique.")
        bars.append(bar)
    if len(bars) < 1150:
        raise LabError("Too few completed Wave 4 candles.")
    return tuple(bars)


def fetch_full_bundle(client: Wave4PracticeClient, count: int = CANDLE_COUNT) -> dict[str, Any]:
    summary = client.summary()
    if summary["open_trade_count"] or summary["pending_order_count"]:
        raise LabError(
            "Existing Practice trades or pending orders found; Wave 4 research will not alter them."
        )
    available = client.available_instruments()
    missing = [instrument for instrument in INSTRUMENTS if instrument not in available]
    if missing:
        raise LabError("One or more Wave 4 JPY-cross instruments are unavailable.")
    candles = {instrument: client.candles(instrument, count) for instrument in INSTRUMENTS}
    return {
        "status": "wave4_full_ephemeral_market_data",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "instruments": list(INSTRUMENTS),
        "granularity": GRANULARITY,
        "pip_size": PIP_SIZE,
        "candles": candles,
    }


def export_preholdout(bundle: object) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("status") != "wave4_full_ephemeral_market_data":
        raise LabError("Invalid Wave 4 full-data bundle.")
    raw = bundle.get("candles")
    if not isinstance(raw, dict) or set(raw) != set(INSTRUMENTS):
        raise LabError("Wave 4 bundle must contain the complete JPY-cross whitelist.")
    exported: dict[str, dict[str, Any]] = {}
    ranges: dict[str, dict[str, Any]] = {}
    for instrument in INSTRUMENTS:
        payload = raw[instrument]
        bars = parse_candles(payload, instrument)
        split = int(len(bars) * PREHOLDOUT_FRACTION)
        if split < 1000 or split >= len(bars):
            raise LabError("Invalid Wave 4 sealed split.")
        rows = payload.get("candles")
        if not isinstance(rows, list):
            raise LabError("Malformed Wave 4 candle payload.")
        complete = [row for row in rows if isinstance(row, dict) and row.get("complete") is True]
        selected = complete[:split]
        exported[instrument] = {
            "instrument": instrument,
            "granularity": GRANULARITY,
            "candles": selected,
        }
        ranges[instrument] = {
            "exported_complete_candles": len(selected),
            "withheld_complete_candles": len(complete) - len(selected),
            "first_exported_time": selected[0]["time"],
            "last_exported_time": selected[-1]["time"],
            "first_withheld_time": complete[split]["time"],
        }
    return {
        "status": "wave4_preholdout_market_data",
        "environment": "practice",
        "granularity": GRANULARITY,
        "pip_size": PIP_SIZE,
        "preholdout_fraction": PREHOLDOUT_FRACTION,
        "holdout_exported": False,
        "instruments": list(INSTRUMENTS),
        "ranges": ranges,
        "candles": exported,
    }


def _read_json(path: str) -> Any:
    source = Path(path)
    if source.stat().st_size > MAX_RESPONSE * len(INSTRUMENTS):
        raise LabError("Wave 4 input file is too large.")
    return json.loads(source.read_text(encoding="utf-8"))


def _write_json(path: str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and seal OANDA Practice Wave 4 JPY-cross data.")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("--output", default="state/oanda-wave4-full.json")
    fetch.add_argument("--count", type=int, default=CANDLE_COUNT)
    export = commands.add_parser("export-preholdout")
    export.add_argument("--input", required=True)
    export.add_argument("--output", default="state/oanda-wave4-preholdout.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            payload = fetch_full_bundle(Wave4PracticeClient.from_environment(), args.count)
            _write_json(args.output, payload)
            print(
                f"Captured {len(INSTRUMENTS)} H4 JPY crosses for sealed Wave 4 research. No orders sent."
            )
        else:
            payload = export_preholdout(_read_json(args.input))
            _write_json(args.output, payload)
            print(
                "Exported only the first 80% of Wave 4 completed candles; final 20% remains sealed."
            )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Wave 4 file operation failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
