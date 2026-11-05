"""1970s 1,500 ft2 neglected-house synthetic inventory contract tests.

The separately executed GitHub workflow runs the FULL source-bound M4 case,
three distinct scripted provider stages, private Option 2 PDF and raster audit.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from inspection_engine.core import DataError, SYSTEMS, load_project
from inspection_engine.agents import plan_specialists
from inspection_engine.m4_workflow import preflight_case
from scripts.run_1970s_house_dry_run import (
    ZONES, HYPOTHESIS_BY_ID, COVERED_ROOMS, EXPECTED_ROLE_IDS,
    PROJECT_ID, build_synthetic_property, _inside_external_directory,
    _propose_by_script, _q02_script, _q03_script,
)


class SyntheticNeglectedHomeInventoryTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="1970s_source_inventory_")
        self.addCleanup(workspace.cleanup)
        self.folder = Path(workspace.name)
        self.source, self.document = build_synthetic_property(self.folder / "source")

    def test_description_preserved_without_inventing_address_or_inspector(self):
        p = self.document["property"]
        self.assertTrue(p["synthetic"])
        self.assertEqual(p["reported_living_area_sqft"], 1500)
        self.assertEqual(p["bedrooms"], 3)
        self.assertEqual(p["full_bathrooms"], 2)
        self.assertTrue(p["ensuite_full_bathroom_in_primary_bedroom"])
        self.assertTrue(p["has_basement"])
        self.assertTrue(p["attached_garage"])
        self.assertTrue(p["attic_accessible_by_description"])
        self.assertEqual(p["construction_period"], "1970s")
        self.assertIsNone(p["basement_area_sqft"])
        self.assertEqual(p["building_type"], "residential")
        self.assertIsNone(p["qualified_reviewer"])
        self.assertEqual(self.document["project_id"], PROJECT_ID)
        self.assertFalse(self.document["findings"])

    def test_thirteen_systems_and_all_required_named_rooms_captured(self):
        self.assertEqual(len(ZONES), 20)
        self.assertEqual(len(self.document["media"]), 20)
        self.assertEqual(len(set(m["id"] for m in self.document["media"])), 20)
        self.assertTrue(set(COVERED_ROOMS) <= {m["room_label"] for m in self.document["media"]})
        p = preflight_case(self.source)
        self.assertEqual(len(p["coverage"]), len(SYSTEMS))
        self.assertTrue(p["ready_for_specialist_execution"])
        self.assertEqual(len(p["specialist_plan"]["jobs"]), 20)
        self.assertEqual({j["assigned_to"] for j in p["specialist_plan"]["jobs"]},
                         EXPECTED_ROLE_IDS)
        self.assertFalse(p["customer_release_allowed"])
        self.assertFalse(p["inspector_approved"])
        self.assertTrue(all(row["open"] for row in p["coverage"]))

    def test_each_generated_image_is_a_declared_schematic_not_field_photo(self):
        p = load_project(self.source)
        for record in p["media"]:
            self.assertIn("SYNTHETIC", record["caption"])
            self.assertIn("No actual condition confirmed", record["caption"])
            with Image.open(self.source.parent / record["path"]) as img:
                self.assertEqual(img.format, "PNG")
                self.assertEqual(img.size, (1060, 660))

    def test_no_invented_equipment_serial_manufacturing_year_or_code_approval(self):
        self.assertEqual(len(self.document["equipment"]), 2)
        for item in self.document["equipment"]:
            self.assertEqual(item["model"], "NOT VERIFIED")
            self.assertEqual(item["serial"], "NOT VERIFIED")
        self.assertTrue(any("lead/asbestos" in lim["description"] for lim in self.document["limitations"]))
        self.assertTrue(any("manufacturer" in lim["description"] for lim in self.document["limitations"]))
        self.assertEqual(len(HYPOTHESIS_BY_ID), 13)

    def test_scripted_writer_is_explicitly_not_real_vision(self):
        calls = {"writer": []}
        answer = _propose_by_script(None, "ROLE T01; evidence ID P01; area assigned by inspector site;", calls)
        self.assertEqual(len(answer["candidates"]), 1)
        self.assertEqual(answer["candidates"][0]["type"], "potential_concern")
        self.assertIn("Actual condition is unknown", answer["candidates"][0]["description"])
        empty = _propose_by_script(None, "ROLE T05; evidence ID P14; area assigned by inspector interior;", calls)
        self.assertEqual(empty, {"candidates": [], "requests": []})
        self.assertEqual(calls["writer"], ["P01", "P14"])

    def test_basement_alias_never_claims_a_concealed_crawlspace_finding(self):
        calls = {"writer": []}
        answer = _propose_by_script(
            None, "ROLE T02; evidence ID P08; area assigned by inspector basement;", calls)
        self.assertEqual(answer, {"candidates": [], "requests": []})
        self.assertEqual(calls["writer"], ["P08"])

    def test_q02_refuses_to_confirm_schematic_as_real_evidence(self):
        calls = {"q02": 0, "unfamiliar_q02_prompts": 0}
        result = _q02_script(None, "UNTRUSTED HYPOTHESIS", calls)
        self.assertEqual(result["decision"], "insufficient_evidence")
        self.assertIn("synthetic", result["reason"])
        self.assertEqual(calls["q02"], 1)

    def test_q03_keeps_coverage_pending_and_all_entries(self):
        calls = {"q03": 0}
        packet = {"queue": {"entries": [
            {"entry_id": "coverage:HAZARD:roof", "type": "coverage_task"},
            {"entry_id": "finding:F01", "type": "finding"},
        ]}}
        reply = _q03_script("LEDGER_PACKET_JSON: " + json.dumps(packet), {}, calls)
        self.assertEqual(len(reply["decisions"]), 2)
        self.assertEqual(reply["decisions"][0]["decision"], "needs_evidence")
        self.assertTrue(reply["decisions"][0]["evidence_gap"])
        self.assertEqual(reply["decisions"][1]["decision"], "distinct")
        self.assertEqual(calls["q03"], 1)

    def test_workspace_never_writes_into_git_checkout(self):
        from scripts.run_1970s_house_dry_run import __file__ as mod_file
        checkout = Path(mod_file).resolve().parents[3]
        self.assertTrue((checkout / ".git").exists())
        with self.assertRaisesRegex(DataError, "outside Git"):
            _inside_external_directory(checkout / "must_not_create_private_dryrun")


if __name__ == "__main__":
    unittest.main()
