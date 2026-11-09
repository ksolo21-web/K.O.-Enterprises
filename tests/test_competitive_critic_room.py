"""CE-1N sealed source-PDF visual critic room tests (fictional local evidence).

The suite verifies source/page integrity and immutable packet mechanics, not
that a real separate qualified reviewer has inspected a real issuer PDF.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import unittest
from pathlib import Path

from company_os.competitive_critic_room import (
    _manifest, inspect_sealed_critic_room, stage_critic_room,
)
from company_os.pdf_page_render import render_pdf_page
from company_os.source_provenance import EvidenceError
import test_competitive_pdf_source_handoff as original_fixture


class SealedCriticRoomTests(unittest.TestCase):
    def setUp(self):
        self.fixture = original_fixture.IssuerPdfHandoffTests(
            "test_signed_pdf_handoff_returns_hold_and_all_package_page_tasks"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.handoff = self.fixture.handoff()
        self.root = self.fixture.fx.root
        self.parent = self.root / "private-critic-rooms"
        self.parent.mkdir(mode=0o700)
        self.images = {}
        for item in self.handoff["critic_worklist"]["all_issuer_pdf_pages"]:
            document = item["document_id"]
            n = item["page_number"]
            source = (
                self.root / "state" / "competitive_engine" / "capture_staging"
                / "pkg-one" / (document + ".pdf")
            )
            self.images[f"{document}-page-{n:03d}.png"] = render_pdf_page(
                source.read_bytes(), n,
            )
        self.counter = 0

    def stage(self, *, room=None, images=None, parent=None, dossier=None,
              staged_policy=None):
        self.counter += 1
        return stage_critic_room(
            self.root, self.parent if parent is None else parent,
            room or ("review-room-" + str(self.counter)),
            self.fixture.d if dossier is None else dossier,
            self.fixture.fx.issuer, "pkg-one", self.fixture.mapping,
            self.images if images is None else images,
            staging_policy_envelope=(self.fixture.fx.envelope()
                                     if staged_policy is None else staged_policy),
            staging_trust_ledger=self.fixture.fx.trust,
            now=self.fixture.now,
        )

    def test_complete_actual_PDF_page_packet_stays_reviewer_pending(self):
        staged = self.stage()
        status = inspect_sealed_critic_room(
            staged["workroom"], expected_manifest_sha256=staged["manifest_sha256"],
        )
        self.assertEqual(status["state"], "READ_ONLY_SOURCE_PAGE_ROOM_HASHES_VERIFIED_REVIEW_PENDING")
        self.assertEqual(status["page_count"], 2)
        self.assertEqual(status["original_source_count"], 1)
        self.assertFalse(status["reviewer_visual_inspection_completed"])
        self.assertFalse(status["real_issuer_authenticated"])
        self.assertFalse(status["reviewer_independence_operationally_verified"])
        self.assertFalse(status["publication_authorized"])

    def test_review_room_contains_full_claim_dossier_and_all_attachment_pages(self):
        staged = self.stage()
        packet = json.loads((Path(staged["workroom"])/"manifest.json").read_text())
        self.assertEqual(packet["dossier"], self.fixture.d)
        self.assertEqual(len(packet["pages"]), 2)
        self.assertEqual(
            {p["document_id"] for p in packet["original_pdf_worklist"]["all_issuer_pdf_pages"]},
            {"attachment", "notice"},
        )
        self.assertEqual(
            packet["handoff_sha256"], self.handoff["handoff_sha256"],
        )
        self.assertFalse(packet["reviewer_visual_inspection_completed"])

    def test_room_and_png_are_sealed_against_writes(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        self.assertEqual(stat.S_IMODE(room.stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((room/"pages").stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((room/"manifest.json").stat().st_mode), 0o400)
        self.assertEqual(
            {stat.S_IMODE(p.stat().st_mode) for p in (room/"pages").iterdir()},
            {0o400},
        )

    def test_missing_original_page_png_blocks_before_packet_creation(self):
        images = dict(self.images)
        images.pop(next(iter(images)))
        with self.assertRaises(EvidenceError):
            self.stage(images=images)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_unexpected_extra_page_png_blocks_before_packet_creation(self):
        images = dict(self.images)
        images["fabricated-page-001.png"] = next(iter(images.values()))
        with self.assertRaises(EvidenceError):
            self.stage(images=images)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_wrong_actual_png_for_source_page_blocks(self):
        images = dict(self.images)
        first, second = list(images)
        images[first] = images[second]
        with self.assertRaises(EvidenceError):
            self.stage(images=images)

    def test_tampered_original_issuer_document_blocks_new_packet(self):
        path = self.root / "state/competitive_engine/capture_staging/pkg-one/notice.pdf"
        path.write_bytes(path.read_bytes() + b"additional-bytes-after-signed-capture")
        with self.assertRaises(EvidenceError):
            self.stage()

    def test_old_issuer_source_after_revoked_staging_receipt_blocks(self):
        self.fixture.fx.policy["revision"] = 2
        self.fixture.fx.policy["revoked_receipts"] = ["receipt-event-002"]
        new = self.fixture.fx.envelope()
        self.fixture.fx.trust.accept_policy(new, now=self.fixture.now)
        with self.assertRaises(EvidenceError):
            self.stage(staged_policy=new)

    def test_untrusted_public_parent_permissions_are_rejected(self):
        self.parent.chmod(0o755)
        with self.assertRaises(EvidenceError):
            self.stage()
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_parent_directory_symlink_is_rejected(self):
        another = self.root/"other-private-rooms"
        another.mkdir(mode=0o700)
        link = self.root/"linked-private-rooms"
        link.symlink_to(another, target_is_directory=True)
        with self.assertRaises(EvidenceError):
            self.stage(parent=link)

    def test_cannot_overwrite_existing_sealed_packet_identifier(self):
        self.stage(room="repeat-room")
        with self.assertRaises(EvidenceError):
            self.stage(room="repeat-room")

    def test_wrong_expected_external_manifest_digest_is_rejected(self):
        staged = self.stage()
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(staged["workroom"], expected_manifest_sha256="0"*64)

    def test_manifest_tampering_is_rejected_after_resealing(self):
        staged = self.stage()
        path = Path(staged["workroom"])/"manifest.json"
        path.chmod(0o600)
        old = path.read_bytes()
        path.write_bytes(old.replace(
            b'"publication_authorized":false', b'"publication_authorized":true',
        ))
        path.chmod(0o400)
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(
                staged["workroom"], expected_manifest_sha256=staged["manifest_sha256"],
            )

    def test_symlinked_manifest_is_rejected_before_read(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        manifest = room/"manifest.json"
        original = self.parent/"manifest-original"
        original.write_bytes(manifest.read_bytes())
        room.chmod(0o700)
        manifest.unlink()
        manifest.symlink_to(original)
        room.chmod(0o500)
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(
                room, expected_manifest_sha256=staged["manifest_sha256"],
            )

    def test_extra_injected_room_file_is_rejected(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        room.chmod(0o700)
        (room/"fake-review-approval.json").write_text('{"approved":true}')
        room.chmod(0o500)
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(
                room, expected_manifest_sha256=staged["manifest_sha256"],
            )

    def test_missing_page_after_sealing_is_rejected(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        pages = room/"pages"
        pages.chmod(0o700)
        next(iter(pages.iterdir())).unlink()
        pages.chmod(0o500)
        with self.assertRaises((EvidenceError, OSError)):
            inspect_sealed_critic_room(
                room, expected_manifest_sha256=staged["manifest_sha256"],
            )

    def test_group_writable_file_is_rejected(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        target = room/"manifest.json"
        target.chmod(0o660)
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(
                room, expected_manifest_sha256=staged["manifest_sha256"],
            )

    def test_manifest_path_traversal_cannot_read_other_private_file(self):
        staged = self.stage()
        room = Path(staged["workroom"])
        marker = self.parent/"private-signer-key"
        marker.write_text("test synthetic credential marker")
        manifest = room/"manifest.json"
        packet = json.loads(manifest.read_text())
        packet["pages"][0]["file"] = "../../private-signer-key"
        raw = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        manifest.chmod(0o600)
        manifest.write_bytes(raw)
        manifest.chmod(0o400)
        with self.assertRaises(EvidenceError):
            inspect_sealed_critic_room(
                room, expected_manifest_sha256=hashlib.sha256(raw).hexdigest(),
            )

    def test_forged_dossier_without_matching_original_handoff_is_rejected(self):
        changed = copy.deepcopy(self.handoff)
        changed["critic_worklist"]["dossier_sha256"] = "0"*64
        with self.assertRaises(EvidenceError):
            _manifest(changed, self.fixture.d, self.images)

    def test_no_live_network_critic_signature_or_publication_interface(self):
        import company_os.competitive_critic_room as module
        for name in ("fetch", "publish", "send", "sign_review", "approve", "launch"):
            self.assertFalse(hasattr(module, name))


if __name__ == "__main__":
    unittest.main()
