"""Adversarial CE-1C2 receipt-to-PDF package integration tests.

The signer is EPHEMERAL and TEST-ONLY. No real issuer, transport, independent
reviewer, or production service is exercised by this test module.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from company_os.procurement_package import assess_package
from company_os.signed_capture_receipts import inspect_signed_capture_bundle
from company_os.source_provenance import EvidenceError
from test_procurement_package import ProcurementPackagePreflightTests


class SignedCaptureReceiptsTests(unittest.TestCase):
    def setUp(self):
        # Reuse actual *parsed* synthetic PDF fixture, without inheriting or
        # duplicating its 53 existing test methods.
        self.fixture = ProcurementPackagePreflightTests(
            "test_full_synthetic_pdf_package_remains_on_independent_review_hold"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.folder = self.fixture.folder
        self.manifest = self.fixture.manifest
        self.now = self.fixture.now
        self.private = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            self.private.public_key().public_bytes_raw()
        ).decode("ascii")
        self.env = patch.dict(os.environ, {
            "KO_CAPTURE_RECEIPT_PUBLIC_KEY_B64": public,
            "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.listing_file = self.folder / "issuer-listing.html"
        self.listing_html = (
            "<html><body><h1>Example procurement package</h1>\n" +
            "\n".join(
                '<a href="' + d["source_url"] + '">' + d["id"] + " PDF attachment</a>"
                for d in self.manifest["documents"]
            ) + "</body></html>"
        )
        self.listing_file.write_text(self.listing_html, encoding="utf-8")
        self.listing_payload = {
            "schema_version": "1.0",
            "record_kind": "issuer_listing_capture",
            "capture_id": "listing-capture-001",
            "package_id": self.manifest["package_id"],
            "listing_url": self.manifest["issuer_url"],
            "listing_filename": "issuer-listing.html",
            "listing_sha256": hashlib.sha256(self.listing_file.read_bytes()).hexdigest(),
            "listing_observed_at": self.now.isoformat(),
            "listing_reference": self.manifest["discovery"]["issuer_listing_reference"],
            "listed_items": [
                {k: d[k] for k in ("source_url", "kind", "sequence")}
                | {"document_id": d["id"]}
                for d in self.manifest["documents"]
            ],
            "capture_actor": "synthetic-protected-capture",
            "capture_method": "approved_tls_fetch",
        }
        self.documents_payload = [
            {
                "schema_version": "1.0",
                "record_kind": "pdf_document_capture",
                "capture_id": "capture-" + d["id"],
                "package_id": self.manifest["package_id"],
                "document_id": d["id"],
                "source_url": d["source_url"],
                "sha256": d["sha256"],
                "bytes_received": (self.folder / d["filename"]).stat().st_size,
                "media_type": "application/pdf",
                "observed_at": d["observed_at"],
                "capture_actor": "synthetic-protected-capture",
                "capture_method": "approved_tls_fetch",
                "permit_id": "approved-permit-" + d["id"],
                "tls_certificate_sha256": "a" * 64,
                "pinned_ip": "93.184.216.34",
            }
            for d in self.manifest["documents"]
        ]

    def sign(self, payload):
        signed = json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        return {
            "payload": deepcopy(payload),
            "signature": base64.b64encode(self.private.sign(signed)).decode("ascii"),
        }

    def write(self):
        self.fixture.save()
        data = {
            "schema_version": "1.0",
            "listing": self.sign(self.listing_payload),
            "documents": [self.sign(p) for p in self.documents_payload],
        }
        (self.folder / "capture_receipts.json").write_text(
            json.dumps(data, separators=(",", ":")), encoding="utf-8",
        )
        return data

    def verdict(self, *, strict=True):
        self.fixture.save()
        return assess_package(
            self.folder, now=self.now, require_capture_receipts=strict
        )

    def blocked(self, fragment, *, strict=True):
        self.write()
        v = self.verdict(strict=strict)
        self.assertEqual(v["status"], "BLOCK", v)
        self.assertFalse(v["publication_authorized"])
        self.assertIn(fragment.lower(), " ".join(v["errors"]).lower())
        return v

    def test_every_signed_original_matches_but_still_no_release(self):
        self.write()
        result = self.verdict()
        self.assertEqual(result["status"], "HOLD_INDEPENDENT_ISSUER_AND_CLIENT_REVIEW", result)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(
            result["capture_evidence"]["state"],
            "SIGNED_CAPTURE_METADATA_MATCHED_REVIEW_REQUIRED",
        )
        self.assertEqual(result["capture_evidence"]["document_receipts_matched"], 3)
        self.assertFalse(result["capture_evidence"]["publication_authorized"])

    def test_offline_legacy_package_is_held_not_upgraded(self):
        v = self.verdict(strict=False)
        self.assertTrue(v["status"].startswith("HOLD"), v)
        self.assertEqual(v["capture_evidence"]["state"], "MISSING_SIGNED_ORIGINAL_CAPTURE")
        self.assertFalse(v["publication_authorized"])

    def test_strict_mode_blocks_missing_receipts(self):
        self.fixture.save()
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("missing", str(v["errors"]))

    def test_strict_mode_rejects_unknown_signer_public_key(self):
        self.write()
        key2 = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        os.environ["KO_CAPTURE_RECEIPT_PUBLIC_KEY_B64"] = base64.b64encode(
            key2
        ).decode("ascii")
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("capture signature", str(v["errors"]))

    def test_no_public_key_is_fail_closed(self):
        self.write()
        del os.environ["KO_CAPTURE_RECEIPT_PUBLIC_KEY_B64"]
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("public key", str(v["errors"]))

    def test_no_host_registry_is_fail_closed(self):
        self.write()
        del os.environ["KO_SOURCE_APPROVED_HOSTS"]
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("registry", str(v["errors"]))

    def test_tampered_signer_payload_rejected(self):
        data = self.write()
        data["documents"][0]["payload"]["sha256"] = "f" * 64
        (self.folder / "capture_receipts.json").write_text(json.dumps(data))
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("signature", str(v["errors"]))

    def test_tampered_bundle_blocks_even_nonstrict_legacy_mode(self):
        self.write()
        path = self.folder / "capture_receipts.json"
        path.write_text('{"invalid": "sidecar"}')
        v = self.verdict(strict=False)
        self.assertEqual(v["status"], "BLOCK")

    def test_signed_pdf_hash_not_matching_local_manifest_rejected(self):
        self.documents_payload[0]["sha256"] = "f" * 64
        self.blocked("hash differs")

    def test_signed_file_size_mismatch_rejected(self):
        self.documents_payload[1]["bytes_received"] += 1
        self.blocked("size differs")

    def test_signed_document_wrong_source_url_rejected(self):
        self.documents_payload[0]["source_url"] = "https://issuer.example/replacement.pdf"
        self.blocked("URL not bound")

    def test_signed_receipt_from_wrong_package_rejected(self):
        self.documents_payload[1]["package_id"] = "wrong-package"
        self.blocked("wrong package")

    def test_listing_from_wrong_package_rejected(self):
        self.listing_payload["package_id"] = "wrong-package"
        self.blocked("wrong package")

    def test_listing_hash_mismatch_rejected(self):
        self.listing_payload["listing_sha256"] = "b" * 64
        self.blocked("listing hash mismatch")

    def test_unlisted_extra_pdf_link_in_original_listing_rejected(self):
        self.listing_html = self.listing_html.replace(
            "</body>", '<a href="/unlisted-addendum-2.pdf">Extra amendment</a></body>',
        )
        self.listing_file.write_text(self.listing_html, encoding="utf-8")
        self.listing_payload["listing_sha256"] = hashlib.sha256(
            self.listing_file.read_bytes()
        ).hexdigest()
        self.blocked("PDF links differ")

    def test_missing_pdf_link_in_original_listing_rejected(self):
        self.listing_html = self.listing_html.replace(
            '<a href="https://issuer.example/addendum-1.pdf">addendum-1 PDF attachment</a>',
            "",
        )
        self.listing_file.write_text(self.listing_html, encoding="utf-8")
        self.listing_payload["listing_sha256"] = hashlib.sha256(
            self.listing_file.read_bytes()
        ).hexdigest()
        self.blocked("PDF links differ")

    def test_signed_listing_omits_one_manifest_document_rejected(self):
        self.listing_payload["listed_items"].pop()
        self.blocked("inventory differ")

    def test_duplicate_listing_document_rejected(self):
        self.listing_payload["listed_items"].append(deepcopy(self.listing_payload["listed_items"][0]))
        self.blocked("duplicate captured listing")

    def test_signed_addendum_role_drift_rejected(self):
        self.listing_payload["listed_items"][1]["kind"] = "attachment"
        self.listing_payload["listed_items"][1]["sequence"] = None
        self.blocked("differs from package document")

    def test_unsupported_source_host_rejected(self):
        self.documents_payload[0]["source_url"] = "https://untrusted.example/a.pdf"
        self.blocked("URL not bound")

    def test_future_dated_listing_rejected(self):
        self.listing_payload["listing_observed_at"] = (
            self.now + timedelta(hours=1)
        ).isoformat()
        self.blocked("stale or future")

    def test_stale_listing_rejected(self):
        old = (self.now - timedelta(days=2)).isoformat()
        self.listing_payload["listing_observed_at"] = old
        self.blocked("stale")

    def test_document_capture_time_mismatch_rejected(self):
        self.documents_payload[0]["observed_at"] = (
            self.now - timedelta(hours=3)
        ).isoformat()
        self.blocked("inconsistent with issuer listing")

    def test_manifest_document_time_rollback_rejected(self):
        self.documents_payload[0]["observed_at"] = (
            self.now - timedelta(minutes=3)
        ).isoformat()
        self.blocked("timestamp differs")

    def test_duplicate_capture_id_rejected(self):
        self.documents_payload[1]["capture_id"] = self.documents_payload[0]["capture_id"]
        self.blocked("duplicate document capture")

    def test_missing_document_receipt_rejected(self):
        self.documents_payload.pop()
        self.blocked("missing or extra")

    def test_invalid_issuer_listing_filename_rejected(self):
        self.listing_payload["listing_filename"] = "../../outside.html"
        self.blocked("listing filename")

    def test_symlink_issuer_listing_rejected(self):
        other = self.folder.parent / (self.folder.name + "-listing.html")
        other.write_text(self.listing_html)
        self.addCleanup(lambda: other.unlink(missing_ok=True))
        self.listing_file.unlink()
        self.listing_file.symlink_to(other)
        self.blocked("absent or unsafe")

    def test_malicious_private_ip_receipt_rejected(self):
        self.documents_payload[0]["pinned_ip"] = "169.254.169.254"
        self.blocked("not public")

    def test_wrong_pdf_media_type_rejected(self):
        self.documents_payload[0]["media_type"] = "text/html"
        self.blocked("not authorized")

    def test_unsupported_capture_method_rejected(self):
        self.documents_payload[0]["capture_method"] = "manual_unverified"
        self.blocked("not authorized")

    def test_duplicate_json_keys_rejected(self):
        self.write()
        path = self.folder / "capture_receipts.json"
        path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
        v = self.verdict()
        self.assertEqual(v["status"], "BLOCK")
        self.assertIn("invalid capture", str(v["errors"]))

    def test_receipt_sidecar_has_no_private_key_or_auto_signing_function(self):
        self.write()
        serialized = (self.folder / "capture_receipts.json").read_text()
        self.assertNotIn("private_key", serialized.lower())
        self.assertNotIn("secret", serialized.lower())
        self.assertFalse(hasattr(inspect_signed_capture_bundle, "sign"))

    def test_relative_pdf_links_are_normalized_and_checked(self):
        self.listing_html = (
            "<html><body><h1>Listing with relative PDF references</h1>" +
            "".join(
                '<a href="/' + d["id"] + '.pdf">' + d["id"] + ' PDF file</a>'
                for d in self.manifest["documents"]
            ) + "</body></html>"
        )
        self.listing_file.write_text(self.listing_html, encoding="utf-8")
        self.listing_payload["listing_sha256"] = hashlib.sha256(
            self.listing_file.read_bytes()
        ).hexdigest()
        self.write()
        v = self.verdict()
        self.assertTrue(v["status"].startswith("HOLD"), v)


if __name__ == "__main__":
    unittest.main()
