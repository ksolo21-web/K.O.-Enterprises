"""M4 V6 issuer evidence negative tests using only fabricated associations/people.

NOT a real ASHI / InterNACHI member, not a live credential lookup.
"""
from __future__ import annotations

from datetime import date
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from inspection_engine.core import DataError, sha256
from inspection_engine.m4_human_review import _digest, _bytes
from inspection_engine.m4_issuer_receipts import issuer_evidence_preflight
import test_m4_credential_gate as credential_tests


class M4IssuerReceiptTests(unittest.TestCase):
    def setUp(self):
        self.v5=credential_tests.M4ProfessionalCredentialGateTests(
            "test_synthetic_credential_and_revocation_preflight_pass_still_never_releases"
        )
        self.v5.setUp()
        self.addCleanup(self.v5.doCleanups)
        self.b=self.v5
        self.b.qualification_payload["reviewers"][0]["qualification_basis"]="professional_certification"
        self.b.qualification_payload["reviewers"][0]["qualification_issuer"]="ASHI_CERTIFIED"
        self.b.qualification_payload["reviewers"][1]["qualification_basis"]="professional_certification"
        self.b.qualification_payload["reviewers"][1]["qualification_issuer"]="INTERNACHI_CPI"
        self.b.resign()
        self.verify_key=Ed25519PrivateKey.generate()
        self.verifier_root=self.b.f.root/"issuer_verifier_root.json"
        self.root_data={
            "schema_version":1,
            "issuer_verifier_id":"synthetic-issuer-analyst",
            "organization_id":"SeparateIssuerValidationOffice",
            "public_key_hex":self.verify_key.public_key().public_bytes(
                serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex(),
            "active":True,
            "enrolled_by_external_authority":True,
            "external_enrollment_reference":"TEST ONLY: no independently checked authority"
        }
        self.store=self.b.f.root/"issuer_capture_store"
        self.store.mkdir()
        self.urls=[
            "https://www.homeinspector.org/for-consumers/find-an-inspector/",
            "https://www.nachi.org/verify/lookup"
        ]
        self.captures=[]
        for i in range(2):
            capture=self.store/("synthetic-issuer-%s.txt"%i)
            capture.write_text(
                "SYNTHETIC OFFLINE TEST ONLY - NOT FROM AN ISSUER. "*6,
                encoding="utf-8")
            self.captures.append(capture)
        self.payload={
            "schema_version":1,
            "issuer_verifier_id":self.root_data["issuer_verifier_id"],
            "verifier_registry_sha256":None,
            "officer_registry_sha256":sha256(self.b.officers),
            "reviewer_registry_sha256":sha256(self.b.f.trust),
            "project_id":self.b.f.packet["project_id"],
            "request_digest":_digest(self.b.f.packet),
            "qualifications_digest":_digest(self.b.qualification_payload),
            "checked_on":"2026-11-03",
            "valid_until":"2026-11-09",
            "claims":[{
                "role":self.b.f.roles[i],
                "reviewer_id":self.b.f.ids[i],
                "qualification_issuer":self.b.qualification_payload["reviewers"][i]["qualification_issuer"],
                "credential_identifier":self.b.qualification_payload["reviewers"][i]["credential_identifier"],
                "issuer_url":self.urls[i],
                "issuer_record_type":"association_directory_or_direct_response",
                "association_status_claim":"active_certification_evidence",
                "identity_match_method":"Test-only name and credential cross-check",
                "captured_at":"2026-11-03",
                "captured_relative_path":self.captures[i].name,
                "captured_sha256":sha256(self.captures[i]),
                "evidence_provenance":"verifier_captured_official_page",
                "verifier_notes":"SYNTHETIC: no actual online lookup or external identity authentication"
            } for i in range(2)],
            "customer_release_allowed":False
        }
        self.envelope=self.b.f.root/"issuer_source_receipts.json"
        self.reseal()

    def reseal(self, *, rewrite_root=True):
        if rewrite_root:
            self.b._save(self.verifier_root,self.root_data)
        self.payload["verifier_registry_sha256"]=sha256(self.verifier_root)
        self.b._save(self.envelope,{
            "schema_version":1,
            "payload":self.payload,
            "signature_hex":self.verify_key.sign(_bytes(self.payload)).hex(),
            "key_algorithm":"Ed25519"
        })

    def check(self, *, root_pin=None, when=None, watermark=17):
        return issuer_evidence_preflight(
            self.b.f.work,self.b.f.trust,self.b.officers,
            self.b.qualification_file,self.b.revocation_file,self.b.evidence_root,
            self.verifier_root,self.envelope,self.store,
            independently_pinned_registry_sha256=root_pin or sha256(self.verifier_root),
            minimum_revocation_sequence=watermark,
            as_of=when or date(2026,11,3)
        )

    def test_two_synthetic_source_receipts_pass_only_internal_custody(self):
        result=self.check()
        self.assertEqual(result["issuer_captured_sources_bound"],2)
        self.assertTrue(result["registered_verifier_signature_verified"])
        for k in ("customer_release_allowed",
                  "independent_official_issuer_authenticity_verified",
                  "out_of_band_verifier_enrollment_independently_verified",
                  "real_identity_independently_authenticated",
                  "qualified_for_customer_release"):
            self.assertFalse(result[k])

    def test_issuer_root_hash_mismatch_is_fail_closed(self):
        with self.assertRaisesRegex(DataError,"root pin"):
            self.check(root_pin="0"*64)

    def test_receipt_forgery_without_correct_signature_is_fail_closed(self):
        env=json.loads(self.envelope.read_text())
        env["payload"]["claims"][0]["issuer_url"]="https://www.nachi.org/verify/lookup"
        self.b._save(self.envelope,env)
        with self.assertRaisesRegex(DataError,"signature invalid"):
            self.check()

    def test_source_capture_hash_tampering_rejected(self):
        self.captures[1].write_text("TAMPERED")
        with self.assertRaisesRegex(DataError,"invalid size|differ"):
            self.check()

    def test_unknown_certificate_issuer_rejected(self):
        self.payload["claims"][0]["qualification_issuer"]="PAY_TO_CERTIFY"
        self.reseal()
        with self.assertRaisesRegex(DataError,"must match"):
            self.check()

    def test_issuer_url_subdomain_lookalike_rejected(self):
        self.payload["claims"][0]["issuer_url"]="https://www.homeinspector.org.evil.example/for-consumers/find-an-inspector/"
        self.reseal()
        with self.assertRaisesRegex(DataError,"issuer-controlled URL"):
            self.check()

    def test_insecure_http_issuer_reference_rejected(self):
        self.payload["claims"][0]["issuer_url"]="http://www.homeinspector.org/for-consumers/find-an-inspector/"
        self.reseal()
        with self.assertRaisesRegex(DataError,"issuer-controlled URL"):
            self.check()

    def test_member_status_not_certification_rejected(self):
        self.payload["claims"][0]["association_status_claim"]="membership_only"
        self.reseal()
        with self.assertRaisesRegex(DataError,"membership-only"):
            self.check()

    def test_unapproved_source_page_path_rejected(self):
        self.payload["claims"][0]["issuer_url"]="https://www.homeinspector.org/wp-content/test.png"
        self.reseal()
        with self.assertRaisesRegex(DataError,"ASHI source"):
            self.check()

    def test_training_cannot_substitute_for_certification(self):
        self.b.qualification_payload["reviewers"][0]["qualification_basis"]="professional_training"
        self.b.resign()
        self.payload["qualifications_digest"]=_digest(self.b.qualification_payload)
        self.reseal()
        with self.assertRaisesRegex(DataError,"certified reviewer"):
            self.check()

    def test_false_qualification_digest_rejected(self):
        self.payload["qualifications_digest"]="f"*64
        self.reseal()
        with self.assertRaisesRegex(DataError,"different case"):
            self.check()

    def test_issuer_capture_path_traversal_rejected(self):
        self.payload["claims"][0]["captured_relative_path"]="../synthetic-issuer-0.txt"
        self.reseal()
        with self.assertRaisesRegex(DataError,"path is unsafe"):
            self.check()

    def test_issuer_capture_symlink_rejected(self):
        link=self.store/"symlinked.txt"
        link.symlink_to(self.captures[0])
        self.payload["claims"][0]["captured_relative_path"]=link.name
        self.reseal()
        with self.assertRaisesRegex(DataError,"symbolic links"):
            self.check()

    def test_same_reviewer_and_issuer_verifier_identity_rejected(self):
        self.root_data["issuer_verifier_id"]=self.b.f.ids[0]
        self.reseal()
        with self.assertRaisesRegex(DataError,"must be independent"):
            self.check()

    def test_same_officer_and_issuer_verifier_organization_rejected(self):
        self.root_data["organization_id"]=self.b.officer_orgs[0]
        self.reseal()
        with self.assertRaisesRegex(DataError,"must be independent"):
            self.check()

    def test_issuer_receipt_expired_rejected(self):
        self.payload["valid_until"]="2026-11-02"
        self.reseal()
        with self.assertRaisesRegex(DataError,"stale, future dated, or expired"):
            self.check()

    def test_missing_issuer_receipt_rejected(self):
        self.payload["claims"].pop()
        self.reseal()
        with self.assertRaisesRegex(DataError,"per qualified reviewer"):
            self.check()

    def test_duplicate_issuer_role_rejected(self):
        self.payload["claims"][1]["role"]=self.payload["claims"][0]["role"]
        self.reseal()
        with self.assertRaisesRegex(DataError,"missing or duplicated"):
            self.check()

    def test_revocation_watermark_is_still_enforced(self):
        with self.assertRaisesRegex(DataError,"rolled back"):
            self.check(watermark=18)

    def test_issuer_evidence_cannot_live_inside_source_root(self):
        with self.assertRaisesRegex(DataError,"own private non-Git area"):
            issuer_evidence_preflight(
                self.b.f.work,self.b.f.trust,self.b.officers,
                self.b.qualification_file,self.b.revocation_file,self.b.evidence_root,
                self.verifier_root,self.envelope,self.b.f.root/"source",
                independently_pinned_registry_sha256=sha256(self.verifier_root),
                minimum_revocation_sequence=17,
                as_of=date(2026,11,3)
            )

    def test_release_claim_rejected_before_any_proof_processing(self):
        self.payload["customer_release_allowed"]=True
        self.reseal()
        with self.assertRaisesRegex(DataError,"complete bound source contract"):
            self.check()


if __name__=="__main__":
    unittest.main()
