"""M4 V9 — media-level ground truth and model prediction localization.

Strict additive layer over V8's 100-case serious-defect evaluator. Every
adjudicated label and every pre-review prediction is tied to a specific
source photo or video frame and a normalized region. Wrong photo, wrong
frame or non-overlapping region cannot be accepted as a true positive.

Hash pins, source media and professional-review identities are DECLARED
locally; no independent field verification, real-case consent or production
release is inferred. No model inference or network activity occurs.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import math

from .serious_defect_benchmark import BenchmarkBlock
from .m4_frozen_safety_audit import (
    score_frozen_safety_audit, blinded_evidence_view, digest, _hex, _ident,
    _time, _keys, MAX_CASES, MAX_PREDICTIONS
)

MEDIA_FIELDS = {"case_id", "media_id", "sha256", "kind", "parent_video_sha256",
                "frame_time_ms", "review_status", "area"}
REGION_FIELDS = {"case_id", "reference_id", "media_id", "source_media_sha256", "bbox"}
GROUNDING_FIELDS = {"schema_version", "evaluation_id", "model_snapshot_sha256",
                    "media_manifest_sha256", "prediction_regions_sha256",
                    "blinded_media_view_sha256", "frozen_at_utc",
                    "customer_release_allowed"}
KINDS = {"photo", "video", "video_frame"}
IMAGE_STATUSES = {"reviewed", "reviewed_no_defect", "inconclusive", "not_inspected"}
MAX_MEDIA = 50000
MIN_IOU = 0.25
MIN_NEGATIVE_CASES = 10
MIN_NEGATIVE_MEDIA = 10


def _bbox(value: object) -> tuple[float, float, float, float]:
    if (not isinstance(value, list) or len(value) != 4 or
        any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise BenchmarkBlock("Evidence localization needs four finite coordinates")
    x0, y0, x1, y1 = (float(v) for v in value)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise BenchmarkBlock("Evidence localization outside normalized photo/frame")
    return x0, y0, x1, y1


def _iou(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    left, top, right, bottom = (
        max(first[0], second[0]), max(first[1], second[1]),
        min(first[2], second[2]), min(first[3], second[3])
    )
    overlap = max(0, right-left) * max(0, bottom-top)
    aa = (first[2]-first[0])*(first[3]-first[1])
    bb = (second[2]-second[0])*(second[3]-second[1])
    return overlap/(aa+bb-overlap) if aa+bb>overlap else 0.0


def blinded_media_view(media_manifest: list[dict]) -> list[dict]:
    """No defect labels, reviewer dispositions or credential data."""
    if not isinstance(media_manifest, list):
        raise BenchmarkBlock("Media manifest must be a list")
    return [
        {name: item[name] for name in (
            "case_id", "media_id", "sha256", "kind", "parent_video_sha256",
            "frame_time_ms", "area")}
        for item in media_manifest
    ]


def _validate_media(cases: list[dict], media_manifest: list[dict],
                    training_index: dict) -> tuple[dict, dict, int, int]:
    if not isinstance(media_manifest, list) or not 1 <= len(media_manifest) <= MAX_MEDIA:
        raise BenchmarkBlock("Bounded source media manifest required")
    case_by_id = {_ident(case["case_id"], "media case"): case for case in cases}
    if len(case_by_id) != len(cases):
        raise BenchmarkBlock("Duplicate case IDs in media audit")
    media_by_key = {}
    by_case = defaultdict(list)
    used_hashes = set()
    for row in media_manifest:
        _keys(row, MEDIA_FIELDS, "source media")
        cid = _ident(row["case_id"], "media case")
        mid = _ident(row["media_id"], "original media ID")
        sh = _hex(row["sha256"], "original media bytes")
        kind = row["kind"]
        if cid not in case_by_id or kind not in KINDS:
            raise BenchmarkBlock("Unknown media case or source type")
        key = (cid, mid)
        if key in media_by_key or sh in used_hashes:
            raise BenchmarkBlock("Duplicate media ID or identical source bytes")
        used_hashes.add(sh)
        if sh in training_index["source_digests"]:
            raise BenchmarkBlock("Training/holdout original photo or video collision")
        if (not isinstance(row["area"], str) or not 3 <= len(row["area"].strip()) <= 100):
            raise BenchmarkBlock("Missing source media inspection area")
        parent = row["parent_video_sha256"]
        ms = row["frame_time_ms"]
        if kind == "video_frame":
            _hex(parent, "original parent video SHA256")
            if type(ms) is not int or not 0 <= ms <= 2*60*60*1000:
                raise BenchmarkBlock("Video frame timestamp invalid")
        elif parent is not None or ms is not None:
            raise BenchmarkBlock("Only derived video frames may have a video parent/timestamp")
        if kind == "video":
            if row["review_status"] != "source_only":
                raise BenchmarkBlock("Original video must be source-only; evaluate exact frames")
        elif row["review_status"] not in IMAGE_STATUSES:
            raise BenchmarkBlock("Unsupported original photo/frame evidence status")
        media_by_key[key] = row
        by_case[cid].append(row)
    if media_manifest != sorted(media_manifest, key=lambda r:(r["case_id"],r["media_id"])):
        raise BenchmarkBlock("Media manifest must be canonical and ordered")
    for cid, case in case_by_id.items():
        rows = sorted(by_case[cid],key=lambda r:r["media_id"])
        if not any(r["kind"] != "video" for r in rows):
            raise BenchmarkBlock("Every held-out case needs reviewed image/frame evidence")
        if case.get("media_manifest_sha256") != digest(rows):
            raise BenchmarkBlock("Original media not bound to independently frozen case manifest")
        video_hashes = {r["sha256"] for r in rows if r["kind"]=="video"}
        for r in rows:
            if r["kind"]=="video_frame" and r["parent_video_sha256"] not in video_hashes:
                raise BenchmarkBlock("Video frame lacks matching original-video source")
    incomplete = [(r["case_id"],r["media_id"]) for r in media_manifest
                  if r["review_status"] in {"inconclusive","not_inspected"}]
    if incomplete:
        raise BenchmarkBlock("Incomplete or not-inspected media blocks serious-defect acceptance")
    reviewed = sum(r["review_status"]=="reviewed" for r in media_manifest)
    negatives = sum(r["review_status"]=="reviewed_no_defect" for r in media_manifest)
    return media_by_key, by_case, reviewed, negatives


def _regions(rows: list[dict], media_by_key: dict, *, expected: set,
             kind: str) -> dict:
    if not isinstance(rows, list) or len(rows) > MAX_PREDICTIONS:
        raise BenchmarkBlock("Invalid bounded " + kind + " localizations")
    found = {}
    for row in rows:
        _keys(row, REGION_FIELDS, kind + " localization")
        key = (_ident(row["case_id"], kind+" case"),
               _ident(row["reference_id"], kind+" reference"))
        media_key = (key[0], _ident(row["media_id"], kind+" media"))
        media = media_by_key.get(media_key)
        if key in found or key not in expected:
            raise BenchmarkBlock("Duplicate or unrecognized " + kind + " localization")
        if media is None or media["kind"] == "video":
            raise BenchmarkBlock(kind+" must reference an original photo or declared frame")
        if row["source_media_sha256"] != media["sha256"]:
            raise BenchmarkBlock(kind+" source-media SHA256 mismatch")
        if media["review_status"] not in ("reviewed","reviewed_no_defect"):
            raise BenchmarkBlock("Unreviewed media cannot support scored findings")
        found[key] = (media_key, _bbox(row["bbox"]))
    if set(found) != expected:
        raise BenchmarkBlock("Every " + kind + " needs exactly one media-level localization")
    return found


def score_media_grounded_safety_audit(
    cases: list[dict],
    predictions: list[dict],
    human_matches: list[dict],
    model_snapshot: dict,
    adjudication_snapshot: dict,
    training_index: dict,
    media_manifest: list[dict],
    prediction_regions: list[dict],
    label_regions: list[dict],
    grounding_snapshot: dict, *,
    independent_case_pin_sha256: str,
    independent_model_snapshot_pin_sha256: str,
    independent_adjudication_pin_sha256: str,
    independent_training_index_pin_sha256: str,
    independent_media_manifest_pin_sha256: str,
    independent_prediction_regions_pin_sha256: str,
    independent_label_regions_pin_sha256: str,
    independent_grounding_snapshot_pin_sha256: str
) -> dict:
    """Fail closed when a human-accepted claim lacks original media agreement."""
    for label, supplied, value in (
        ("media manifest",independent_media_manifest_pin_sha256,media_manifest),
        ("prediction regions",independent_prediction_regions_pin_sha256,prediction_regions),
        ("human label regions",independent_label_regions_pin_sha256,label_regions),
        ("grounding snapshot",independent_grounding_snapshot_pin_sha256,grounding_snapshot)
    ):
        if digest(value) != _hex(supplied, "independent "+label+" pin"):
            raise BenchmarkBlock("Changed after independent pin: "+label)

    media_by_key, by_case, reviewed, negative_count = _validate_media(
        cases,media_manifest,training_index
    )
    expected_preds = {(p["case_id"],p["prediction_id"]) for p in predictions}
    expected_labels = {(c["case_id"],l["label_id"])
                       for c in cases for l in c["labels"]}
    preds_by_key = _regions(prediction_regions,media_by_key,
                            expected=expected_preds,kind="model prediction")
    labels_by_key = _regions(label_regions,media_by_key,
                             expected=expected_labels,kind="human label")
    for key,(med,_box) in labels_by_key.items():
        if media_by_key[med]["review_status"] != "reviewed":
            raise BenchmarkBlock("No-defect control cannot contain an adjudicated defect")
    for row in media_manifest:
        if row["review_status"]=="reviewed" and not any(
            loc[0]==(row["case_id"],row["media_id"]) for loc in labels_by_key.values()
        ):
            raise BenchmarkBlock("Reviewed media without labels must be declared a negative control")

    _keys(grounding_snapshot,GROUNDING_FIELDS,"pre-review media grounding snapshot")
    if (grounding_snapshot["schema_version"] != 1
        or grounding_snapshot["customer_release_allowed"] is not False
        or grounding_snapshot["evaluation_id"] != model_snapshot.get("evaluation_id")
        or grounding_snapshot["model_snapshot_sha256"] != digest(model_snapshot)
        or grounding_snapshot["media_manifest_sha256"] != digest(media_manifest)
        or grounding_snapshot["prediction_regions_sha256"] != digest(prediction_regions)
        or grounding_snapshot["blinded_media_view_sha256"] != digest(blinded_media_view(media_manifest))
        or grounding_snapshot["frozen_at_utc"] != model_snapshot.get("generated_at_utc")):
        raise BenchmarkBlock("Pre-review source photo/frame grounding not frozen with model")
    if _time(adjudication_snapshot["adjudicated_at_utc"],"adjudication") <= _time(
        grounding_snapshot["frozen_at_utc"],"grounding freeze"
    ):
        raise BenchmarkBlock("Media predictions must be frozen before human adjudication")

    actual_iou=[]
    for match in human_matches:
        if match["disposition"] != "matched":
            continue
        predkey = (match["case_id"], match["prediction_id"])
        labelkey = (match["case_id"], match["matched_label_id"])
        if predkey not in preds_by_key or labelkey not in labels_by_key:
            raise BenchmarkBlock("Accepted match has no complete media-level evidence")
        pred_media,pred_bbox = preds_by_key[predkey]
        label_media,label_bbox = labels_by_key[labelkey]
        if pred_media != label_media:
            raise BenchmarkBlock("Wrong original photo or wrong video frame cannot count as detected defect")
        overlap = _iou(pred_bbox,label_bbox)
        if overlap < MIN_IOU:
            raise BenchmarkBlock("Predicted region does not overlap adjudicated defect region")
        actual_iou.append(round(overlap,4))

    # V8 remains the authority for serious misses, precision, blind match
    # disposition, and all existing conservative cohort thresholds.
    result=score_frozen_safety_audit(
        cases,predictions,human_matches,model_snapshot,adjudication_snapshot,
        training_index,
        independent_case_pin_sha256=independent_case_pin_sha256,
        independent_model_snapshot_pin_sha256=independent_model_snapshot_pin_sha256,
        independent_adjudication_pin_sha256=independent_adjudication_pin_sha256,
        independent_training_index_pin_sha256=independent_training_index_pin_sha256
    )
    negative_case_count = sum(
        any(row["review_status"]=="reviewed_no_defect" for row in by_case[c["case_id"]])
        and len(c["labels"])==0
        for c in cases
    )
    has_negatives = (negative_case_count >= MIN_NEGATIVE_CASES
                     and negative_count >= MIN_NEGATIVE_MEDIA
                     and negative_case_count*10 >= len(cases))
    # Negative controls must themselves be free of model false-positive
    # proposals to meet the stricter pilot gate; false alarms are still
    # reported and scored when present, not converted into a pass.
    negative_cases = {c["case_id"] for c in cases if not c["labels"]}
    negative_false_alarms = [
        m["prediction_id"] for m in human_matches
        if m["case_id"] in negative_cases and m["disposition"] != "matched"
    ]
    grounded_pass = (result["metric_thresholds_met_only"] and has_negatives
                     and not negative_false_alarms)
    return {
        "schema_version": 1,
        "status": "SOURCE_MEDIA_GROUNDED_METRICS_ONLY_EXTERNAL_PROFESSIONAL_VALIDATION_PENDING",
        "evaluation_id": result["evaluation_id"],
        "v8_audit": result,
        "media_manifest_sha256": digest(media_manifest),
        "prediction_regions_sha256": digest(prediction_regions),
        "human_label_regions_sha256": digest(label_regions),
        "grounding_snapshot_sha256": digest(grounding_snapshot),
        "reviewed_defect_media_count": reviewed,
        "reviewed_no_defect_media_count": negative_count,
        "negative_control_case_count": negative_case_count,
        "negative_controls_minimum_met": has_negatives,
        "negative_control_false_alarms": len(negative_false_alarms),
        "matched_photo_or_frame_iou": actual_iou,
        "accepted_matches_meet_media_and_iou_threshold": True,
        "media_grounded_metric_thresholds_met_only": grounded_pass,
        "actual_source_bytes_independently_rehashed": False,
        "real_photo_or_video_contents_professionally_validated": False,
        "independent_evaluation_pins_authenticated": False,
        "qualified_inspector_authorized": False,
        "customer_release_allowed": False
    }
