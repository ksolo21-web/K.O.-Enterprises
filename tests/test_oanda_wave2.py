from datetime import datetime, timedelta, timezone
import json
from unittest import TestCase

from experiments.oanda_demo.tournament import Bar, INSTRUMENTS, build_features
from experiments.oanda_demo.wave2 import (
    PRIMARY_INSTRUMENT,
    _timestamp_maps,
    evaluate_bundle,
    metrics,
    signal_at,
)


def feature_with_shock(direction: int, *, shock_index: int = 25):
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    bars = []
    previous = 1.2000
    for index in range(50):
        opening = previous
        change = 0.00001
        if index == shock_index:
            change = direction * 0.0030
        close = opening + change
        high = max(opening, close) + 0.00030
        low = min(opening, close) - 0.00030
        spread = 0.00010
        bars.append(
            Bar(
                time=start + timedelta(hours=index),
                bid_o=opening,
                bid_h=high,
                bid_l=low,
                bid_c=close,
                ask_o=opening + spread,
                ask_h=high + spread,
                ask_l=low + spread,
                ask_c=close + spread,
            )
        )
        previous = close
    return build_features(tuple(bars))


def flat_payload(instrument: str, count: int = 5000):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    previous = 1.1000
    for index in range(count):
        opening = previous
        close = opening + 0.000001
        high = close + 0.00020
        low = opening - 0.00020
        bid = {
            "o": str(opening),
            "h": str(high),
            "l": str(low),
            "c": str(close),
        }
        ask = {key: str(float(value) + 0.00010) for key, value in bid.items()}
        rows.append(
            {
                "time": (start + timedelta(hours=index)).isoformat(),
                "complete": True,
                "bid": bid,
                "ask": ask,
            }
        )
        previous = close
    return {"instrument": instrument, "granularity": "H1", "candles": rows}


class OandaWave2Tests(TestCase):
    def test_signal_requires_primary_shock_and_two_same_direction_confirmations(self):
        features = {
            PRIMARY_INSTRUMENT: feature_with_shock(1),
            "EUR_USD": feature_with_shock(1),
            "AUD_USD": feature_with_shock(1),
            "NZD_USD": feature_with_shock(-1),
        }
        signal = signal_at(features, _timestamp_maps(features), 26)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["direction"], 1)
        self.assertEqual(signal["confirmations"], 2)
        self.assertGreaterEqual(signal["stop_distance"], 0.0004)

        rejected = {
            PRIMARY_INSTRUMENT: feature_with_shock(1),
            "EUR_USD": feature_with_shock(-1),
            "AUD_USD": feature_with_shock(-1),
            "NZD_USD": feature_with_shock(1),
        }
        self.assertIsNone(signal_at(rejected, _timestamp_maps(rejected), 26))

    def test_signal_uses_the_completed_bar_before_entry(self):
        features = {
            PRIMARY_INSTRUMENT: feature_with_shock(1, shock_index=26),
            "EUR_USD": feature_with_shock(1, shock_index=26),
            "AUD_USD": feature_with_shock(1, shock_index=26),
            "NZD_USD": feature_with_shock(1, shock_index=26),
        }
        maps = _timestamp_maps(features)
        self.assertIsNone(signal_at(features, maps, 26))
        self.assertIsNotNone(signal_at(features, maps, 27))

    def test_stress_metrics_charge_two_pips_per_trade(self):
        trades = [
            {
                "direction": 1,
                "r_multiple": 1.0,
                "stress_r_multiple": 0.8,
                "pnl_pips": 10.0,
                "exit_reason": "target",
            },
            {
                "direction": -1,
                "r_multiple": -0.5,
                "stress_r_multiple": -0.7,
                "pnl_pips": -5.0,
                "exit_reason": "stop",
            },
        ]
        base = metrics(trades)
        stress = metrics(trades, stress=True)
        self.assertAlmostEqual(base["sum_r"], 0.5)
        self.assertAlmostEqual(stress["sum_r"], 0.1)
        self.assertAlmostEqual(base["total_pips"], 5.0)
        self.assertAlmostEqual(stress["total_pips"], 1.0)

    def test_failed_preholdout_gate_never_inspects_holdout(self):
        bundle = {
            "status": "practice_market_data",
            "captured_at": "2026-07-28T00:00:00+00:00",
            "summary": {
                "environment": "practice",
                "account_id": "101-001-1234567-001",
            },
            "candles": {
                instrument: flat_payload(instrument) for instrument in INSTRUMENTS
            },
        }
        result = evaluate_bundle(bundle)
        self.assertFalse(result["preholdout_aggregate"]["passed"])
        self.assertFalse(result["holdout_inspected"])
        self.assertIsNone(result["holdout"])
        self.assertEqual(result["decision"], "preholdout_gate_failed")
        serialized = json.dumps(result)
        self.assertNotIn("101-001-1234567-001", serialized)
        self.assertNotIn("account_id", serialized)


if __name__ == "__main__":
    import unittest

    unittest.main()
