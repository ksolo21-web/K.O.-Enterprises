"""CE-1C3a safety tests: real generated PDFs, mocked HTTPS, zero live requests."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.approved_pdf_capture import stage_issuer_listing, stage_pdf
from company_os.approved_source_fetch import _download_https, inspect_source_permit
from company_os.policy import ApprovalRequired, PauseActive
from company_os.source_provenance import EvidenceError
import test_procurement_package as pdf_fixture
import test_approved_source_fetch as tls_fixture

HOST = "issuer.example"
BASE = "https://issuer.example/"
DOCUMENT = BASE + "solicitation.pdf"
LISTING = BASE + "solicitations"
PDF_TEXT = "Solicitation opens through 2026-11-27T18:00:00+00:00; referenced official source file."


class ApprovedPdfCaptureTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.signer = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            self.signer.public_key().public_bytes_raw()
        ).decode("ascii")
        self.env = patch.dict(os.environ, {
            "KO_SOURCE_PERMIT_PUBLIC_KEY_B64": public,
            "KO_SOURCE_APPROVED_HOSTS": HOST,
            "COMPANY_OS_PAUSED": "0",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.pdf = pdf_fixture.make_pdf(PDF_TEXT)
        self.listing = (
            b"<html><body><h1>Original issuer listing</h1>"
            b"<a href='/solicitation.pdf'>Original tender PDF</a></body></html>"
        )

    def permit(self, *, kind="pdf", **changes):
        pdf = kind == "pdf"
        payload = {
            "schema_version": "3.0" if pdf else "2.0",
            "target_url": DOCUMENT if pdf else LISTING,
            "publisher": "Synthetic issuer", "title": "Synthetic procurement document",
            "origin_id": "issuer-test", "source_kind": "issuer_primary",
            "rights_basis": "public_access", "approved_by": "test-governance",
            "permit_id": "pdf-permit-001" if pdf else "html-permit-001",
            "max_bytes": len(self.pdf) + 1024 if pdf else 4096,
            "approved_at": (self.now-timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now+timedelta(minutes=20)).isoformat(),
        }
        if pdf:
            payload["media_type"] = "application/pdf"
        payload.update(changes)
        signed = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False).encode("utf-8")
        return {
            "target": payload,
            "signature": base64.b64encode(self.signer.sign(signed)).decode(),
        }

    def approval(self):
        return {
            "id": 58, "status": "approved", "action": "call_approved_api",
            "approval_class": "policy_gated", "estimated_cost_cents": 0,
            "expires_at": (self.now+timedelta(minutes=20)).isoformat(),
        }

    def stage(self, *, kind="pdf", permit=None, approval=None, package_id="test-package",
              document_id="solicitation"):
        if kind == "pdf":
            return stage_pdf(
                repo_root=self.root, package_id=package_id,
                document_id=document_id,
                permit=permit if permit is not None else self.permit(),
                approval=approval if approval is not None else self.approval(),
            )
        return stage_issuer_listing(
            repo_root=self.root, package_id=package_id,
            permit=permit if permit is not None else self.permit(kind="listing"),
            approval=approval if approval is not None else self.approval(),
        )

    def transport(self, *, kind="pdf", raw=None, mime=None):
        if raw is None:
            raw = self.pdf if kind == "pdf" else self.listing
        if mime is None:
            mime = "application/pdf" if kind == "pdf" else "text/html"
        mocked = patch("company_os.approved_pdf_capture._download_https",
                       return_value=(raw, mime, "93.184.216.34", "a"*64, "TLSv1.3"))
        self.addCleanup(mocked.stop)
        return mocked.start()

    def test_scoped_signed_pdf_permit_is_valid(self):
        checked = inspect_source_permit(self.permit())
        self.assertEqual(checked["schema_version"], "3.0")
        self.assertEqual(checked["media_type"], "application/pdf")

    def test_v2_text_permit_does_not_expand_into_pdf_access(self):
        self.transport()
        with self.assertRaises(EvidenceError) as ctx:
            self.stage(permit=self.permit(kind="listing"))
        self.assertIn("PDF requires", str(ctx.exception))

    def test_v3_pdf_permit_does_not_expand_into_text_capture(self):
        self.transport(kind="listing")
        with self.assertRaises(EvidenceError):
            self.stage(kind="listing", permit=self.permit())

    def test_pdf_permit_denies_other_media_type(self):
        for mime in ("image/png", "text/html", "application/octet-stream"):
            with self.subTest(mime=mime):
                with self.assertRaises(EvidenceError):
                    inspect_source_permit(self.permit(media_type=mime))

    def test_v3_permit_cannot_exceed_pdf_size_policy(self):
        for size in (0, 20, True, 4*1024*1024+1, "1000"):
            with self.subTest(size=size), self.assertRaises(EvidenceError):
                inspect_source_permit(self.permit(max_bytes=size))

    def test_old_v2_text_limit_remains_intact(self):
        with self.assertRaises(EvidenceError):
            inspect_source_permit(self.permit(kind="listing", max_bytes=4*1024*1024))

    def test_v2_cannot_smuggle_media_type_field(self):
        with self.assertRaises(EvidenceError):
            inspect_source_permit(self.permit(kind="listing", media_type="application/pdf"))

    def test_unapproved_download_denied_before_network(self):
        with patch("company_os.approved_pdf_capture._download_https") as network:
            with self.assertRaises(ApprovalRequired):
                self.stage(approval={"id":9, "status":"pending"})
            network.assert_not_called()

    def test_paused_repository_denied_before_network_and_disk(self):
        (self.root / "PAUSE_AUTONOMY").write_text("paused")
        with patch("company_os.approved_pdf_capture._download_https") as network:
            with self.assertRaises(PauseActive):
                self.stage()
            network.assert_not_called()
        self.assertFalse((self.root/"state").exists())

    def test_environment_pause_denied_before_network(self):
        os.environ["COMPANY_OS_PAUSED"] = "1"
        with patch("company_os.approved_pdf_capture._download_https") as network:
            with self.assertRaises(PauseActive):
                self.stage()
            network.assert_not_called()

    def test_pdf_staged_only_to_private_ignored_state_without_signing(self):
        mock = self.transport()
        staged = self.stage()
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"/"solicitation.pdf"
        self.assertEqual(path.read_bytes(), self.pdf)
        self.assertEqual(staged.sha256, hashlib.sha256(self.pdf).hexdigest())
        self.assertEqual(staged.source_url, DOCUMENT)
        self.assertEqual(staged.reviewed_pdf_pages, 1)
        self.assertFalse(staged.original_issuer_authenticated)
        self.assertFalse(staged.capture_receipt_signed)
        self.assertFalse(staged.publication_authorized)
        self.assertEqual(staged.state, "UNSIGNED_CAPTURE_REQUIRES_SEPARATE_ATTESTATION")
        mock.assert_called_once_with(
            DOCUMENT, len(self.pdf)+1024, expected_media="application/pdf",
        )
        self.assertFalse((path.parent/"capture_receipts.json").exists())
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_html_issuer_listing_staged_and_links_checked(self):
        mock = self.transport(kind="listing")
        staged = self.stage(kind="listing")
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"/"issuer-listing.html"
        self.assertEqual(path.read_bytes(), self.listing)
        self.assertEqual(staged.media_type, "text/html")
        self.assertIsNone(staged.reviewed_pdf_pages)
        self.assertFalse(staged.capture_receipt_signed)
        mock.assert_called_once_with(LISTING, 4096, expected_media="text")

    def test_no_supported_pdf_links_rejected(self):
        self.transport(kind="listing", raw=b"<html><body>This listing has no documents to inspect.</body></html>")
        with self.assertRaises(EvidenceError):
            self.stage(kind="listing")
        self.assertFalse((self.root/"state").exists())

    def test_rogue_offsite_pdf_anchor_rejected(self):
        raw=(b"<html><body><a href='https://evil.example/other.pdf'>"
             b"External PDF source</a></body></html>")
        self.transport(kind="listing", raw=raw)
        with self.assertRaises(EvidenceError):
            self.stage(kind="listing")
        self.assertFalse((self.root/"state").exists())

    def test_unreadable_or_scanned_pdf_rejected_before_storage(self):
        invalid_pdf = pdf_fixture.make_pdf("Blank unrecognized image", scanned=True)
        self.transport(raw=invalid_pdf)
        with self.assertRaises(EvidenceError):
            self.stage()
        self.assertFalse((self.root/"state").exists())

    def test_transport_rejects_unexpected_html_for_pdf(self):
        self.transport(raw=self.listing, mime="text/html")
        with self.assertRaises(EvidenceError):
            self.stage()
        self.assertFalse((self.root/"state").exists())

    def test_cross_domain_permit_tampering_is_rejected(self):
        forged = self.permit()
        forged["target"]["target_url"] = "https://evil.example/document.pdf"
        with patch("company_os.approved_pdf_capture._download_https") as net:
            with self.assertRaises(EvidenceError):
                self.stage(permit=forged)
            net.assert_not_called()

    def test_identical_file_replay_is_not_silently_overwritten(self):
        self.transport()
        first = self.stage()
        with self.assertRaises(EvidenceError) as ctx:
            self.stage()
        self.assertIn("already staged", str(ctx.exception))
        path = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"/"solicitation.pdf"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), first.sha256)

    def test_different_package_uses_separate_private_directory(self):
        self.transport()
        p1 = self.stage(package_id="first-package")
        p2 = self.stage(package_id="second-package")
        self.assertEqual(p1.sha256, p2.sha256)
        self.assertTrue((self.root/"state"/"competitive_engine"/"capture_staging"/"first-package"/"solicitation.pdf").exists())
        self.assertTrue((self.root/"state"/"competitive_engine"/"capture_staging"/"second-package"/"solicitation.pdf").exists())

    def test_invalid_document_id_does_not_create_disk_artifact(self):
        with patch("company_os.approved_pdf_capture._download_https") as network:
            with self.assertRaises(EvidenceError):
                self.stage(document_id="../../secret")
            network.assert_not_called()
        self.assertFalse((self.root/"state").exists())

    def test_symlink_private_storage_blocked(self):
        (self.root/"state").symlink_to(self.root.parent, target_is_directory=True)
        self.transport()
        with self.assertRaises(EvidenceError):
            self.stage()

    def test_private_pdf_file_symlink_cannot_be_overwritten(self):
        folder = self.root/"state"/"competitive_engine"/"capture_staging"/"test-package"
        folder.mkdir(parents=True)
        target = self.root/"secret-sentinel.pdf"
        target.write_bytes(b"unchanged-secret")
        (folder/"solicitation.pdf").symlink_to(target)
        self.transport()
        with self.assertRaises(EvidenceError):
            self.stage()
        self.assertEqual(target.read_bytes(), b"unchanged-secret")

    def test_post_retrieval_pause_prevents_persisting_bytes(self):
        def fetched(*args, **kwargs):
            (self.root/"PAUSE_AUTONOMY").write_text("paused")
            return (self.pdf, "application/pdf", "93.184.216.34", "a"*64, "TLSv1.3")
        with patch("company_os.approved_pdf_capture._download_https",side_effect=fetched):
            with self.assertRaises(PauseActive):
                self.stage()
        self.assertFalse((self.root/"state").exists())

    def test_post_retrieval_expired_permit_prevents_persisting(self):
        with patch("company_os.approved_pdf_capture.inspect_source_permit",
                   wraps=inspect_source_permit) as permitted:
            permit = self.permit()
            self.transport()
            with patch("company_os.approved_pdf_capture.inspect_source_permit",
                       side_effect=[inspect_source_permit(permit),
                                    EvidenceError("source permit expired")]):
                with self.assertRaises(EvidenceError):
                    self.stage(permit=permit)
        self.assertFalse((self.root/"state").exists())

    def test_host_tampering_pdf_response_denied(self):
        from unittest.mock import MagicMock
        response = tls_fixture.MockResponse(body=self.pdf,headers=[
            ("Content-Type","text/html"), ("Content-Length",str(len(self.pdf))),
        ])
        conn=tls_fixture.MockConnection(response)
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(2,("93.184.216.34",443),"93.184.216.34")),patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",
            return_value=conn,
        ):
            with self.assertRaises(EvidenceError):
                _download_https(DOCUMENT,len(self.pdf)+1024,expected_media="application/pdf")
        self.assertTrue(conn.closed)

    def test_pdf_redirect_and_oversize_refused_in_shared_transport(self):
        for response in (
            tls_fixture.MockResponse(
                body=self.pdf,status=302,headers=[("Location",DOCUMENT)]
            ),
            tls_fixture.MockResponse(
                body=self.pdf,headers=[
                    ("Content-Type","application/pdf"),
                    ("Content-Length",str(len(self.pdf)+5000)),
                ],
            ),
        ):
            conn=tls_fixture.MockConnection(response)
            with self.subTest(response_status=response.status),patch(
                "company_os.approved_source_fetch._resolve_pinned_endpoint",
                return_value=(2,("93.184.216.34",443),"93.184.216.34")),patch(
                "company_os.approved_source_fetch._PinnedHTTPSConnection",return_value=conn,
            ):
                with self.assertRaises(EvidenceError):
                    _download_https(DOCUMENT,len(self.pdf)+1024,expected_media="application/pdf")
            self.assertTrue(conn.closed)

    def test_unsupported_mime_or_charset_pdf_refused_in_transport(self):
        for content_type in (
            "application/pdf; charset=utf-8",
            "application/octet-stream", "text/html",
        ):
            resp=tls_fixture.MockResponse(body=self.pdf,headers=[("Content-Type",content_type)])
            c=tls_fixture.MockConnection(resp)
            with self.subTest(content_type=content_type),patch(
                "company_os.approved_source_fetch._resolve_pinned_endpoint",
                return_value=(2,("93.184.216.34",443),"93.184.216.34")),patch(
                "company_os.approved_source_fetch._PinnedHTTPSConnection",return_value=c,
            ):
                with self.assertRaises(EvidenceError):
                    _download_https(DOCUMENT,len(self.pdf)+1024,expected_media="application/pdf")

    def test_pdf_declared_size_cap_and_magic_header(self):
        resp=tls_fixture.MockResponse(body=b"not a pdf"*20,headers=[("Content-Type","application/pdf")])
        c=tls_fixture.MockConnection(resp)
        with patch("company_os.approved_source_fetch._resolve_pinned_endpoint",
                   return_value=(2,("93.184.216.34",443),"93.184.216.34")),patch(
            "company_os.approved_source_fetch._PinnedHTTPSConnection",return_value=c,
        ):
            with self.assertRaises(EvidenceError):
                _download_https(DOCUMENT,4096,expected_media="application/pdf")

    def test_no_release_permission_through_stage_metadata(self):
        self.transport()
        m=self.stage().unsigned_metadata()
        self.assertFalse(m["capture_receipt_signed"])
        self.assertFalse(m["original_issuer_authenticated"])
        self.assertFalse(m["independent_critic_approved"])
        self.assertFalse(m["publication_authorized"])
        self.assertNotIn("signature",m)
        self.assertNotIn("private_key",m)


if __name__=="__main__":
    unittest.main()
