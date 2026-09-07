from unittest import TestCase

from experiments.oanda_demo.preholdout_export import export_preholdout
from experiments.oanda_demo.tournament import INSTRUMENTS
from tests.test_oanda_tournament import payload


class OandaPreholdoutExportTests(TestCase):
    def test_export_contains_only_first_eighty_percent_and_no_account_data(self):
        bundle = {
            "status": "practice_market_data",
            "captured_at": "2026-09-07T00:00:00+00:00",
            "summary": {
                "environment": "practice",
                "balance": 12345,
                "nav": 12345,
                "account_id": "101-001-1234567-001",
            },
            "candles": {
                instrument: payload(instrument, 1200, phase=index)
                for index, instrument in enumerate(INSTRUMENTS)
            },
        }
        exported = export_preholdout(bundle)
        self.assertEqual(exported["status"], "pre_holdout_market_data")
        self.assertFalse(exported["holdout_exported"])
        self.assertNotIn("summary", exported)
        serialized = str(exported)
        self.assertNotIn("12345", serialized)
        self.assertNotIn("101-001-1234567-001", serialized)
        for instrument in INSTRUMENTS:
            original = bundle["candles"][instrument]["candles"]
            selected = exported["candles"][instrument]["candles"]
            self.assertEqual(len(selected), 960)
            self.assertEqual(selected[-1]["time"], original[959]["time"])
            self.assertEqual(
                exported["ranges"][instrument]["first_withheld_time"],
                original[960]["time"],
            )
