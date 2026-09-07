"""Sanitized, read-only audit of the current OANDA Practice account state.

The report omits credentials, account identifiers, client extensions, and the
absolute Practice balance. It exists to determine whether an existing trade or
pending order is protected before any additional demo experiment is considered.
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

from .forward_lab import ForwardPracticeClient
from .lab import LabError


def _number(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise LabError(f"Invalid Practice {name}.") from None
    if not math.isfinite(number):
        raise LabError(f"Invalid Practice {name}.")
    return number


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def _optional_price(order: object) -> str | None:
    if not isinstance(order, dict):
        return None
    price = order.get("price")
    if price is None:
        return None
    number = _number(price, "attached-order price")
    if number <= 0:
        raise LabError("Invalid Practice attached-order price.")
    return str(price)


def _trade_row(trade: object) -> dict[str, Any]:
    if not isinstance(trade, dict):
        raise LabError("Malformed Practice open trade.")
    try:
        instrument = str(trade["instrument"])
        current_units = _number(trade["currentUnits"], "trade units")
        entry_price = _number(trade["price"], "trade entry price")
        unrealized = _number(trade.get("unrealizedPL", 0), "unrealized P/L")
        financing = _number(trade.get("financing", 0), "financing")
        opened = datetime.fromisoformat(str(trade["openTime"]).replace("Z", "+00:00"))
    except KeyError:
        raise LabError("Malformed Practice open trade.") from None
    if opened.tzinfo is None or not instrument or current_units == 0 or entry_price <= 0:
        raise LabError("Invalid Practice open-trade values.")
    stop_price = _optional_price(trade.get("stopLossOrder"))
    target_price = _optional_price(trade.get("takeProfitOrder"))
    trailing_distance = None
    trailing = trade.get("trailingStopLossOrder")
    if isinstance(trailing, dict) and trailing.get("distance") is not None:
        distance = _number(trailing["distance"], "trailing-stop distance")
        if distance <= 0:
            raise LabError("Invalid Practice trailing-stop distance.")
        trailing_distance = str(trailing["distance"])
    return {
        "trade_reference": _digest(trade.get("id", "missing")),
        "instrument": instrument,
        "direction": "long" if current_units > 0 else "short",
        "absolute_units": abs(current_units),
        "entry_price": entry_price,
        "open_time": opened.astimezone(timezone.utc).isoformat(),
        "age_hours": round(
            max(0.0, (datetime.now(timezone.utc) - opened.astimezone(timezone.utc)).total_seconds() / 3600),
            4,
        ),
        "unrealized_virtual_pl_usd": round(unrealized, 5),
        "financing_virtual_usd": round(financing, 5),
        "stop_loss_attached": stop_price is not None,
        "stop_loss_price": stop_price,
        "take_profit_attached": target_price is not None,
        "take_profit_price": target_price,
        "trailing_stop_attached": trailing_distance is not None,
        "trailing_stop_distance": trailing_distance,
        "fully_protected": stop_price is not None and target_price is not None,
    }


def _pending_row(order: object) -> dict[str, Any]:
    if not isinstance(order, dict):
        raise LabError("Malformed Practice pending order.")
    order_type = str(order.get("type", "UNKNOWN"))
    instrument = str(order.get("instrument", ""))
    units = order.get("units")
    price = order.get("price") or order.get("priceBound")
    return {
        "order_reference": _digest(order.get("id", "missing")),
        "type": order_type,
        "instrument": instrument or None,
        "absolute_units": abs(_number(units, "pending-order units")) if units is not None else None,
        "price": str(price) if price is not None else None,
        "time_in_force": str(order.get("timeInForce")) if order.get("timeInForce") is not None else None,
        "dependent_trade_reference": _digest(order["tradeID"]) if order.get("tradeID") is not None else None,
    }


def build_audit(client: ForwardPracticeClient) -> dict[str, Any]:
    summary = client.summary()
    trades = client.open_trades()
    pending = client.pending_orders()
    trade_rows = [_trade_row(trade) for trade in trades]
    pending_rows = [_pending_row(order) for order in pending]
    return {
        "status": "oanda_practice_account_audit",
        "environment": "practice",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "account_identifier_included": False,
        "absolute_balance_included": False,
        "reported_open_trade_count": summary["open_trade_count"],
        "observed_open_trade_count": len(trade_rows),
        "reported_pending_order_count": summary["pending_order_count"],
        "observed_pending_order_count": len(pending_rows),
        "open_trades": trade_rows,
        "pending_orders": pending_rows,
        "unprotected_open_trade_count": sum(not row["fully_protected"] for row in trade_rows),
        "aggregate_unrealized_virtual_pl_usd": round(
            sum(row["unrealized_virtual_pl_usd"] for row in trade_rows), 5
        ),
        "warning": "Practice funds and P/L are virtual and not withdrawable.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit current OANDA Practice positions without mutation.")
    parser.add_argument("--output", default="state/oanda-practice-account-audit.json")
    args = parser.parse_args(argv)
    try:
        report = build_audit(ForwardPracticeClient.from_environment())
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            "OANDA Practice audit: "
            f"open={report['observed_open_trade_count']}, "
            f"pending={report['observed_pending_order_count']}, "
            f"unprotected={report['unprotected_open_trade_count']}, "
            f"unrealized_virtual_pl=${report['aggregate_unrealized_virtual_pl_usd']:.5f}."
        )
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else "Practice account audit failed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
