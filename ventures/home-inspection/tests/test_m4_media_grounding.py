"""M4 V9 media-grounding tests — synthetic sources and identities only.

These checks test exact photo/frame hashes and normalized coordinates, not the
contents of real images or a genuine professional's diagnosis.
"""
from __future__ import annotations

import copy
import hashlib
import math
import unittest

from inspection_engine.m4_media_grounding import (
    score_media_grounded_safety_audit, blinded_media_view, MIN_IOU
)
from inspection_engine.m4_frozen_safety_audit import digest
from inspection_engine.serious_defect_benchmark import BenchmarkBlock, SYSTEMS
import test_m4_frozen_safety_audit as v8


def sha(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def photo(case_id, media_id="photo-001", *, review="reviewed"):
    return {
        "case_id":case_id,"media_id":media_id,
        "sha256":sha("SYNTHETIC_ORIGINAL_"+case_id+"_"+media_id),
        "kind":"photo","parent_video_sha256":None,"frame_time_ms":None,
        "review_status":review,"area":"Electrical wall",
    }


def region(cid, ref, media, *, bbox=None):
    return {
        "case_id":cid,"reference_id":ref,"media_id":media["media_id"],
        "source_media_sha256":media["sha256"],
        "bbox":[.2,.2,.4,.4] if bbox is None else bbox,
    }


class MediaGroundingTests(unittest.TestCase):
    def setUp(self):
        self.base=v8.FrozenSafetyAuditTests("test_single_synthetic_case_does_not_meet_cohort_and_never_releases")
        self.base.setUp()
        cid=self.base.cases[0]["case_id"]
        self.media=[photo(cid)]
        self.p_regions=[region(cid,"prediction-001",self.media[0])]
        self.l_regions=[region(cid,"label-001",self.media[0])]
        self.seal()

    def seal(self):
        for case in self.base.cases:
            members=sorted(
                [r for r in self.media if r["case_id"]==case["case_id"]],
                key=lambda r:r["media_id"]
            )
            case["media_manifest_sha256"]=digest(members)
        self.media.sort(key=lambda r:(r["case_id"],r["media_id"]))
        self.base.reseal()
        self.grounding={
            "schema_version":1,
            "evaluation_id":self.base.model["evaluation_id"],
            "model_snapshot_sha256":digest(self.base.model),
            "media_manifest_sha256":digest(self.media),
            "prediction_regions_sha256":digest(self.p_regions),
            "blinded_media_view_sha256":digest(blinded_media_view(self.media)),
            "frozen_at_utc":self.base.model["generated_at_utc"],
            "customer_release_allowed":False
        }

    def score(self,**overrides):
        return score_media_grounded_safety_audit(
            self.base.cases,self.base.predictions,self.base.matches,
            self.base.model,self.base.adjudication,self.base.training,
            self.media,self.p_regions,self.l_regions,self.grounding,
            independent_case_pin_sha256=overrides.get("case",digest(self.base.cases)),
            independent_model_snapshot_pin_sha256=overrides.get("model",digest(self.base.model)),
            independent_adjudication_pin_sha256=overrides.get("adjudication",digest(self.base.adjudication)),
            independent_training_index_pin_sha256=overrides.get("training",digest(self.base.training)),
            independent_media_manifest_pin_sha256=overrides.get("media",digest(self.media)),
            independent_prediction_regions_pin_sha256=overrides.get("pred_regions",digest(self.p_regions)),
            independent_label_regions_pin_sha256=overrides.get("label_regions",digest(self.l_regions)),
            independent_grounding_snapshot_pin_sha256=overrides.get("grounding",digest(self.grounding)),
        )

    def test_one_photo_localized_defect_passes_geometry_but_not_cohort(self):
        result=self.score()
        self.assertEqual(len(result["matched_photo_or_frame_iou"]),1)
        self.assertEqual(result["matched_photo_or_frame_iou"][0],1)
        self.assertFalse(result["negative_controls_minimum_met"])
        self.assertFalse(result["media_grounded_metric_thresholds_met_only"])
        self.assertFalse(result["actual_source_bytes_independently_rehashed"])
        self.assertFalse(result["real_photo_or_video_contents_professionally_validated"])
        self.assertFalse(result["customer_release_allowed"])

    def test_label_metadata_does_not_appear_in_blinded_media_view(self):
        view=blinded_media_view(self.media)
        self.assertEqual(len(view),1)
        self.assertNotIn("review_status",view[0])
        self.assertNotIn("labels",view[0])
        self.assertNotIn("adjudicator_id",view[0])

    def test_wrong_photo_same_case_cannot_match(self):
        other=photo(self.base.cases[0]["case_id"],"photo-002",review="reviewed_no_defect")
        self.media.append(other)
        self.p_regions[0]=region(other["case_id"],"prediction-001",other)
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"Wrong original photo"):
            self.score()

    def test_wrong_bbox_same_photo_cannot_match(self):
        self.p_regions[0]["bbox"]=[.7,.7,.9,.9]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"does not overlap"):
            self.score()

    def test_partial_overlap_below_quarter_threshold_fails(self):
        self.p_regions[0]["bbox"]=[.35,.35,.55,.55]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"does not overlap"):
            self.score()

    def test_partial_overlap_above_threshold_accepted(self):
        self.p_regions[0]["bbox"]=[.25,.2,.45,.4]
        self.seal()
        r=self.score()
        self.assertTrue(r["matched_photo_or_frame_iou"][0]>=MIN_IOU)

    def test_wrong_source_hash_in_prediction_region_rejected(self):
        self.p_regions[0]["source_media_sha256"]=sha("wrong-photo")
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"source-media SHA256 mismatch"):
            self.score()

    def test_wrong_source_hash_in_human_label_rejected(self):
        self.l_regions[0]["source_media_sha256"]=sha("wrong-label")
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"source-media SHA256 mismatch"):
            self.score()

    def test_deleted_model_media_localization_blocks(self):
        self.p_regions=[]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"exactly one media-level"):
            self.score()

    def test_deleted_human_label_media_localization_blocks(self):
        self.l_regions=[]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"exactly one media-level"):
            self.score()

    def test_duplicate_region_for_a_prediction_rejected(self):
        self.p_regions.append(copy.deepcopy(self.p_regions[0]))
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"Duplicate or unrecognized"):
            self.score()

    def test_unknown_original_media_id_rejected(self):
        self.p_regions[0]["media_id"]="unknown-photo"
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"original photo or declared frame"):
            self.score()

    def test_bad_coordinates_and_nan_rejected(self):
        for box in ([.4,.2,.2,.4],[0,0,2,1],[0,0,float("nan"),1],["0",0,1,1]):
            with self.subTest(box=box):
                self.p_regions[0]["bbox"]=box
                if any(type(v) is float and not math.isfinite(v) for v in box):
                    # A NaN cannot be frozen into canonical JSON. Earlier
                    # rejection is the intended fail-closed behavior.
                    with self.assertRaisesRegex(BenchmarkBlock,"Noncanonical"):
                        self.seal()
                else:
                    self.seal()
                    with self.assertRaises(BenchmarkBlock):
                        self.score()

    def test_unsorted_photo_inventory_rejected(self):
        second=photo(self.base.cases[0]["case_id"],"aaa-photo",review="reviewed_no_defect")
        self.media.append(second)
        self.seal()
        self.media.reverse()
        with self.assertRaisesRegex(BenchmarkBlock,"canonical and ordered"):
            self.score()

    def test_modified_photo_manifest_independent_pin_rejected(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Changed after independent pin: media manifest"):
            self.score(media="f"*64)

    def test_changed_pre_match_regions_independent_pin_rejected(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Changed after independent pin: prediction regions"):
            self.score(pred_regions="f"*64)

    def test_changed_human_label_regions_independent_pin_rejected(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Changed after independent pin: human label regions"):
            self.score(label_regions="f"*64)

    def test_changed_grounding_snapshot_independent_pin_rejected(self):
        with self.assertRaisesRegex(BenchmarkBlock,"Changed after independent pin: grounding snapshot"):
            self.score(grounding="f"*64)

    def test_model_grounding_snapshot_wrong_media_hash_rejected(self):
        self.grounding["media_manifest_sha256"]="f"*64
        with self.assertRaisesRegex(BenchmarkBlock,"not frozen with model"):
            self.score()

    def test_model_grounding_snapshot_wrong_prediction_hash_rejected(self):
        self.grounding["prediction_regions_sha256"]="f"*64
        with self.assertRaisesRegex(BenchmarkBlock,"not frozen with model"):
            self.score()

    def test_not_inspected_photo_prevents_successful_evaluation(self):
        self.media[0]["review_status"]="not_inspected"
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"Incomplete or not-inspected media"):
            self.score()

    def test_inconclusive_photo_prevents_successful_evaluation(self):
        self.media[0]["review_status"]="inconclusive"
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"Incomplete or not-inspected media"):
            self.score()

    def test_human_label_cannot_attach_to_no_defect_control(self):
        self.media[0]["review_status"]="reviewed_no_defect"
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"No-defect control"):
            self.score()

    def test_empty_reviewed_photo_requires_explicit_negative_status(self):
        self.base.cases[0]["labels"]=[]
        self.base.predictions=[]
        self.base.matches=[]
        self.l_regions=[]
        self.p_regions=[]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"without labels"):
            self.score()

    def test_training_overlap_of_original_photo_is_rejected(self):
        self.base.training["source_digests"].append(self.media[0]["sha256"])
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"original photo or video collision"):
            self.score()

    def test_repeated_original_media_bytes_are_rejected(self):
        dup=photo(self.base.cases[0]["case_id"],"photo-002",review="reviewed_no_defect")
        dup["sha256"]=self.media[0]["sha256"]
        self.media.append(dup)
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"identical source bytes"):
            self.score()

    def test_video_frame_requires_original_video(self):
        self.media[0]["kind"]="video_frame"
        self.media[0]["parent_video_sha256"]=sha("missing-original-video")
        self.media[0]["frame_time_ms"]=700
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"lacks matching original-video"):
            self.score()

    def test_valid_derived_video_frame_maps_to_original_video(self):
        cid=self.base.cases[0]["case_id"]
        parent={
            "case_id":cid,"media_id":"video-001","sha256":sha("video-parent-"+cid),
            "kind":"video","parent_video_sha256":None,"frame_time_ms":None,
            "review_status":"source_only","area":"Roof video"
        }
        frame={
            "case_id":cid,"media_id":"frame-001","sha256":sha("frame-source-"+cid),
            "kind":"video_frame","parent_video_sha256":parent["sha256"],
            "frame_time_ms":1000,"review_status":"reviewed","area":"Roof video"
        }
        self.media=[frame,parent]
        self.p_regions=[region(cid,"prediction-001",frame)]
        self.l_regions=[region(cid,"label-001",frame)]
        self.seal()
        result=self.score()
        self.assertEqual(result["matched_photo_or_frame_iou"],[1])
        self.assertFalse(result["customer_release_allowed"])

    def test_predicted_video_frame_wrong_timestamp_is_rejected(self):
        cid=self.base.cases[0]["case_id"]
        parent={
            "case_id":cid,"media_id":"video-001","sha256":sha("video-parent-"+cid),
            "kind":"video","parent_video_sha256":None,"frame_time_ms":None,
            "review_status":"source_only","area":"Roof video"
        }
        frame={
            "case_id":cid,"media_id":"frame-001","sha256":sha("frame-source-"+cid),
            "kind":"video_frame","parent_video_sha256":parent["sha256"],
            "frame_time_ms":-1,"review_status":"reviewed","area":"Roof video"
        }
        self.media=[frame,parent]
        self.p_regions=[region(cid,"prediction-001",frame)]
        self.l_regions=[region(cid,"label-001",frame)]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"timestamp invalid"):
            self.score()

    def test_wrong_frame_same_original_video_cannot_match(self):
        cid=self.base.cases[0]["case_id"]
        parent={
            "case_id":cid,"media_id":"video-001","sha256":sha("original-"+cid),
            "kind":"video","parent_video_sha256":None,"frame_time_ms":None,
            "review_status":"source_only","area":"Roof video"
        }
        frame=photo(cid,"frame-001")
        frame.update({"kind":"video_frame","parent_video_sha256":parent["sha256"],
                      "frame_time_ms":1000})
        later=photo(cid,"frame-002",review="reviewed_no_defect")
        later.update({"kind":"video_frame","parent_video_sha256":parent["sha256"],
                      "frame_time_ms":3000})
        self.media=[parent,frame,later]
        self.l_regions=[region(cid,"label-001",frame)]
        self.p_regions=[region(cid,"prediction-001",later)]
        self.seal()
        with self.assertRaisesRegex(BenchmarkBlock,"wrong video frame"):
            self.score()

    def test_original_video_cannot_serve_as_normalized_still(self):
        cid=self.base.cases[0]["case_id"]
        self.media[0]["kind"]="video"
        self.media[0]["review_status"]="source_only"
        self.seal()
        with self.assertRaises(BenchmarkBlock):
            self.score()

    def _hundred_case_fixture(self, *, negative: int, false_alarm=False):
        systems=sorted(SYSTEMS)
        self.base.cases=[]
        self.base.predictions=[]
        self.base.matches=[]
        self.media=[]
        self.p_regions=[]
        self.l_regions=[]
        for i in range(100):
            idx=i+1
            c=v8.synthetic_case(idx,
                severity="critical" if i<30 else "moderate",
                system=systems[i%len(systems)],
                scope="commercial" if i%2 else "residential")
            is_negative=i>=100-negative
            if is_negative:c["labels"]=[]
            self.base.cases.append(c)
            m=photo(c["case_id"],review="reviewed_no_defect" if is_negative else "reviewed")
            self.media.append(m)
            if not is_negative:
                p=v8.prediction(c)
                self.base.predictions.append(p)
                self.base.matches.append(v8.matched(c))
                self.p_regions.append(region(c["case_id"],p["prediction_id"],m))
                self.l_regions.append(region(c["case_id"],"label-001",m))
        if false_alarm:
            last=self.base.cases[-1]
            p={"case_id":last["case_id"],"prediction_id":"false-alarm-001",
               "system":"electrical","source_evidence_sha256":last["evidence_sha256"]}
            self.base.predictions.append(p)
            self.base.matches.append({
                "case_id":last["case_id"],"prediction_id":p["prediction_id"],
                "adjudicator_id":last["independent_adjudicator_id"],
                "disposition":"false_positive","matched_label_id":None,
                "reason":"Synthetic false alarm on independently adjudicated clean control"
            })
            self.p_regions.append(region(last["case_id"],p["prediction_id"],self.media[-1]))
        self.seal()

    def test_100_case_synthetic_with_10_clean_controls_can_meet_metrics_not_release(self):
        self._hundred_case_fixture(negative=10)
        r=self.score()
        self.assertEqual(r["negative_control_case_count"],10)
        self.assertEqual(r["reviewed_no_defect_media_count"],10)
        self.assertEqual(r["v8_audit"]["serious_defect_score"]["critical_defects"],30)
        self.assertTrue(r["media_grounded_metric_thresholds_met_only"])
        self.assertFalse(r["customer_release_allowed"])
        self.assertFalse(r["v8_audit"]["customer_release_allowed"])

    def test_nine_clean_controls_fail_media_grounded_threshold(self):
        self._hundred_case_fixture(negative=9)
        r=self.score()
        self.assertTrue(r["v8_audit"]["metric_thresholds_met_only"])
        self.assertFalse(r["negative_controls_minimum_met"])
        self.assertFalse(r["media_grounded_metric_thresholds_met_only"])

    def test_clean_control_false_alarm_never_passes_grounded_threshold(self):
        self._hundred_case_fixture(negative=10,false_alarm=True)
        r=self.score()
        self.assertTrue(r["v8_audit"]["metric_thresholds_met_only"])
        self.assertEqual(r["negative_control_false_alarms"],1)
        self.assertFalse(r["media_grounded_metric_thresholds_met_only"])
        self.assertEqual(r["v8_audit"]["false_positives"],1)

    def test_clean_photo_false_alarm_on_otherwise_defective_property_blocks(self):
        self._hundred_case_fixture(negative=10)
        case=self.base.cases[0]   # Has a correctly detected critical defect.
        clean=photo(case["case_id"],"photo-002",review="reviewed_no_defect")
        self.media.append(clean)
        pid="false-alarm-other-clean-photo"
        self.base.predictions.append({
            "case_id":case["case_id"],"prediction_id":pid,"system":"electrical",
            "source_evidence_sha256":case["evidence_sha256"]
        })
        self.base.matches.append({
            "case_id":case["case_id"],"prediction_id":pid,
            "adjudicator_id":case["independent_adjudicator_id"],
            "disposition":"false_positive","matched_label_id":None,
            "reason":"Synthetic false alarm on a reviewed clear photo at a property with real defects"
        })
        self.p_regions.append(region(case["case_id"],pid,clean))
        self.seal()
        result=self.score()
        self.assertTrue(result["v8_audit"]["metric_thresholds_met_only"])
        self.assertEqual(result["negative_control_false_alarms"],1)
        self.assertFalse(result["media_grounded_metric_thresholds_met_only"])
        self.assertFalse(result["customer_release_allowed"])

    def test_critical_miss_even_with_clean_controls_blocks(self):
        self._hundred_case_fixture(negative=10)
        self.base.matches[0]=v8.matched(self.base.cases[0],disposition="inconclusive")
        self.seal()
        r=self.score()
        self.assertEqual(len(r["v8_audit"]["serious_defect_score"]["critical_misses"]),1)
        self.assertFalse(r["media_grounded_metric_thresholds_met_only"])


if __name__ == "__main__":
    unittest.main()
