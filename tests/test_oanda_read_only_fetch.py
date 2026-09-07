import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from experiments.oanda_demo.read_only_fetch import fetch_snapshot, main


def candle_fixture(count=240):
    candles = []
    for index in range(count):
        base = 1.10 + index * 0.000001
        bid = {
            "o": f"{base:.6f}",
            "h": f"{base + 0.0005:.6f}",
            "l": f"{base - 0.0005:.6f}",
            "c": f"{base + 0.00003:.6f}",
        }
        ask = {key: f"{float(value) + 0.0001:.6f}" for key, value in bid.items()}
        candles.append(
            {
                "time": f"2026-01-{1 + index // 24:02d}T{index % 24:02d}:00:00+00:00",
                "complete": True,
                "bid": bid,
                "ask": ask,
            }
        )
    return {"instrument": "EUR_USD", "granularity": "H1", "candles": candles}


class ReadOnlyFetchTests(TestCase):
    def test_snapshot_reads_summary_and_candles_even_with_open_demo_trades(self):
        client = Mock()
        summary = {
            "environment": "practice",
            "currency": "USD",
            "nav": 1000.0,
            "balance": 1000.0,
            "open_trade_count": 3,
        }
        candles = candle_fixture()
        client.summary.return_value = summary
        client.candles.return_value = candles

        returned_summary, returned_candles = fetch_snapshot(client, 240)

        self.assertIs(returned_summary, summary)
        self.assertIs(returned_candles, candles)
        client.summary.assert_called_once_with()
        client.candles.assert_called_once_with(240)

    def test_cli_writes_only_candles_and_does_not_disclose_account_values(self):
        client = Mock()
        client.summary.return_value = {
            "environment": "practice",
            "currency": "USD",
            "nav": 9876.54,
            "balance": 9876.54,
            "open_trade_count": 2,
        }
        candles = candle_fixture()
        client.candles.return_value = candles

        with TemporaryDirectory() as directory:
            output = Path(directory) / "candles.json"
            stdout = io.StringIO()
            with patch(
                "experiments.oanda_demo.read_only_fetch.PracticeReader.from_environment",
                return_value=client,
            ), patch("sys.stdout", stdout):
                result = main(["--output", str(output), "--count", "240"])

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), candles)
            message = stdout.getvalue()
            self.assertIn("Existing open practice trades detected", message)
            self.assertIn("No orders sent", message)
            self.assertNotIn("9876.54", message)
            self.assertNotIn("2 existing", message)

    def test_cli_fails_closed_without_writing_on_reader_error(self):
        client = Mock()
        client.summary.side_effect = ValueError("private fixture detail")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "candles.json"
            stderr = io.StringIO()
            with patch(
                "experiments.oanda_demo.read_only_fetch.PracticeReader.from_environment",
                return_value=client,
            ), patch("sys.stderr", stderr):
                result = main(["--output", str(output), "--count", "240"])

            self.assertEqual(result, 2)
            self.assertFalse(output.exists())
            self.assertNotIn("private fixture detail", stderr.getvalue())
