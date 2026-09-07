from datetime import datetime, timedelta, timezone
import json
from unittest import TestCase
from unittest.mock import Mock

from experiments.oanda_demo.lab import LabError
from experiments.oanda_demo.wave3_cross_data import (
    GRANULARITY,
    INSTRUMENTS,
    Wave3PracticeClient,
    export_preholdout,
    parse_candles,
)


def payload(instrument: str, count: int = 1300):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    previous = 1.2000
    for index in range(count):
        opening = previous
        close = opening + (0.00003 if index % 2 == 0 else -0.00002)
        high = max(opening, close) + 0.00030
        low = min(opening, close) - 0.00030
        bid = {
            "o": str(opening),
            "h": str(high),
            "l": str(low),
            "c": str(close),
        }
        ask = {key: str(float(value) + 0.00012) for key, value in bid.items()}
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


def keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys(child)


class OandaWave3CrossDataTests(TestCase):
    def test_instrument_universe_is_disjoint_from_opened_wave1_pairs(self):
        self.assertTrue(
            set(INSTRUMENTS).isdisjoint({"EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD"})
        )
        self.assertEqual(GRANULARITY, "H4")

    def test_reader_refuses_order_and_live_routes_before_network(self):
        client = Wave3PracticeClient("private-token", "101-001-1234567-001")
        client._opener = Mock()
        for route in ("orders", "trades", "positions", "../orders", "https://api-fxtrade.oanda.com"):
            with self.subTest(route=route), self.assertRaises(LabError):
                client._get(route)
        client._opener.open.assert_not_called()

    def test_parser_rejects_wrong_granularity_crossed_quotes_and_duplicates(self):
        wrong = payload("EUR_GBP")
        wrong["granularity"] = "H1"
        with self.assertRaises(LabError):
            parse_candles(wrong, "EUR_GBP")

        crossed = payload("EUR_GBP")
        crossed["candles"][5]["ask"]["o"] = "1.0"
        with self.assertRaises(LabError):
            parse_candles(crossed, "EUR_GBP")

        duplicate = payload("EUR_GBP")
        duplicate["candles"][6]["time"] = duplicate["candles"][5]["time"]
        with self.assertRaises(LabError):
            parse_candles(duplicate, "EUR_GBP")

    def test_export_withholds_final_twenty_percent_and_strips_account_data(self):
        bundle = {
            "status": "wave3_full_ephemeral_market_data",
            "captured_at": "2026-09-07T00:00:00+00:00",
            "summary": {
                "environment": "practice",
                "balance": 98765,
                "account_id": "101-001-1234567-001",
            },
            "instruments": list(INSTRUMENTS),
            "granularity": GRANULARITY,
            "candles": {instrument: payload(instrument) for instrument in INSTRUMENTS},
        }
        result = export_preholdout(bundle)
        self.assertFalse(result["holdout_exported"])
        self.assertNotIn("summary", result)
        self.assertTrue({"summary", "balance", "account_id"}.isdisjoint(keys(result)))
        self.assertNotIn("101-001-1234567-001", json.dumps(result))
        for instrument in INSTRUMENTS:
            selected = result["candles"][instrument]["candles"]
            original = bundle["candles"][instrument]["candles"]
            self.assertEqual(len(selected), 1040)
            self.assertEqual(selected[-1]["time"], original[1039]["time"])
            self.assertEqual(
                result["ranges"][instrument]["first_withheld_time"],
                original[1040]["time"],
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
