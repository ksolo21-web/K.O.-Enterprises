"""CE-1B adversarial tests. All network operations are mocked."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import ssl
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from company_os.approved_source_fetch import (
    MAX_DNS_ANSWERS, CaptureReceipt, _PinnedHTTPSConnection,
    _download_https, _resolve_pinned_endpoint, fetch_and_capture,
    inspect_source_permit,
)
from company_os.policy import ApprovalRequired, PauseActive
from company_os.source_provenance import EvidenceError, SourceLedger

KEY = "synthetic-governance-secret-" + "A" * 48
URL = "https://detroitmi.gov/public/eligibility"


class MockResponse:
    def __init__(self, body=b"Public source says a Detroit certificate is required for the janitorial service.",
                 status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers if headers is not None else [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        self.last_read = None

    def getheaders(self):
        return self.headers

    def getheader(self, key, default=None):
        for k, v in self.headers:
            if k.lower() == key.lower():
                return v
        return default

    def read(self, n=-1):
        self.last_read = n
        return self.body if n < 0 else self.body[:n]


class MockConnection:
    def __init__(self, response):
        self.response = response
        self.sock = MagicMock()
        self.sock.getpeercert.return_value = b"demo-der-certificate"
        self.sock.version.return_value = "TLSv1.3"
        self.request_args = None
        self.closed = False

    def request(self, method, path, headers):
        self.request_args = (method, path, headers)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class ApprovedSourceFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "KO_SOURCE_ACCESS_POLICY_KEY": KEY,
            "KO_SOURCE_APPROVED_HOSTS": "detroitmi.gov",
            "COMPANY_OS_PAUSED": "0",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ledger = SourceLedger(self.root)
        self.addCleanup(self.ledger.close)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)

    def permit(self, **changes):
        base = {
            "schema_version": "1.0",
            "target_url": URL, "publisher": "City department",
            "title": "Source listing", "origin_id": "detroit-ocp",
            "source_kind": "issuer_primary", "rights_basis": "public_access",
            "approved_by": "test-governance", "permit_id": "permit-1",
            "max_bytes": 4096,
            "approved_at": (self.now - timedelta(minutes=2)).isoformat(),
            "expires_at": (self.now + timedelta(minutes=10)).isoformat(),
        }
        base.update(changes)
        signed = json.dumps(base, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False).encode()
        return {
            "target": base,
            "signature": hmac.new(KEY.encode(), signed, hashlib.sha256).hexdigest(),
        }

    def approved(self):
        return {
            "id": 23, "status": "approved", "action": "call_approved_api",
            "approval_class": "policy_gated",
            "estimated_cost_cents": 0,
            "expires_at": (self.now + timedelta(minutes=20)).isoformat(),
        }

    def fake_transport(self, response=None):
        response = response or MockResponse()
        connection = MockConnection(response)
        self.pinned = patch(
            "company_os.approved_source_fetch._resolve_pinned_endpoint",
            return_value=(socket.AF_INET, ("93.184.216.34", 443), "93.184.216.34"),
        )
        self.connection = patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
            return_value=connection,
        )
        self.pinned.start()
        self.connection.start()
        self.addCleanup(self.connection.stop)
        self.addCleanup(self.pinned.stop)
        return connection

    def capture(self, **changes):
        params = {
            "ledger": self.ledger, "permit": self.permit(),
            "approval": self.approved(), "document_id": "detroit-demo",
            "evidence_excerpt": "Detroit certificate is required for the janitorial service.",
            "repo_root": self.root,
        }
        params.update(changes)
        return fetch_and_capture(**params)

    def test_signed_permit_valid_when_exact_and_current(self):
        checked = inspect_source_permit(self.permit())
        self.assertEqual(checked["target_url"], URL)
        self.assertEqual(checked["max_bytes"], 4096)

    def test_policy_key_absent_fails_closed(self):
        del os.environ["KO_SOURCE_ACCESS_POLICY_KEY"]
        with self.assertRaises(EvidenceError):
            inspect_source_permit(self.permit())

    def test_bad_key_length_fails_closed(self):
        os.environ["KO_SOURCE_ACCESS_POLICY_KEY"] = "short"
        with self.assertRaises(EvidenceError):
            inspect_source_permit(self.permit())

    def test_tampered_url_cannot_borrow_authorization(self):
        p = self.permit()
        p["target"]["target_url"] = "https://another.example/secret"
        with self.assertRaises(EvidenceError):
            inspect_source_permit(p)

    def test_tampered_bytes_budget_rejected(self):
        p = self.permit()
        p["target"]["max_bytes"] = 10_000_000
        with self.assertRaises(EvidenceError):
            inspect_source_permit(p)

    def test_forged_signature_is_rejected(self):
        p = self.permit()
        p["signature"] = "0" * 64
        with self.assertRaises(EvidenceError):
            inspect_source_permit(p)

    def test_missing_or_extra_signed_fields_rejected(self):
        for action in ("missing", "extra"):
            p = self.permit()
            if action == "missing":
                p["target"].pop("permit_id")
            else:
                p["target"]["untrusted"] = "extra"
            with self.subTest(action=action), self.assertRaises(EvidenceError):
                inspect_source_permit(p)

    def test_noncanonical_url_cannot_be_approved(self):
        for url in (
            "http://detroitmi.gov/eligibility",
            "https://DETROITMI.gov/public/eligibility",
            "https://detroitmi.gov.evil.com/public",
            "https://detroitmi.gov:8443/public",
            "https://127.0.0.1/x",
            "https://detroitmi.gov/public#frag",
            "https://detroitmi.gov/public?api_key=private",
        ):
            with self.subTest(url=url), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(target_url=url))

    def test_issuer_classification_and_legal_rights_must_be_explicit(self):
        for changes in (
            {"rights_basis": "unknown"},
            {"source_kind": "verified_by_ai"},
            {"publisher": ""},
            {"origin_id": ""},
            {"permit_id": ""},
            {"approved_by": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(**changes))

    def test_policy_maximum_body_limit_is_bounded(self):
        for n in (0, 19, 512001, -1, True, "512"):
            with self.subTest(n=n), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(max_bytes=n))

    def test_expired_policy_refused(self):
        p = self.permit(expires_at=(self.now-timedelta(seconds=1)).isoformat())
        with self.assertRaises(EvidenceError):
            inspect_source_permit(p)

    def test_seven_day_limit_and_future_policy_refused(self):
        for changes in (
            {"expires_at": (self.now + timedelta(days=10)).isoformat()},
            {"approved_at": (self.now + timedelta(days=1)).isoformat()},
            {"approved_at": "not a date"},
        ):
            with self.subTest(changes=changes), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(**changes))

    def test_missing_action_approval_blocks_before_dns(self):
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint") as resolver:
            with self.assertRaises(ApprovalRequired):
                self.capture(approval=None)
            resolver.assert_not_called()

    def test_emergency_pause_blocks_even_valid_authorizations(self):
        (self.root/"PAUSE_AUTONOMY").write_text("paused")
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint") as resolver:
            with self.assertRaises(PauseActive):
                self.capture()
            resolver.assert_not_called()

    def test_environment_pause_blocks_even_without_pause_file(self):
        os.environ["COMPANY_OS_PAUSED"] = "yes"
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint") as resolver:
            with self.assertRaises(PauseActive):
                self.capture()
            resolver.assert_not_called()

    def test_missing_source_permit_never_invokes_dns(self):
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint") as resolver:
            with self.assertRaises(EvidenceError):
                self.capture(permit={})
            resolver.assert_not_called()

    def test_dns_public_ipv4_is_pinned(self):
        with patch("company_os.approved_source_fetch.socket.getaddrinfo",
                   return_value=[(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",("93.184.216.34",443))]):
            family, sockaddr, ip = _resolve_pinned_endpoint("detroitmi.gov")
        self.assertEqual(family, socket.AF_INET)
        self.assertEqual(sockaddr, ("93.184.216.34",443))
        self.assertEqual(ip, "93.184.216.34")

    def test_dns_public_ipv6_is_pinned(self):
        address = "2606:4700:4700::1111"
        with patch("company_os.approved_source_fetch.socket.getaddrinfo",
                   return_value=[(socket.AF_INET6,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",
                                  (address,443,0,0))]):
            family, sockaddr, ip = _resolve_pinned_endpoint("detroitmi.gov")
        self.assertEqual(family, socket.AF_INET6)
        self.assertEqual(ip, address)

    def test_dns_mixed_safe_and_unsafe_is_rejected(self):
        answers = [
            (socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",("93.184.216.34",443)),
            (socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",("127.0.0.1",443)),
        ]
        with patch("company_os.approved_source_fetch.socket.getaddrinfo",return_value=answers):
            with self.assertRaises(EvidenceError):
                _resolve_pinned_endpoint("detroitmi.gov")

    def test_dns_restricted_addresses_are_all_blocked(self):
        for address in ("127.0.0.1","10.0.0.2","192.168.0.3","169.254.169.254",
                        "0.0.0.0","100.64.0.1","224.0.0.1","255.255.255.255"):
            with self.subTest(address=address), patch(
                "company_os.approved_source_fetch.socket.getaddrinfo",
                return_value=[(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",(address,443))],
            ):
                with self.assertRaises(EvidenceError):
                    _resolve_pinned_endpoint("detroitmi.gov")

    def test_dns_empty_and_too_many_fail_closed(self):
        for records in ([], [
            (socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",
             ("93.184.216.34",443))
            for _ in range(MAX_DNS_ANSWERS+1)
        ]):
            with patch("company_os.approved_source_fetch.socket.getaddrinfo",return_value=records):
                with self.assertRaises(EvidenceError):
                    _resolve_pinned_endpoint("detroitmi.gov")

    def test_dns_failure_is_nonfatal_to_program_but_blocks(self):
        with patch("company_os.approved_source_fetch.socket.getaddrinfo",
                   side_effect=OSError("dns connection")):
            with self.assertRaises(EvidenceError):
                _resolve_pinned_endpoint("detroitmi.gov")

    def test_socket_uses_numeric_pinned_address_and_correct_tls_hostname(self):
        with patch("company_os.approved_source_fetch.ssl.create_default_context") as ctx, patch(
            "company_os.approved_source_fetch.socket.socket"
        ) as sock:
            conn = _PinnedHTTPSConnection(
                "detroitmi.gov", socket.AF_INET, ("93.184.216.34",443),
            )
            conn.connect()
            sock.assert_called_once_with(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP)
            sock.return_value.connect.assert_called_once_with(("93.184.216.34",443))
            ctx.return_value.wrap_socket.assert_called_once_with(
                sock.return_value, server_hostname="detroitmi.gov",
            )
            self.assertTrue(ctx.return_value.check_hostname)
            self.assertEqual(ctx.return_value.verify_mode,ssl.CERT_REQUIRED)

    def test_socket_closes_if_tls_handshake_fails(self):
        with patch("company_os.approved_source_fetch.ssl.create_default_context") as ctx, patch(
            "company_os.approved_source_fetch.socket.socket"
        ) as sock:
            ctx.return_value.wrap_socket.side_effect = ssl.SSLError("cert mismatch")
            conn = _PinnedHTTPSConnection(
                "detroitmi.gov", socket.AF_INET, ("93.184.216.34",443),
            )
            with self.assertRaises(ssl.SSLError):
                conn.connect()
            sock.return_value.close.assert_called_once()

    def test_success_is_captured_but_never_independently_verified(self):
        connection = self.fake_transport()
        result = self.capture()
        self.assertIsInstance(result,CaptureReceipt)
        self.assertEqual(result.review_status,"HOLD_INDEPENDENT_REVIEW")
        self.assertFalse(result.publication_authorized)
        self.assertEqual(result.source_url,URL)
        self.assertEqual(result.pinned_ip,"93.184.216.34")
        self.assertEqual(result.bytes_read,len(connection.response.body))
        method, path, headers = connection.request_args
        self.assertEqual((method,path),("GET","/public/eligibility"))
        self.assertEqual(headers["Host"],"detroitmi.gov")
        self.assertEqual(headers["Accept-Encoding"],"identity")
        self.assertTrue(connection.closed)
        report = self.ledger.assess()
        self.assertEqual(report["state"],"INTERNAL_ONLY_UNVERIFIED")
        self.assertEqual(report["total_snapshots"],1)
        self.assertFalse(report["publication_authorized"])
        raw_ledger = self.ledger.path.read_bytes()
        self.assertNotIn(connection.response.body,raw_ledger)

    def test_header_content_length_matches_hard_cap(self):
        body = b"A" * 100
        response = MockResponse(body=body, headers=[
            ("Content-Type","text/plain"),("Content-Length","99999"),
        ])
        conn = self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()
        self.assertTrue(conn.closed)
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_redirects_not_followed_even_to_same_host(self):
        for status in (301,302,303,307,308,404,500,204):
            response = MockResponse(status=status,headers=[
                ("Content-Type","text/plain"),("Location","https://detroitmi.gov/other")
            ])
            with self.subTest(status=status), patch(
                "company_os.approved_source_fetch._download_https",
                wraps=_download_https,
            ):
                # No remote connection: use mocked TLS connection each iteration.
                with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                           return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")), patch(
                    "company_os.approved_source_fetch._PinnedHTTPSConnection",
                    return_value=MockConnection(response),
                ):
                    with self.assertRaises(EvidenceError):
                        self.capture()
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_compressed_body_rejected(self):
        response = MockResponse(headers=[
            ("Content-Type","text/plain"),("Content-Encoding","gzip"),
        ])
        self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()

    def test_duplicate_content_encoding_rejected(self):
        response = MockResponse(headers=[
            ("Content-Type","text/plain"),
            ("Content-Encoding","identity"),("Content-Encoding","gzip"),
        ])
        self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()

    def test_transfer_encoding_conflicts_and_unknown_values_rejected(self):
        for headers in (
            [("Content-Type","text/plain"),("Transfer-Encoding","gzip")],
            [("Content-Type","text/plain"),("Transfer-Encoding","chunked"),
             ("Content-Length","77")],
            [("Content-Type","text/plain"),("Transfer-Encoding","chunked"),
             ("Transfer-Encoding","chunked")],
        ):
            with self.subTest(headers=headers), patch(
                "company_os.approved_source_fetch._resolve_pinned_endpoint",
                return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34"),
            ), patch("company_os.approved_source_fetch._PinnedHTTPSConnection",
                     return_value=MockConnection(MockResponse(headers=headers))):
                with self.assertRaises(EvidenceError):
                    self.capture()

    def test_invalid_permit_metadata_is_refused(self):
        for update in (
            {"permit_id":"test;injected-header"},
            {"permit_id":"bad\\path"},
            {"publisher":"malformed\nPublisher"},
            {"approved_by":"bad\nUser"},
        ):
            with self.subTest(update=update), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(**update))

    def test_permit_is_revalidated_after_network_retrieval(self):
        self.fake_transport()
        permit = self.permit()
        with patch("company_os.approved_source_fetch.inspect_source_permit",
                   wraps=inspect_source_permit) as inspected:
            self.capture(permit=permit)
            self.assertEqual(inspected.call_count,2)

    def test_pdf_content_rejected_until_ce1c(self):
        response = MockResponse(body=b"%PDF-1.7" * 15,headers=[
            ("Content-Type","application/pdf"),
        ])
        self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()

    def test_charset_is_strict(self):
        for charset in ("iso-8859-1","utf-16","latin1"):
            response = MockResponse(headers=[("Content-Type",f"text/html; charset={charset}")])
            with self.subTest(charset=charset):
                with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                           return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")), patch(
                    "company_os.approved_source_fetch._PinnedHTTPSConnection",
                    return_value=MockConnection(response),
                ):
                    with self.assertRaises(EvidenceError):
                        self.capture()

    def test_duplicate_content_length_rejected(self):
        response = MockResponse(headers=[
            ("Content-Type","text/plain"),("Content-Length","77"),("Content-Length","78"),
        ])
        self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()

    def test_duplicate_content_type_rejected(self):
        response = MockResponse(headers=[
            ("Content-Type","text/html"),("Content-Type","text/plain"),
        ])
        self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()

    def test_body_cap_enforced_even_if_content_length_is_omitted(self):
        body=b"X"*4100
        response=MockResponse(body=body,headers=[("Content-Type","text/plain")])
        conn=self.fake_transport(response)
        with self.assertRaises(EvidenceError):
            self.capture()
        self.assertEqual(conn.response.last_read,4097)
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_invalid_utf8_and_binary_rejected(self):
        for body in (b"\xff"*100, b"\x00"*100, b"<html>broken"):
            response=MockResponse(body=body,headers=[("Content-Type","text/html")])
            with self.subTest(body=body[:5]), patch(
                "company_os.approved_source_fetch._resolve_pinned_endpoint",
                return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34"),
            ), patch("company_os.approved_source_fetch._PinnedHTTPSConnection",
                     return_value=MockConnection(response)):
                with self.assertRaises(EvidenceError):
                    self.capture()

    def test_tls_certificate_required(self):
        connection=MockConnection(MockResponse())
        connection.sock.getpeercert.return_value=None
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")),patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
            return_value=connection,
        ):
            with self.assertRaises(EvidenceError):
                self.capture()
        self.assertTrue(connection.closed)

    def test_tls_weak_version_refused(self):
        connection=MockConnection(MockResponse())
        connection.sock.version.return_value="TLSv1.1"
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")),patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
            return_value=connection,
        ):
            with self.assertRaises(EvidenceError):
                self.capture()
        self.assertTrue(connection.closed)

    def test_connection_exception_cannot_write_partial_ledger(self):
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")),patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
        ) as factory:
            factory.return_value.request.side_effect=OSError("connect timeout")
            with self.assertRaises(EvidenceError):
                self.capture()
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_quote_absent_blocks_fetched_document(self):
        self.fake_transport()
        with self.assertRaises(EvidenceError):
            self.capture(evidence_excerpt="This statement was not in the captured document.")
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_policy_exact_url_cannot_be_swapped_by_caller(self):
        p=self.permit()
        p["target"]["target_url"]="https://evil.example/x"
        self.fake_transport()
        with self.assertRaises(EvidenceError):
            self.capture(permit=p)
        self.assertEqual(self.ledger.audit()["events"],0)

    def test_source_classification_remains_attributed_not_true(self):
        self.fake_transport()
        self.capture()
        state=self.ledger.assess()
        self.assertEqual(state["state"],"INTERNAL_ONLY_UNVERIFIED")

    def test_raw_body_never_dumps_to_public_files(self):
        connection=self.fake_transport()
        self.capture()
        content=self.ledger.path.read_bytes()
        self.assertNotIn(connection.response.body,content)

    def test_no_redirect_target_resolution_is_ever_invoked(self):
        response=MockResponse(status=302,headers=[
            ("Content-Type","text/plain"),("Location","https://evil.example/private"),
        ])
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(socket.AF_INET,("93.184.216.34",443),"93.184.216.34")) as resolver,patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
            return_value=MockConnection(response),
        ):
            with self.assertRaises(EvidenceError):
                self.capture()
            resolver.assert_called_once_with("detroitmi.gov")


if __name__=="__main__":
    unittest.main()
