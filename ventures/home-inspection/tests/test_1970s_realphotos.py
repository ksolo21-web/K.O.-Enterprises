"""Contract tests for the real-photo composite whole-house dry-run.

No network in unit tests; only the dedicated Actions dry-run downloads images.
"""
import unittest
from scripts.run_1970s_real_photos import (
    PHOTOS, ALLOWED_LICENCES, SEVERITY_ORDER, UNVERIFIED_SPACES,
    CASE_ID, _image_url
)
from inspection_engine.agents import AREA_SYSTEMS, SYSTEM_OWNER
from inspection_engine.core import SYSTEMS


class RealPhotoCompositeContract(unittest.TestCase):
    def test_all_reference_images_are_different_real_source_files(self):
        self.assertGreaterEqual(len(PHOTOS), 14)
        self.assertEqual(len({x[0] for x in PHOTOS}), len(PHOTOS))
        self.assertEqual(len({x[3] for x in PHOTOS}), len(PHOTOS))
        self.assertTrue(CASE_ID.startswith("COMPOSITE-"))

    def test_each_source_has_precise_license_and_credit(self):
        for p in PHOTOS:
            self.assertIn(p[5], ALLOWED_LICENCES)
            self.assertNotEqual(p[5], "Wikimedia Commons licensed")
            self.assertTrue(p[4])
            self.assertTrue(p[3].lower().endswith((".jpg",".jpeg")))
            self.assertTrue(_image_url(p[3]).startswith("https://upload.wikimedia.org/wikipedia/commons/"))

    def test_every_image_routes_to_actual_specialist(self):
        roles=set()
        for p in PHOTOS:
            area=p[1]
            self.assertIn(area,AREA_SYSTEMS)
            systems=AREA_SYSTEMS[area]
            self.assertTrue(systems)
            roles.update(SYSTEM_OWNER[s] for s in systems)
        self.assertEqual(roles,set(f"T{i:02}" for i in range(1,9)))

    def test_major_systems_and_two_bathrooms_present(self):
        codes={p[1] for p in PHOTOS}
        self.assertTrue({"roof","attic","site","foundation","basement","electrical","plumbing","water_heating","hvac","garage","exterior","interior","framing"}<=codes)
        names=" ".join(p[2].lower() for p in PHOTOS)
        self.assertIn("en-suite",names)
        self.assertIn("hall full bath",names)
        self.assertGreaterEqual(len(SYSTEMS),13)
        self.assertTrue(any("subfloor" in n.lower() for n in UNVERIFIED_SPACES) or
                        any("floor" in n.lower() for n in UNVERIFIED_SPACES))

    def test_no_professional_inspector_or_model_accuracy_can_be_claimed(self):
        from inspect import getsource
        import scripts.run_1970s_real_photos as run
        source=getsource(run.run)
        for phrase in ('"qualified_inspector_signed":False',
                       '"AI_vision_model_inference_performed":False',
                       '"customer_release_allowed":False',
                       '"original_house_photographs":False',
                       '"independent_Q02_Q03_human_review_performed":False'):
            self.assertIn(phrase,source)

    def test_severity_is_conservative_and_professional_followup_is_present(self):
        for p in PHOTOS:
            self.assertIn(p[6],SEVERITY_ORDER)
            self.assertGreater(len(p[7]),22)
            self.assertGreater(len(p[8]),45)

    def test_output_sources_are_not_synthetic_schematics(self):
        from inspect import getsource
        import scripts.run_1970s_real_photos as run
        text=getsource(run._make_source)
        self.assertIn("_fetch_real_photo",text)
        self.assertNotIn("_schematic(",text)
        self.assertIn("upstream_original_sha256",text)

    def test_real_source_image_download_fails_closed(self):
        from unittest.mock import patch
        import scripts.run_1970s_real_photos as run
        with patch.object(run, "urlopen",side_effect=OSError("network deliberately offline")), patch.object(run.time, "sleep"):
            with self.assertRaisesRegex(ValueError,"unavailable"):
                run._fetch_real_photo(PHOTOS[0][3])


if __name__=="__main__":
    unittest.main()
