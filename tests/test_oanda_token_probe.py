import io
import json
from unittest import TestCase
from unittest.mock import Mock
from urllib.error import HTTPError

from experiments.oanda_demo.lab import LabError
from experiments.oanda_demo.token_probe import (
    LIVE_ORIGIN,
    PRACTICE_ORIGIN,
    authorized_account_ids,
    diagnose_practice_credentials,
    resolve_account_id,
)


def opener_for(account_ids):
    opener = Mock()
    payload = {"accounts": [{"id": account_id, "tags": []} for account_id in account_ids]}
    opener.open.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
    return opener


def rejecting_opener(url, code=401):
    opener = Mock()
    opener.open.side_effect = HTTPError(
        url,
        code,
        "secret broker detail",
        {},
        None,
    )
    return opener


class OandaTokenProbeTests(TestCase):
    def test_probe_uses_only_fixed_practice_account_list_get(self):
        opener = opener_for(["101-001-1234567-001"])
        self.assertEqual(
            authorized_account_ids("private-token", opener=opener),
            ("101-001-1234567-001",),
        )
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url,
            "https://api-fxpractice.oanda.com/v3/accounts",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer private-token")

    def test_common_copy_paste_wrappers_are_removed_without_changing_token(self):
        opener = opener_for(["101-001-1234567-001"])
        self.assertEqual(
            authorized_account_ids(
                ' OANDA_demo_API_token="Bearer private-token" ', opener=opener
            ),
            ("101-001-1234567-001",),
        )
        request = opener.open.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer private-token")

    def test_invalid_config_recovers_only_one_authorized_account(self):
        resolved, recovered = resolve_account_id(
            "private-token",
            "not-an-account-id",
            opener=opener_for(["101-001-1234567-001"]),
        )
        self.assertEqual(resolved, "101-001-1234567-001")
        self.assertTrue(recovered)

    def test_matching_config_is_used_without_recovery(self):
        resolved, recovered = resolve_account_id(
            "private-token",
            " 101-001-1234567-001\n",
            opener=opener_for(
                ["101-001-1234567-001", "101-001-7654321-002"]
            ),
        )
        self.assertEqual(resolved, "101-001-1234567-001")
        self.assertFalse(recovered)

    def test_diagnosis_normalizes_account_wrapper_and_reports_adjustment(self):
        result = diagnose_practice_credentials(
            'OANDA_demo_API_token="Bearer private-token"',
            "OANDA_demo_account_ID='101-001-1234567-001'",
            practice_opener=opener_for(["101-001-1234567-001"]),
        )
        self.assertEqual(
            result,
            ("101-001-1234567-001", False, True, True),
        )

    def test_invalid_config_with_multiple_accounts_fails_closed(self):
        with self.assertRaises(LabError) as caught:
            resolve_account_id(
                "private-token",
                "1234567",
                opener=opener_for(
                    ["101-001-1234567-001", "101-001-7654321-002"]
                ),
            )
        message = str(caught.exception)
        self.assertIn("multiple accounts", message)
        self.assertNotIn("101-001-1234567-001", message)
        self.assertNotIn("private-token", message)

    def test_valid_but_unauthorized_config_never_falls_back(self):
        with self.assertRaises(LabError) as caught:
            resolve_account_id(
                "private-token",
                "101-001-9999999-001",
                opener=opener_for(["101-001-1234567-001"]),
            )
        message = str(caught.exception)
        self.assertIn("not authorized", message)
        self.assertNotIn("101-001-9999999-001", message)
        self.assertNotIn("101-001-1234567-001", message)
        self.assertNotIn("private-token", message)

    def test_practice_rejection_and_live_success_are_classified_live_only(self):
        practice = rejecting_opener(PRACTICE_ORIGIN + "/v3/accounts")
        live = opener_for(["101-001-1234567-001"])
        with self.assertRaises(LabError) as caught:
            diagnose_practice_credentials(
                "private-token",
                "101-001-1234567-001",
                practice_opener=practice,
                live_opener=live,
            )
        message = str(caught.exception)
        self.assertIn("OANDA Live", message)
        self.assertIn("not OANDA Practice", message)
        self.assertNotIn("101-001-1234567-001", message)
        self.assertNotIn("private-token", message)
        live_request = live.open.call_args.args[0]
        self.assertEqual(live_request.get_method(), "GET")
        self.assertEqual(live_request.full_url, LIVE_ORIGIN + "/v3/accounts")

    def test_rejection_by_both_environments_is_specific_and_redacted(self):
        practice = rejecting_opener(PRACTICE_ORIGIN + "/v3/accounts")
        live = rejecting_opener(LIVE_ORIGIN + "/v3/accounts")
        with self.assertRaises(LabError) as caught:
            diagnose_practice_credentials(
                "private-token",
                "101-001-1234567-001",
                practice_opener=practice,
                live_opener=live,
            )
        message = str(caught.exception)
        self.assertIn("rejected by both", message)
        self.assertIn("OANDA_demo_API_token", message)
        self.assertNotIn("private-token", message)
        self.assertNotIn("101-001-1234567-001", message)

    def test_http_error_and_bad_payload_do_not_disclose_credentials(self):
        opener = rejecting_opener(PRACTICE_ORIGIN + "/v3/accounts")
        with self.assertRaises(LabError) as caught:
            authorized_account_ids("private-token", opener=opener)
        message = str(caught.exception)
        self.assertIn("HTTP 401", message)
        self.assertNotIn("private-token", message)
        self.assertNotIn("secret broker detail", message)

        bad = Mock()
        bad.open.return_value = io.BytesIO(b"not json")
        with self.assertRaises(LabError):
            authorized_account_ids("private-token", opener=bad)

    def test_empty_duplicate_and_malformed_account_lists_are_rejected(self):
        for payload in [
            {"accounts": []},
            {
                "accounts": [
                    {"id": "101-001-1234567-001"},
                    {"id": "101-001-1234567-001"},
                ]
            },
            {"accounts": [{"id": "not-an-account"}]},
            {"accounts": ["101-001-1234567-001"]},
        ]:
            opener = Mock()
            opener.open.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
            with self.subTest(payload=payload), self.assertRaises(LabError):
                authorized_account_ids("private-token", opener=opener)

    def test_token_validation_rejects_missing_or_embedded_whitespace(self):
        for token in [None, "", "bad token", "bad\ntoken"]:
            with self.subTest(token=token), self.assertRaises(LabError):
                authorized_account_ids(
                    token, opener=opener_for(["101-001-1234567-001"])
                )

    def test_unapproved_origin_is_rejected_before_network(self):
        opener = opener_for(["101-001-1234567-001"])
        with self.assertRaises(LabError):
            authorized_account_ids(
                "private-token",
                opener=opener,
                origin="https://example.com",
            )
        opener.open.assert_not_called()
