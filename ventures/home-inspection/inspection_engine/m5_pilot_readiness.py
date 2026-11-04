"""M5 V1: private professional pilot cohort design/readiness preflight.

This is PLANNING ONLY: declarations do not establish real consent, issuer
credentials, independent reviewers, original media, or model accuracy.
Never releases cases or claims a working inspection business.
"""
from __future__ import annotations
from collections import Counter

from .m4_frozen_safety_audit import _ident, _keys
from .serious_defect_benchmark import BenchmarkBlock, SYSTEMS

FIELDS = {"case_id", "property_group_id", "scope", "systems", "critical_labels", "total_defect_labels",
          "clean_media_controls", "reviewer_id", "adjudicator_id", "custodian_id",
          "consent_document_declared", "byte_preflight_declared", "synthetic"}
MAX_CASES = 2000


def assess_pilot_cohort_design(cases, *, training_property_groups):
    """Summarize documentary readiness, never approve real field activities.

    Cohort thresholds mirror V8/V9, not a new/watered-down accuracy standard.
    """
    if not isinstance(cases, list) or len(cases) > MAX_CASES:
        raise BenchmarkBlock("Bounded proposed pilot cases required")
    if (not isinstance(training_property_groups, list)
            or len(training_property_groups) > 20000):
        raise BenchmarkBlock("Training/tuning property-group exclusion list required")
    known_training = set()
    for group in training_property_groups:
        _ident(group, "training group")
        if group in known_training:
            raise BenchmarkBlock("Repeated training/tuning group")
        known_training.add(group)

    seen_ids = set()
    seen_groups = set()
    total_critical = 0
    clean_case_count = 0
    clean_media_count = 0
    systems = set()
    scopes = set()
    consent_declarations = 0
    byte_declarations = 0
    distinct_review = 0
    collisions = 0
    synthetic_count = 0
    for row in cases:
        _keys(row, FIELDS, "proposed M5 pilot case")
        cid = _ident(row["case_id"], "pilot case")
        group = _ident(row["property_group_id"], "pilot property group")
        if cid in seen_ids or group in seen_groups:
            raise BenchmarkBlock("Repeated case or property family in holdout design")
        seen_ids.add(cid)
        seen_groups.add(group)
        if group in known_training:
            collisions += 1
        if row["scope"] not in ("residential", "commercial"):
            raise BenchmarkBlock("Unsupported pilot scope")
        scopes.add(row["scope"])
        subjects = row["systems"]
        if (not isinstance(subjects, list) or not subjects
                or any(not isinstance(s, str) for s in subjects)
                or len(subjects) != len(set(subjects))
                or not set(subjects) <= SYSTEMS):
            raise BenchmarkBlock("Invalid or duplicated inspection system coverage")
        systems.update(subjects)
        severe = row["critical_labels"]
        total = row["total_defect_labels"]
        clean = row["clean_media_controls"]
        if (type(severe) is not int or type(total) is not int
                or not 0 <= severe <= total <= 1000
                or type(clean) is not int or not 0 <= clean <= 1000):
            raise BenchmarkBlock("Invalid bounded defect-label/control counts")
        total_critical += severe
        clean_media_count += clean
        # A clean photo in an otherwise defective property is NOT a clean case.
        if total == 0 and clean > 0:
            clean_case_count += 1
        for field in ("reviewer_id", "adjudicator_id", "custodian_id"):
            _ident(row[field], field)
        if len({row["reviewer_id"], row["adjudicator_id"],
                row["custodian_id"]}) == 3:
            distinct_review += 1
        for field in ("consent_document_declared", "byte_preflight_declared", "synthetic"):
            if type(row[field]) is not bool:
                raise BenchmarkBlock("Pilot declaration must be boolean: " + field)
        consent_declarations += row["consent_document_declared"]
        byte_declarations += row["byte_preflight_declared"]
        synthetic_count += row["synthetic"]
    cohort = len(cases)
    size_met = cohort >= 100
    critical_met = total_critical >= 30
    systems_met = systems == SYSTEMS
    scopes_met = scopes == {"residential", "commercial"}
    clean_met = clean_case_count >= 10 and clean_media_count >= 10 and (
        cohort > 0 and clean_case_count * 10 >= cohort)
    independent_roles_declared = cohort > 0 and distinct_review == cohort
    consistency_met = (collisions == 0 and independent_roles_declared
                       and consent_declarations == cohort
                       and byte_declarations == cohort)
    # No field signatures, actual media, credentials or model inference is
    # authenticated here; the booleans above are statements, not evidence.
    return {
        "schema_version": 1,
        "status": "M5_DOCUMENTARY_COHORT_DESIGN_ONLY_REAL_PILOT_NOT_AUTHORIZED",
        "planned_cases": cohort,
        "planned_critical_labels": total_critical,
        "planned_clean_control_cases": clean_case_count,
        "planned_clean_source_controls": clean_media_count,
        "planned_system_coverage": len(systems),
        "planned_scopes": sorted(scopes),
        "training_property_group_collisions": collisions,
        "distinct_review_roles_declared_cases": distinct_review,
        "consent_document_declared_cases": consent_declarations,
        "source_byte_preflight_declared_cases": byte_declarations,
        "synthetic_or_example_cases": synthetic_count,
        "cohort_size_design_met": size_met,
        "critical_label_design_met": critical_met,
        "thirteen_system_design_met": systems_met,
        "residential_commercial_design_met": scopes_met,
        "clean_controls_design_met": clean_met,
        "documentary_consistency_met": consistency_met,
        "all_cohort_design_checks_met_only": all((
            size_met, critical_met, systems_met, scopes_met,
            clean_met, consistency_met)),
        "real_consent_and_issuer_identity_authenticated": False,
        "model_serious_defect_accuracy_verified": False,
        "independent_holdout_custody_authenticated": False,
        "qualified_human_report_signoff_verified": False,
        "field_pilot_authorized": False,
        "customer_release_allowed": False,
    }
