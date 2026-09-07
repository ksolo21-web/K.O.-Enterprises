from datetime import datetime, timedelta, timezone
from unittest import TestCase

from experiments.oanda_demo.tournament import Bar, build_features
from experiments.oanda_demo.wave4_evaluate import (
    EXACT_PARAMETERS,
    _timestamp_maps,
    metrics,
    setup_at_signal,
    signal_at_entry,
)
from experiments.oanda_demo.wave4_jpy_data import INSTRUMENTS, PIP_SIZE


def market_times(count):
    stamp = datetime(2025, 1, 6, 1, tzinfo=timezone.utc)
    result = []
    while len(result) < count:
        if stamp.weekday() < 5:
            result.append(stamp)
        stamp += timedelta(hours=4)
    return result


def trending_features(direction=1, count=130):
    bars = []
    previous = 145.0
    for index, stamp in enumerate(market_times(count)):
        opening = previous
        change = direction * (0.018 + (index % 5) * 0.001)
        close = opening + change
        high = max(opening, close) + 0.04
        low = min(opening, close) - 0.04
        spread = 0.012
        bars.append(
            Bar(
                stamp,
                opening,
                high,
                low,
                close,
                opening + spread,
                high + spread,
                low + spread,
                close + spread,
            )
        )
        previous = close
    return build_features(tuple(bars))


class OandaWave4EvaluateTests(TestCase):
    def test_breadth_setup_uses_all_completed_pairs(self):
        features = {instrument: trending_features(1) for instrument in INSTRUMENTS}
        setup = setup_at_signal(features, _timestamp_maps(features), 100)
        self.assertIsNotNone(setup)
        self.assertEqual(setup["direction"], 1)
        self.assertEqual(setup["positive_pairs"], len(INSTRUMENTS))
        self.assertGreater(setup["median_score"], EXACT_PARAMETERS.median_threshold)

    def test_entry_occurs_after_signal_and_has_protection_distance(self):
        features = {instrument: trending_features(1) for instrument in INSTRUMENTS}
        maps = _timestamp_maps(features)
        entry_index = next(
            index
            for index, bar in enumerate(features["USD_JPY"].bars[80:], start=80)
            if bar.time.weekday() < 4 and bar.time.hour not in (21, 22)
        )
        signal = signal_at_entry(features, maps, entry_index)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["signal_index"], entry_index - 1)
        self.assertLess(signal["signal_time"], signal["entry_time"])
        self.assertGreaterEqual(signal["stop_distance"], 0.05)

    def test_jpy_pip_stress_is_deducted_in_risk_units(self):
        trades = [
            {"direction": 1, "r_multiple": 1.0, "pnl_pips": 10.0, "stop_distance_pips": 20.0, "exit_reason": "target"},
            {"direction": -1, "r_multiple": -0.5, "pnl_pips": -5.0, "stop_distance_pips": 20.0, "exit_reason": "stop"},
        ]
        base = metrics(trades)
        stress = metrics(trades, 4.0)
        self.assertEqual(PIP_SIZE, 0.01)
        self.assertAlmostEqual(base["sum_r"], 0.5)
        self.assertAlmostEqual(stress["sum_r"], 0.1)
        self.assertAlmostEqual(stress["total_pips_after_extra_cost"], -3.0)


if __name__ == "__main__":
    import unittest

    unittest.main()
