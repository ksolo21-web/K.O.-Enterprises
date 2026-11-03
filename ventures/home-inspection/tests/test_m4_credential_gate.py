"""V5 fail-closed professional credential precheck: SYNTHETIC signed records only."""
from __future__ import annotations

from datetime import date
import json
import os
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from inspection_engine.core import DataError, sha256
from inspection_engine.m4_human_review import _digest, _bytes
from inspection_engine.m4_credential_gate import professional_review_preflight, POLICY
from test_m4_human_review import HumanReviewTests


class M4ProfessionalCredentialGateTests(unittest.TestCase):
    def setUp(self):
        # Reuse the actual M4 source-to-PDF, Q01/Q02/Q03 and reviewer signing
        # fixture rather than bypassing the completed pipeline.
        self.fixture=HumanReviewTests("test_two_distinct_key_verified_reviews_never_release")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture
        self.f.sign(0)
        self.f.sign(1)
        self.now=date(2026,11,3)
        self.officer_keys=[Ed25519PrivateKey.generate() for _ in range(2)]
        self.officer_ids=["synthetic-evaluator","synthetic-revocation-monitor"]
        self.officer_orgs=["EvaluatorOrg","RevocationOffice"]
        self.officers=self.f.root/"credential_officers.json"
        self.reg={
            "schema_version":1,
            "qualification_officer":{
                "officer_id":self.officer_ids[0],
                "public_key_hex":self._pub(0),
                "active":True,"organization_id":self.officer_orgs[0]},
            "revocation_officer":{
                "officer_id":self.officer_ids[1],
                "public_key_hex":self._pub(1),
                "active":True,"organization_id":self.officer_orgs[1]}}
        self._save(self.officers,self.reg)
        self.evidence_root=self.f.root/"private_qualification_proof"
        self.evidence_root.mkdir()
        self.proofs=[]
        for index in (0,1):
            path=self.evidence_root/("proof-%d.txt"%index)
            path.write_text("SYNTHETIC TEST-ONLY QUALIFICATION, NO REAL INSPECTOR\n")
            self.proofs.append(path)
        self.qualification_payload={
            "schema_version":1,"signer_id":self.officer_ids[0],
            "project_id":self.f.packet["project_id"],
            "request_digest":_digest(self.f.packet),
            "trust_sha256":sha256(self.f.trust),
            "officer_registry_sha256":sha256(self.officers),
            "policy_sha256":sha256(POLICY),
            "jurisdiction":"US-MI",
            "checked_on":"2026-11-03",
            "valid_until":"2026-11-24",
            "reviewers":[{
                "reviewer_id":self.f.ids[i],
                "role":self.f.roles[i],
                "public_key_hex":self.f.keys[i].public_key().public_bytes(
                    ser.Encoding.Raw,ser.PublicFormat.Raw).hex(),
                "organization_id":"SyntheticHomeInspectorFirm" if i==0 else "SyntheticIndependentQA",
                "qualification_basis":"documented_field_experience",
                "qualification_issuer":"SYNTHETIC-TEST-NO-REAL-ISSUER",
                "credential_identifier":"TEST-NOT-A-CREDENTIAL-"+str(i),
                "scope":"private_residential_visual_home_inspection",
                "evidence_path":self.proofs[i].name,
                "evidence_sha256":sha256(self.proofs[i]),
                "verified_on":"2026-11-03",
                "valid_until":"2026-11-24",
                "identity_checked_method":"Synthetic demo identity; not authenticated",
                "independence_checked":True,
                "conflict_declared":False
            } for i in (0,1)]
        }
        self.revocation_payload={
            "schema_version":1,"signer_id":self.officer_ids[1],
            "project_id":self.f.packet["project_id"],
            "request_digest":_digest(self.f.packet),
            "trust_sha256":sha256(self.f.trust),
            "checked_on":"2026-11-03",
            "valid_until":"2026-11-04",
            "revoked_reviewer_ids":[],
            "revoked_officer_ids":[],
            "revocation_sequence":17,
        }
        self.qualification_file=self.f.root/"qualification_signed.json"
        self.revocation_file=self.f.root/"revocations_signed.json"
        self.resign()

    def _pub(self,i):
        return self.officer_keys[i].public_key().public_bytes(
            ser.Encoding.Raw,ser.PublicFormat.Raw).hex()

    def _save(self,path,data):
        path.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")

    def resign(self):
        for filename,payload,index in (
            (self.qualification_file,self.qualification_payload,0),
            (self.revocation_file,self.revocation_payload,1)):
            self._save(filename,{
                "schema_version":1,
                "key_algorithm":"Ed25519",
                "payload":payload,
                "signature_hex":self.officer_keys[index].sign(_bytes(payload)).hex()})

    def check(self,**kwargs):
        return professional_review_preflight(
            self.f.work,self.f.trust,self.officers,
            self.qualification_file,self.revocation_file,self.evidence_root,
            as_of=kwargs.get("as_of",self.now))

    def test_synthetic_credential_and_revocation_preflight_pass_still_never_releases(self):
        result=self.check()
        self.assertEqual(result["status"],"LOCAL_SIGNED_CREDENTIAL_EVIDENCE_PRECHECK_ONLY")
        self.assertEqual(result["verified_credential_proof_files"],2)
        self.assertEqual(result["review_signatures_verified"],2)
        self.assertTrue(result["fresh_revocation_signature_verified"])
        for flag in ("customer_release_allowed","qualified_for_customer_release",
                     "real_identity_independently_authenticated","professional_issuer_live_checked",
                     "statutory_local_requirements_verified","competence_field_benchmarked"):
            self.assertFalse(result[flag],flag)

    def test_reviewer_signature_missing_blocks_gate(self):
        (self.f.work/"quality_review_signed.json").unlink()
        with self.assertRaisesRegex(DataError,"Both distinct human review"):
            self.check()

    def test_tampered_proof_document_blocks_preflight(self):
        self.proofs[0].write_text("MUTATED EVIDENCE")
        with self.assertRaisesRegex(DataError,"proof has changed"):
            self.check()

    def test_review_snapshot_stale_blocks_even_if_qualification_untouched(self):
        original=self.qualification_payload["request_digest"]
        self.qualification_payload["request_digest"]="f"*64
        self.resign()
        with self.assertRaisesRegex(DataError,"not bound"):
            self.check()
        self.qualification_payload["request_digest"]=original

    def test_invalid_officer_signature_blocks_preflight(self):
        env=json.loads(self.qualification_file.read_text())
        env["payload"]["jurisdiction"]="US-XX"
        self._save(self.qualification_file,env)
        with self.assertRaisesRegex(DataError,"signature invalid"):
            self.check()

    def test_reviewer_cannot_self_verify_as_qualification_officer(self):
        self.reg["qualification_officer"]["public_key_hex"]=self.f.keys[0].public_key().public_bytes(
            ser.Encoding.Raw,ser.PublicFormat.Raw).hex()
        self._save(self.officers,self.reg)
        with self.assertRaisesRegex(DataError,"cannot self-verify"):
            self.check()

    def test_separate_officers_required(self):
        self.reg["revocation_officer"]["public_key_hex"]=self.reg["qualification_officer"]["public_key_hex"]
        self._save(self.officers,self.reg)
        with self.assertRaisesRegex(DataError,"must be different"):
            self.check()

    def test_expires_after_30_days_or_is_expired_blocks_preflight(self):
        for future in ("2027-01-01","2026-11-02"):
            self.qualification_payload["valid_until"]=future
            self.resign()
            with self.subTest(future=future), self.assertRaisesRegex(DataError,"expired, future-dated, or overlong"):
                self.check()

    def test_independence_of_reviewer_organizations_required(self):
        self.qualification_payload["reviewers"][1]["organization_id"]=self.qualification_payload["reviewers"][0]["organization_id"]
        self.resign()
        with self.assertRaisesRegex(DataError,"organizations overlap"):
            self.check()

    def test_independence_of_assessor_and_reviewer_organizations_required(self):
        self.qualification_payload["reviewers"][0]["organization_id"]=self.officer_orgs[0]
        self.resign()
        with self.assertRaisesRegex(DataError,"organizations overlap"):
            self.check()

    def test_unresolved_conflict_of_interest_blocks_gate(self):
        self.qualification_payload["reviewers"][1]["conflict_declared"]=True
        self.resign()
        with self.assertRaisesRegex(DataError,"conflicts fail"):
            self.check()

    def test_reviewers_cannot_claim_nonexistent_michigan_license_scheme(self):
        self.qualification_payload["reviewers"][0]["qualification_basis"]="michigan_home_inspector_license"
        self.resign()
        with self.assertRaisesRegex(DataError,"Unknown professional competency basis"):
            self.check()

    def test_reviewer_credential_expired_or_stale_blocks_gate(self):
        self.qualification_payload["reviewers"][0]["valid_until"]="2026-11-02"
        self.resign()
        with self.assertRaisesRegex(DataError,"expired or stale"):
            self.check()

    def test_reviewer_revocation_blocks_gate_even_after_signing(self):
        self.revocation_payload["revoked_reviewer_ids"].append(self.f.ids[0])
        self.resign()
        with self.assertRaisesRegex(DataError,"Revoked reviewer"):
            self.check()

    def test_officer_revocation_blocks_gate(self):
        self.revocation_payload["revoked_officer_ids"].append(self.officer_ids[1])
        self.resign()
        with self.assertRaisesRegex(DataError,"Revoked reviewer"):
            self.check()

    def test_stale_revocation_attestation_blocks_gate(self):
        self.revocation_payload["checked_on"]="2026-10-31"
        self.revocation_payload["valid_until"]="2026-11-02"
        self.resign()
        with self.assertRaisesRegex(DataError,"expired, stale"):
            self.check()

    def test_future_dated_revocation_attestation_blocks_gate(self):
        self.revocation_payload["checked_on"]="2026-11-04"
        self.revocation_payload["valid_until"]="2026-11-05"
        self.resign()
        with self.assertRaisesRegex(DataError,"future-dated"):
            self.check()

    def test_policy_expired_by_2027_blocks_preflight(self):
        with self.assertRaisesRegex(DataError,"policy is stale"):
            self.check(as_of=date(2027,1,1))

    def test_credential_evidence_cannot_live_inside_git_directory(self):
        inside=self.f.root/"public_checkout"
        inside.mkdir()
        (inside/".git").mkdir()
        with self.assertRaisesRegex(DataError,"cannot be kept"):
            professional_review_preflight(
                self.f.work,self.f.trust,self.officers,self.qualification_file,
                self.revocation_file,inside,as_of=self.now)

    def test_verifier_cannot_swap_reviewer_identity(self):
        self.qualification_payload["reviewers"][1]["reviewer_id"]="synthetic-other"
        self.resign()
        with self.assertRaisesRegex(DataError,"does not identify"):
            self.check()

if __name__=="__main__":
    unittest.main()
