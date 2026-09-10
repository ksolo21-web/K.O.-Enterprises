"""Validate navigation/presentation review evidence; never infer visual correctness."""
import re
from descriptive_access_contract import validate_review_record, validate_review_inventory


def validate_navigation_presentation(review, artifact_sha256=None, screenshot_inventory=None, entrances=None, roads=None):
    errors = []
    def check(ok, message):
        if not ok: errors.append("navigation_presentation_review: " + message)
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    if not isinstance(review, dict):
        return ["navigation_presentation_review is required"]
    digest = review.get("artifact_sha256")
    check(isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "valid final artifact_sha256 required")
    if artifact_sha256 is not None:
        check(digest == artifact_sha256, "review must bind the actual final PDF")
    full = review.get("actual_size_screenshot")
    crops = review.get("closeup_screenshots")
    check(text(full), "actual_size_screenshot required")
    check(isinstance(crops, list) and bool(crops) and all(text(x) for x in crops), "closeup_screenshots required")
    if isinstance(crops, list):
        check(full not in crops, "full-page and close-up evidence must be distinct")
    if screenshot_inventory is not None:
        check(isinstance(full,str) and bool(re.fullmatch(r"page-1-1x\.png",full)), "actual-size evidence must be a 1x full-page capture")
        check(isinstance(crops,list) and all(isinstance(x,str) and re.fullmatch(r"page-1-region-[1-6]\.png",x) for x in crops), "close-ups must use region captures")
        check(full in screenshot_inventory, "actual-size evidence must be in final capture inventory")
        check(isinstance(crops, list) and all(x in screenshot_inventory for x in crops), "close-ups must be in final capture inventory")
    e = review.get("entrances")
    if not isinstance(e, dict):
        check(False, "entrances review required")
    else:
        check(e.get("inventory_complete") is True, "complete entrance representation inventory required")
        check(text(e.get("inventory_source_evidence")), "entrance inventory source evidence required")
        records=e.get("representations")
        check(isinstance(records,list), "entrance representations list required")
        if isinstance(records,list):
            ids=[]
            if not records: check(text(e.get("no_entrances_evidence")), "empty entrance inventory requires evidence")
            for record in records:
                if not isinstance(record,dict):
                    check(False,"entrance representation must be an object");continue
                ids.append(record.get("entrance_id"))
                for key in ("entrance_id","serving_street","directions_evidence","decision_evidence"):
                    check(text(record.get(key)), "entrance " + key + " required")
                mode=record.get("representation")
                check(mode in ("named_street","feature_callout","numbered_key","descriptive_access"), "valid entrance representation required")
                if mode == "descriptive_access":
                    actual = next((x for x in entrances or [] if isinstance(x,dict) and x.get("id")==record.get("entrance_id")), None)
                    errors.extend(validate_review_record(record, artifact_sha256 or digest, actual))
                sufficient=record.get("named_street_sufficient")
                check(type(sufficient) is bool, "named_street_sufficient decision required")
                if mode == "named_street": check(sufficient is True, "named street representation must resolve access")
                if mode in ("feature_callout","numbered_key"):
                    check(sufficient is False, "redundant entrance callout/key when named streets suffice")
                if mode == "numbered_key": check(text(record.get("approval_evidence")), "numbered key requires approved necessary convention evidence")
            errors.extend(validate_review_inventory(records))
            check(all(text(x) for x in ids) and len(set(str(x) for x in ids))==len(ids), "unique entrance IDs required")
            if entrances is not None:
                valid=isinstance(entrances,list) and all(isinstance(x,dict) for x in entrances)
                check(valid,"verified entrance inventory must contain objects")
                if valid:
                    check(set(str(x) for x in ids)==set(str(x.get("id")) for x in entrances), "representations must cover every verified entrance exactly once")
                    indexed={str(x.get("id")):x for x in entrances}
                    road_names={str(x.get("id")):x.get("name") for x in roads or [] if isinstance(x,dict)}
                    for record in records:
                        if not isinstance(record,dict): continue
                        actual=indexed.get(str(record.get("entrance_id")))
                        if actual:
                            check(record.get("representation")==actual.get("representation","feature_callout"), "representation must agree with verified entrance record")
                            if roads is not None:
                                check(record.get("serving_street")==road_names.get(str(actual.get("public_road_id"))), "serving street must agree with verified public road")
    sections={
        "street_paths": (("whole_map_review_completed","views_consistent"), "unresolved_discontinuities", ("road","location","source_comparison","visual_evidence")),
        "label_placement": (("whole_map_review_completed","post_repair_review_completed"), "remaining_avoidable_placements", ("label","road","usable_run_center_assessment","southern_whitespace_assessment","chosen_position_reason","visual_evidence"))
    }
    for name,(flags,failures,fields) in sections.items():
        section=review.get(name)
        if not isinstance(section,dict):
            check(False,name+" required");continue
        for flag in flags: check(section.get(flag) is True,name+" requires "+flag)
        check(section.get(failures)==[],name+" "+failures+" must be an explicit empty list")
        records=section.get("observations")
        check(isinstance(records,list) and bool(records),name+" location-specific observations required")
        if isinstance(records,list):
            for record in records:
                check(isinstance(record,dict),name+" observation must be an object")
                if isinstance(record,dict):
                    for field in fields: check(text(record.get(field)),name+" observation requires "+field)
                    evidence=record.get("visual_evidence","")
                    check(isinstance(evidence,str) and text(full) and full in evidence and isinstance(crops,list) and any(isinstance(x,str) and x in evidence for x in crops),name+" visual evidence must name full-page and close-up captures")
    return errors
