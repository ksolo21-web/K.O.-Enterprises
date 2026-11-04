"""M5 V6 regression: deterministic synthetic benchmark *contract*, NOT AI accuracy.

Exercises the existing serious-defect scoring and pilot cohort logic against
non-real, human-review-declared test fixtures. It deliberately declares
synthetic case fields required by the production scorer, but never sends the
fixtures to a production service or treats declarations as authentic evidence.
"""
from __future__ import annotations

import hashlib
import json

from inspection_engine.serious_defect_benchmark import (
    METRIC_REVIEW_PENDING, SYSTEMS, score_serious_defects,
)
from inspection_engine.m5_pilot_readiness import assess_pilot_cohort_design

# Independent static expected values guard these gates against quiet drift.
SYSTEM_ORDER = tuple(sorted(SYSTEMS))
MIN_CASES = 100
MIN_CRITICAL = 30
MIN_PRECISION = 0.95
EXPECTED_LABELS = 90
MIN_CLEAN_CASES = 10
MIN_CLEAN_MEDIA = 10

class ContractBlock(ValueError):
    pass


def fixture():
    """100 unique invented properties; first 90 have one invented defect each."""
    cases, predictions, cohort = [], [], []
    for i in range(MIN_CASES):
        cid = "synthetic-contract-case-%03d" % i
        system = SYSTEM_ORDER[i % len(SYSTEM_ORDER)]
        severity = "critical" if i < 30 else "major" if i < 60 else "moderate"
        has_defect = i < EXPECTED_LABELS
        labels = ([{"label_id": "invented-label-001",
                    "status": "adjudicated", "severity": severity,
                    "system": system}] if has_defect else [])
        cases.append({
            "case_id": cid,
            "evidence_sha256": hashlib.sha256(
                ("NOT-A-REAL-PROPERTY-" + cid).encode()).hexdigest(),
            "synthetic": False,  # Schema-compatible DECLARATION, NEVER real provenance.
            "consented_for_evaluation": True,  # Also fictitious; not authenticated.
            "partition": "locked_holdout", "training_overlap": False,
            "qualified_labeler_id": "UNVERIFIED-FIXTURE-LABELER-%03d" % i,
            "independent_adjudicator_id": "UNVERIFIED-FIXTURE-REVIEWER-%03d" % i,
            "jurisdiction": "MI", "scope": "residential" if i % 2 == 0 else "commercial",
            "labels": labels,
        })
        if has_defect:
            predictions.append({
                "case_id": cid, "prediction_id": "invented-prediction-001",
                "system": system, "matched_label_id": "invented-label-001",
                "human_match_verified": True,  # Intentional synthetic simulation.
            })
        cohort.append({
            "case_id": cid, "property_group_id": "synthetic-test-family-%03d" % i,
            "scope": cases[-1]["scope"], "systems": [system],
            "critical_labels": 1 if i < MIN_CRITICAL else 0,
            "total_defect_labels": 1 if has_defect else 0,
            "clean_media_controls": 0 if has_defect else 1,
            "reviewer_id": "DECLARED-A-%03d" % i,
            "adjudicator_id": "DECLARED-B-%03d" % i,
            "custodian_id": "DECLARED-C-%03d" % i,
            "consent_document_declared": True,
            "byte_preflight_declared": True,
            "synthetic": True,
        })
    return cases, predictions, cohort


def false_positive(case: dict, n: int) -> dict:
    return {
        "case_id": case["case_id"], "prediction_id": "invented-false-alarm-%03d" % n,
        "system": SYSTEM_ORDER[n % len(SYSTEM_ORDER)],
        "matched_label_id": None, "human_match_verified": True,
    }


def assert_contract(actual: bool, description: str):
    if not actual:
        raise ContractBlock("Benchmark contract drift: " + description)


def run_matrix() -> dict:
    cases, base, cohort = fixture()
    baseline = score_serious_defects(cases, base)
    design = assess_pilot_cohort_design(cohort, training_property_groups=[])
    assert_contract(len(cases) == 100 and len(base) == 90, "fixed fixture counts")
    assert_contract(len(SYSTEMS) == 13 and len(SYSTEM_ORDER) == 13,
                    "all 13 required inspection systems")
    assert_contract(baseline["minimum_cohort_met"] is True,
                    "real-case-declaration minimum still evaluated")
    assert_contract(baseline["human_adjudicated_defects"] == EXPECTED_LABELS and
                    baseline["critical_defects"] == MIN_CRITICAL,
                    "expected invented defect totals")
    assert_contract(baseline["metric_thresholds_met"] is True and
                    baseline["status"] == METRIC_REVIEW_PENDING and
                    baseline["professional_credentials_externally_verified"] is False and
                    baseline["production_release_allowed"] is False,
                    "metric success must not become professional approval")
    assert_contract(set(baseline["per_system"]) == SYSTEMS and
                    baseline["human_verified_precision"] == 1.0,
                    "13-system coverage and baseline precision")
    assert_contract(design["all_cohort_design_checks_met_only"] is True and
                    design["planned_clean_control_cases"] == MIN_CLEAN_CASES and
                    design["planned_clean_source_controls"] == MIN_CLEAN_MEDIA and
                    design["planned_critical_labels"] == MIN_CRITICAL and
                    design["field_pilot_authorized"] is False and
                    design["customer_release_allowed"] is False,
                    "cohort controls must be design-only")

    scenarios = {}
    scenarios["all_declared_matches"] = baseline

    one_alarm = score_serious_defects(cases, base + [false_positive(cases[90], 0)])
    assert_contract(one_alarm["metric_thresholds_met"] is True and
                    0.95 < one_alarm["human_verified_precision"] < 1.0 and
                    one_alarm["production_release_allowed"] is False,
                    "one false alarm does not imply real-world approval")
    scenarios["one_false_alarm_above_precision_floor"] = one_alarm

    false_alarms = [false_positive(cases[90 + i], i) for i in range(5)]
    low_precision = score_serious_defects(cases, base + false_alarms)
    assert_contract(low_precision["metric_thresholds_met"] is False and
                    low_precision["status"] == "BLOCKED" and
                    len(low_precision["unmatched_or_unverified_predictions"]) == 5 and
                    low_precision["human_verified_precision"] < MIN_PRECISION,
                    "five false alarms must breach 95 percent precision")
    scenarios["five_false_alarms"] = low_precision

    missing_critical = score_serious_defects(cases, base[1:])
    assert_contract(missing_critical["metric_thresholds_met"] is False and
                    len(missing_critical["critical_misses"]) == 1 and
                    missing_critical["critical_misses"][0]["severity"] == "critical",
                    "one missed critical finding must block")
    scenarios["one_missing_critical"] = missing_critical

    missing_major = score_serious_defects(
        cases, [p for p in base if p["case_id"] != cases[30]["case_id"]])
    assert_contract(missing_major["metric_thresholds_met"] is False and
                    len(missing_major["major_misses"]) == 1,
                    "one missed major finding must block")
    scenarios["one_missing_major"] = missing_major

    under_size = score_serious_defects(cases[:-1], base)
    assert_contract(under_size["metric_thresholds_met"] is False and
                    under_size["minimum_cohort_met"] is False,
                    "99 cases must not satisfy 100-case minimum")
    scenarios["ninety_nine_cases"] = under_size

    # Preserve a distinction: missing moderate defects is reported, but the
    # strict *zero-major/critical* criterion alone does not make it an automatic
    # metric failure. Human review remains indispensable in all scenarios.
    missing_moderate = score_serious_defects(
        cases, [p for p in base if p["case_id"] != cases[60]["case_id"]])
    assert_contract(missing_moderate["metric_thresholds_met"] is True and
                    any(x["severity"] == "moderate"
                        for x in missing_moderate["all_misses"]) and
                    missing_moderate["production_release_allowed"] is False,
                    "moderate misses must remain visible and not release")
    scenarios["missing_moderate_is_reported"] = missing_moderate

    no_clean = [dict(row) for row in cohort]
    no_clean[90]["clean_media_controls"] = 0
    revised = assess_pilot_cohort_design(no_clean, training_property_groups=[])
    assert_contract(revised["planned_clean_control_cases"] == 9 and
                    revised["clean_controls_design_met"] is False and
                    revised["all_cohort_design_checks_met_only"] is False and
                    revised["field_pilot_authorized"] is False,
                    "nine clean cases must not meet ten clean control cases")
    scenarios["nine_clean_controls"] = revised

    overlapping = assess_pilot_cohort_design(
        cohort, training_property_groups=[cohort[0]["property_group_id"]])
    assert_contract(overlapping["training_property_group_collisions"] == 1 and
                    overlapping["all_cohort_design_checks_met_only"] is False and
                    overlapping["field_pilot_authorized"] is False,
                    "training-family collision must block")
    scenarios["training_family_overlap"] = overlapping

    summary = {
        "schema_version": 1,
        "status": "NINE_SYNTHETIC_SOFTWARE_BENCHMARK_CONTRACTS_ONLY",
        "scenario_names": list(scenarios),
        "synthetic_scenarios_checked": len(scenarios),
        "invented_cases": len(cases),
        "invented_defect_labels": EXPECTED_LABELS,
        "invented_critical_labels": MIN_CRITICAL,
        "invented_clean_control_cases": MIN_CLEAN_CASES,
        "systems_covered": len(SYSTEMS),
        "scopes": ["commercial", "residential"],
        "source_media_authenticated": False,
        "professional_labeling_or_consent_authenticated": False,
        "model_inference_run": False,
        "actual_accuracy_verified": False,
        "human_release_authorized": False,
        "customer_release_allowed": False,
    }
    return summary


def main():
    try:
        result = run_matrix()
    except (ContractBlock, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status":"SYNTHETIC_BENCHMARK_CONTRACT_BLOCKED",
                          "reason":str(exc),"customer_release_allowed":False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
