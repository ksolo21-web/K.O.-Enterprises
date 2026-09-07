from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from experiments.oanda_demo.forward_lab import (
    APPROVAL_PHRASE,
    CANDLE_COUNT,
    INSTRUMENTS,
    MAX_UNITS,
    MAX_VIRTUAL_RISK_USD,
    ForwardPracticeClient,
    MarketFeatures,
    build_plan,
    execute_plan,
    select_signal,
)
from experiments.oanda_demo.lab import LabError, PRACTICE_ORIGIN


def market(
    instrument,
    *,
    score24=0.0,
    score6=0.0,
    efficiency=0.1,
    zscore=0.0,
    candle_direction=0,
    close_location=0.5,
):
    return MarketFeatures(
        instrument=instrument,
        signal_time=datetime(2026, 9, 7, 20, tzinfo=timezone.utc),
        atr=0.0012,
        score_24=score24,
        score_6=score6,
        efficiency_24=efficiency,
        zscore_24=zscore,
        candle_direction=candle_direction,
        close_location=close_location,
    )


class FakeClient:
    def __init__(self):
        self.placed = None
        self.request_id = None

    def summary(self):
        return {
            "nav": 1_000_000.0,
            "margin_available": 1_000_000.0,
            "open_trade_count": 0,
            "pending_order_count": 0,
            "guaranteed_stop_mode": "DISABLED",
        }

    def instrument_metadata(self):
        return {
            instrument: {
                "display_precision": 5,
                "minimum_trade_size": 1,
                "maximum_order_units": 100_000_000,
            }
            for instrument in INSTRUMENTS
        }

    def candles(self, instrument):
        return {"instrument": instrument}

    def prices(self):
        now = datetime.now(timezone.utc)
        return {
            instrument: {
                "bid": 1.10000,
                "ask": 1.10010,
                "time": now,
                "tradeable": True,
                "available_long": 100_000,
                "available_short": 100_000,
            }
            for instrument in INSTRUMENTS
        }

    def open_trades(self):
        if self.placed is None:
            return []
        return [
            {
                "id": "77",
                "stopLossOrder": {"price": self.placed["stopLossOnFill"]["price"]},
                "takeProfitOrder": {"price": self.placed["takeProfitOnFill"]["price"]},
            }
        ]

    def place_market_order(self, order, *, request_id):
        self.placed = order
        self.request_id = request_id
        return {
            "transaction_id": "76",
            "trade_id": "77",
            "instrument": order["instrument"],
            "units": order["units"],
            "fill_price": "1.10010",
            "fill_time": "2026-09-07T22:30:00Z",
        }


class OandaForwardLabTests(TestCase):
    def test_shared_parser_minimum_is_satisfied(self):
        self.assertGreaterEqual(CANDLE_COUNT, 1000)

    def test_client_refuses_live_and_unapproved_routes_before_network(self):
        opener = Mock()
        client = ForwardPracticeClient(
            "private-token", "101-001-1234567-001", opener=opener
        )
        for method, route in [
            ("GET", "orders"),
            ("GET", "trades"),
            ("GET", "https://api-fxtrade.oanda.com"),
            ("POST", "trades"),
            ("DELETE", "orders"),
        ]:
            with self.subTest(method=method, route=route), self.assertRaises(LabError):
                client._request(method, route, payload={} if method == "POST" else None)
        opener.open.assert_not_called()
        self.assertNotIn("api-fxtrade", PRACTICE_ORIGIN)

    def test_selector_switches_between_current_trend_and_reversal_arms(self):
        trend = {
            instrument: market(instrument, efficiency=0.35)
            for instrument in INSTRUMENTS
        }
        trend["EUR_USD"] = market(
            "EUR_USD",
            score24=1.1,
            score6=0.5,
            efficiency=0.55,
            candle_direction=1,
        )
        selected = select_signal(trend)
        self.assertEqual(selected["strategy"], "forward_adaptive_trend_v1")
        self.assertEqual(selected["instrument"], "EUR_USD")
        self.assertEqual(selected["direction"], 1)

        reversal = {
            instrument: market(instrument, efficiency=0.15)
            for instrument in INSTRUMENTS
        }
        reversal["GBP_USD"] = market(
            "GBP_USD",
            efficiency=0.2,
            zscore=2.2,
            candle_direction=-1,
            close_location=0.35,
        )
        selected = select_signal(reversal)
        self.assertEqual(selected["strategy"], "forward_exhaustion_reversal_v1")
        self.assertEqual(selected["instrument"], "GBP_USD")
        self.assertEqual(selected["direction"], -1)

    def test_plan_caps_units_and_virtual_risk(self):
        client = FakeClient()
        features = market(
            "EUR_USD",
            score24=1.0,
            score6=0.4,
            efficiency=0.5,
            candle_direction=1,
        )
        with patch(
            "experiments.oanda_demo.forward_lab._market_features",
            side_effect=lambda instrument, payload: (
                features if instrument == "EUR_USD" else market(instrument, efficiency=0.35)
            ),
        ):
            plan = build_plan(client)
        self.assertTrue(plan["eligible"])
        self.assertEqual(plan["environment"], "practice")
        self.assertLessEqual(abs(plan["signed_units"]), MAX_UNITS)
        self.assertLessEqual(
            plan["estimated_max_virtual_risk_usd"], MAX_VIRTUAL_RISK_USD
        )
        serialized = json.dumps(plan)
        self.assertNotIn("101-001-1234567-001", serialized)
        self.assertNotIn("private-token", serialized)

    def test_existing_trade_blocks_plan_before_market_scanning(self):
        client = FakeClient()
        client.summary = lambda: {
            "nav": 1000.0,
            "margin_available": 1000.0,
            "open_trade_count": 1,
            "pending_order_count": 0,
            "guaranteed_stop_mode": "DISABLED",
        }
        client.instrument_metadata = Mock()
        plan = build_plan(client)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "existing_practice_trade_or_order")
        client.instrument_metadata.assert_not_called()

    def test_execution_requires_exact_short_lived_plan_permit(self):
        client = FakeClient()
        plan = {
            "eligible": True,
            "plan_id": "ko-fwd-12345678901234567890",
            "strategy": "forward_adaptive_trend_v1",
            "instrument": "EUR_USD",
            "direction": "long",
            "signed_units": 100,
            "price_bound": "1.10030",
            "stop_loss": "1.09810",
            "take_profit": "1.10360",
            "estimated_max_virtual_risk_usd": 0.2,
        }
        with tempfile.TemporaryDirectory() as directory:
            permit_path = Path(directory) / "permit.json"
            permit_path.write_text(
                json.dumps(
                    {
                        "environment": "practice",
                        "scope": "oanda_practice_forward_experiment_only",
                        "plan_id": plan["plan_id"],
                        "max_orders": 1,
                        "max_units": 100,
                        "max_virtual_risk_usd": 1.0,
                        "single_use": True,
                        "request_id": "ko-fwd-test-0001",
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(minutes=30)
                        ).isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(LabError):
                execute_plan(client, plan, str(permit_path))
            with patch.dict(
                os.environ,
                {"OANDA_PRACTICE_EXECUTION_APPROVAL": APPROVAL_PHRASE},
                clear=True,
            ):
                result = execute_plan(client, plan, str(permit_path))

        self.assertEqual(result["status"], "practice_forward_order_filled")
        self.assertTrue(result["attached_stop_verified"])
        self.assertTrue(result["attached_take_profit_verified"])
        self.assertFalse(result["real_money"])
        self.assertEqual(client.placed["type"], "MARKET")
        self.assertEqual(client.placed["timeInForce"], "FOK")
        self.assertIn("priceBound", client.placed)
        self.assertIn("stopLossOnFill", client.placed)
        self.assertIn("takeProfitOnFill", client.placed)
        self.assertNotIn("clientExtensions", client.placed)
        self.assertNotIn("tradeClientExtensions", client.placed)
        self.assertEqual(client.request_id, "ko-fwd-test-0001")


if __name__ == "__main__":
    import unittest

    unittest.main()
