import copy
import json
from unittest import TestCase

from experiments.oanda_demo.tournament import INSTRUMENTS
from experiments.oanda_demo.tournament_diagnostics import diagnose
from tests.test_oanda_tournament import payload


class OandaTournamentDiagnosticsTests(TestCase):
    def test_diagnostics_are_deterministic_and_never_touch_holdout(self):
        bundle = {
            "status": "practice_market_data",
            "captured_at": "2026-09-07T00:00:00+00:00",
            "summary": {"environment": "practice"},
            "candles": {
                instrument: payload(instrument, 1200, phase=index)
                for index, instrument in enumerate(INSTRUMENTS)
            },
        }
        first = diagnose(copy.deepcopy(bundle))
        second = diagnose(copy.deepcopy(bundle))
        self.assertEqual(first, second)
        self.assertFalse(first["holdout_inspected"])
        self.assertEqual(first["candidate_count"], 56)
        self.assertEqual(len(first["best_by_family"]), 5)
        self.assertNotIn("trade_log", json.dumps(first))
