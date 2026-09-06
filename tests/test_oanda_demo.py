from datetime import datetime, timedelta, timezone
import copy
import io
import json
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

from experiments.oanda_demo.lab import LabError, NoRedirects, PracticeReader, replay, signals, validate_candles, one_bar_trade


def fixture():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i in range(240):
        base = 1.10 + ((i % 80) if i % 160 < 80 else 80-(i % 80)) * 0.00005
        bid = {"o": str(base), "h": str(base+0.0005), "l": str(base-0.0005), "c": str(base+0.00003)}
        ask = {k: str(float(v)+0.0001) for k, v in bid.items()}
        candles.append({"time": (start+timedelta(hours=i)).isoformat(), "complete": True, "bid": bid, "ask": ask})
    return {"instrument": "EUR_USD", "granularity": "H1", "candles": candles}


class PracticeSafetyTests(TestCase):
    def test_credentials_are_required_and_account_cannot_inject_a_path(self):
        for token, account in [(None, None), ("test-token", "https://example.com"), ("test-token", "101-001-1234567-001/../../orders"), ("bad\ntoken", "101-001-1234567-001")]:
            with self.assertRaises(LabError):
                PracticeReader(token, account)

    def test_only_fixed_practice_get_routes_are_available(self):
        reader = PracticeReader("test-token", "101-001-1234567-001")
        for route in ["orders", "transactions", "https://api-fxtrade.oanda.com", "../orders"]:
            with self.assertRaises(LabError):
                reader._get(route)
        response = io.BytesIO(json.dumps({"account": {"currency": "USD", "NAV": "50", "balance": "50", "openTradeCount": 0}}).encode())
        with patch.object(reader._opener, "open", return_value=response) as opened:
            self.assertEqual(reader.summary()["balance"], 50)
            request = opened.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.full_url, "https://api-fxpractice.oanda.com/v3/accounts/101-001-1234567-001/summary")

    def test_redirect_and_http_error_never_disclose_credentials(self):
        with self.assertRaises(LabError):
            NoRedirects().redirect_request(None, None, 302, "", {}, "https://api-fxtrade.oanda.com")
        reader = PracticeReader("private-fixture-token", "101-001-1234567-001")
        with patch.object(reader._opener, "open", side_effect=HTTPError("https://example.com", 401, "secret detail", {}, None)):
            with self.assertRaises(LabError) as caught:
                reader.summary()
            self.assertNotIn("private-fixture-token", str(caught.exception))
            self.assertNotIn("secret detail", str(caught.exception))

    def test_bad_price_wrong_market_duplicate_time_and_incomplete_data_rejected(self):
        for mutate in [lambda d: d.update(instrument="USD_JPY"), lambda d: d["candles"][0]["bid"].update(c="NaN"), lambda d: d["candles"][1].update(time=d["candles"][0]["time"]), lambda d: d.update(candles=d["candles"][:100])]:
            data = fixture()
            mutate(data)
            with self.assertRaises(LabError):
                validate_candles(data)

    def test_future_candles_do_not_change_earlier_signals(self):
        data = fixture()
        original = signals(validate_candles(data))
        changed = copy.deepcopy(data)
        for b in changed["candles"][180:]:
            for side in ["bid", "ask"]:
                for key in "ohlc":
                    b[side][key] = str(float(b[side][key])*2)
        self.assertEqual(original[:180], signals(validate_candles(changed))[:180])

    def test_stop_wins_ambiguous_bar_and_spread_is_paid(self):
        bar = {"bid": {"o": 1.1, "h": 1.2, "l": 1.0, "c": 1.1}, "ask": {"o": 1.1001, "h": 1.2001, "l": 1.0001, "c": 1.1001}}
        trade = one_bar_trade(bar, 1, 100, 0.001)
        self.assertEqual(trade["reason"], "stop")
        self.assertLess(trade["pnl"], 0)
        flat = {"bid": {k: 1.1 for k in "ohlc"}, "ask": {k: 1.1001 for k in "ohlc"}}
        for direction in [1, -1]:
            self.assertAlmostEqual(one_bar_trade(flat, direction, 100, 0.001)["pnl"], -0.012, places=7)

    def test_replay_is_deterministic_separate_holdouts_are_virtual_and_unoptimized(self):
        first, second = replay(fixture()), replay(fixture())
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "historical_simulation_not_broker_trades")
        self.assertEqual([x["risk_percent"] for x in first["scenarios"]], [1, 2, 5])
        for scenario in first["scenarios"]:
            self.assertEqual(scenario["holdout"]["start_virtual_usd"], 50)
            self.assertEqual(scenario["development"]["start_virtual_usd"], 50)
            self.assertIsNone(scenario["holdout"]["goal_500_reached_at"])
