"""R52 authority-chain regression tests.

These are synthetic software/controller tests. They do not approve a real card.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

import engine
import enforcer_critic
import fixer_advisor
import repair
import r52_policy


REV = "segment-role-whole-label-2026-09-13-r52"


class R52AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"GITHUB_ACTIONS": "false"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_pdf(self):
        path = self.root / "source.pdf"
        with fitz.open() as doc:
            page = doc.new_page(width=400, height=240)
            page.draw_line((30,150),(370,150),color=(0.1,0.7,0.2),width=4)
            page.insert_text((100,65),"Source Road",fontsize=10)
            box = list(page.search_for("Source Road")[0])
            font = page.get_fonts()[0][4]
            doc.save(path)
        return path, box, font

    def pin(self, path):
        return {"file": path.name, "sha256": engine.sha(path)}

    def failed_enforcer(self, source):
        path = self.root / "enforcer-fail.json"
        engine.json_write(path, {
            "schema_version": 1,
            "kind": "territory_enforcer_critic",
            "r52_revision": REV,
            "artifact_sha256": engine.sha(source),
            "review_sha256": "0"*64,
            "findings": ["label is bound to the wrong entrance segment"],
            "passed": False,
            "release_gate_eligible": False,
        })
        return path

    def fixer_request(self):
        source, box, font = self.make_pdf()
        verdict = self.failed_enforcer(source)
        request = {
            "schema_version": 1,
            "kind": "territory_fixer_request",
            "candidate": self.pin(source),
            "enforcer_verdict": self.pin(verdict),
            "repair_scope": {
                "type": "label_only",
                "approved_masks": [[80,40,270,148]],
                "labels": [{
                    "label_id": "source-road-entrance",
                    "street": "Source Road",
                    "navigation_role": "entrance_run",
                    "segment_id": "source-road-west-entrance",
                    "source_evidence": "synthetic locked source fixture",
                    "old_box": box,
                    "text": "Source Road",
                    "font_resource": font,
                    "font_size": 10,
                    "road_id": "fixture-road-1",
                    "road_polyline": [[30,150],[370,150]],
                    "road_width": 4,
                    "placements": [
                        {"kind":"direct","baseline":[100,80]},
                        {"kind":"direct","baseline":[100,144]}
                    ],
                }],
            },
        }
        path = self.root / "fixer-request.json"
        engine.json_write(path, request)
        return source, verdict, path

    def test_exact_r52_policy_verifies(self):
        result = r52_policy.verify()
        self.assertEqual(result["revision"], REV)
        self.assertTrue(result["activation_passed"])
        self.assertTrue(result["mandatory_internal_reviewer"])
        self.assertTrue(result["exact_segment_role_binding_required"])
        self.assertTrue(result["whole_label_suffix_review_required"])
        self.assertTrue(result["native_font_spacing_visual_review_required"])

    def test_r52_score_floor_is_strict_and_minimum_based(self):
        good = {"overall_score":9.5,"categories":{k:{"score":9.5} for k in engine.CATEGORIES}}
        engine.score_guard(good)
        exact_nine = {"overall_score":9.0,"categories":{k:{"score":9.0} for k in engine.CATEGORIES}}
        with self.assertRaises(engine.GateError):
            engine.score_guard(exact_nine)
        masked = {"overall_score":9.8,"categories":{k:{"score":10.0} for k in engine.CATEGORIES}}
        masked["categories"]["labels"]["score"] = 9.2
        with self.assertRaises(engine.GateError):
            engine.score_guard(masked)
        over_ten = {"overall_score":10.1,"categories":{k:{"score":10.1} for k in engine.CATEGORIES}}
        with self.assertRaises(engine.GateError):
            engine.score_guard(over_ten)

    def test_fixer_advisor_cannot_pass_or_edit(self):
        source, verdict, request = self.fixer_request()
        out = self.root / "advice.json"
        with patch.object(engine, "private_guard"), patch.object(engine, "verify_skills", return_value={"r52":{"revision":REV}}):
            advice = fixer_advisor.advise(request, out)
        self.assertTrue(advice["repair_authorized"])
        self.assertFalse(advice["release_authorized"])
        self.assertTrue(advice["enforcer_recheck_required"])
        self.assertEqual(advice["source_sha256"], engine.sha(source))
        self.assertEqual(advice["enforcer_verdict_sha256"], engine.sha(verdict))
        self.assertEqual(engine.sha(source), advice["source_sha256"])

    def test_builder_rejects_raw_self_authored_repair(self):
        raw = self.root / "raw.json"
        engine.json_write(raw, {"mode":"approved_vector_label_revision"})
        with patch.object(engine, "private_guard"), patch.object(engine, "verify_skills", return_value={"r52":{"revision":REV}}):
            with self.assertRaises(repair.RepairError):
                repair.repair(raw, self.root/"rounds")

    def test_builder_executes_only_fixer_advice_after_failed_enforcer(self):
        source, _, request = self.fixer_request()
        advice_path = self.root / "advice.json"
        with patch.object(engine, "private_guard"), patch.object(engine, "verify_skills", return_value={"r52":{"revision":REV}}):
            fixer_advisor.advise(request, advice_path)
            result = repair.repair(advice_path, self.root/"rounds", workspace_root=self.root)
        self.assertGreaterEqual(result["rounds"], 1)
        self.assertIsNotNone(result["selected"])
        self.assertFalse(result["release_ready"])
        self.assertTrue(result["independent_visual_review_required"])
        self.assertEqual(engine.sha(source), engine.json_read(advice_path)["source_sha256"])

    def test_enforcer_is_only_role_that_can_mark_gate_eligible(self):
        candidate, _, _ = self.make_pdf()
        review = self.root / "review.json"
        scores = {k:{"score":9.6} for k in engine.CATEGORIES}
        engine.json_write(review, {"artifact_sha256":engine.sha(candidate),"overall_score":9.6,"categories":scores})
        job = self.root / "enforcer-job.json"
        engine.json_write(job, {
            "schema_version":1,
            "kind":"territory_enforcer_review",
            "candidate":self.pin(candidate),
            "internal_review":self.pin(review),
            "independent_visual_required":False,
        })
        ok={"returncode":0,"payload":{"passed":True,"errors":[]},"stdout":"","stderr":""}
        with patch.object(engine, "private_guard"), patch.object(engine, "verify_skills", return_value={"r52":{"revision":REV}}), patch.object(enforcer_critic, "_run_validator", return_value=ok):
            verdict=enforcer_critic.enforce(job,self.root/"enforcer-pass.json")
        self.assertTrue(verdict["passed"])
        self.assertTrue(verdict["release_gate_eligible"])
        self.assertTrue(verdict["builder_cannot_override"])
        self.assertEqual(verdict["edits_performed"],0)

    def test_enforcer_rejects_exact_nine_even_if_validators_say_pass(self):
        candidate, _, _ = self.make_pdf()
        review = self.root / "review-nine.json"
        scores = {k:{"score":9.0} for k in engine.CATEGORIES}
        engine.json_write(review, {"artifact_sha256":engine.sha(candidate),"overall_score":9.0,"categories":scores})
        job = self.root / "enforcer-nine-job.json"
        engine.json_write(job, {
            "schema_version":1,
            "kind":"territory_enforcer_review",
            "candidate":self.pin(candidate),
            "internal_review":self.pin(review),
            "independent_visual_required":False,
        })
        ok={"returncode":0,"payload":{"passed":True,"errors":[]},"stdout":"","stderr":""}
        with patch.object(engine, "private_guard"), patch.object(engine, "verify_skills", return_value={"r52":{"revision":REV}}), patch.object(enforcer_critic, "_run_validator", return_value=ok):
            verdict=enforcer_critic.enforce(job,self.root/"enforcer-nine.json")
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["release_gate_eligible"])
        self.assertTrue(any("R52 requires overall_score" in x for x in verdict["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
