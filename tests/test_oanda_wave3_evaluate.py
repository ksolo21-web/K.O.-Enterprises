from datetime import datetime, timedelta, timezone
import json
from unittest import TestCase

from experiments.oanda_demo.tournament import Bar, build_features
from experiments.oanda_demo.wave3_cross_data import GRANULARITY, INSTRUMENTS
from experiments.oanda_demo.wave3_evaluate import (
    HOLDOUT_START,
    evaluate_bundle,
    metrics,
    signal_at,
)


def feature_with_extreme(signal_index: int = 50):
    start = datetime(2025, 1, 6, 1, tzinfo=timezone.utc)
    bars = []
    for index in range(90):
        baseline = 1.5000 + (index % 7) * 0.00001
        opening = baseline - 0.00002
        close = baseline
        high = max(opening, close) + 0.00040
        low = min(opening, close) - 0.00040
        if index == signal_index:
            opening = 1.4800
            close = 1.4850
            high = 1.4860
            low = 1.4790
        spread = 0.0002
        bars.append(
            Bar(
                time=start + timedelta(hours=4 * index),
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
    return build_features(tuple(bars))


def flat_payload(instrument: str, count: int = 5000):
    start = HOLDOUT_START - timedelta(hours=4 * 3999)
    rows = []
    previous = 1.2000
    for index in range(count):
        opening = previous
        close = opening + 0.000001
        high = close + 0.0003
        low = opening - 0.0003
        bid = {
            "o": str(opening),
            "h": str(high),
            "l": str(low),
            "c": str(close),
        }
        ask = {key: str(float(value) + 0.0002) for key, value in bid.items()}
        rows.append(
            {
                "time": (start + timedelta(hours=4 * index)).isoformat(),
                "complete": True,
                "bid": bid,
                "ask": ask,
            }
        )
        previous = close
    return {"instrument": instrument, "granularity": GRANULARITY, "candles": rows}


class OandaWave3EvaluateTests(TestCase):
    def test_signal_enters_only_after_completed_extreme_reversal(self):
        features = feature_with_extreme()
        self.assertIsNone(signal_at(features, 50))
        signal = signal_at(features, 51)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["direction"], 1)
        self.assertEqual(signal["signal_index"], 50)
        self.assertEqual(signal["signal_time"], features.bars[50].time)
        self.assertEqual(signal["entry_time"], features.bars[51].time)
        self.assertLess(signal["zscore"], -1.7)

    def test_extra_cost_is_deducted_in_risk_units(self):
        trades = [
            {
                "direction": 1,
                "r_multiple": 1.0,
                "pnl_pips": 10.0,
                "stop_distance_pips": 20.0,
                "exit_reason": "target",
            },
            {
                "direction": -1,
                "r_multiple": -0.5,
                "pnl_pips": -5.0,
                "stop_distance_pips": 20.0,
                "exit_reason": "stop",
            },
        ]
        base = metrics(trades)
        stress = metrics(trades, 4.0)
        self.assertAlmostEqual(base["sum_r"], 0.5)
        self.assertAlmostEqual(stress["sum_r"], 0.1)
        self.assertAlmostEqual(stress["total_pips_after_extra_cost"], -3.0)

    def test_failed_preholdout_never_opens_sealed_holdout_or_leaks_account_data(self):
        bundle = {
            "status": "wave3_full_ephemeral_market_data",
            "captured_at": "2026-09-07T00:00:00+00:00",
            "summary": {
                "environment": "practice",
                "account_id": "101-001-1234567-001",
                "balance": 12345,
            },
            "instruments": list(INSTRUMENTS),
            "granularity": GRANULARITY,
            "candles": {
                instrument: flat_payload(instrument) for instrument in INSTRUMENTS
            },
        }
        first = evaluate_bundle(bundle)
        second = evaluate_bundle(bundle)
        self.assertEqual(first, second)
        self.assertFalse(first["preholdout"]["aggregate"]["passed"])
        self.assertFalse(first["holdout_inspected"])
        self.assertIsNone(first["holdout"])
        self.assertEqual(first["decision"], "preholdout_gate_failed")
        serialized = json.dumps(first)
        self.assertNotIn("101-001-1234567-001", serialized)
        self.assertNotIn("account_id", serialized)
        self.assertNotIn("12345", serialized)


if __name__ == "__main__":
    import unittest

    unittest.main()
