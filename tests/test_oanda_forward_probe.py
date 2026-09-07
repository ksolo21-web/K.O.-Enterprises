from datetime import datetime, timedelta, timezone
import json
from unittest import TestCase
from unittest.mock import Mock, patch

from experiments.oanda_demo.forward_lab import INSTRUMENTS, MarketFeatures
from experiments.oanda_demo.forward_probe import (
    PROBE_MAX_UNITS,
    PROBE_MAX_VIRTUAL_RISK_USD,
    build_probe_plan,
    current_prices_without_units_available,
    select_probe_signal,
)
from experiments.oanda_demo.lab import LabError


def market(
    instrument,
    *,
    score24=0.0,
    score6=0.0,
    efficiency=0.1,
    candle_direction=0,
):
    return MarketFeatures(
        instrument=instrument,
        signal_time=datetime(2026, 9, 7, 21, tzinfo=timezone.utc),
        atr=0.00075,
        score_24=score24,
        score_6=score6,
        efficiency_24=efficiency,
        zscore_24=0.0,
        candle_direction=candle_direction,
        close_location=0.6,
    )


class FakeClient:
    def summary(self):
        return {
            "nav": 50_000.0,
            "margin_available": 50_000.0,
            "open_trade_count": 0,
            "pending_order_count": 0,
            "guaranteed_stop_mode": "DISABLED",
        }

    def instrument_metadata(self):
        return {
            instrument: {
                "display_precision": 5,
                "minimum_trade_size": 1,
                "maximum_order_units": 100_000,
            }
            for instrument in INSTRUMENTS
        }

    def candles(self, instrument):
        return {"instrument": instrument}

    def _request(self, method, resource, *, params=None, payload=None, request_id=None):
        if method != "GET" or resource != "pricing":
            raise AssertionError("unexpected fake request")
        now = datetime.now(timezone.utc)
        return {
            "prices": [
                {
                    "instrument": instrument,
                    "time": now.isoformat(),
                    "status": "tradeable",
                    "bids": [{"price": "1.10000"}],
                    "asks": [{"price": "1.10010"}],
                }
                for instrument in INSTRUMENTS
            ]
        }


class OandaForwardProbeTests(TestCase):
    def test_current_like_snapshot_selects_gbp_and_rejects_unconfirmed_aud(self):
        markets = {
            "AUD_USD": market(
                "AUD_USD",
                score24=0.739155,
                score6=0.019777,
                efficiency=0.228419,
                candle_direction=1,
            ),
            "GBP_USD": market(
                "GBP_USD",
                score24=0.618882,
                score6=0.133298,
                efficiency=0.246612,
                candle_direction=1,
            ),
            "EUR_USD": market(
                "EUR_USD",
                score24=0.542951,
                score6=-0.340069,
                efficiency=0.226066,
                candle_direction=1,
            ),
            "NZD_USD": market(
                "NZD_USD",
                score24=0.073924,
                score6=0.178973,
                efficiency=0.027496,
                candle_direction=1,
            ),
        }
        selected = select_probe_signal(markets)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["instrument"], "GBP_USD")
        self.assertEqual(selected["direction"], 1)
        self.assertEqual(selected["strategy"], "forward_relative_strength_probe_v1")

    def test_price_parser_tolerates_missing_units_available(self):
        client = FakeClient()
        prices = current_prices_without_units_available(client)
        self.assertEqual(set(prices), set(INSTRUMENTS))
        self.assertTrue(all(price["tradeable"] for price in prices.values()))
        self.assertTrue(all("available_long" not in price for price in prices.values()))

    def test_price_parser_rejects_crossed_or_missing_market(self):
        client = FakeClient()
        original = client._request

        def crossed(*args, **kwargs):
            payload = original(*args, **kwargs)
            payload["prices"][0]["asks"][0]["price"] = "1.09900"
            return payload

        client._request = crossed
        with self.assertRaises(LabError):
            current_prices_without_units_available(client)

    def test_probe_plan_is_capped_at_one_virtual_dollar(self):
        client = FakeClient()
        selected = market(
            "GBP_USD",
            score24=0.62,
            score6=0.14,
            efficiency=0.25,
            candle_direction=1,
        )
        with patch(
            "experiments.oanda_demo.forward_probe._market_features",
            side_effect=lambda instrument, payload: (
                selected if instrument == "GBP_USD" else market(instrument)
            ),
        ), patch(
            "experiments.oanda_demo.forward_probe._blocked_time",
            return_value=False,
        ):
            plan = build_probe_plan(client)
        self.assertTrue(plan["eligible"])
        self.assertEqual(plan["instrument"], "GBP_USD")
        self.assertEqual(plan["direction"], "long")
        self.assertLessEqual(abs(plan["signed_units"]), PROBE_MAX_UNITS)
        self.assertLessEqual(
            plan["estimated_max_virtual_risk_usd"],
            PROBE_MAX_VIRTUAL_RISK_USD,
        )
        self.assertFalse(plan["validated_profitability"])
        self.assertFalse(plan["real_money"])
        self.assertIn("warning", plan)
        serialized = json.dumps(plan)
        self.assertNotIn("account_id", serialized)

    def test_existing_trade_blocks_before_candle_or_price_reads(self):
        client = FakeClient()
        client.summary = lambda: {
            "nav": 50_000.0,
            "margin_available": 50_000.0,
            "open_trade_count": 1,
            "pending_order_count": 0,
            "guaranteed_stop_mode": "DISABLED",
        }
        client.instrument_metadata = Mock()
        client.candles = Mock()
        plan = build_probe_plan(client)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "existing_practice_trade_or_order")
        client.instrument_metadata.assert_not_called()
        client.candles.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
