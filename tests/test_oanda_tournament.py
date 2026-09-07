from datetime import datetime, timedelta, timezone
import copy
import json
import math
from unittest import TestCase
from unittest.mock import Mock

from experiments.oanda_demo.lab import LabError
from experiments.oanda_demo.tournament import (
    Bar,
    Candidate,
    INSTRUMENTS,
    PracticeResearchClient,
    backtest,
    build_features,
    candidate_signal,
    evaluate_bundle,
    generate_candidates,
    parse_candles,
)


def payload(instrument: str, count: int = 1200, phase: float = 0.0):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    previous = 1.1 + phase * 0.001
    for index in range(count):
        wave = math.sin((index + phase * 11) / 17.0) * 0.0008
        drift = index * 0.0000004
        center = 1.1 + wave + drift + phase * 0.001
        opening = previous
        close = center
        high = max(opening, close) + 0.00035
        low = min(opening, close) - 0.00035
        spread = 0.00010
        bid = {"o": str(opening), "h": str(high), "l": str(low), "c": str(close)}
        ask = {key: str(float(value) + spread) for key, value in bid.items()}
        candles.append(
            {
                "time": (start + timedelta(hours=index)).isoformat(),
                "complete": True,
                "bid": bid,
                "ask": ask,
            }
        )
        previous = close
    return {"instrument": instrument, "granularity": "H1", "candles": candles}


def bars(count: int = 1200):
    return parse_candles(payload("EUR_USD", count), "EUR_USD")


class OandaTournamentTests(TestCase):
    def test_candidate_catalog_is_fresh_and_bounded(self):
        candidates = generate_candidates()
        self.assertEqual(len(candidates), 56)
        self.assertEqual(
            {candidate.family for candidate in candidates},
            {
                "compression_breakout",
                "range_reversion",
                "failed_breakout",
                "impulse_pullback",
                "session_breakout",
            },
        )
        self.assertFalse(any("sma" in candidate.identifier.lower() for candidate in candidates))

    def test_reader_rejects_non_get_research_routes_before_network(self):
        client = PracticeResearchClient("private-token", "101-001-1234567-001")
        client._opener = Mock()
        with self.assertRaises(LabError):
            client._get("orders")
        client._opener.open.assert_not_called()

    def test_parse_rejects_crossed_or_duplicate_candles(self):
        crossed = payload("EUR_USD")
        crossed["candles"][10]["ask"]["o"] = "1.0"
        with self.assertRaises(LabError):
            parse_candles(crossed, "EUR_USD")

        duplicate = payload("EUR_USD")
        duplicate["candles"][11]["time"] = duplicate["candles"][10]["time"]
        with self.assertRaises(LabError):
            parse_candles(duplicate, "EUR_USD")

    def test_backtest_is_deterministic_and_future_data_cannot_change_past(self):
        original = bars(1300)
        candidate = Candidate(
            "range_reversion",
            tuple(
                sorted(
                    {
                        "lookback": 24,
                        "zscore": 1.6,
                        "max_efficiency": 0.45,
                        "stop_atr": 1.25,
                        "target_r": 1.15,
                        "hold": 10,
                    }.items()
                )
            ),
        )
        first = backtest(build_features(original), candidate, 0, 900)
        second = backtest(build_features(original), candidate, 0, 900)
        self.assertEqual(first, second)

        changed = list(original)
        for index in range(900, len(changed)):
            bar = changed[index]
            changed[index] = Bar(
                bar.time,
                bar.bid_o * 2,
                bar.bid_h * 2,
                bar.bid_l * 2,
                bar.bid_c * 2,
                bar.ask_o * 2,
                bar.ask_h * 2,
                bar.ask_l * 2,
                bar.ask_c * 2,
            )
        third = backtest(build_features(tuple(changed)), candidate, 0, 900)
        self.assertEqual(first, third)

    def test_every_signal_uses_only_completed_history(self):
        feature_set = build_features(bars(1300))
        for candidate in generate_candidates():
            signal = candidate_signal(candidate, feature_set, len(feature_set.bars))
            if signal is not None:
                self.assertIn(signal.direction, (-1, 1))
                self.assertGreaterEqual(signal.stop_distance, 0.0004)
                self.assertGreater(signal.target_r, 0)
                self.assertGreater(signal.max_hold, 0)

    def test_full_tournament_is_deterministic_and_sanitized(self):
        bundle = {
            "status": "practice_market_data",
            "captured_at": "2026-09-07T00:00:00+00:00",
            "summary": {
                "environment": "practice",
                "currency": "USD",
                "balance": 100000,
                "nav": 100000,
                "open_trade_count": 0,
                "pending_order_count": 0,
            },
            "candles": {
                instrument: payload(instrument, 1200, phase=index)
                for index, instrument in enumerate(INSTRUMENTS)
            },
        }
        first = evaluate_bundle(copy.deepcopy(bundle))
        second = evaluate_bundle(copy.deepcopy(bundle))
        self.assertEqual(first, second)
        self.assertEqual(first["environment"], "practice")
        self.assertEqual(first["candidate_count"], 56)
        self.assertIn(first["decision"], {"eligible_for_guarded_demo_execution", "no_strategy_passed_holdout"})
        serialized = json.dumps(first)
        self.assertNotIn("private-token", serialized)
        self.assertNotIn("101-001-1234567-001", serialized)


if __name__ == "__main__":
    import unittest
    unittest.main()
