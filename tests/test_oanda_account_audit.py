import io
import json
from unittest import TestCase
from unittest.mock import Mock

from experiments.oanda_demo.account_audit import PracticeAuditClient, build_audit


class FakeAuditClient:
    def summary(self):
        return {
            "nav": 100000.0,
            "margin_available": 99999.0,
            "open_trade_count": 1,
            "pending_order_count": 2,
            "guaranteed_stop_mode": "DISABLED",
        }

    def open_trades(self):
        return [
            {
                "id": "77",
                "instrument": "GBP_USD",
                "price": "1.35000",
                "openTime": "2026-09-07T22:30:00Z",
                "initialUnits": "888",
                "currentUnits": "888",
                "unrealizedPL": "0.42",
                "financing": "0.00",
                "stopLossOrder": {"price": "1.33875"},
                "takeProfitOrder": {"price": "1.36406"},
                "clientExtensions": {"comment": "must-not-leak"},
            }
        ]

    def pending_orders(self):
        return [
            {
                "id": "78",
                "type": "STOP_LOSS",
                "tradeID": "77",
                "price": "1.33875",
                "timeInForce": "GTC",
            },
            {
                "id": "79",
                "type": "TAKE_PROFIT",
                "tradeID": "77",
                "price": "1.36406",
                "timeInForce": "GTC",
            },
        ]


class OandaAccountAuditTests(TestCase):
    def test_audit_reports_protection_without_identifiers_or_balance(self):
        report = build_audit(FakeAuditClient())
        self.assertEqual(report["observed_open_trade_count"], 1)
        self.assertEqual(report["observed_pending_order_count"], 2)
        self.assertEqual(report["unprotected_open_trade_count"], 0)
        self.assertEqual(report["aggregate_unrealized_virtual_pl_usd"], 0.42)
        trade = report["open_trades"][0]
        self.assertEqual(trade["instrument"], "GBP_USD")
        self.assertTrue(trade["fully_protected"])
        serialized = json.dumps(report)
        self.assertNotIn("100000", serialized)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn('"77"', serialized)

    def test_pending_order_reader_uses_one_fixed_practice_get(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(
            json.dumps({"orders": [{"id": "78", "type": "STOP_LOSS"}]}).encode()
        )
        client = PracticeAuditClient(
            "private-token", "101-001-1234567-001", opener=opener
        )
        rows = client.pending_orders()
        self.assertEqual(len(rows), 1)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url,
            "https://api-fxpractice.oanda.com/v3/accounts/101-001-1234567-001/pendingOrders",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
