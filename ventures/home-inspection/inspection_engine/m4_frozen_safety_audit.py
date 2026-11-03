"""M4 V8 frozen, blinded serious-defect evaluation audit — private, no release.

This builds on the existing serious_defect_benchmark (100 real, consented
holdout cases; 30 critical defects; all 13 systems; both property scopes; no
major/critical miss; >=95% verified precision). It adds evidence/corpus
fingerprints, model-output sealing, mandatory post-freeze adjudication for
every prediction and exact training/holdout source-group collision checks.

Externally supplied digests and declared professionals are not independent
proof of custody, identities, model blindness, or real-world ground truth.
The audit NEVER trains, authorizes a model, approves a report or releases data.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from .core import DataError
from .serious_defect_benchmark import (
    validate_real_holdout, score_serious_defects, SYSTEMS, BenchmarkBlock
)

HEX = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,99}\Z")
UTC = re.compile(r"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z")
MAX_CASES = 2000
MAX_PREDICTIONS = 20000


def digest(value: object) -> str:
    try:
        raw=json.dumps(value,sort_keys=True,ensure_ascii=True,
                       separators=(",",":"),allow_nan=False).encode("ascii")
    except (ValueError,TypeError,UnicodeError) as exc:
        raise BenchmarkBlock("Noncanonical safety benchmark JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _hex(value: object, label: str) -> str:
    if not isinstance(value,str) or HEX.fullmatch(value) is None:
        raise BenchmarkBlock("Missing/invalid SHA256: "+label)
    return value


def _ident(value: object, label: str) -> str:
    if not isinstance(value,str) or IDENT.fullmatch(value) is None:
        raise BenchmarkBlock("Malformed ID: "+label)
    return value


def _time(value: object, label: str) -> datetime:
    if not isinstance(value,str) or UTC.fullmatch(value) is None:
        raise BenchmarkBlock("Canonical UTC timestamp required: "+label)
    try:
        result=datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise BenchmarkBlock("Invalid UTC timestamp: "+label) from exc
    return result


def _keys(record: object, expected: set[str], context: str) -> dict:
    if not isinstance(record,dict) or set(record)!=expected:
        raise BenchmarkBlock("Invalid "+context+" schema")
    return record


def _index(values: object, label: str, *, sha: bool=False) -> set[str]:
    if not isinstance(values,list) or len(values)>MAX_PREDICTIONS:
        raise BenchmarkBlock("Invalid "+label+" index")
    seen=set()
    for value in values:
        if sha:_hex(value,label)
        else:_ident(value,label)
        if value in seen:
            raise BenchmarkBlock("Duplicate "+label+" entry")
        seen.add(value)
    return seen


def score_frozen_safety_audit(
    cases: list[dict],
    model_predictions: list[dict],
    human_matches: list[dict],
    model_snapshot: dict,
    adjudication_snapshot: dict,
    training_index: dict, *,
    independent_case_pin_sha256: str,
    independent_model_snapshot_pin_sha256: str,
    independent_adjudication_pin_sha256: str,
    independent_training_index_pin_sha256: str,
) -> dict:
    """Return metrics and exact missing evidence with release hard-disabled.

    The four external digest pins MUST be independently recorded BEFORE they
    are used as trust evidence; passing a digest calculated from the same file
    during this call does not provide independent validation.
    """
    if not isinstance(cases,list) or not 1<=len(cases)<=MAX_CASES:
        raise BenchmarkBlock("Bounded, nonempty holdout cases required")
    if not isinstance(model_predictions,list) or len(model_predictions)>MAX_PREDICTIONS:
        raise BenchmarkBlock("Bounded model prediction list required")
    if not isinstance(human_matches,list) or len(human_matches)>MAX_PREDICTIONS:
        raise BenchmarkBlock("Bounded independent match list required")

    case_pin=_hex(independent_case_pin_sha256,"external case pin")
    model_pin=_hex(independent_model_snapshot_pin_sha256,"external prediction pin")
    adjudication_pin=_hex(independent_adjudication_pin_sha256,"external match pin")
    training_pin=_hex(independent_training_index_pin_sha256,"external training pin")
    if digest(cases)!=case_pin:
        raise BenchmarkBlock("Holdout case manifest changed after independent pin")
    if digest(model_snapshot)!=model_pin:
        raise BenchmarkBlock("Frozen model snapshot differs from independent pin")
    if digest(adjudication_snapshot)!=adjudication_pin:
        raise BenchmarkBlock("Independent adjudication snapshot differs from pin")
    if digest(training_index)!=training_pin:
        raise BenchmarkBlock("Training exclusion registry differs from independent pin")

    _keys(training_index,
          {"schema_version","model_sha256","source_digests","source_group_ids",
           "registry_scope","customer_release_allowed"},"training exclusion registry")
    if (training_index["schema_version"]!=1
        or training_index["registry_scope"]!="ALL_KNOWN_TRAINING_AND_TUNING_SOURCES"
        or training_index["customer_release_allowed"] is not False):
        raise BenchmarkBlock("Incomplete training or tuning exclusion registry")
    training_model=_hex(training_index["model_sha256"],"training model")
    training_hashes=_index(training_index["source_digests"],"training source",sha=True)
    training_groups=_index(training_index["source_group_ids"],"training source group")

    # Existing policy validates explicit consent, locked holdout, dual distinct
    # human reviewers and all accepted one-to-one label matches. Before that,
    # enforce additional evidence-binding for *all* predicted concerns.
    cases_by_id={}
    source_hashes=set()
    source_groups=set()
    for case in cases:
        if not isinstance(case,dict):
            raise BenchmarkBlock("Holdout case must be a record")
        case_id=_ident(case.get("case_id"),"holdout case")
        group=_ident(case.get("source_group_id"),"property/collection leakage group")
        sha=_hex(case.get("evidence_sha256"),"holdout original evidence")
        if case_id in cases_by_id or sha in source_hashes or group in source_groups:
            raise BenchmarkBlock("Duplicate holdout case/source/property group")
        if sha in training_hashes or group in training_groups:
            raise BenchmarkBlock("Training/holdout source collision detected")
        cases_by_id[case_id]=case
        source_hashes.add(sha)
        source_groups.add(group)

    _keys(model_snapshot,
          {"schema_version","evaluation_id","model_id","model_sha256","prompt_sha256",
           "generated_at_utc","case_manifest_sha256","training_index_sha256",
           "predictions_sha256","blinded_to_labels_declared","customer_release_allowed"},
          "frozen model snapshot")
    if (model_snapshot["schema_version"]!=1
        or model_snapshot["customer_release_allowed"] is not False
        or model_snapshot["blinded_to_labels_declared"] is not True):
        raise BenchmarkBlock("Explicit blind model snapshot required")
    eval_id=_ident(model_snapshot["evaluation_id"],"evaluation run")
    _ident(model_snapshot["model_id"],"model ID")
    model_hash=_hex(model_snapshot["model_sha256"],"model artifact")
    _hex(model_snapshot["prompt_sha256"],"prompt receipt")
    model_time=_time(model_snapshot["generated_at_utc"],"model freeze")
    if (model_hash!=training_model
        or model_snapshot["case_manifest_sha256"]!=digest(cases)
        or model_snapshot["training_index_sha256"]!=digest(training_index)
        or model_snapshot["predictions_sha256"]!=digest(model_predictions)):
        raise BenchmarkBlock("Predictions not bound to frozen model, cohort or training exclusion")

    prediction_keys=set()
    for row in model_predictions:
        _keys(row,{"case_id","prediction_id","system","source_evidence_sha256"},
              "pre-review model prediction")
        key=(_ident(row["case_id"],"prediction case"),
             _ident(row["prediction_id"],"prediction"))
        case=cases_by_id.get(key[0])
        if case is None or key in prediction_keys:
            raise BenchmarkBlock("Model prediction missing case or repeated ID")
        if row["system"] not in SYSTEMS:
            raise BenchmarkBlock("Unknown predicted inspection system")
        if row["source_evidence_sha256"]!=case["evidence_sha256"]:
            raise BenchmarkBlock("Prediction not grounded to exact source evidence")
        prediction_keys.add(key)

    _keys(adjudication_snapshot,
          {"schema_version","evaluation_id","case_manifest_sha256",
           "model_snapshot_sha256","matches_sha256","adjudicated_at_utc",
           "reviewer_independent_of_model_declared","customer_release_allowed"},
          "match adjudication snapshot")
    if (adjudication_snapshot["schema_version"]!=1
        or adjudication_snapshot["customer_release_allowed"] is not False
        or adjudication_snapshot["reviewer_independent_of_model_declared"] is not True
        or adjudication_snapshot["evaluation_id"]!=eval_id
        or adjudication_snapshot["case_manifest_sha256"]!=digest(cases)
        or adjudication_snapshot["model_snapshot_sha256"]!=digest(model_snapshot)
        or adjudication_snapshot["matches_sha256"]!=digest(human_matches)):
        raise BenchmarkBlock("Post-freeze adjudication not bound to exact model/case/matches")
    if _time(adjudication_snapshot["adjudicated_at_utc"],"adjudication")<=model_time:
        raise BenchmarkBlock("Human matching must occur strictly after frozen predictions")

    seen=set()
    claimed_labels=set()
    detection_rows=[]
    label_by_key={(c["case_id"],l.get("label_id")):l for c in cases for l in c.get("labels",[])}
    for row in human_matches:
        _keys(row,{"case_id","prediction_id","adjudicator_id","disposition",
                   "matched_label_id","reason"},"independent match")
        key=(_ident(row["case_id"],"matching case"),
             _ident(row["prediction_id"],"matching prediction"))
        if key in seen or key not in prediction_keys:
            raise BenchmarkBlock("Unrecognized/duplicate model prediction adjudication")
        seen.add(key)
        case=cases_by_id[key[0]]
        if row["adjudicator_id"]!=case.get("independent_adjudicator_id"):
            raise BenchmarkBlock("Match reviewer differs from independent case adjudicator")
        if (not isinstance(row["reason"],str)
            or not 16<=len(row["reason"].strip())<=1500):
            raise BenchmarkBlock("Every match disposition needs substantive reason")
        disp=row["disposition"]
        if disp not in ("matched","false_positive","inconclusive"):
            raise BenchmarkBlock("Unrecognized match disposition")
        lid=row["matched_label_id"]
        if disp=="matched":
            lk=(key[0],lid)
            if (not isinstance(lid,str) or lk not in label_by_key
                or lk in claimed_labels):
                raise BenchmarkBlock("Accepted label is nonexistent or matched multiple times")
            claimed_labels.add(lk)
        elif lid is not None:
            raise BenchmarkBlock("Unmatched/inconclusive predictions cannot claim a true label")
        pred=next(p for p in model_predictions if p["case_id"]==key[0] and p["prediction_id"]==key[1])
        if disp=="matched" and pred["system"]!=label_by_key[(key[0],lid)]["system"]:
            raise BenchmarkBlock("Wrong-system label match not accepted")
        detection_rows.append({
            "case_id":key[0],"prediction_id":key[1],"system":pred["system"],
            "matched_label_id":lid,"human_match_verified":disp=="matched"
        })
    if seen!=prediction_keys:
        raise BenchmarkBlock("Every frozen prediction needs explicit human disposition")
    # This is deterministic once matched rows are frozen, without resolving
    # ambiguous free-text claims on the model's behalf.
    validate_real_holdout(cases,detection_rows)
    result=score_serious_defects(cases,detection_rows)
    system_totals={}
    for system in sorted(SYSTEMS):
        r=result["per_system"].get(system,{"total":0,"detected":0,
                                         "critical":0,"critical_missed":0})
        system_totals[system]={
            "reviewed_defects":r["total"],
            "matched":r["detected"],
            "missed":r["total"]-r["detected"],
            "critical":r["critical"],
            "critical_missed":r["critical_missed"],
            "recall":round(r["detected"]/r["total"],4) if r["total"] else None
        }
    return {
        "schema_version":1,
        "status":"FROZEN_EVALUATION_METRICS_ONLY_NOT_PRODUCTION_APPROVAL",
        "evaluation_id":eval_id,"model_artifact_sha256":model_hash,
        "case_manifest_sha256":digest(cases),
        "frozen_prediction_sha256":digest(model_snapshot),
        "independent_match_snapshot_sha256":digest(adjudication_snapshot),
        "training_index_sha256":digest(training_index),
        "prediction_count":len(model_predictions),
        "adjudicated_predictions":len(human_matches),
        "false_positives":len(result["unmatched_or_unverified_predictions"]),
        "inconclusive_count":sum(x["disposition"]=="inconclusive" for x in human_matches),
        "serious_defect_score":result,
        "per_system":system_totals,
        "metric_thresholds_met_only":result["metric_thresholds_met"],
        "real_world_case_consent_independently_verified":False,
        "human_professional_credentials_independently_verified":False,
        "prediction_freeze_timestamp_independently_verified":False,
        "external_pin_origin_independently_verified":False,
        "model_never_saw_labels_independently_proven":False,
        "training_data_coverage_and_near_duplicates_verified":False,
        "qualified_inspector_release_authority":False,
        "customer_release_allowed":False
    }
